import sys
import struct
import time
import random
import json
import os
import numpy as np
from PyQt6.QtCore import (QThread, pyqtSignal, QTimer, Qt, QAbstractTableModel, QModelIndex)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QTableView, QHeaderView, 
                             QFrame, QInputDialog, QMessageBox, QStyledItemDelegate, QComboBox, 
                             QAbstractItemView, QTabWidget, QListWidget)
import pyqtgraph as pg

# --- CONFIGURATION ---
SAMPLES_PER_PACKET = 10   
PACKET_HEADER = b'ES'
PACKET_STRUCT_FMT = f'<2s{SAMPLES_PER_PACKET * 5}f' 
PACKET_SIZE = struct.calcsize(PACKET_STRUCT_FMT)
PROFILE_FILE = "profiles.json"
MAX_BUFFER_SIZE = 600000 
ROLLING_WINDOW_SIZE = 30000 # 30 seconds @ 1kHz

# --- STYLING ---
STYLESHEET = """
QMainWindow { background-color: #1e1e1e; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
QLabel { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
QFrame#Panel { background-color: #252526; border-radius: 8px; border: 1px solid #3e3e42; }
QLabel#StatValue { font-size: 24px; font-weight: bold; color: #fff; }
QLabel#StatLabel { font-size: 11px; color: #aaa; text-transform: uppercase; }
QLabel#Header { font-size: 14px; font-weight: bold; color: #aaa; padding-top: 10px;}
QPushButton { background-color: #3e3e42; border-radius: 4px; padding: 8px; color: white; font-weight: bold; font-family: 'Segoe UI', sans-serif; }
QPushButton:pressed { background-color: #007acc; }
QPushButton:disabled { background-color: #2d2d30; color: #555; }
QPushButton#BtnRun { background-color: #2ecc71; }
QPushButton#BtnRun:checked { background-color: #e74c3c; } 
QPushButton#BtnTare { background-color: #8e44ad; font-size: 12px; padding: 4px; border-radius: 4px; } 
QPushButton#BtnFlush { background-color: #e67e22; }
QPushButton#BtnSteam { background-color: #95a5a6; }
QPushButton#BtnSteam:checked { background-color: #c0392b; }
QPushButton#BtnDel { background-color: #c0392b; } 
QTabWidget::pane { border: 1px solid #3e3e42; background: #252526; }
QTabBar::tab { background: #1e1e1e; color: #aaa; padding: 8px 20px; }
QTabBar::tab:selected { background: #3e3e42; color: white; font-weight: bold; }
QListWidget { background-color: #1e1e1e; border: 1px solid #3e3e42; color: white; font-family: 'Segoe UI'; }
QTableView { background-color: #1e1e1e; gridline-color: #3e3e42; selection-background-color: #007acc; color: #e0e0e0; }
QHeaderView::section { background-color: #252526; padding: 4px; border: 1px solid #3e3e42; color: #aaa; }
QTableView QLineEdit { background-color: #252526; color: white; border: none; }
QComboBox { background-color: #252526; color: white; border: 1px solid #555; }
QComboBox QAbstractItemView { background-color: #252526; color: white; selection-background-color: #007acc; }
QDialog { background-color: #252526; color: white; }
QDialog QLabel { color: #e0e0e0; }
QDialog QLineEdit { background-color: #3e3e42; color: white; border: 1px solid #555; padding: 4px; }
"""

