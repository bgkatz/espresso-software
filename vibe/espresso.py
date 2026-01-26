import sys
import struct
import time
import random
import csv
import json
import collections
import numpy as np
from datetime import datetime

from PyQt6.QtCore import (QThread, pyqtSignal, QTimer, Qt, QAbstractTableModel, 
                          QModelIndex, QDateTime)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QTabWidget, QTableView, 
                             QHeaderView, QFileDialog, QGroupBox, QGridLayout, QMessageBox)
from PyQt6.QtGui import QAction
import pyqtgraph as pg

# --- CONFIGURATION & PROTOCOL ---
# Must match STM32 C code exactly
SAMPLES_PER_PACKET = 50   # 50ms worth of data per packet (at 1kHz)
PACKET_HEADER = b'ES'
# 2 bytes header + (50 samples * 12 bytes/sample)
PACKET_STRUCT_FMT = f'<2s{SAMPLES_PER_PACKET * 3}f' 
PACKET_SIZE = struct.calcsize(PACKET_STRUCT_FMT)

# --- 1. MOCK HARDWARE SIMULATOR ---
class MockEspressoMachine:
    """
    Simulates the STM32 Firmware. 
    Generates binary packets and reacts to commands.
    """
    def __init__(self):
        self.pressure = 0.0
        self.flow = 0.0
        self.temp = 20.0  # Room temp
        self.target_temp = 93.0
        self.target_pressure = 0.0
        self.pump_on = False
        self.valve_open = False
        
        # Physics state
        self.boiler_heat_rate = 0.5  # deg/sec
        self.pump_ramp_rate = 2.0    # bar/sec

    def read(self, size):
        """Simulates USB CDC read. Returns a binary packet of SAMPLES_PER_PACKET."""
        time.sleep(SAMPLES_PER_PACKET / 1000.0) # Simulate 1kHz accumulation time
        
        # Generate 'SAMPLES_PER_PACKET' data points
        data = []
        for _ in range(SAMPLES_PER_PACKET):
            self._update_physics_step(0.001) # 1ms step
            data.extend([self.pressure, self.flow, self.temp])
            
        # Pack into binary format: [Header, P, F, T, P, F, T...]
        return struct.pack(PACKET_STRUCT_FMT, PACKET_HEADER, *data)

    def write(self, data):
        """Simulates receiving a command from PC."""
        cmd_str = data.decode('utf-8').strip()
        print(f"[SIM HARDWARE] Received: {cmd_str}")
        
        if cmd_str.startswith("SET_P:"):
            self.target_pressure = float(cmd_str.split(":")[1])
            self.valve_open = True
        elif cmd_str == "STOP":
            self.target_pressure = 0.0
            self.valve_open = False
        elif cmd_str.startswith("SET_T:"):
            self.target_temp = float(cmd_str.split(":")[1])

    def _update_physics_step(self, dt):
        """Simple physics engine for realism."""
        # Temp Logic
        if self.temp < self.target_temp:
            self.temp += self.boiler_heat_rate * dt
        else:
            self.temp -= 0.1 * dt # Cool down
        
        # Pressure Logic (Laggy pump)
        if self.valve_open:
            if self.pressure < self.target_pressure:
                self.pressure += self.pump_ramp_rate * dt
            elif self.pressure > self.target_pressure:
                self.pressure -= self.pump_ramp_rate * dt
        else:
            self.pressure *= 0.95 # Bleed off pressure rapidly
            
        # Flow Logic (Roughly proportional to pressure for resistance)
        self.flow = self.pressure * 0.5 + random.uniform(-0.1, 0.1)
        # Add sensor noise
        self.pressure += random.uniform(-0.05, 0.05)
        self.temp += random.uniform(-0.02, 0.02)

# --- 2. BACKEND WORKER THREAD ---
class SerialWorker(QThread):
    data_available = pyqtSignal(np.ndarray) # Emits chunk of data (N, 3)
    
    def __init__(self, port_name=None):
        super().__init__()
        self.running = True
        self.port_name = port_name
        self.mock_mode = (port_name is None)
        self.connection = None
        self.log_file = None

    def send_command(self, cmd_str):
        """Thread-safe command sender"""
        if self.connection:
            try:
                self.connection.write(cmd_str.encode('utf-8'))
            except Exception as e:
                print(f"Serial Write Error: {e}")

    def run(self):
        # 1. Connect
        if self.mock_mode:
            self.connection = MockEspressoMachine()
        else:
            import serial
            try:
                self.connection = serial.Serial(self.port_name, 115200, timeout=1)
            except Exception as e:
                print(f"Failed to open serial: {e}")
                return

        # 2. Setup Logging
        filename = f"shot_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Pressure", "Flow", "Temp"])

        # 3. Loop
        print("Worker Thread Started. Listening for packets...")
        while self.running:
            try:
                # Read exact packet size
                raw_data = self.connection.read(PACKET_SIZE)
                
                if len(raw_data) == PACKET_SIZE:
                    # Unpack
                    unpacked = struct.unpack(PACKET_STRUCT_FMT, raw_data)
                    header = unpacked[0]
                    
                    if header == PACKET_HEADER:
                        # Convert tuple to numpy array (reshape to N x 3)
                        # unpacked[1:] contains the flats, length = SAMPLES * 3
                        chunk = np.array(unpacked[1:], dtype=np.float32).reshape(-1, 3)
                        
                        # Log to Disk (Append mode)
                        with open(filename, 'a', newline='') as f:
                            writer = csv.writer(f)
                            # Create timestamps for this chunk
                            now = time.time()
                            # Back-calculate timestamps for the burst
                            times = np.linspace(now - (SAMPLES_PER_PACKET*0.001), now, SAMPLES_PER_PACKET)
                            
                            # Combine time and data for CSV
                            rows = np.column_stack((times, chunk))
                            writer.writerows(rows)

                        # Send to GUI
                        self.data_available.emit(chunk)
                    else:
                        print("Sync Error: Bad Header")
            except Exception as e:
                print(f"Serial Loop Error: {e}")
                time.sleep(1)

    def stop(self):
        self.running = False
        self.wait()

