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
PACKET_STRUCT_FMT = f'<2s{SAMPLES_PER_PACKET * 4}f' 
PACKET_SIZE = struct.calcsize(PACKET_STRUCT_FMT)
PROFILE_FILE = "profiles_adv.json"

# --- STYLING ---
STYLESHEET = """
QMainWindow { background-color: #1e1e1e; }
QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
QFrame#Panel { background-color: #252526; border-radius: 8px; border: 1px solid #3e3e42; }
QLabel#Heading { font-size: 16px; font-weight: bold; color: #ffffff; padding: 5px; }

/* Status Labels */
QLabel#StatValue { font-size: 24px; font-weight: bold; color: #fff; }
QLabel#StatLabel { font-size: 11px; color: #aaa; text-transform: uppercase; }

/* Buttons */
QPushButton { background-color: #3e3e42; border: none; border-radius: 4px; padding: 8px; color: white; font-weight: bold; }
QPushButton:pressed { background-color: #007acc; }
QPushButton:disabled { background-color: #2d2d30; color: #555; }

/* Specific Buttons */
QPushButton#BtnPower { background-color: #c0392b; font-size: 18px; border-radius: 8px; }
QPushButton#BtnPower:checked { background-color: #27ae60; } /* Green when ON */

QPushButton#BtnFlush { background-color: #e67e22; }
QPushButton#BtnSteam { background-color: #95a5a6; }
QPushButton#BtnSteam:checked { background-color: #c0392b; }
QPushButton#BtnRun { background-color: #2ecc71; }
QPushButton#BtnRun:checked { background-color: #e74c3c; }

/* Table */
QTableView { background-color: #1e1e1e; gridline-color: #3e3e42; selection-background-color: #007acc; }
QHeaderView::section { background-color: #252526; padding: 4px; border: 1px solid #3e3e42; color: #aaa; }
"""

# --- 1. MOCK HARDWARE (With Power State) ---
class MockEspressoMachine:
    def __init__(self):
        self.powered = False  # Start UNPOWERED
        
        self.pressure = 0.0
        self.flow = 0.0
        self.temp_water = 20.0 # Room temp
        self.temp_group = 20.0
        
        # Targets
        self.target_val = 0.0
        self.control_mode = 'P'
        self.target_temp_water = 20.0 # Default to room temp
        self.target_temp_group = 20.0
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
        
        # Always allow Power commands
        if cmd == "POWER_ON":
            self.powered = True
            self.target_temp_water = 93.0 # Default setpoint
            self.target_temp_group = 93.0
            print("HW: Power ON")
            return
        elif cmd == "POWER_OFF":
            self.powered = False
            self.target_temp_water = 20.0 # Cool down
            self.target_temp_group = 20.0
            self.target_val = 0.0 # Stop pump
            print("HW: Power OFF")
            return

        # Ignore other commands if powered off
        if not self.powered:
            return

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
            self.target_temp_water = 140.0
        elif cmd == "STEAM_OFF":
            self.steam_mode = False
            self.target_temp_water = 93.0
        elif cmd == "STOP":
            self.target_val = 0.0

    def _physics_step(self, dt):
        # Thermal Logic
        # If powered, heat to target. If not, cool to 20C.
        tgt_w = self.target_temp_water if self.powered else 20.0
        tgt_g = self.target_temp_group if self.powered else 20.0
        
        if self.temp_water < tgt_w: self.temp_water += 2.0 * dt
        else: self.temp_water -= 0.5 * dt # Cool down
        
        if self.temp_group < tgt_g: self.temp_group += 0.5 * dt
        else: self.temp_group -= 0.1 * dt

        # Pump Logic
        if self.powered:
            puck_res = 1.5 
            cur = self.pressure if self.control_mode == 'P' else self.flow
            err = self.target_val - cur
            self.pump_duty += err * 5.0 * dt
            self.pump_duty = max(0.0, min(12.0, self.pump_duty))
            self.pressure = self.pump_duty
            self.flow = (self.pressure / puck_res) + random.uniform(-0.1, 0.1)
        else:
            # Depressurize immediately if power cut
            self.pressure *= 0.9
            self.flow = 0.0
            self.pump_duty = 0.0
            
        if self.flow < 0: self.flow = 0
        self.pressure += random.uniform(-0.05, 0.05)