# --- 1. MOCK HARDWARE ---
class MockEspressoMachine:
    def __init__(self):
        self.powered = False
        self.p = 0.0; self.f = 0.0; self.w = 0.0
        self.tw = 20.0; self.tg = 20.0
        self.tgt_val = 0.0; self.ctrl_mode = 'P'
        self.tgt_tw = 20.0; self.tgt_tg = 20.0
        self.steam = False; self.pump_duty = 0.0

    def read(self, size):
        time.sleep(SAMPLES_PER_PACKET / 1000.0) 
        data = []
        for _ in range(SAMPLES_PER_PACKET):
            self._step(0.001)
            data.extend([self.p, self.f, self.w, self.tw, self.tg])
        return struct.pack(PACKET_STRUCT_FMT, PACKET_HEADER, *data)

    def write(self, data):
        cmd = data.decode('utf-8').strip()
        if cmd == "POWER_ON": self.powered = True; self.tgt_tw = 93.0; self.tgt_tg = 93.0
        elif cmd == "POWER_OFF": self.powered = False; self.tgt_val = 0.0; self.tgt_tw = 20.0; self.steam = False
        elif cmd == "TARE": self.w = 0.0 
        elif self.powered:
            if cmd.startswith("SET_P:"): self.ctrl_mode = 'P'; self.tgt_val = float(cmd.split(":")[1])
            elif cmd.startswith("SET_F:"): self.ctrl_mode = 'F'; self.tgt_val = float(cmd.split(":")[1])
            elif cmd.startswith("SET_TW:"): self.tgt_tw = float(cmd.split(":")[1])
            elif cmd.startswith("SET_TG:"): self.tgt_tg = float(cmd.split(":")[1])
            elif cmd == "STEAM_ON": self.steam = True; self.tgt_tw = 140.0
            elif cmd == "STEAM_OFF": self.steam = False; self.tgt_tw = 93.0
            elif cmd == "STOP": self.tgt_val = 0.0

    def _step(self, dt):
        tgt_w = (140.0 if self.steam else self.tgt_tw) if self.powered else 20.0
        tgt_g = self.tgt_tg if self.powered else 20.0
        self.tw += (tgt_w - self.tw) * 0.5 * dt
        self.tg += (tgt_g - self.tg) * 0.1 * dt

        if self.powered:
            cur = self.p if self.ctrl_mode == 'P' else self.f
            self.pump_duty += (self.tgt_val - cur) * 5.0 * dt
            self.pump_duty = max(0.0, min(12.0, self.pump_duty))
            self.p = self.pump_duty
            self.f = (self.p / 1.5)
            self.w += self.f * dt 
        else:
            self.p *= 0.9; self.f = 0.0; self.pump_duty = 0.0

# --- 2. SERIAL WORKER ---
class SerialWorker(QThread):
    data_available = pyqtSignal(np.ndarray) 
    def __init__(self):
        super().__init__()
        self.running = True
        self.connection = MockEspressoMachine() 
        self.last_p = 0.0; self.last_f = 0.0; self.last_w = 0.0; self.last_tw = 0.0; self.last_tg = 0.0

    def send_command(self, cmd): self.connection.write(cmd.encode('utf-8'))
    def run(self):
        while self.running:
            try:
                raw = self.connection.read(PACKET_SIZE)
                if len(raw) == PACKET_SIZE:
                    unpacked = struct.unpack(PACKET_STRUCT_FMT, raw)
                    if unpacked[0] == PACKET_HEADER:
                        chunk = np.array(unpacked[1:], dtype=np.float32).reshape(-1, 5)
                        self.last_p = chunk[-1, 0]; self.last_f = chunk[-1, 1]; self.last_w = chunk[-1, 2]
                        self.last_tw = chunk[-1, 3]; self.last_tg = chunk[-1, 4]
                        self.data_available.emit(chunk)
            except: time.sleep(0.01)
    def stop(self): self.running = False; self.wait()

# --- 3. UI COMPONENTS ---
class SmartDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() == 0: 
            cb = QComboBox(parent); cb.addItems(["P", "F"]); return cb
        elif index.column() == 4: 
            cb = QComboBox(parent); cb.addItems(["Time >", "Weight >", "Press >", "Press <"]); return cb
        return super().createEditor(parent, option, index)
    def setEditorData(self, editor, index):
        if isinstance(editor, QComboBox): editor.setCurrentText(index.model().data(index, Qt.ItemDataRole.EditRole))
        else: super().setEditorData(editor, index)
    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox): model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
        else: super().setModelData(editor, model, index)

class StateProfileModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._data = [
            ["F", 4.0, 93.0, 93.0, "Time >", 4.0],      
            ["P", 4.0, 93.0, 93.0, "Press >", 3.5],     
            ["P", 9.0, 93.0, 93.0, "Weight >", 36.0],   
            ["P", 0.0, 93.0, 93.0, "Time >", 0.1]       
        ]
        self._headers = ["Mode", "Set", "Tw", "Tg", "Exit Cond", "Exit Val"]
    def rowCount(self, p=None): return len(self._data)
    def columnCount(self, p=None): return 6
    def data(self, index, role):
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole): return str(self._data[index.row()][index.column()])
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal: return self._headers[section]
    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            try:
                row, col = index.row(), index.column()
                val = float(value) if col in [1, 2, 3, 5] else value
                self._data[row][col] = val
                self.dataChanged.emit(index, index); return True
            except: return False
        return False
    def flags(self, index): return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
    def add_step(self):
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data)); self._data.append(["P", 0.0, 93.0, 93.0, "Time >", 5.0]); self.endInsertRows()
    def remove_step(self, row):
        if 0 <= row < len(self._data): self.beginRemoveRows(QModelIndex(), row, row); del self._data[row]; self.endRemoveRows()
    def get_data(self): return self._data
    def set_data(self, data): self.beginResetModel(); self._data = data; self.endResetModel()

