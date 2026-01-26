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
                             QComboBox, QStyledItemDelegate)
from PyQt6.QtGui import QColor, QFont
import pyqtgraph as pg

# --- CONFIGURATION ---
SAMPLES_PER_PACKET = 50   
PACKET_HEADER = b'ES'
# Structure: [Header 2s] [P, F, T_water, T_group] * 50
PACKET_STRUCT_FMT = f'<2s{SAMPLES_PER_PACKET * 4}f' 
PACKET_SIZE = struct.calcsize(PACKET_STRUCT_FMT)
PROFILE_FILE = "profiles_adv.json"

# --- STYLING ---
STYLESHEET = """
QMainWindow { background-color: #1e1e1e; }
QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
QFrame#Panel { background-color: #252526; border-radius: 8px; border: 1px solid #3e3e42; }
QLabel#Heading { font-size: 16px; font-weight: bold; color: #ffffff; padding: 5px; }
QLabel#StatValue { font-size: 24px; font-weight: bold; color: #fff; }
QLabel#StatLabel { font-size: 11px; color: #aaa; text-transform: uppercase; }

/* Buttons */
QPushButton { background-color: #3e3e42; border: none; border-radius: 4px; padding: 8px; color: white; font-weight: bold; }
QPushButton:pressed { background-color: #007acc; }
QPushButton#BtnFlush { background-color: #e67e22; }
QPushButton#BtnSteam { background-color: #95a5a6; }
QPushButton#BtnSteam:checked { background-color: #c0392b; } /* Red when STEAM is ON */
QPushButton#BtnRun { background-color: #2ecc71; }
QPushButton#BtnRun:checked { background-color: #e74c3c; }

/* Table */
QTableView { background-color: #1e1e1e; gridline-color: #3e3e42; selection-background-color: #007acc; }
QHeaderView::section { background-color: #252526; padding: 4px; border: 1px solid #3e3e42; color: #aaa; }
"""

# --- 1. MOCK HARDWARE (Dual Temp + Flow Control) ---
class MockEspressoMachine:
    def __init__(self):
        self.pressure = 0.0
        self.flow = 0.0
        self.temp_water = 90.0 
        self.temp_group = 85.0
        
        # Targets
        self.target_val = 0.0 # Can be Pressure OR Flow
        self.control_mode = 'P' # 'P' or 'F'
        self.target_temp_water = 93.0
        self.target_temp_group = 93.0
        self.steam_mode = False
        
        # Physics
        self.pump_duty = 0.0

    def read(self, size):
        time.sleep(SAMPLES_PER_PACKET / 1000.0) 
        data = []
        for _ in range(SAMPLES_PER_PACKET):
            self._physics_step(0.001)
            data.extend([self.pressure, self.flow, self.temp_water, self.temp_group])
        return struct.pack(PACKET_STRUCT_FMT, PACKET_HEADER, *data)

    def write(self, data):
        cmd = data.decode('utf-8').strip()
        if cmd.startswith("SET_P:"):
            self.control_mode = 'P'
            self.target_val = float(cmd.split(":")[1])
        elif cmd.startswith("SET_F:"):
            self.control_mode = 'F'
            self.target_val = float(cmd.split(":")[1])
        elif cmd.startswith("SET_TW:"):
            self.target_temp_water = float(cmd.split(":")[1])
        elif cmd.startswith("SET_TG:"):
            self.target_temp_group = float(cmd.split(":")[1])
        elif cmd == "STEAM_ON":
            self.steam_mode = True
            self.target_temp_water = 140.0 # Steam temp
        elif cmd == "STEAM_OFF":
            self.steam_mode = False
            self.target_temp_water = 93.0
        elif cmd == "STOP":
            self.target_val = 0.0
            self.control_mode = 'P'

    def _physics_step(self, dt):
        # 1. Thermal Logic (Water vs Group)
        # Water heats fast, Group heats slow (thermal mass)
        if self.temp_water < self.target_temp_water: self.temp_water += 2.0 * dt
        else: self.temp_water -= 0.5 * dt
        
        if self.temp_group < self.target_temp_group: self.temp_group += 0.5 * dt
        else: self.temp_group -= 0.1 * dt

        # 2. Hydraulic Logic (Pressure vs Flow Control)
        # We simulate a pump curve where Flow = PumpDuty - Resistance
        puck_resistance = 1.5 # Arbitrary resistance unit
        
        # Simple PID-ish behavior for the pump
        current_val = self.pressure if self.control_mode == 'P' else self.flow
        error = self.target_val - current_val
        
        self.pump_duty += error * 5.0 * dt
        self.pump_duty = max(0.0, min(12.0, self.pump_duty)) # Clamp 0-12 bar equivalent
        
        # Resulting Physics
        self.pressure = self.pump_duty
        # Flow depends on Pressure vs Resistance
        self.flow = (self.pressure / puck_resistance) + random.uniform(-0.1, 0.1)
        if self.flow < 0: self.flow = 0
        
        # Noise
        self.pressure += random.uniform(-0.05, 0.05)