# --- 2. WORKER (Standard) ---
class SerialWorker(QThread):
    data_available = pyqtSignal(np.ndarray) 
    def __init__(self):
        super().__init__()
        self.running = True
        self.connection = MockEspressoMachine() 

    def send_command(self, cmd_str):
        self.connection.write(cmd_str.encode('utf-8'))

    def run(self):
        while self.running:
            try:
                raw = self.connection.read(PACKET_SIZE)
                if len(raw) == PACKET_SIZE:
                    unpacked = struct.unpack(PACKET_STRUCT_FMT, raw)
                    if unpacked[0] == PACKET_HEADER:
                        chunk = np.array(unpacked[1:], dtype=np.float32).reshape(-1, 4)
                        self.data_available.emit(chunk)
            except: time.sleep(0.01)
    
    def stop(self): self.running = False; self.wait()

# --- 3. PROFILE MODEL (Standard) ---
class ProfileModel(QAbstractTableModel):
    def __init__(self, steps=None):
        super().__init__()
        self._data = steps or [[5.0, "F", 4.0, 93.0, 93.0], [25.0, "P", 9.0, 93.0, 93.0]]
        self._headers = ["Time", "Mode", "Val", "Tw", "Tg"]
    def rowCount(self, p=None): return len(self._data)
    def columnCount(self, p=None): return 5
    def data(self, index, role):
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return str(self._data[index.row()][index.column()])
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal: return self._headers[section]
    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            try:
                if index.column() == 1: self._data[index.row()][1] = str(value).upper().strip()
                else: self._data[index.row()][index.column()] = float(value)
                self.dataChanged.emit(index, index); return True
            except: return False
        return False
    def flags(self, index): return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
    def add_step(self):
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append([5.0, "P", 0.0, 93.0, 93.0])
        self.endInsertRows()
    def get_data(self): return self._data
    def set_data(self, data): self.beginResetModel(); self._data = data; self.endResetModel()

