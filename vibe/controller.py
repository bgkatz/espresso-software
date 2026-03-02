"""
PiEspresso controller — Python/QML bridge.

Contains:
  MockEspressoMachine  — simulated hardware (swap for serial.Serial on real hardware)
  SerialWorker         — QThread that reads packets and emits data
  ProfileModel         — QAbstractListModel exposing profile steps to QML ListView
  EspressoController   — QObject with properties/signals/slots consumed by QML
"""
import struct
import time
import json
import os

import numpy as np

from PyQt6.QtCore import (
    QObject, QThread, QTimer, QModelIndex, Qt,
    pyqtSignal, pyqtSlot, pyqtProperty,
    QAbstractListModel,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SAMPLES_PER_PACKET = 10
PACKET_HEADER      = b'ES'
PACKET_STRUCT_FMT  = f'<2s{SAMPLES_PER_PACKET * 5}f'
PACKET_SIZE        = struct.calcsize(PACKET_STRUCT_FMT)
PROFILE_FILE       = "profiles.json"
LOG_DIR            = "logs"
CHART_HZ           = 30          # chart update rate (Hz)
STATE_MACHINE_HZ   = 20          # profile state-machine tick rate (Hz)

EXIT_CONDITIONS      = ["Time >", "Weight >", "Pressure >", "Pressure <"]
PREDICTIVE_STOP_G   = 2.0       # grams before weight target to cut pump

# ---------------------------------------------------------------------------
# 1. Mock hardware  (replace self.connection with serial.Serial(...) for real hw)
# ---------------------------------------------------------------------------
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
        if   cmd == "POWER_ON":   self.powered = True;  self.tgt_tw = 93.0; self.tgt_tg = 93.0
        elif cmd == "POWER_OFF":  self.powered = False; self.tgt_val = 0.0; self.tgt_tw = 20.0; self.steam = False
        elif cmd == "TARE":       self.w = 0.0
        elif self.powered:
            if   cmd.startswith("SET_P:"): self.ctrl_mode = 'P'; self.tgt_val = float(cmd.split(":")[1])
            elif cmd.startswith("SET_F:"): self.ctrl_mode = 'F'; self.tgt_val = float(cmd.split(":")[1])
            elif cmd.startswith("SET_TW:"): self.tgt_tw = float(cmd.split(":")[1])
            elif cmd.startswith("SET_TG:"): self.tgt_tg = float(cmd.split(":")[1])
            elif cmd == "STEAM_ON":  self.steam = True;  self.tgt_tw = 140.0
            elif cmd == "STEAM_OFF": self.steam = False; self.tgt_tw = 93.0
            elif cmd == "STOP":  self.tgt_val = 0.0

    def _step(self, dt):
        tgt_w = (140.0 if self.steam else self.tgt_tw) if self.powered else 20.0
        tgt_g = self.tgt_tg if self.powered else 20.0
        self.tw += (tgt_w - self.tw) * 0.5 * dt
        self.tg += (tgt_g - self.tg) * 0.5 * dt
        if self.powered:
            cur = self.p if self.ctrl_mode == 'P' else self.f
            self.pump_duty += (self.tgt_val - cur) * 5.0 * dt
            self.pump_duty = max(0.0, min(12.0, self.pump_duty))
            self.p = self.pump_duty
            self.f = self.p / 1.5
            self.w += self.f * dt
        else:
            self.p *= 0.9; self.f = 0.0; self.pump_duty = 0.0


# ---------------------------------------------------------------------------
# 2. Serial worker thread
# ---------------------------------------------------------------------------
class SerialWorker(QThread):
    data_available = pyqtSignal(np.ndarray)   # shape (N, 5): p, f, w, tw, tg

    def __init__(self):
        super().__init__()
        self.running = True
        self.connection = MockEspressoMachine()
        # Latest values — readable from any thread (written only by this thread)
        self.last_p = 0.0; self.last_f = 0.0; self.last_w = 0.0
        self.last_tw = 20.0; self.last_tg = 20.0

    def send_command(self, cmd: str):
        self.connection.write(cmd.encode())

    def run(self):
        while self.running:
            try:
                raw = self.connection.read(PACKET_SIZE)
                if len(raw) == PACKET_SIZE:
                    unpacked = struct.unpack(PACKET_STRUCT_FMT, raw)
                    if unpacked[0] == PACKET_HEADER:
                        chunk = np.array(unpacked[1:], dtype=np.float32).reshape(-1, 5)
                        self.last_p  = float(chunk[-1, 0])
                        self.last_f  = float(chunk[-1, 1])
                        self.last_w  = float(chunk[-1, 2])
                        self.last_tw = float(chunk[-1, 3])
                        self.last_tg = float(chunk[-1, 4])
                        self.data_available.emit(chunk)
            except Exception:
                time.sleep(0.01)

    def stop(self):
        self.running = False
        self.wait()


# ---------------------------------------------------------------------------
# 3. Profile model (QAbstractListModel → QML ListView)
# ---------------------------------------------------------------------------
_DEFAULT_STEPS = [
    ["F", 4.0, 93.0, 93.0, "Time >",      4.0, 0.0],
    ["P", 4.0, 93.0, 93.0, "Pressure >",  3.5, 2.0],
    ["P", 9.0, 93.0, 93.0, "Weight >",   36.0, 3.0],
    ["P", 0.0, 93.0, 93.0, "Time >",      0.1, 0.0],
]
_BLANK_STEP = ["P", 0.0, 93.0, 93.0, "Time >", 5.0, 0.0]

class ProfileModel(QAbstractListModel):
    # Custom roles accessed in QML as model.stepMode, model.setVal, etc.
    ModeRole     = Qt.ItemDataRole.UserRole + 1
    SetValRole   = Qt.ItemDataRole.UserRole + 2
    TwRole       = Qt.ItemDataRole.UserRole + 3
    TgRole       = Qt.ItemDataRole.UserRole + 4
    ExitCondRole = Qt.ItemDataRole.UserRole + 5
    ExitValRole  = Qt.ItemDataRole.UserRole + 6
    RampTimeRole = Qt.ItemDataRole.UserRole + 7

    def __init__(self):
        super().__init__()
        self._steps = [list(s) for s in _DEFAULT_STEPS]

    # --- QAbstractListModel interface ---
    def roleNames(self):
        return {
            self.ModeRole:     b'stepMode',
            self.SetValRole:   b'setVal',
            self.TwRole:       b'tw',
            self.TgRole:       b'tg',
            self.ExitCondRole: b'exitCond',
            self.ExitValRole:  b'exitVal',
            self.RampTimeRole: b'rampTime',
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._steps)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._steps):
            return None
        s = self._steps[index.row()]
        return {
            self.ModeRole:     s[0],
            self.SetValRole:   float(s[1]),
            self.TwRole:       float(s[2]),
            self.TgRole:       float(s[3]),
            self.ExitCondRole: s[4],
            self.ExitValRole:  float(s[5]),
            self.RampTimeRole: float(s[6]) if len(s) > 6 else 0.0,
        }.get(role)

    # --- Slots called from QML to mutate a step ---
    @pyqtSlot(int, str)
    def setMode(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][0] = value
            self._notify(row, self.ModeRole)

    @pyqtSlot(int, float)
    def setSetVal(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][1] = value
            self._notify(row, self.SetValRole)

    @pyqtSlot(int, float)
    def setTw(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][2] = value
            self._notify(row, self.TwRole)

    @pyqtSlot(int, float)
    def setTg(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][3] = value
            self._notify(row, self.TgRole)

    @pyqtSlot(int, str)
    def setExitCond(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][4] = value
            self._notify(row, self.ExitCondRole)

    @pyqtSlot(int, float)
    def setExitVal(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][5] = value
            self._notify(row, self.ExitValRole)

    @pyqtSlot(int, float)
    def setRampTime(self, row, value):
        if 0 <= row < len(self._steps):
            while len(self._steps[row]) < 7:
                self._steps[row].append(0.0)
            self._steps[row][6] = value
            self._notify(row, self.RampTimeRole)

    @pyqtSlot()
    def addStep(self):
        row = len(self._steps)
        self.beginInsertRows(QModelIndex(), row, row)
        self._steps.append(list(_BLANK_STEP))
        self.endInsertRows()

    @pyqtSlot(int)
    def removeStep(self, row):
        if 0 <= row < len(self._steps):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._steps[row]
            self.endRemoveRows()

    # --- Bulk access for state machine / persistence ---
    def get_data(self):
        return [list(s) for s in self._steps]

    def set_data(self, data):
        self.beginResetModel()
        self._steps = [list(s) for s in data]
        self.endResetModel()

    def _notify(self, row, role):
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [role])