# --- 4. MAIN GUI ---
class EspressoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PiEspresso Ultimate")
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)
        self.setCursor(Qt.CursorShape.ArrowCursor) # Force Cursor Visible
        
        # Buffer
        self.buffer = np.zeros((MAX_BUFFER_SIZE, 5), dtype=np.float32)
        self.ptr = 0
        
        self.paused = False; self.is_powered = False
        self.profile_running = False; self.is_heating = False
        self.active_profile = []; self.current_step_idx = 0; self.step_start_time = 0
        self.saved_profiles = {}

        self.init_ui()
        self.load_profiles_from_disk()

        self.worker = SerialWorker()
        self.worker.data_available.connect(self.update_data)
        self.worker.start()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.run_state_machine)
        self.timer.start(50) 
        self.toggle_power(False)

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central)
        
        # --- LEFT PANEL ---
        sidebar = QFrame(); sidebar.setObjectName("Panel"); sidebar.setFixedWidth(420); sl = QVBoxLayout(sidebar)
        
        self.btn_power = QPushButton("STANDBY"); self.btn_power.setCheckable(True); self.btn_power.clicked.connect(self.toggle_power)
        sl.addWidget(self.btn_power); sl.addSpacing(10)
        
        sl.addWidget(QLabel("MANUAL OVERRIDE", objectName="Header"))
        row_man = QHBoxLayout()
        self.btn_flush = QPushButton("FLUSH"); self.btn_flush.setCheckable(True); self.btn_flush.setObjectName("BtnFlush"); self.btn_flush.clicked.connect(self.toggle_flush)
        self.btn_steam = QPushButton("STEAM"); self.btn_steam.setCheckable(True); self.btn_steam.setObjectName("BtnSteam"); self.btn_steam.clicked.connect(self.toggle_steam)
        row_man.addWidget(self.btn_flush); row_man.addWidget(self.btn_steam); sl.addLayout(row_man); sl.addSpacing(10)

        self.tabs = QTabWidget(); sl.addWidget(self.tabs)
        
        tab_edit = QWidget(); l_edit = QVBoxLayout(tab_edit); l_edit.setContentsMargins(5,5,5,5)
        self.model = StateProfileModel(); self.table = QTableView(); self.table.setModel(self.model)
        self.table.verticalHeader().hide(); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setItemDelegate(SmartDelegate()); l_edit.addWidget(self.table)
        row_steps = QHBoxLayout()
        btn_add = QPushButton("+ Step"); btn_add.clicked.connect(self.model.add_step)
        btn_del = QPushButton("- Step"); btn_del.setObjectName("BtnDel"); btn_del.clicked.connect(self.delete_selected_step)
        btn_save = QPushButton("Save"); btn_save.clicked.connect(self.save_profile_dialog)
        row_steps.addWidget(btn_add); row_steps.addWidget(btn_del); row_steps.addWidget(btn_save)
        l_edit.addLayout(row_steps); self.tabs.addTab(tab_edit, "Editor")

        tab_lib = QWidget(); l_lib = QVBoxLayout(tab_lib); l_lib.setContentsMargins(5,5,5,5)
        self.list_widget = QListWidget(); self.list_widget.itemDoubleClicked.connect(self.load_from_library); l_lib.addWidget(self.list_widget)
        row_lib_btns = QHBoxLayout()
        btn_load = QPushButton("Load Selected"); btn_load.clicked.connect(self.load_from_library)
        btn_del_prof = QPushButton("Delete"); btn_del_prof.setObjectName("BtnDel"); btn_del_prof.clicked.connect(self.delete_profile_file)
        row_lib_btns.addWidget(btn_load); row_lib_btns.addWidget(btn_del_prof); l_lib.addLayout(row_lib_btns); self.tabs.addTab(tab_lib, "Library")
        
        self.btn_run = QPushButton("RUN PROFILE"); self.btn_run.setCheckable(True); self.btn_run.setObjectName("BtnRun"); self.btn_run.setFixedHeight(50)
        self.btn_run.clicked.connect(self.toggle_profile); sl.addWidget(self.btn_run)
        layout.addWidget(sidebar)
        
        # --- RIGHT PANEL ---
        right = QWidget(); rl = QVBoxLayout(right)
        stats = QFrame(); stats.setObjectName("Panel"); stats.setFixedHeight(80); sls = QHBoxLayout(stats)
        self.lbl_p = self.mk_stat(sls, "Pressure")
        w_widget = QWidget(); w_layout = QVBoxLayout(w_widget); w_layout.setContentsMargins(0,0,0,0)
        wb_layout = QHBoxLayout(); self.lbl_w_val = QLabel("0.0"); self.lbl_w_val.setObjectName("StatValue"); self.lbl_w_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_tare = QPushButton("TARE"); self.btn_tare.setObjectName("BtnTare"); self.btn_tare.setFixedWidth(60); self.btn_tare.clicked.connect(self.tare_scale)
        wb_layout.addWidget(self.lbl_w_val); wb_layout.addWidget(self.btn_tare)
        w_lbl = QLabel("WEIGHT (g)"); w_lbl.setObjectName("StatLabel"); w_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_layout.addLayout(wb_layout); w_layout.addWidget(w_lbl); sls.addWidget(w_widget)
        rl.addWidget(stats)
        
        self.glw = pg.GraphicsLayoutWidget(); self.glw.setBackground('#1e1e1e')
        
        # P1: EXTRACTION PLOT
        p1 = self.glw.addPlot(row=0, col=0, title="Extraction")
        p1.showGrid(x=True, y=True, alpha=0.3)
        p1.setLabel('left', "Pressure (Bar), Flow (ml/s), Weight (g)") # Y-Axis Label
        p1.setLabel('bottom', "Time (s)") # X-Axis Label
        p1.addLegend(offset=(30, 30)) # FIX: Legend added BEFORE items
        self.c_p = p1.plot(pen=pg.mkPen('#2ecc71', width=2), name="Bar")
        self.c_f = p1.plot(pen=pg.mkPen('#3498db', width=2), name="Flow")
        self.c_w = p1.plot(pen=pg.mkPen('#ffffff', width=1, style=Qt.PenStyle.DashLine), name="Weight")

        # P2: TEMPERATURE PLOT
        p2 = self.glw.addPlot(row=1, col=0, title="Temperature")
        p2.setXLink(p1)
        p2.showGrid(x=True, y=True, alpha=0.3)
        p2.setLabel('left', "Temperature (°C)") # Y-Axis Label
        p2.setLabel('bottom', "Time (s)") # X-Axis Label
        p2.addLegend(offset=(30, 30)) # FIX: Legend added BEFORE items
        self.c_tw = p2.plot(pen=pg.mkPen('#e74c3c', width=2), name="Water")
        self.c_tg = p2.plot(pen=pg.mkPen('#f39c12', width=2), name="Group")
        
        rl.addWidget(self.glw)
        layout.addWidget(right)

    def mk_stat(self, l, t):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0)
        lbl = QLabel("0.0"); lbl.setObjectName("StatValue"); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cap = QLabel(t); cap.setObjectName("StatLabel"); cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl); v.addWidget(cap); l.addWidget(w); return lbl

    # --- ACTIONS ---
    def delete_selected_step(self):
        selection = self.table.selectionModel().selectedRows()
        if selection:
            for r in sorted([x.row() for x in selection], reverse=True): self.model.remove_step(r)
        else:
            if self.model.rowCount() > 0: self.model.remove_step(self.model.rowCount() - 1)
    def load_profiles_from_disk(self):
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE, 'r') as f: self.saved_profiles = json.load(f)
            except: self.saved_profiles = {}
        self.refresh_library_list()
    def refresh_library_list(self): self.list_widget.clear(); self.list_widget.addItems(sorted(self.saved_profiles.keys()))
    def save_profiles_to_disk(self):
        with open(PROFILE_FILE, 'w') as f: json.dump(self.saved_profiles, f, indent=4)
        self.refresh_library_list()
    def save_profile_dialog(self):
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile Name:")
        if ok and name: self.saved_profiles[name] = self.model.get_data(); self.save_profiles_to_disk(); QMessageBox.information(self, "Saved", f"Profile '{name}' saved.")
    def load_from_library(self):
        item = self.list_widget.currentItem()
        if not item: return
        name = item.text()
        if name in self.saved_profiles: self.model.set_data(self.saved_profiles[name]); self.tabs.setCurrentIndex(0)
    def delete_profile_file(self):
        item = self.list_widget.currentItem()
        if not item: return
        name = item.text()
        reply = QMessageBox.question(self, 'Delete', f"Delete '{name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes: del self.saved_profiles[name]; self.save_profiles_to_disk()
    def tare_scale(self): 
        self.worker.send_command("TARE"); self.buffer[:self.ptr, 2] = 0 
    def toggle_flush(self, c):
        if c: self.start_session(); self.worker.send_command("SET_P:3.0"); self.btn_run.setEnabled(False)
        else: self.worker.send_command("STOP"); self.btn_run.setEnabled(True)
    def toggle_steam(self, c): self.worker.send_command("STEAM_ON" if c else "STEAM_OFF")

    # --- LOGIC ---
    def run_state_machine(self):
        if not self.profile_running or not self.is_powered: return
        if self.is_heating:
            cur_tw = self.worker.last_tw; cur_tg = self.worker.last_tg
            target_tw = self.active_profile[0][2]; target_tg = self.active_profile[0][3]
            if abs(cur_tw - target_tw) < 1.0 and abs(cur_tg - target_tg) < 1.0:
                self.start_session(); self.is_heating = False; self.step_start_time = time.time(); self.btn_run.setText("STOP"); self.execute_step(self.active_profile[0])
            else:
                self.worker.send_command("STOP"); self.worker.send_command(f"SET_TW:{target_tw}"); self.worker.send_command(f"SET_TG:{target_tg}"); self.btn_run.setText(f"HEATING ({cur_tw:.0f}/{target_tw:.0f})")
            return
        now = time.time(); elapsed = now - self.step_start_time
        cur_p = self.worker.last_p; cur_w = self.worker.last_w
        if self.current_step_idx >= len(self.active_profile): self.stop_profile(); return
        step = self.active_profile[self.current_step_idx]
        trig = step[4]; val = float(step[5]); next_step = False
        if trig == "Time >" and elapsed >= val: next_step = True
        elif trig == "Weight >" and cur_w >= val: next_step = True
        elif trig == "Press >" and cur_p >= val: next_step = True
        elif trig == "Press <" and cur_p <= val and elapsed > 1.0: next_step = True 
        if next_step:
            self.current_step_idx += 1
            if self.current_step_idx < len(self.active_profile): self.execute_step(self.active_profile[self.current_step_idx])
    def execute_step(self, step):
        self.step_start_time = time.time()
        self.worker.send_command(f"SET_{step[0]}:{step[1]}")
        self.worker.send_command(f"SET_TW:{step[2]}")
        self.worker.send_command(f"SET_TG:{step[3]}")
    def toggle_profile(self, checked):
        if checked:
            self.active_profile = self.model._data; self.current_step_idx = 0; self.worker.send_command("TARE"); self.is_heating = True; self.profile_running = True
        else: self.stop_profile()
    def stop_profile(self):
        self.profile_running = False; self.is_heating = False; self.worker.send_command("STOP"); self.btn_run.setChecked(False); self.btn_run.setText("RUN PROFILE"); self.paused = True
    def toggle_power(self, c):
        self.is_powered = c; self.btn_power.setText("ACTIVE" if c else "STANDBY")
        self.worker.send_command("POWER_ON" if c else "POWER_OFF")
        self.btn_tare.setEnabled(c); self.tabs.setEnabled(c); self.btn_flush.setEnabled(c); self.btn_steam.setEnabled(c); self.btn_run.setEnabled(c)
        if not c:
            if self.btn_flush.isChecked(): self.btn_flush.click()
            if self.btn_steam.isChecked(): self.btn_steam.click()
    def start_session(self): self.ptr = 0; self.paused = False 

    # --- UPDATES ---
    def update_data(self, chunk):
        self.lbl_p.setText(f"{chunk[-1,0]:.1f}"); self.lbl_w_val.setText(f"{chunk[-1,2]:.1f}")
        if self.paused: return
        n = len(chunk)
        if self.ptr + n >= MAX_BUFFER_SIZE: self.ptr = 0 
        self.buffer[self.ptr : self.ptr + n] = chunk; self.ptr += n
        
        if self.profile_running and not self.is_heating: start_idx = 0
        else: start_idx = max(0, self.ptr - ROLLING_WINDOW_SIZE)
            
        valid_data = self.buffer[start_idx : self.ptr]
        
        # TIME AXIS (Seconds)
        t = np.arange(start_idx, self.ptr) / 1000.0
        
        self.c_p.setData(t, valid_data[:, 0], autoDownsample=True)
        self.c_f.setData(t, valid_data[:, 1], autoDownsample=True)
        self.c_w.setData(t, valid_data[:, 2], autoDownsample=True)
        self.c_tw.setData(t, valid_data[:, 3], autoDownsample=True)
        self.c_tg.setData(t, valid_data[:, 4], autoDownsample=True)

    def closeEvent(self, e): self.worker.stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setOverrideCursor(Qt.CursorShape.ArrowCursor)
    window = EspressoApp()
    window.show()
    sys.exit(app.exec())