# --- 2. WORKER THREAD ---
class SerialWorker(QThread):
    data_available = pyqtSignal(np.ndarray) 
    def __init__(self):
        super().__init__()
        self.running = True
        self.connection = MockEspressoMachine() # Directly using mock for now

    def send_command(self, cmd_str):
        self.connection.write(cmd_str.encode('utf-8'))

    def run(self):
        while self.running:
            try:
                raw = self.connection.read(PACKET_SIZE)
                if len(raw) == PACKET_SIZE:
                    unpacked = struct.unpack(PACKET_STRUCT_FMT, raw)
                    if unpacked[0] == PACKET_HEADER:
                        # Reshape: [P, F, Tw, Tg]
                        chunk = np.array(unpacked[1:], dtype=np.float32).reshape(-1, 4)
                        self.data_available.emit(chunk)
            except: time.sleep(0.01)

    def stop(self):
        self.running = False; self.wait()

# --- 3. ADVANCED PROFILE MODEL ---
class ProfileModel(QAbstractTableModel):
    def __init__(self, steps=None):
        super().__init__()
        # Data: [Duration, Mode(P/F), Value, TempWater, TempGroup]
        self._data = steps or [[5.0, "F", 4.0, 93.0, 93.0], [25.0, "P", 9.0, 93.0, 93.0]]
        self._headers = ["Time(s)", "Mode", "Value", "T_Water", "T_Group"]

    def rowCount(self, p=None): return len(self._data)
    def columnCount(self, p=None): return 5
    def data(self, index, role):
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return str(self._data[index.row()][index.column()])
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            row, col = index.row(), index.column()
            try:
                if col == 1: # Mode Column
                    val = str(value).upper().strip()
                    if val in ['P', 'F']: self._data[row][col] = val
                else:
                    self._data[row][col] = float(value)
                self.dataChanged.emit(index, index)
                return True
            except: return False
        return False
    def flags(self, index): return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
    def add_step(self):
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append([5.0, "P", 0.0, 93.0, 93.0])
        self.endInsertRows()
    def get_data(self): return self._data
    def set_data(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

# --- 4. MAIN GUI ---
class EspressoFinalGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PiEspresso Dual-Zone")
        self.resize(1200, 750)
        self.setStyleSheet(STYLESHEET)
        
        # State
        self.history = 30000 
        self.buf = {
            'p': np.zeros(self.history), 'f': np.zeros(self.history),
            'tw': np.zeros(self.history), 'tg': np.zeros(self.history),
            'tgt_val': np.zeros(self.history) # Target P or F
        }
        self.ptr = 0
        self.active_profile = None
        self.profile_start = 0
        self.tgt_mode = 'P' # Current manual/profile mode
        
        self.init_ui()
        self.worker = SerialWorker()
        self.worker.data_available.connect(self.update_data)
        self.worker.start()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.logic_loop)
        self.timer.start(100)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # === LEFT PANEL: CONTROLS ===
        sidebar = QFrame()
        sidebar.setObjectName("Panel")
        sidebar.setFixedWidth(380)
        sl = QVBoxLayout(sidebar)
        
        # 1. Manual Controls
        sl.addWidget(QLabel("Manual Override", objectName="Heading"))
        
        row_man = QHBoxLayout()
        self.btn_flush = QPushButton("FLUSH")
        self.btn_flush.setObjectName("BtnFlush")
        self.btn_flush.setCheckable(True)
        self.btn_flush.clicked.connect(self.toggle_flush)
        
        self.btn_steam = QPushButton("STEAM")
        self.btn_steam.setObjectName("BtnSteam")
        self.btn_steam.setCheckable(True)
        self.btn_steam.clicked.connect(self.toggle_steam)
        
        row_man.addWidget(self.btn_flush)
        row_man.addWidget(self.btn_steam)
        sl.addLayout(row_man)
        
        # 2. Profile Editor
        sl.addSpacing(20)
        sl.addWidget(QLabel("Profile Editor", objectName="Heading"))
        
        self.model = ProfileModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        sl.addWidget(self.table)
        
        # Buttons
        row_edit = QHBoxLayout()
        btn_add = QPushButton("+ Step")
        btn_add.clicked.connect(self.model.add_step)
        
        self.btn_run = QPushButton("RUN PROFILE")
        self.btn_run.setObjectName("BtnRun")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setCheckable(True)
        self.btn_run.clicked.connect(self.toggle_profile)
        
        row_edit.addWidget(btn_add)
        row_edit.addWidget(self.btn_run)
        sl.addLayout(row_edit)
        
        # 3. Profile Load/Save (Simplified for brevity)
        row_file = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_profile)
        btn_load = QPushButton("Load")
        btn_load.clicked.connect(self.load_profile)
        row_file.addWidget(btn_save)
        row_file.addWidget(btn_load)
        sl.addLayout(row_file)

        layout.addWidget(sidebar)

        # === RIGHT PANEL: PLOTS ===
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0,0,0,0)
        
        # Stats Bar
        stats = QFrame()
        stats.setObjectName("Panel")
        stats.setFixedHeight(80)
        sl_stats = QHBoxLayout(stats)
        self.lbl_p = self.mk_stat(sl_stats, "Pressure", "0.0 Bar")
        self.lbl_f = self.mk_stat(sl_stats, "Flow", "0.0 ml/s")
        self.lbl_tw = self.mk_stat(sl_stats, "Water Temp", "93.0 C")
        self.lbl_tg = self.mk_stat(sl_stats, "Group Temp", "85.0 C")
        rl.addWidget(stats)
        
        # Plots
        self.glw = pg.GraphicsLayoutWidget() 
        self.glw.setBackground('#1e1e1e')
        rl.addWidget(self.glw)
        
        # Plot 1: Pressure & Flow
        p1 = self.glw.addPlot(row=0, col=0, title="Hydraulics")
        p1.showGrid(x=True, y=True, alpha=0.3)
        p1.setLabel('left', 'Pressure (Bar)')
        p1.addLegend()
        self.c_p = p1.plot(pen=pg.mkPen('#2ecc71', width=2), name="Pressure")
        self.c_tgt = p1.plot(pen=pg.mkPen('#2ecc71', width=1, style=Qt.PenStyle.DashLine), name="Target")
        
        # Secondary Axis for Flow? Or just overlay scaled? 
        # For simplicity, we plot Flow on same graph but in Blue
        self.c_f = p1.plot(pen=pg.mkPen('#3498db', width=2), name="Flow")
        
        # Plot 2: Temperatures
        p2 = self.glw.addPlot(row=1, col=0, title="Thermals")
        p2.setXLink(p1)
        p2.showGrid(x=True, y=True, alpha=0.3)
        p2.addLegend()
        self.c_tw = p2.plot(pen=pg.mkPen('#e74c3c', width=2), name="Water")
        self.c_tg = p2.plot(pen=pg.mkPen('#f39c12', width=2), name="Group")

        layout.addWidget(right)

    def mk_stat(self, layout, title, val):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(0); l.setContentsMargins(0,0,0,0)
        lbl_v = QLabel(val); lbl_v.setObjectName("StatValue"); lbl_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_t = QLabel(title); lbl_t.setObjectName("StatLabel"); lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(lbl_v); l.addWidget(lbl_t)
        layout.addWidget(w)
        return lbl_v

    # --- LOGIC ---
    def update_data(self, chunk):
        # Chunk: [Pressure, Flow, WaterTemp, GroupTemp]
        n = len(chunk)
        if self.ptr + n >= self.history: self.ptr = 0 # Simple reset
        
        sl = slice(self.ptr, self.ptr + n)
        self.buf['p'][sl] = chunk[:, 0]
        self.buf['f'][sl] = chunk[:, 1]
        self.buf['tw'][sl] = chunk[:, 2]
        self.buf['tg'][sl] = chunk[:, 3]
        
        # Update Target Plot (Holds last known target)
        self.buf['tgt_val'][sl] = np.full(n, self.worker.connection.target_val)
        
        self.ptr += n
        
        # Refresh Plots (Downsampled)
        limit = self.ptr
        self.c_p.setData(self.buf['p'][:limit], autoDownsample=True)
        self.c_f.setData(self.buf['f'][:limit], autoDownsample=True)
        self.c_tgt.setData(self.buf['tgt_val'][:limit], autoDownsample=True)
        
        self.c_tw.setData(self.buf['tw'][:limit], autoDownsample=True)
        self.c_tg.setData(self.buf['tg'][:limit], autoDownsample=True)
        
        # Update Text
        last = chunk[-1]
        self.lbl_p.setText(f"{last[0]:.1f}")
        self.lbl_f.setText(f"{last[1]:.1f}")
        self.lbl_tw.setText(f"{last[2]:.1f}")
        self.lbl_tg.setText(f"{last[3]:.1f}")

    def logic_loop(self):
        if self.active_profile:
            elapsed = time.time() - self.profile_start
            cum = 0
            found = False
            for step in self.active_profile:
                # Step: [Dur, Mode, Val, Tw, Tg]
                dur = float(step[0])
                if cum <= elapsed < (cum + dur):
                    # Found current step
                    mode = step[1]
                    val = float(step[2])
                    tw = float(step[3])
                    tg = float(step[4])
                    
                    # Send commands (Optimization: only send if changed in real app)
                    self.worker.send_command(f"SET_{mode}:{val}")
                    self.worker.send_command(f"SET_TW:{tw}")
                    self.worker.send_command(f"SET_TG:{tg}")
                    found = True
                    break
                cum += dur
            
            if not found: self.toggle_profile() # Done

    # --- CONTROLS ---
    def toggle_flush(self, checked):
        if checked:
            self.worker.send_command("SET_P:3.0") # Low pressure flush
            self.btn_run.setEnabled(False)
        else:
            self.worker.send_command("STOP")
            self.btn_run.setEnabled(True)

    def toggle_steam(self, checked):
        if checked:
            self.worker.send_command("STEAM_ON")
        else:
            self.worker.send_command("STEAM_OFF")

    def toggle_profile(self, checked):
        if checked:
            self.active_profile = self.model.get_data()
            self.profile_start = time.time()
            self.btn_run.setText("STOP PROFILE")
            self.btn_flush.setEnabled(False)
        else:
            self.active_profile = None
            self.worker.send_command("STOP")
            self.btn_run.setText("RUN PROFILE")
            self.btn_flush.setEnabled(True)

    def save_profile(self):
        name, ok = QInputDialog.getText(self, "Save", "Name:")
        if ok:
            data = self.model.get_data()
            try:
                with open(PROFILE_FILE, 'r') as f: db = json.load(f)
            except: db = {}
            db[name] = data
            with open(PROFILE_FILE, 'w') as f: json.dump(db, f)

    def load_profile(self):
        try:
            with open(PROFILE_FILE, 'r') as f: db = json.load(f)
            name, ok = QInputDialog.getItem(self, "Load", "Profile:", list(db.keys()), 0, False)
            if ok: self.model.set_data(db[name])
        except: pass

    def closeEvent(self, e):
        self.worker.stop()
        e.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EspressoFinalGUI()
    window.show()
    sys.exit(app.exec())
