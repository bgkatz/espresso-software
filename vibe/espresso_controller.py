import sys
import struct
import time
import random
import numpy as np
from PyQt6.QtCore import (QThread, pyqtSignal, QTimer, Qt, QAbstractTableModel, QModelIndex)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QTableView, QHeaderView, 
                             QFrame)
import pyqtgraph as pg

# --- CONFIGURATION ---
SAMPLES_PER_PACKET = 10   
PACKET_HEADER = b'ES'
# Structure: [Header 2s] + [Pressure, Flow, Weight, Tw, Tg] * 10
PACKET_STRUCT_FMT = f'<2s{SAMPLES_PER_PACKET * 5}f' 
PACKET_SIZE = struct.calcsize(PACKET_STRUCT_FMT)

# --- STYLING ---
STYLESHEET = """
QMainWindow { background-color: #1e1e1e; }
QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
QFrame#Panel { background-color: #252526; border-radius: 8px; border: 1px solid #3e3e42; }
QLabel#StatValue { font-size: 24px; font-weight: bold; color: #fff; }
QLabel#StatLabel { font-size: 11px; color: #aaa; text-transform: uppercase; }

/* Buttons */
QPushButton { background-color: #3e3e42; border-radius: 4px; padding: 8px; color: white; font-weight: bold; }
QPushButton:pressed { background-color: #007acc; }
QPushButton:disabled { background-color: #2d2d30; color: #555; }

/* Special Buttons */
QPushButton#BtnRun { background-color: #2ecc71; }
QPushButton#BtnRun:checked { background-color: #e74c3c; } /* Red when STOP */
QPushButton#BtnTare { background-color: #8e44ad; font-size: 12px; padding: 4px; border-radius: 4px; } 

/* Table */
QTableView { background-color: #1e1e1e; gridline-color: #3e3e42; selection-background-color: #007acc; }
QHeaderView::section { background-color: #252526; padding: 4px; border: 1px solid #3e3e42; color: #aaa; }
"""

# --- 1. MOCK HARDWARE (SIMULATOR) ---
class MockEspressoMachine:
    def __init__(self):
        self.powered = False
        self.p = 0.0; self.f = 0.0; self.w = 0.0
        self.tw = 20.0; self.tg = 20.0
        self.tgt_val = 0.0; self.ctrl_mode = 'P'
        self.tgt_tw = 20.0; self.tgt_tg = 20.0
        self.steam = False
        self.pump_duty = 0.0

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
        # Cache for Logic Loop
        self.last_p = 0.0; self.last_f = 0.0; self.last_w = 0.0

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
                        self.data_available.emit(chunk)
            except: time.sleep(0.01)
    def stop(self): self.running = False; self.wait()

# --- 3. STATE PROFILE MODEL ---
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
            row, col = index.row(), index.column()
            try:
                val = value
                if col in [1, 2, 3, 5]: val = float(value)
                self._data[row][col] = val
                self.dataChanged.emit(index, index); return True
            except: return False
        return False
    def flags(self, index): return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
    def add_step(self):
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append(["P", 0.0, 93.0, 93.0, "Time >", 5.0])
        self.endInsertRows()