# ---------------------------------------------------------------------------
# 4. Main controller — the Python/QML bridge
# ---------------------------------------------------------------------------
class EspressoController(QObject):
    # Property-change signals
    pressureChanged      = pyqtSignal(float)
    flowChanged          = pyqtSignal(float)
    weightChanged        = pyqtSignal(float)
    tempWaterChanged     = pyqtSignal(float)
    tempGroupChanged     = pyqtSignal(float)
    poweredChanged       = pyqtSignal(bool)
    steamOnChanged       = pyqtSignal(bool)
    flushOnChanged       = pyqtSignal(bool)
    profileRunningChanged = pyqtSignal(bool)
    statusTextChanged    = pyqtSignal(str)
    stepIndexChanged     = pyqtSignal(int)
    elapsedTimeChanged   = pyqtSignal(float)
    savedProfileNamesChanged = pyqtSignal('QVariantList')

    # Chart signals
    # Emitted at CHART_HZ; QML connects and appends to LineSeries
    newDataPoint = pyqtSignal(float, float, float, float, float, float)
    # args:                   t_s,  press,  flow,  weight, tw,   tg
    sessionStarted   = pyqtSignal()   # tells chart to clear all series
    previousShotReady        = pyqtSignal()   # ghost overlay data is ready
    currentStepTargetChanged = pyqtSignal(float)
    shotAvailableChanged     = pyqtSignal(bool)
    shotSaved                = pyqtSignal(str)  # emits saved filename on success

    def __init__(self):
        super().__init__()
        # Live values
        self._pressure   = 0.0
        self._flow       = 0.0
        self._weight     = 0.0
        self._temp_water = 20.0
        self._temp_group = 20.0
        self._powered         = False
        self._steam_on        = False
        self._flush_on        = False
        self._profile_running = False
        self._status_text     = "STANDBY"
        self._step_index      = 0
        self._elapsed_time    = 0.0
        self._saved_profile_names = []

        # Session / profile state
        self._t0               = time.monotonic()  # chart x-axis reference (reset on session start)
        self._session_start    = None   # monotonic time of shot start (set only when actively running)
        self._active_profile   = []
        self._current_step_idx = 0
        self._step_start_time  = 0.0
        self._is_heating       = False
        self._saved_profiles   = {}

        # Shot recording (ghost overlay + log export)
        self._recording       = False
        self._shot_times      = []; self._shot_pressures = []
        self._shot_flows      = []; self._shot_weights   = []
        self._shot_tw         = []; self._shot_tg        = []
        self._shot_available  = False
        self._ghost_times     = []; self._ghost_pressures = []
        self._ghost_flows     = []; self._ghost_weights   = []

        # Profile target overlay
        self._current_step_target = 0.0

        # Transition ramp state
        self._ramp_start    = 0.0
        self._ramp_target   = 0.0
        self._ramp_duration = 0.0

        self._profile_model = ProfileModel()

        # Serial worker
        self._worker = SerialWorker()
        self._worker.data_available.connect(self._on_data)
        self._worker.start()

        # State machine timer
        self._state_timer = QTimer()
        self._state_timer.timeout.connect(self._run_state_machine)
        self._state_timer.start(1000 // STATE_MACHINE_HZ)

        # Chart update timer — decoupled from packet rate
        self._chart_timer = QTimer()
        self._chart_timer.timeout.connect(self._emit_chart_point)
        self._chart_timer.start(1000 // CHART_HZ)

        self._load_profiles()

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------
    @pyqtProperty(float, notify=pressureChanged)
    def pressure(self):      return self._pressure

    @pyqtProperty(float, notify=flowChanged)
    def flow(self):          return self._flow

    @pyqtProperty(float, notify=weightChanged)
    def weight(self):        return self._weight

    @pyqtProperty(float, notify=tempWaterChanged)
    def tempWater(self):     return self._temp_water

    @pyqtProperty(float, notify=tempGroupChanged)
    def tempGroup(self):     return self._temp_group

    @pyqtProperty(bool, notify=poweredChanged)
    def powered(self):       return self._powered

    @pyqtProperty(bool, notify=steamOnChanged)
    def steamOn(self):       return self._steam_on

    @pyqtProperty(bool, notify=flushOnChanged)
    def flushOn(self):       return self._flush_on

    @pyqtProperty(bool, notify=profileRunningChanged)
    def profileRunning(self): return self._profile_running

    @pyqtProperty(str, notify=statusTextChanged)
    def statusText(self):    return self._status_text

    @pyqtProperty(int, notify=stepIndexChanged)
    def stepIndex(self):     return self._step_index

    @pyqtProperty(float, notify=elapsedTimeChanged)
    def elapsedTime(self):   return self._elapsed_time

    @pyqtProperty('QVariantList', notify=savedProfileNamesChanged)
    def savedProfileNames(self): return self._saved_profile_names

    @pyqtProperty(float, notify=currentStepTargetChanged)
    def currentStepTarget(self): return self._current_step_target

    @pyqtProperty(bool, notify=shotAvailableChanged)
    def shotAvailable(self): return self._shot_available

    @pyqtProperty('QVariantList', notify=previousShotReady)
    def ghostTimes(self):     return self._ghost_times

    @pyqtProperty('QVariantList', notify=previousShotReady)
    def ghostPressures(self): return self._ghost_pressures

    @pyqtProperty('QVariantList', notify=previousShotReady)
    def ghostFlows(self):     return self._ghost_flows

    @pyqtProperty('QVariantList', notify=previousShotReady)
    def ghostWeights(self):   return self._ghost_weights

    @pyqtProperty(QObject, constant=True)
    def profileModel(self):  return self._profile_model

    # -----------------------------------------------------------------------
    # Private update helpers (only emit if value actually changed)
    # -----------------------------------------------------------------------
    def _set(self, attr, value, signal, digits=2):
        value = round(value, digits)
        if getattr(self, attr) != value:
            setattr(self, attr, value)
            signal.emit(value)

    def _set_status(self, s):
        if self._status_text != s:
            self._status_text = s
            self.statusTextChanged.emit(s)

    # -----------------------------------------------------------------------
    # Data handler (called from SerialWorker thread via Qt signal)
    # -----------------------------------------------------------------------
    def _on_data(self, chunk):
        last = chunk[-1]
        self._set('_pressure',   float(last[0]), self.pressureChanged,  2)
        self._set('_flow',       float(last[1]), self.flowChanged,       2)
        self._set('_weight',     float(last[2]), self.weightChanged,     1)
        self._set('_temp_water', float(last[3]), self.tempWaterChanged,  1)
        self._set('_temp_group', float(last[4]), self.tempGroupChanged,  1)

        if self._session_start is not None:
            t = time.monotonic() - self._session_start
            self._elapsed_time = t
            self.elapsedTimeChanged.emit(t)

    def _emit_chart_point(self):
        # Always emit with a real moving timestamp so the chart scrolls continuously
        t = time.monotonic() - self._t0
        self.newDataPoint.emit(t, self._pressure, self._flow,
                               self._weight, self._temp_water, self._temp_group)
        if self._recording:
            self._shot_times.append(t)
            self._shot_pressures.append(self._pressure)
            self._shot_flows.append(self._flow)
            self._shot_weights.append(self._weight)
            self._shot_tw.append(self._temp_water)
            self._shot_tg.append(self._temp_group)

    # -----------------------------------------------------------------------
    # Profile state machine (ticks at STATE_MACHINE_HZ)
    # -----------------------------------------------------------------------
    def _run_state_machine(self):
        if not self._profile_running or not self._powered:
            return

        if self._is_heating:
            step0 = self._active_profile[0]
            tgt_tw, tgt_tg = float(step0[2]), float(step0[3])
            if abs(self._temp_water - tgt_tw) < 1.0 and abs(self._temp_group - tgt_tg) < 1.0:
                self._is_heating = False
                self._session_start = time.monotonic()
                self._t0 = self._session_start   # chart resets to t=0 for the shot
                # Start recording this shot for the ghost overlay and log export
                self._recording = True
                self._shot_times.clear();     self._shot_pressures.clear()
                self._shot_flows.clear();     self._shot_weights.clear()
                self._shot_tw.clear();        self._shot_tg.clear()
                if self._shot_available:
                    self._shot_available = False
                    self.shotAvailableChanged.emit(False)
                self.sessionStarted.emit()
                self._execute_step(self._active_profile[0])
                self._update_step_index(0)
                n = len(self._active_profile)
                self._set_status(f"STEP 1 / {n}")
            else:
                self._worker.send_command("STOP")
                self._worker.send_command(f"SET_TW:{tgt_tw}")
                self._worker.send_command(f"SET_TG:{tgt_tg}")
                self._set_status(f"HEATING  {self._temp_water:.0f}° → {tgt_tw:.0f}°")
            return

        if self._current_step_idx >= len(self._active_profile):
            self.stopProfile()
            return

        elapsed = time.monotonic() - self._step_start_time
        step = self._active_profile[self._current_step_idx]
        trig, val = step[4], float(step[5])

        # Transition ramp: send interpolated setpoint each tick until ramp completes
        if self._ramp_duration > 0 and elapsed < self._ramp_duration:
            t_frac = elapsed / self._ramp_duration
            ramped = self._ramp_start + (self._ramp_target - self._ramp_start) * t_frac
            self._worker.send_command(f"SET_{step[0]}:{ramped:.2f}")

        # Predictive stop: cut pump PREDICTIVE_STOP_G grams before weight target
        weight_threshold = val - PREDICTIVE_STOP_G if trig == "Weight >" else val
        next_step = (
            (trig == "Time >"      and elapsed >= val) or
            (trig == "Weight >"    and self._weight >= weight_threshold) or
            (trig == "Pressure >"  and self._pressure >= val) or
            (trig == "Pressure <"  and self._pressure <= val and elapsed > 1.0)
        )

        if next_step:
            self._current_step_idx += 1
            if self._current_step_idx < len(self._active_profile):
                self._execute_step(self._active_profile[self._current_step_idx])
                self._update_step_index(self._current_step_idx)
                n = len(self._active_profile)
                self._set_status(f"STEP {self._current_step_idx + 1} / {n}")
            else:
                self.stopProfile()

    def _execute_step(self, step):
        self._step_start_time = time.monotonic()
        self._ramp_target   = float(step[1])
        self._ramp_duration = float(step[6]) if len(step) > 6 else 0.0
        if self._ramp_duration > 0:
            # Start from current reading; ramp is driven by _run_state_machine ticks
            self._ramp_start = self._pressure if step[0] == 'P' else self._flow
            self._worker.send_command(f"SET_{step[0]}:{self._ramp_start:.2f}")
        else:
            self._ramp_start = float(step[1])
            self._worker.send_command(f"SET_{step[0]}:{step[1]}")
        self._worker.send_command(f"SET_TW:{step[2]}")
        self._worker.send_command(f"SET_TG:{step[3]}")
        self._update_step_target(float(step[1]))

    def _update_step_target(self, val):
        if self._current_step_target != val:
            self._current_step_target = val
            self.currentStepTargetChanged.emit(val)

    def _update_step_index(self, idx):
        if self._step_index != idx:
            self._step_index = idx
            self.stepIndexChanged.emit(idx)

    # -----------------------------------------------------------------------
    # Slots — called from QML
    # -----------------------------------------------------------------------
    @pyqtSlot()
    def togglePower(self):
        self._powered = not self._powered
        self.poweredChanged.emit(self._powered)
        if self._powered:
            self._worker.send_command("POWER_ON")
            self._set_status("IDLE")
        else:
            if self._profile_running: self.stopProfile()
            if self._flush_on:        self.stopFlush()
            if self._steam_on:        self._steam_on = False; self._worker.send_command("STEAM_OFF"); self.steamOnChanged.emit(False)
            self._worker.send_command("POWER_OFF")
            self._set_status("STANDBY")

    @pyqtSlot()
    def tare(self):
        self._worker.send_command("TARE")
        self._weight = 0.0
        self.weightChanged.emit(0.0)

    @pyqtSlot()
    def toggleProfile(self):
        if self._profile_running:
            self.stopProfile()
        else:
            self._active_profile   = self._profile_model.get_data()
            self._current_step_idx = 0
            self._is_heating       = True
            self._profile_running  = True
            self._session_start    = None
            self._worker.send_command("TARE")
            self.profileRunningChanged.emit(True)
            self._update_step_index(0)
            self._set_status("HEATING...")

    @pyqtSlot()
    def stopProfile(self):
        self._profile_running = False
        self._is_heating      = False
        # Save this shot as the ghost overlay for the next shot; mark log as saveable
        if self._recording and len(self._shot_times) > 0:
            n = len(self._shot_times)
            step = max(1, n // 300)   # downsample to ~300 points max
            self._ghost_times     = self._shot_times[::step]
            self._ghost_pressures = self._shot_pressures[::step]
            self._ghost_flows     = self._shot_flows[::step]
            self._ghost_weights   = self._shot_weights[::step]
            self.previousShotReady.emit()
            self._shot_available = True
            self.shotAvailableChanged.emit(True)
        self._recording = False
        self._worker.send_command("STOP")
        self.profileRunningChanged.emit(False)
        self._update_step_target(0.0)
        self._set_status("IDLE")

    @pyqtSlot()
    def startFlush(self):
        if not self._powered:
            return
        self._flush_on      = True
        self._session_start = time.monotonic()
        self._t0 = self._session_start   # chart resets to t=0 for the flush
        self.sessionStarted.emit()
        self._worker.send_command("SET_P:3.0")
        self.flushOnChanged.emit(True)
        self._set_status("FLUSHING")

    @pyqtSlot()
    def stopFlush(self):
        self._flush_on = False
        self._worker.send_command("STOP")
        self.flushOnChanged.emit(False)
        self._set_status("IDLE")

    @pyqtSlot()
    def toggleSteam(self):
        self._steam_on = not self._steam_on
        self._worker.send_command("STEAM_ON" if self._steam_on else "STEAM_OFF")
        self.steamOnChanged.emit(self._steam_on)

    @pyqtSlot(str)
    def saveProfile(self, name):
        if not name:
            return
        self._saved_profiles[name] = self._profile_model.get_data()
        self._save_to_disk()

    @pyqtSlot(str)
    def loadProfile(self, name):
        if name in self._saved_profiles:
            self._profile_model.set_data(self._saved_profiles[name])

    @pyqtSlot(str)
    def deleteProfile(self, name):
        if name in self._saved_profiles:
            del self._saved_profiles[name]
            self._save_to_disk()

    @pyqtSlot()
    def saveShot(self):
        """Write the most recent shot's time-series data to a CSV log file."""
        if not self._shot_times:
            return
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            ts = time.strftime("%Y-%m-%d_%H-%M-%S")
            fname = os.path.join(LOG_DIR, f"shot_{ts}.csv")
            n = len(self._shot_times)
            tw = self._shot_tw  if len(self._shot_tw)  == n else [0.0] * n
            tg = self._shot_tg  if len(self._shot_tg)  == n else [0.0] * n
            with open(fname, 'w') as f:
                f.write("time_s,pressure_bar,flow_mls,weight_g,temp_water_c,temp_group_c\n")
                for i in range(n):
                    f.write(f"{self._shot_times[i]:.3f},"
                            f"{self._shot_pressures[i]:.3f},"
                            f"{self._shot_flows[i]:.3f},"
                            f"{self._shot_weights[i]:.3f},"
                            f"{tw[i]:.2f},"
                            f"{tg[i]:.2f}\n")
            self.shotSaved.emit(os.path.basename(fname))
        except Exception as e:
            self.shotSaved.emit(f"ERROR: {e}")

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------
    def _load_profiles(self):
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE) as f:
                    self._saved_profiles = json.load(f)
            except Exception:
                self._saved_profiles = {}
        self._refresh_names()

    def _save_to_disk(self):
        with open(PROFILE_FILE, 'w') as f:
            json.dump(self._saved_profiles, f, indent=2)
        self._refresh_names()

    def _refresh_names(self):
        names = sorted(self._saved_profiles.keys())
        self._saved_profile_names = names
        self.savedProfileNamesChanged.emit(names)

    # -----------------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------------
    def shutdown(self):
        self._state_timer.stop()
        self._chart_timer.stop()
        self._worker.stop()
