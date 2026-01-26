import sys
import struct
import time
import random
import csv
import json
import os
import numpy as np
from datetime import datetime

from PyQt6.QtCore import (QThread, pyqtSignal, QTimer, Qt, QAbstractTableModel, 
                          QModelIndex)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QTableView, QHeaderView, 
                             QGridLayout, QFrame, QListWidget, QInputDialog, QMessageBox,
                             QSplitter)
from PyQt6.QtGui import QColor, QFont
import pyqtgraph as pg

# --- CONFIGURATION ---
SAMPLES_PER_PACKET = 50   
PACKET_HEADER = b'ES'
PACKET_STRUCT_FMT = f'<2s{SAMPLES_PER_PACKET * 3}f' 
PACKET_SIZE = struct.calcsize(PACKET_STRUCT_FMT)
PROFILE_FILE = "profiles.json"

# --- STYLING (The "Modern" Look) ---
STYLESHEET = """
QMainWindow { background-color: #1e1e1e; }
QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; font-size: 14px; }

/* Panels */
QFrame#Panel { 
    background-color: #252526; 
    border-radius: 10px; 
    border: 1px solid #3e3e42; 
}

/* Headings */
QLabel#Heading { 
    font-size: 18px; 
    font-weight: bold; 
    color: #ffffff; 
    padding: 5px; 
}

/* Live Stats */
QLabel#StatValue { font-size: 28px; font-weight: bold; color: #fff; }
QLabel#StatLabel { font-size: 12px; color: #aaa; text-transform: uppercase; }

/* Buttons */
QPushButton {
    background-color: #3e3e42;
    border: none;
    border-radius: 5px;
    padding: 10px;
    color: white;
    font-weight: bold;
}
QPushButton:pressed { background-color: #007acc; }

/* Specific Button Colors */
QPushButton#BtnBrew { background-color: #2ecc71; font-size: 16px; }
QPushButton#BtnBrew:checked { background-color: #e74c3c; } /* Red when STOP is active */
QPushButton#BtnProfile { background-color: #3498db; }
QPushButton#BtnSave { background-color: #9b59b6; }
QPushButton#BtnLoad { background-color: #f1c40f; color: black; }

/* Lists and Tables */
QListWidget, QTableView {
    background-color: #1e1e1e;
    border: 1px solid #3e3e42;
    gridline-color: #3e3e42;
    selection-background-color: #007acc;
}
QHeaderView::section {
    background-color: #252526;
    padding: 4px;
    border: 1px solid #3e3e42;
    color: #aaa;
}
"""

# --- 1. MOCK HARDWARE (Same as before) ---
class MockEspressoMachine:
    def __init__(self):
        self.pressure = 0.0
        self.flow = 0.0
        self.temp = 20.0 
        self.target_temp = 93.0
        self.target_pressure = 0.0
        self.valve_open = False
        
        # Physics constants
        self.boiler_heat_rate = 0.5
        self.pump_ramp_rate = 4.0 

    def read(self, size):
        time.sleep(SAMPLES_PER_PACKET / 1000.0) 
        data = []
        for _ in range(SAMPLES_PER_PACKET):
            self._update_physics_step(0.001)
            data.extend([self.pressure, self.flow, self.temp])
        return struct.pack(PACKET_STRUCT_FMT, PACKET_HEADER, *data)

    def write(self, data):
        cmd_str = data.decode('utf-8').strip()
        if cmd_str.startswith("SET_P:"):
            self.target_pressure = float(cmd_str.split(":")[1])
            self.valve_open = True
        elif cmd_str == "STOP":
            self.target_pressure = 0.0
            self.valve_open = False
        elif cmd_str.startswith("SET_T:"):
            self.target_temp = float(cmd_str.split(":")[1])

    def _update_physics_step(self, dt):
        # Temp Logic
        if self.temp < self.target_temp: self.temp += self.boiler_heat_rate * dt
        else: self.temp -= 0.1 * dt
        # Pressure Logic
        if self.valve_open:
            if self.pressure < self.target_pressure: self.pressure += self.pump_ramp_rate * dt
            elif self.pressure > self.target_pressure: self.pressure -= self.pump_ramp_rate * dt
        else: self.pressure *= 0.95
        # Flow Logic (Flow is high when pressure is low (filling), low when pressure is high (resistance))
        # This mocks a puck building resistance
        if self.pressure < 1.0: self.flow = 8.0 # Free flow
        else: self.flow = (12.0 - self.pressure) * 0.5 + random.uniform(-0.1, 0.1)
        if self.flow < 0: self.flow = 0
        
        self.pressure += random.uniform(-0.02, 0.02)
        self.temp += random.uniform(-0.02, 0.02)