# --- 3. PROFILE EDITOR MODEL ---
class StepModel(QAbstractTableModel):
    """Data Model for the Profile Editor Table"""
    def __init__(self, steps=None):
        super().__init__()
        # Steps: list of [Time(s), Pressure(bar), Temp(C)]
        self._data = steps or [[5.0, 2.0, 93.0], [25.0, 9.0, 93.0]]
        self._headers = ["Duration (s)", "Pressure (bar)", "Temp (C)"]

    def rowCount(self, parent=None): return len(self._data)
    def columnCount(self, parent=None): return 3
    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return str(self._data[index.row()][index.column()])
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            try:
                self._data[index.row()][index.column()] = float(value)
                self.dataChanged.emit(index, index)
                return True
            except ValueError: return False
        return False
    def flags(self, index): return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
    def add_step(self):
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append([5.0, 0.0, 93.0])
        self.endInsertRows()
    def get_profile_data(self): return self._data

# --- 4. MAIN GUI ---
class EspressoGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PiEspresso Controller")
        self.resize(1024, 600) # Typical 7" Touchscreen size
        
        # -- Data Buffers --
        self.history_len = 20000 # Keep last 20k points (20 seconds @ 1kHz)
        self.pressure_buffer = np.zeros(self.history_len)
        self.flow_buffer = np.zeros(self.history_len)
        self.ptr = 0
        
        # -- State --
        self.is_brewing = False
        self.profile_running = False
        self.profile_start_time = 0
        self.current_profile = []
        self.current_step_index = 0
        
        # -- UI Setup --
        self.setup_ui()
        
        # -- Threads --
        # Pass None to force Simulator Mode. Pass '/dev/ttyUSB0' for real hardware.
        self.worker = SerialWorker(port_name=None) 
        self.worker.data_available.connect(self.update_data)
        self.worker.start()
        
        # -- Profile Logic Timer --
        self.logic_timer = QTimer()
        self.logic_timer.timeout.connect(self.run_profile_logic)
        self.logic_timer.start(100) # Check logic every 100ms

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # === LEFT PANEL: CONTROLS ===
        left_panel = QTabWidget()
        left_panel.setFixedWidth(400)
        left_panel.setStyleSheet("QTabBar::tab { height: 50px; width: 150px; font-size: 18px; }")
        
        # Tab 1: Manual
        manual_tab = QWidget()
        m_layout = QVBoxLayout(manual_tab)
        
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("font-size: 24px; font-weight: bold; color: gray;")
        m_layout.addWidget(self.lbl_status)
        
        self.btn_brew = QPushButton("MANUAL BREW (9 Bar)")
        self.btn_brew.setFixedHeight(100)
        self.btn_brew.setStyleSheet("background-color: #2ecc71; color: white; font-size: 24px; border-radius: 10px;")
        self.btn_brew.clicked.connect(self.toggle_manual_brew)
        m_layout.addWidget(self.btn_brew)

        self.btn_stop = QPushButton("STOP ALL")
        self.btn_stop.setFixedHeight(80)
        self.btn_stop.setStyleSheet("background-color: #e74c3c; color: white; font-size: 24px; border-radius: 10px;")
        self.btn_stop.clicked.connect(self.stop_machine)
        m_layout.addWidget(self.btn_stop)
        
        # Tab 2: Profile Editor
        profile_tab = QWidget()
        p_layout = QVBoxLayout(profile_tab)
        
        self.step_model = StepModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.step_model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        p_layout.addWidget(self.table_view)
        
        btn_add_step = QPushButton("Add Step")
        btn_add_step.clicked.connect(self.step_model.add_step)
        p_layout.addWidget(btn_add_step)
        
        self.btn_run_profile = QPushButton("RUN PROFILE")
        self.btn_run_profile.setFixedHeight(60)
        self.btn_run_profile.setStyleSheet("background-color: #3498db; color: white; font-size: 20px;")
        self.btn_run_profile.clicked.connect(self.start_profile)
        p_layout.addWidget(self.btn_run_profile)

        left_panel.addTab(manual_tab, "Manual")
        left_panel.addTab(profile_tab, "Profile")
        layout.addWidget(left_panel)

        # === RIGHT PANEL: PLOT ===
        right_panel = QWidget()
        r_layout = QVBoxLayout(right_panel)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#121212')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Pressure (bar)')
        self.plot_widget.setLabel('bottom', 'Time (samples)')
        
        # CRITICAL OPTIMIZATION: Downsampling for thick lines
        self.curve_p = self.plot_widget.plot(pen=pg.mkPen('#ffaa00', width=3), name="Pressure")
        self.curve_p.setDownsampling(auto=True, method='peak')
        self.curve_p.setClipToView(True)
        
        self.curve_f = self.plot_widget.plot(pen=pg.mkPen('#00aaff', width=2), name="Flow")
        self.curve_f.setDownsampling(auto=True, method='peak')
        
        r_layout.addWidget(self.plot_widget)
        
        # Live Stats
        stats_layout = QHBoxLayout()
        self.val_p = QLabel("0.0 Bar")
        self.val_t = QLabel("93.0 C")
        for l in [self.val_p, self.val_t]:
            l.setStyleSheet("font-size: 30px; font-weight: bold; color: white; background: #333; padding: 10px; border-radius: 5px;")
            stats_layout.addWidget(l)
        r_layout.addLayout(stats_layout)
        
        layout.addWidget(right_panel)

    def update_data(self, chunk):
        """Receives new data chunk from Worker Thread (10-50 samples)"""
        num = len(chunk)
        p_data = chunk[:, 0]
        f_data = chunk[:, 1]
        t_last = chunk[-1, 2] # Latest temp
        p_last = chunk[-1, 0] # Latest pressure
        
        # Update Ring Buffers
        if self.ptr + num < self.history_len:
            self.pressure_buffer[self.ptr : self.ptr + num] = p_data
            self.flow_buffer[self.ptr : self.ptr + num] = f_data
            self.ptr += num
        else:
            # Roll buffer (naive implementation for simplicity)
            self.pressure_buffer = np.roll(self.pressure_buffer, -num)
            self.pressure_buffer[-num:] = p_data
            self.flow_buffer = np.roll(self.flow_buffer, -num)
            self.flow_buffer[-num:] = f_data
            self.ptr = self.history_len # Full
            
        # Update Plot (Only update visible portion)
        self.curve_p.setData(self.pressure_buffer[:self.ptr])
        self.curve_f.setData(self.flow_buffer[:self.ptr])
        
        # Update Text Labels
        self.val_p.setText(f"{p_last:.1f} Bar")
        self.val_t.setText(f"{t_last:.1f} °C")

    # --- CONTROL LOGIC ---
    def toggle_manual_brew(self):
        if not self.is_brewing:
            self.worker.send_command("SET_P:9.0")
            self.is_brewing = True
            self.btn_brew.setText("STOP BREW")
            self.btn_brew.setStyleSheet("background-color: #e74c3c; color: white; font-size: 24px;")
            self.lbl_status.setText("Manual Brewing...")
        else:
            self.stop_machine()

    def stop_machine(self):
        self.worker.send_command("STOP")
        self.is_brewing = False
        self.profile_running = False
        self.btn_brew.setText("MANUAL BREW (9 Bar)")
        self.btn_brew.setStyleSheet("background-color: #2ecc71; color: white; font-size: 24px;")
        self.lbl_status.setText("Stopped")

    def start_profile(self):
        self.current_profile = self.step_model.get_profile_data()
        self.profile_start_time = time.time()
        self.current_step_index = -1 # Will increment to 0 immediately
        self.profile_running = True
        self.lbl_status.setText("Running Profile...")

    def run_profile_logic(self):
        """Checks profile timeline and sends commands"""
        if not self.profile_running: return
        
        elapsed = time.time() - self.profile_start_time
        
        # Calculate which step we should be in
        cumulative_time = 0
        target_step = None
        
        for i, step in enumerate(self.current_profile):
            duration, pressure, temp = step
            if cumulative_time <= elapsed < (cumulative_time + duration):
                target_step = i
                break
            cumulative_time += duration
            
        if target_step is not None:
            # If we just entered a new step, send command
            if target_step != self.current_step_index:
                duration, pressure, temp = self.current_profile[target_step]
                print(f"Executing Profile Step {target_step}: {pressure} bar")
                self.worker.send_command(f"SET_P:{pressure}")
                self.worker.send_command(f"SET_T:{temp}")
                self.current_step_index = target_step
                self.lbl_status.setText(f"Profile Step {target_step+1}: {pressure} bar")
        else:
            # Profile finished
            if elapsed > cumulative_time:
                self.stop_machine()
                self.lbl_status.setText("Profile Complete")

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EspressoGUI()
    window.show()
    sys.exit(app.exec())