# --- 4. MAIN GUI ---
class EspressoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PiEspresso Ultimate")
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)
        
        # State
        self.data = {k: [] for k in ['p','f','w','tw','tg']}
        self.paused = False; self.is_powered = False
        self.profile_running = False; self.active_profile = []; self.current_step_idx = 0; self.step_start_time = 0

        self.init_ui()
        self.worker = SerialWorker()
        self.worker.data_available.connect(self.update_data)
        self.worker.start()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.run_state_machine)
        self.timer.start(50) 
        self.set_power(False)

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central)
        
        # --- LEFT PANEL (Controls) ---
        sidebar = QFrame(); sidebar.setObjectName("Panel"); sidebar.setFixedWidth(400)
        sl = QVBoxLayout(sidebar)
        
        self.btn_power = QPushButton("STANDBY"); self.btn_power.setCheckable(True); self.btn_power.clicked.connect(self.toggle_power)
        sl.addWidget(self.btn_power); sl.addSpacing(10)
        
        self.model = StateProfileModel()
        self.table = QTableView(); self.table.setModel(self.model)
        self.table.verticalHeader().hide(); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        sl.addWidget(self.table)
        
        btn_add = QPushButton("+ Step"); btn_add.clicked.connect(self.model.add_step)
        sl.addWidget(btn_add)
        
        self.btn_run = QPushButton("RUN PROFILE"); self.btn_run.setCheckable(True); self.btn_run.setObjectName("BtnRun")
        self.btn_run.clicked.connect(self.toggle_profile)
        sl.addWidget(self.btn_run)
        layout.addWidget(sidebar)
        
        # --- RIGHT PANEL (Plots) ---
        right = QWidget(); rl = QVBoxLayout(right)
        
        # Stats Bar with TARE
        stats = QFrame(); stats.setObjectName("Panel"); stats.setFixedHeight(80); sls = QHBoxLayout(stats)
        self.lbl_p = self.mk_stat(sls, "Pressure")
        
        # Weight + Tare Group
        w_widget = QWidget(); w_layout = QVBoxLayout(w_widget); w_layout.setContentsMargins(0,0,0,0)
        wb_layout = QHBoxLayout()
        self.lbl_w_val = QLabel("0.0"); self.lbl_w_val.setObjectName("StatValue"); self.lbl_w_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_tare = QPushButton("TARE"); self.btn_tare.setObjectName("BtnTare"); self.btn_tare.setFixedWidth(60)
        self.btn_tare.clicked.connect(self.tare_scale)
        wb_layout.addWidget(self.lbl_w_val); wb_layout.addWidget(self.btn_tare)
        w_lbl = QLabel("WEIGHT (g)"); w_lbl.setObjectName("StatLabel"); w_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_layout.addLayout(wb_layout); w_layout.addWidget(w_lbl); sls.addWidget(w_widget)
        
        rl.addWidget(stats)
        
        # Plots
        self.glw = pg.GraphicsLayoutWidget(); self.glw.setBackground('#1e1e1e')
        
        # P1: Extraction
        p1 = self.glw.addPlot(row=0, col=0, title="Extraction"); p1.showGrid(x=True, y=True, alpha=0.3)
        self.c_p = p1.plot(pen=pg.mkPen('#2ecc71', width=2), name="Bar")
        self.c_f = p1.plot(pen=pg.mkPen('#3498db', width=2), name="Flow")
        self.c_w = p1.plot(pen=pg.mkPen('#ffffff', width=1, style=Qt.PenStyle.DashLine), name="Weight")
        
        # P2: Thermals
        p2 = self.glw.addPlot(row=1, col=0, title="Temperature"); p2.setXLink(p1); p2.showGrid(x=True, y=True, alpha=0.3)
        self.c_tw = p2.plot(pen=pg.mkPen('#e74c3c', width=2), name="Water")
        self.c_tg = p2.plot(pen=pg.mkPen('#f39c12', width=2), name="Group")
        
        rl.addWidget(self.glw)
        layout.addWidget(right)

    def mk_stat(self, l, t):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0)
        lbl = QLabel("0.0"); lbl.setObjectName("StatValue"); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cap = QLabel(t); cap.setObjectName("StatLabel"); cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl); v.addWidget(cap); l.addWidget(w); return lbl

    # --- LOGIC ---
    def tare_scale(self):
        self.worker.send_command("TARE"); self.data['w'] = [] 

    def run_state_machine(self):
        if not self.profile_running or not self.is_powered: return
        now = time.time(); elapsed = now - self.step_start_time
        cur_p = self.worker.last_p; cur_w = self.worker.last_w
        
        if self.current_step_idx >= len(self.active_profile): self.stop_profile(); return
        step = self.active_profile[self.current_step_idx]
        trig = step[4]; val = float(step[5])
        next_step = False
        
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
            self.start_session()
            self.active_profile = self.model._data
            self.current_step_idx = 0
            self.worker.send_command("TARE") 
            self.execute_step(self.active_profile[0])
            self.profile_running = True; self.btn_run.setText("STOP")
        else:
            self.stop_profile()

    def stop_profile(self):
        self.profile_running = False; self.worker.send_command("STOP")
        self.btn_run.setChecked(False); self.btn_run.setText("RUN PROFILE"); self.paused = True

    def toggle_power(self, c):
        self.is_powered = c; self.btn_power.setText("ACTIVE" if c else "STANDBY")
        self.worker.send_command("POWER_ON" if c else "POWER_OFF")
        self.btn_tare.setEnabled(c)

    def start_session(self):
        for k in self.data: self.data[k] = []
        self.paused = False 

    def update_data(self, chunk):
        self.lbl_p.setText(f"{chunk[-1,0]:.1f}"); self.lbl_w_val.setText(f"{chunk[-1,2]:.1f}")
        if self.paused: return
        self.data['p'].extend(chunk[:,0]); self.data['f'].extend(chunk[:,1]); self.data['w'].extend(chunk[:,2])
        self.data['tw'].extend(chunk[:,3]); self.data['tg'].extend(chunk[:,4])
        
        self.c_p.setData(np.array(self.data['p']), autoDownsample=True)
        self.c_f.setData(np.array(self.data['f']), autoDownsample=True)
        self.c_w.setData(np.array(self.data['w']), autoDownsample=True)
        self.c_tw.setData(np.array(self.data['tw']), autoDownsample=True)
        self.c_tg.setData(np.array(self.data['tg']), autoDownsample=True)

    def closeEvent(self, e): self.worker.stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EspressoApp()
    window.show()
    sys.exit(app.exec())