# --- 2. WORKER THREAD ---
class SerialWorker(QThread):
    data_available = pyqtSignal(np.ndarray) 
    
    def __init__(self, port_name=None):
        super().__init__()
        self.running = True
        self.port_name = port_name
        self.connection = None

    def send_command(self, cmd_str):
        if self.connection:
            try: self.connection.write(cmd_str.encode('utf-8'))
            except: pass

    def run(self):
        if self.port_name:
            import serial
            self.connection = serial.Serial(self.port_name, 115200, timeout=1)
        else:
            self.connection = MockEspressoMachine()

        while self.running:
            try:
                raw_data = self.connection.read(PACKET_SIZE)
                if len(raw_data) == PACKET_SIZE:
                    unpacked = struct.unpack(PACKET_STRUCT_FMT, raw_data)
                    if unpacked[0] == PACKET_HEADER:
                        chunk = np.array(unpacked[1:], dtype=np.float32).reshape(-1, 3)
                        self.data_available.emit(chunk)
            except: time.sleep(0.1)

    def stop(self):
        self.running = False
        self.wait()

# --- 3. PROFILE TABLE MODEL ---
class StepModel(QAbstractTableModel):
    def __init__(self, steps=None):
        super().__init__()
        self._data = steps or [[5.0, 2.0, 93.0], [25.0, 9.0, 93.0]]
        self._headers = ["Time(s)", "Bar", "Temp(C)"]

    def rowCount(self, parent=None): return len(self._data)
    def columnCount(self, parent=None): return 3
    def data(self, index, role):
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
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
            except: return False
        return False
    def flags(self, index): return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
    def add_step(self):
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append([5.0, 0.0, 93.0])
        self.endInsertRows()
    def get_profile_data(self): return self._data
    def set_profile_data(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

# --- 4. MAIN MODERN GUI ---
class EspressoModernGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PiEspresso Modern")
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)
        
        # -- Data --
        self.history_len = 30000 
        self.buffers = {
            'pressure': np.zeros(self.history_len),
            'flow': np.zeros(self.history_len),
            'temp': np.zeros(self.history_len),
            'target_p': np.zeros(self.history_len), # Commanded P
            'target_t': np.zeros(self.history_len), # Commanded T
        }
        self.ptr = 0
        self.current_target_p = 0.0
        self.current_target_t = 93.0
        
        # -- Profile State --
        self.profiles = self.load_profiles_from_disk()
        self.active_profile = None
        self.profile_start_time = 0
        
        self.init_ui()
        
        # -- Workers --
        self.worker = SerialWorker(port_name=None)
        self.worker.data_available.connect(self.update_data)
        self.worker.start()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.run_logic_loop)
        self.timer.start(100)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # === LEFT SIDEBAR (Controls) ===
        sidebar = QFrame()
        sidebar.setObjectName("Panel")
        sidebar.setFixedWidth(350)
        sb_layout = QVBoxLayout(sidebar)
        
        # 1. Manual Controls Group
        lbl_man = QLabel("Manual Control")
        lbl_man.setObjectName("Heading")
        sb_layout.addWidget(lbl_man)
        
        self.btn_brew = QPushButton("START BREW")
        self.btn_brew.setObjectName("BtnBrew")
        self.btn_brew.setCheckable(True)
        self.btn_brew.setFixedHeight(80)
        self.btn_brew.clicked.connect(self.toggle_manual_brew)
        sb_layout.addWidget(self.btn_brew)
        
        # 2. Profile Management Group
        sb_layout.addSpacing(20)
        lbl_prof = QLabel("Profile Manager")
        lbl_prof.setObjectName("Heading")
        sb_layout.addWidget(lbl_prof)
        
        self.profile_list = QListWidget()
        self.profile_list.addItems(self.profiles.keys())
        self.profile_list.itemClicked.connect(self.load_selected_profile)
        sb_layout.addWidget(self.profile_list)
        
        # Profile Action Buttons
        row_btns = QHBoxLayout()
        btn_save = QPushButton("Save New")
        btn_save.setObjectName("BtnSave")
        btn_save.clicked.connect(self.save_profile_dialog)
        
        btn_del = QPushButton("Delete")
        btn_del.clicked.connect(self.delete_profile)
        
        row_btns.addWidget(btn_save)
        row_btns.addWidget(btn_del)
        sb_layout.addLayout(row_btns)
        
        # 3. Profile Editor (Mini Table)
        self.step_model = StepModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.step_model)
        self.table_view.verticalHeader().hide()
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        sb_layout.addWidget(self.table_view)
        
        btn_add_step = QPushButton("+ Add Step")
        btn_add_step.clicked.connect(self.step_model.add_step)
        sb_layout.addWidget(btn_add_step)
        
        self.btn_run_profile = QPushButton("RUN PROFILE")
        self.btn_run_profile.setObjectName("BtnProfile")
        self.btn_run_profile.setFixedHeight(60)
        self.btn_run_profile.clicked.connect(self.toggle_profile)
        sb_layout.addWidget(self.btn_run_profile)

        main_layout.addWidget(sidebar)

        # === RIGHT AREA (Plots & Stats) ===
        right_area = QWidget()
        ra_layout = QVBoxLayout(right_area)
        ra_layout.setContentsMargins(0,0,0,0)
        
        # 1. Top Bar (Live Stats)
        stats_panel = QFrame()
        stats_panel.setObjectName("Panel")
        stats_panel.setFixedHeight(80)
        sp_layout = QHBoxLayout(stats_panel)
        
        self.lbl_p = self.create_stat_widget(sp_layout, "Pressure", "0.0 bar")
        self.lbl_f = self.create_stat_widget(sp_layout, "Flow Rate", "0.0 ml/s")
        self.lbl_t = self.create_stat_widget(sp_layout, "Temperature", "93.0 °C")
        
        ra_layout.addWidget(stats_panel)

        # 2. Plots (Vertical Stack)
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.plot_layout.setBackground('#1e1e1e')
        ra_layout.addWidget(self.plot_layout)
        
        # Create 3 stacked plots
        self.p1 = self.plot_layout.addPlot(row=0, col=0, title="Pressure (Bar)")
        self.p2 = self.plot_layout.addPlot(row=1, col=0, title="Flow (ml/s)")
        self.p3 = self.plot_layout.addPlot(row=2, col=0, title="Temperature (°C)")
        
        # Link X Axes
        self.p2.setXLink(self.p1)
        self.p3.setXLink(self.p1)
        
        # Plot Styles
        common_style = {'color': '#aaa', 'font-size': '10pt'}
        for p in [self.p1, self.p2, self.p3]:
            p.showGrid(x=True, y=True, alpha=0.2)
            p.getAxis('left').setPen('#444')
            p.getAxis('bottom').setPen('#444')
        
        # Curves
        # Pressure: Green Solid (Actual), Green Dashed (Target)
        self.c_p_act = self.p1.plot(pen=pg.mkPen('#2ecc71', width=2))
        self.c_p_tgt = self.p1.plot(pen=pg.mkPen('#2ecc71', width=1, style=Qt.PenStyle.DashLine))
        
        # Flow: Blue Solid
        self.c_f_act = self.p2.plot(pen=pg.mkPen('#3498db', width=2))
        
        # Temp: Red Solid, Red Dashed
        self.c_t_act = self.p3.plot(pen=pg.mkPen('#e74c3c', width=2))
        self.c_t_tgt = self.p3.plot(pen=pg.mkPen('#e74c3c', width=1, style=Qt.PenStyle.DashLine))

        main_layout.addWidget(right_area)

    def create_stat_widget(self, layout, title, default):
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0,0,0,0)
        vbox.setSpacing(0)
        
        lbl_val = QLabel(default)
        lbl_val.setObjectName("StatValue")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("StatLabel")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        vbox.addWidget(lbl_val)
        vbox.addWidget(lbl_title)
        layout.addWidget(container)
        return lbl_val

    # --- LOGIC & DATA ---
    def update_data(self, chunk):
        num = len(chunk)
        # Unpack chunk
        p_act = chunk[:, 0]
        f_act = chunk[:, 1]
        t_act = chunk[:, 2]
        
        # Create arrays for "Target" values based on current state
        # (We assume target stayed constant during this 50ms chunk for simplicity)
        p_tgt = np.full(num, self.current_target_p)
        t_tgt = np.full(num, self.current_target_t)
        
        # Ring Buffer Update
        if self.ptr + num < self.history_len:
            sl = slice(self.ptr, self.ptr + num)
            self.buffers['pressure'][sl] = p_act
            self.buffers['flow'][sl] = f_act
            self.buffers['temp'][sl] = t_act
            self.buffers['target_p'][sl] = p_tgt
            self.buffers['target_t'][sl] = t_tgt
            self.ptr += num
        else:
            # Simple reset for demo (Production should roll)
            self.ptr = 0
            
        # Update Plots (Downsampled)
        # Use setDownsampling(auto=True) on all curves for performance
        limit = self.ptr
        self.c_p_act.setData(self.buffers['pressure'][:limit])
        self.c_p_tgt.setData(self.buffers['target_p'][:limit])
        
        self.c_f_act.setData(self.buffers['flow'][:limit])
        
        self.c_t_act.setData(self.buffers['temp'][:limit])
        self.c_t_tgt.setData(self.buffers['target_t'][:limit])
        
        # Update Stats
        self.lbl_p.setText(f"{p_act[-1]:.1f}")
        self.lbl_f.setText(f"{f_act[-1]:.1f}")
        self.lbl_t.setText(f"{t_act[-1]:.1f}")

    def run_logic_loop(self):
        # 1. Profile Logic
        if self.active_profile:
            elapsed = time.time() - self.profile_start_time
            
            # Find current step
            cum_time = 0
            found_step = False
            for step in self.active_profile:
                dur, pres, temp = step
                if cum_time <= elapsed < (cum_time + dur):
                    # We are in this step
                    if self.current_target_p != pres:
                        self.worker.send_command(f"SET_P:{pres}")
                        self.current_target_p = pres
                    if self.current_target_t != temp:
                        self.worker.send_command(f"SET_T:{temp}")
                        self.current_target_t = temp
                    found_step = True
                    break
                cum_time += dur
            
            if not found_step:
                # Profile Done
                self.toggle_profile() # Stop

    # --- ACTION HANDLERS ---
    def toggle_manual_brew(self, checked):
        if checked:
            self.worker.send_command("SET_P:9.0")
            self.current_target_p = 9.0
            self.btn_brew.setText("STOP")
            # Disable profile button
            self.btn_run_profile.setEnabled(False)
        else:
            self.worker.send_command("STOP")
            self.current_target_p = 0.0
            self.btn_brew.setText("START BREW")
            self.btn_run_profile.setEnabled(True)

    def toggle_profile(self):
        if self.active_profile is None:
            # Start Profile
            data = self.step_model.get_profile_data()
            if not data: return
            
            self.active_profile = data
            self.profile_start_time = time.time()
            self.btn_run_profile.setText("STOP PROFILE")
            self.btn_run_profile.setStyleSheet("background-color: #e74c3c")
            self.btn_brew.setEnabled(False)
        else:
            # Stop Profile
            self.active_profile = None
            self.worker.send_command("STOP")
            self.current_target_p = 0.0
            self.btn_run_profile.setText("RUN PROFILE")
            self.btn_run_profile.setStyleSheet("background-color: #3498db")
            self.btn_brew.setEnabled(True)

    # --- PROFILE MANAGEMENT ---
    def load_profiles_from_disk(self):
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE, 'r') as f:
                    return json.load(f)
            except: pass
        # Defaults
        return {
            "Turbo Shot": [[2.0, 3.0, 93.0], [15.0, 6.0, 93.0]],
            "Blooming": [[5.0, 2.0, 93.0], [25.0, 0.0, 93.0], [25.0, 9.0, 93.0]]
        }

    def save_profiles_to_disk(self):
        with open(PROFILE_FILE, 'w') as f:
            json.dump(self.profiles, f, indent=4)

    def load_selected_profile(self, item):
        name = item.text()
        if name in self.profiles:
            self.step_model.set_profile_data(self.profiles[name])

    def save_profile_dialog(self):
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile Name:")
        if ok and name:
            self.profiles[name] = self.step_model.get_profile_data()
            self.save_profiles_to_disk()
            self.profile_list.clear()
            self.profile_list.addItems(self.profiles.keys())

    def delete_profile(self):
        row = self.profile_list.currentRow()
        if row >= 0:
            name = self.profile_list.item(row).text()
            del self.profiles[name]
            self.save_profiles_to_disk()
            self.profile_list.takeItem(row)

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EspressoModernGUI()
    window.show()
    sys.exit(app.exec())