# --- 4. GUI ---
class EspressoPowerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PiEspresso Controller")
        self.resize(1200, 750)
        self.setStyleSheet(STYLESHEET)
        
        # State
        self.history = 30000 
        self.buf = {'p': np.zeros(self.history), 'f': np.zeros(self.history),
                    'tw': np.zeros(self.history), 'tg': np.zeros(self.history),
                    'tgt_val': np.zeros(self.history)}
        self.ptr = 0
        self.active_profile = None
        self.profile_start = 0
        self.is_powered = False # GUI State Logic
        
        self.init_ui()
        self.worker = SerialWorker()
        self.worker.data_available.connect(self.update_data)
        self.worker.start()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.logic_loop)
        self.timer.start(100)
        
        # Ensure startup state is synced
        self.set_power_state(False)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # === LEFT PANEL ===
        sidebar = QFrame()
        sidebar.setObjectName("Panel")
        sidebar.setFixedWidth(380)
        sl = QVBoxLayout(sidebar)
        
        # 1. POWER BUTTON (New)
        self.btn_power = QPushButton("STANDBY (OFF)")
        self.btn_power.setObjectName("BtnPower")
        self.btn_power.setCheckable(True)
        self.btn_power.setFixedHeight(60)
        self.btn_power.clicked.connect(self.toggle_power)
        sl.addWidget(self.btn_power)
        
        sl.addSpacing(10)
        sl.addWidget(QLabel("Manual Override", objectName="Heading"))
        
        # 2. Manual Controls
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
        
        # 3. Profile
        sl.addSpacing(20)
        sl.addWidget(QLabel("Profile Editor", objectName="Heading"))
        
        self.model = ProfileModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        sl.addWidget(self.table)
        
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
        
        layout.addWidget(sidebar)

        # === RIGHT PANEL ===
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0,0,0,0)
        
        # Stats
        stats = QFrame()
        stats.setObjectName("Panel")
        stats.setFixedHeight(80)
        sl_stats = QHBoxLayout(stats)
        self.lbl_p = self.mk_stat(sl_stats, "Pressure", "0.0")
        self.lbl_f = self.mk_stat(sl_stats, "Flow", "0.0")
        self.lbl_tw = self.mk_stat(sl_stats, "Water Temp", "--")
        self.lbl_tg = self.mk_stat(sl_stats, "Group Temp", "--")
        rl.addWidget(stats)
        
        # Plots
        self.glw = pg.GraphicsLayoutWidget() 
        self.glw.setBackground('#1e1e1e')
        rl.addWidget(self.glw)
        
        p1 = self.glw.addPlot(row=0, col=0, title="Hydraulics")
        p1.showGrid(x=True, y=True, alpha=0.3)
        self.c_p = p1.plot(pen=pg.mkPen('#2ecc71', width=2), name="Pressure")
        self.c_tgt = p1.plot(pen=pg.mkPen('#2ecc71', width=1, style=Qt.PenStyle.DashLine))
        self.c_f = p1.plot(pen=pg.mkPen('#3498db', width=2), name="Flow")
        
        p2 = self.glw.addPlot(row=1, col=0, title="Thermals")
        p2.setXLink(p1)
        p2.showGrid(x=True, y=True, alpha=0.3)
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

    # --- NEW: POWER LOGIC ---
    def toggle_power(self, checked):
        self.set_power_state(checked)

    def set_power_state(self, is_on):
        self.is_powered = is_on
        self.btn_power.setChecked(is_on)
        
        if is_on:
            # Enable UI
            self.btn_power.setText("SYSTEM ACTIVE")
            self.worker.send_command("POWER_ON")
            
            self.btn_flush.setEnabled(True)
            self.btn_steam.setEnabled(True)
            self.btn_run.setEnabled(True)
            self.table.setEnabled(True)
        else:
            # Disable UI (Safety Lockout)
            self.btn_power.setText("STANDBY (Click to Start)")
            self.worker.send_command("POWER_OFF")
            
            # Stop any active actions
            if self.btn_run.isChecked(): self.btn_run.click()
            if self.btn_flush.isChecked(): self.btn_flush.click()
            if self.btn_steam.isChecked(): self.btn_steam.click()

            self.btn_flush.setEnabled(False)
            self.btn_steam.setEnabled(False)
            self.btn_run.setEnabled(False)
            self.table.setEnabled(False)

    # --- STANDARD LOGIC ---
    def update_data(self, chunk):
        n = len(chunk)
        if self.ptr + n >= self.history: self.ptr = 0
        sl = slice(self.ptr, self.ptr + n)
        self.buf['p'][sl] = chunk[:, 0]; self.buf['f'][sl] = chunk[:, 1]
        self.buf['tw'][sl] = chunk[:, 2]; self.buf['tg'][sl] = chunk[:, 3]
        
        # Visual Helper: If powered off, target is 0
        tgt = self.worker.connection.target_val if self.is_powered else 0.0
        self.buf['tgt_val'][sl] = np.full(n, tgt)
        
        self.ptr += n
        limit = self.ptr
        self.c_p.setData(self.buf['p'][:limit], autoDownsample=True)
        self.c_f.setData(self.buf['f'][:limit], autoDownsample=True)
        self.c_tgt.setData(self.buf['tgt_val'][:limit], autoDownsample=True)
        self.c_tw.setData(self.buf['tw'][:limit], autoDownsample=True)
        self.c_tg.setData(self.buf['tg'][:limit], autoDownsample=True)
        
        last = chunk[-1]
        self.lbl_p.setText(f"{last[0]:.1f}")
        self.lbl_f.setText(f"{last[1]:.1f}")
        self.lbl_tw.setText(f"{last[2]:.1f}")
        self.lbl_tg.setText(f"{last[3]:.1f}")

    def logic_loop(self):
        if self.active_profile and self.is_powered:
            elapsed = time.time() - self.profile_start
            cum = 0
            found = False
            for step in self.active_profile:
                dur = float(step[0])
                if cum <= elapsed < (cum + dur):
                    self.worker.send_command(f"SET_{step[1]}:{step[2]}")
                    self.worker.send_command(f"SET_TW:{step[3]}")
                    self.worker.send_command(f"SET_TG:{step[4]}")
                    found = True; break
                cum += dur
            if not found: self.toggle_profile(False)

    def toggle_flush(self, checked):
        if checked: self.worker.send_command("SET_P:3.0"); self.btn_run.setEnabled(False)
        else: self.worker.send_command("STOP"); self.btn_run.setEnabled(True)

    def toggle_steam(self, checked):
        if checked: self.worker.send_command("STEAM_ON")
        else: self.worker.send_command("STEAM_OFF")

    def toggle_profile(self, checked):
        if checked:
            self.active_profile = self.model.get_data()
            self.profile_start = time.time()
            self.btn_run.setText("STOP PROFILE"); self.btn_flush.setEnabled(False)
        else:
            self.active_profile = None
            self.worker.send_command("STOP")
            self.btn_run.setText("RUN PROFILE"); self.btn_run.setChecked(False); self.btn_flush.setEnabled(True)

    def closeEvent(self, e): self.worker.stop(); e.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EspressoPowerGUI()
    window.show()
    sys.exit(app.exec())
