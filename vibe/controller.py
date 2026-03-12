"""
PiEspresso controller — Python/QML bridge.

Contains:
  Protocol helpers  — CRC16, frame building, FrameDecoder, parsed data types
  MockEspressoMachine — simulated hardware (swap for serial.Serial on real hw)
  SerialWorker        — QThread with streaming binary frame decoder
  ProfileModel        — QAbstractListModel exposing profile steps to QML
  EspressoController  — QObject with properties/signals/slots consumed by QML
"""
import struct
import time
import json
import os
import datetime
import threading
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import (
    QObject, QThread, QTimer, QModelIndex, Qt,
    pyqtSignal, pyqtSlot, pyqtProperty,
    QAbstractListModel,
)

# ---------------------------------------------------------------------------
# Protocol constants  (mirror protocol.h)
# ---------------------------------------------------------------------------
PROTO_SYNC0 = 0xAA
PROTO_SYNC1 = 0x55

PKT_TELEMETRY = 0x01
PKT_ACK       = 0x02
PKT_ERROR     = 0x03
PKT_COMMAND   = 0x10
PKT_PING      = 0x11

# Command opcodes
CMD_POWER_ON  = 0x01
CMD_POWER_OFF = 0x02
CMD_TARE      = 0x03
CMD_STOP      = 0x04
CMD_STEAM_ON  = 0x05
CMD_STEAM_OFF = 0x06
CMD_SET_P     = 0x10
CMD_SET_F     = 0x11
CMD_SET_TW    = 0x12
CMD_SET_TG    = 0x13
CMD_SET_FL    = 0x14
CMD_SET_PL    = 0x15

# Machine state flags
STATE_FLAG_POWERED = 0x01
STATE_FLAG_STEAM   = 0x02

# Packet rates
SAMPLES_PER_PACKET = 10       # samples per telemetry packet → 100 Hz packets

# Struct formats — all little-endian, matching __attribute__((packed)) C structs
_FMT_MACHINE_STATE = '<fffffBBBx'  # 24 bytes: target_val,tw,tg,fl,pl, flags,mode,overruns,pad
_FMT_SAMPLE        = '<Ifffff'     # 24 bytes: timestamp_us, p, f, w, tw, tg
_FMT_COMMAND       = '<BBf'        # 6 bytes:  seq, opcode, value

_MACHINE_STATE_SIZE = struct.calcsize(_FMT_MACHINE_STATE)   # 24
_SAMPLE_SIZE        = struct.calcsize(_FMT_SAMPLE)           # 24
_TELEMETRY_SIZE     = _MACHINE_STATE_SIZE + _SAMPLE_SIZE * SAMPLES_PER_PACKET  # 264

LOG_DIR      = "logs"
PROFILE_FILE = "profiles.json"
CHART_HZ     = 30
STATE_MACHINE_HZ = 20

EXIT_CONDITIONS   = ["Time >", "Weight >", "Pressure >", "Pressure <"]
PREDICTIVE_STOP_G = 2.0

# ---------------------------------------------------------------------------
# Protocol helpers
# ---------------------------------------------------------------------------

def _crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE: poly=0x1021, init=0xFFFF, no reflection."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
        crc &= 0xFFFF
    return crc


def _build_frame(ptype: int, payload: bytes) -> bytes:
    """Wrap payload in the [SYNC0][SYNC1][TYPE][LEN16][PAYLOAD][CRC16] envelope."""
    plen = len(payload)
    header = bytes([PROTO_SYNC0, PROTO_SYNC1, ptype,
                    plen & 0xFF, (plen >> 8) & 0xFF])
    crc_input = bytes([ptype, plen & 0xFF, (plen >> 8) & 0xFF]) + payload
    crc = _crc16(crc_input)
    return header + payload + struct.pack('<H', crc)


# ---------------------------------------------------------------------------
# Parsed data types
# ---------------------------------------------------------------------------

@dataclass
class ParsedSample:
    timestamp_us: int
    pressure:     float
    flow:         float
    weight:       float
    temp_water:   float
    temp_group:   float


@dataclass
class ParsedTelemetry:
    # Machine state snapshot
    target_val:    float
    target_tw:     float
    target_tg:     float
    flow_limit:    float
    pressure_limit: float
    powered:       bool
    steam_on:      bool
    control_mode:  str    # 'P' or 'F'
    overrun_count: int
    # Raw samples
    samples: List[ParsedSample]


def _parse_telemetry(payload: bytes) -> Optional[ParsedTelemetry]:
    if len(payload) < _TELEMETRY_SIZE:
        return None
    tv, ttw, ttg, tfl, tpl, flags, ctrl_byte, overruns = struct.unpack_from(
        _FMT_MACHINE_STATE, payload, 0)
    samples = []
    off = _MACHINE_STATE_SIZE
    for _ in range(SAMPLES_PER_PACKET):
        ts, p, f, w, tw, tg = struct.unpack_from(_FMT_SAMPLE, payload, off)
        samples.append(ParsedSample(ts, p, f, w, tw, tg))
        off += _SAMPLE_SIZE
    ctrl = chr(ctrl_byte) if ctrl_byte in (ord('P'), ord('F')) else 'P'
    return ParsedTelemetry(
        target_val=tv, target_tw=ttw, target_tg=ttg, flow_limit=tfl, pressure_limit=tpl,
        powered=bool(flags & STATE_FLAG_POWERED),
        steam_on=bool(flags & STATE_FLAG_STEAM),
        control_mode=ctrl,
        overrun_count=overruns,
        samples=samples,
    )


# ---------------------------------------------------------------------------
# Frame decoder — state machine that reconstructs frames from a raw byte stream
# ---------------------------------------------------------------------------

class FrameDecoder:
    """Feed raw bytes in; receive (ptype, payload) callbacks for valid frames."""

    _SYNC0, _SYNC1, _TYPE, _LEN0, _LEN1, _PAYLOAD, _CRC0, _CRC1 = range(8)

    def __init__(self, callback):
        self._cb     = callback
        self._state  = self._SYNC0
        self._ptype  = 0
        self._plen   = 0
        self._buf    = bytearray()
        self._crc_lo = 0

    def feed(self, data: bytes):
        for b in data:
            self._step(b)

    def _step(self, b: int):
        s = self._state
        if s == self._SYNC0:
            if b == PROTO_SYNC0: self._state = self._SYNC1
        elif s == self._SYNC1:
            if   b == PROTO_SYNC1: self._state = self._TYPE
            elif b == PROTO_SYNC0: self._state = self._SYNC1  # 0xAA 0xAA...
            else:                  self._state = self._SYNC0
        elif s == self._TYPE:
            self._ptype = b
            self._state = self._LEN0
        elif s == self._LEN0:
            self._plen  = b
            self._state = self._LEN1
        elif s == self._LEN1:
            self._plen |= b << 8
            self._buf   = bytearray()
            self._state = self._PAYLOAD if self._plen > 0 else self._CRC0
        elif s == self._PAYLOAD:
            self._buf.append(b)
            if len(self._buf) == self._plen:
                self._state = self._CRC0
        elif s == self._CRC0:
            self._crc_lo = b
            self._state  = self._CRC1
        elif s == self._CRC1:
            received = self._crc_lo | (b << 8)
            crc_input = (bytes([self._ptype,
                                self._plen & 0xFF,
                                (self._plen >> 8) & 0xFF])
                         + self._buf)
            if received == _crc16(crc_input):
                self._cb(self._ptype, bytes(self._buf))
            self._state = self._SYNC0


# ---------------------------------------------------------------------------
# Mock hardware
# Simulates the MCU: generates binary TELEMETRY frames, decodes binary COMMAND
# frames, and applies the same physics as main.c.
# ---------------------------------------------------------------------------

class MockEspressoMachine:
    def __init__(self):
        self.powered     = False
        self.p = 0.0; self.f = 0.0; self.w = 0.0
        self.tw = 20.0; self.tg = 20.0
        self.tgt_val     = 0.0
        self.ctrl_mode   = 'P'
        self.tgt_tw      = 20.0
        self.tgt_tg      = 20.0
        self.steam       = False
        self.pump_duty   = 0.0
        self.flow_limit     = 0.0
        self.pressure_limit = 0.0
        self._t_us       = 0
        self._overruns   = 0
        self._lock       = threading.Lock()
        self._rx_decoder = FrameDecoder(self._on_command_frame)

    def read(self, max_bytes: int) -> bytes:
        """Block for 10 ms (simulating 1 kHz ISR), return one TELEMETRY frame."""
        time.sleep(SAMPLES_PER_PACKET / 1000.0)
        with self._lock:
            samples = []
            for _ in range(SAMPLES_PER_PACKET):
                self._step(0.001)
                self._t_us += 1000
                samples.append((self._t_us,
                                 self.p, self.f, self.w, self.tw, self.tg))

            flags = (STATE_FLAG_POWERED if self.powered else 0) | \
                    (STATE_FLAG_STEAM   if self.steam   else 0)
            state_bytes = struct.pack(_FMT_MACHINE_STATE,
                                      self.tgt_val, self.tgt_tw,
                                      self.tgt_tg,  self.flow_limit,
                                      self.pressure_limit,
                                      flags, ord(self.ctrl_mode),
                                      self._overruns)
            self._overruns = 0

        sample_bytes = b''.join(struct.pack(_FMT_SAMPLE, *s) for s in samples)
        return _build_frame(PKT_TELEMETRY, state_bytes + sample_bytes)

    def write(self, data: bytes):
        """Accept binary command frames from the Pi."""
        with self._lock:
            self._rx_decoder.feed(data)

    def _on_command_frame(self, ptype: int, payload: bytes):
        if ptype != PKT_COMMAND or len(payload) < 6:
            return
        _seq, opcode = struct.unpack_from('<BB', payload, 0)
        value = struct.unpack_from('<f', payload, 2)[0]
        self._execute(opcode, value)

    def _execute(self, opcode: int, value: float):
        if   opcode == CMD_POWER_ON:  self.powered = True;  self.tgt_tw = 93.0; self.tgt_tg = 93.0
        elif opcode == CMD_POWER_OFF: self.powered = False; self.tgt_val = 0.0; self.steam = False; self.flow_limit = 0.0; self.pressure_limit = 0.0
        elif opcode == CMD_TARE:      self.w = 0.0
        elif opcode == CMD_STOP:      self.tgt_val = 0.0; self.flow_limit = 0.0; self.pressure_limit = 0.0
        elif opcode == CMD_STEAM_ON:  self.steam = True
        elif opcode == CMD_STEAM_OFF: self.steam = False
        elif opcode == CMD_SET_P:     self.ctrl_mode = 'P'; self.tgt_val = value
        elif opcode == CMD_SET_F:     self.ctrl_mode = 'F'; self.tgt_val = value
        elif opcode == CMD_SET_TW:    self.tgt_tw = value
        elif opcode == CMD_SET_TG:    self.tgt_tg = value
        elif opcode == CMD_SET_FL:    self.flow_limit = value
        elif opcode == CMD_SET_PL:    self.pressure_limit = value

    def _step(self, dt: float):
        sp_w = (140.0 if self.steam else self.tgt_tw) if self.powered else 20.0
        sp_g = self.tgt_tg if self.powered else 20.0
        self.tw += (sp_w - self.tw) * 0.5 * dt
        self.tg += (sp_g - self.tg) * 0.5 * dt
        if self.powered:
            cur = self.p if self.ctrl_mode == 'P' else self.f
            self.pump_duty += (self.tgt_val - cur) * 5.0 * dt
            self.pump_duty  = max(0.0, min(12.0, self.pump_duty))
            self.p = self.pump_duty
            if self.pressure_limit > 0:
                self.p = min(self.p, self.pressure_limit)
            self.f = self.p / 1.5
            if self.flow_limit > 0:
                self.f = min(self.f, self.flow_limit)
            self.w += self.f * dt
        else:
            self.p *= 0.9; self.f = 0.0; self.pump_duty = 0.0


# ---------------------------------------------------------------------------
# Serial worker thread
# ---------------------------------------------------------------------------

class SerialWorker(QThread):
    data_available = pyqtSignal(object)   # emits ParsedTelemetry

    def __init__(self):
        super().__init__()
        self.running    = True
        self.connection = MockEspressoMachine()
        self._seq       = 0
        self._tx_lock   = threading.Lock()

    def send_command(self, opcode: int, value: float = 0.0):
        with self._tx_lock:
            payload = struct.pack(_FMT_COMMAND, self._seq, opcode, value)
            self._seq = (self._seq + 1) & 0xFF
        frame = _build_frame(PKT_COMMAND, payload)
        self.connection.write(frame)

    def run(self):
        decoder = FrameDecoder(self._on_frame)
        while self.running:
            try:
                data = self.connection.read(4096)
                if data:
                    decoder.feed(data)
            except Exception:
                time.sleep(0.01)

    def _on_frame(self, ptype: int, payload: bytes):
        if ptype == PKT_TELEMETRY:
            parsed = _parse_telemetry(payload)
            if parsed:
                self.data_available.emit(parsed)
        # ACK frames noted here if needed for command confirmation

    def stop(self):
        self.running = False
        self.wait()


# ---------------------------------------------------------------------------
# Profile model  (unchanged from previous version)
# Step format: [mode, setVal, tw, tg, exitCond, exitVal, rampTime, flowLimit, pressureLimit]
# ---------------------------------------------------------------------------
_DEFAULT_STEPS = [
    ["F", 4.0, 93.0, 93.0, "Time >",      4.0, 0.0, 0.0, 0.0],
    ["P", 4.0, 93.0, 93.0, "Pressure >",  3.5, 2.0, 0.0, 0.0],
    ["P", 9.0, 93.0, 93.0, "Weight >",   36.0, 3.0, 0.0, 0.0],
    ["P", 0.0, 93.0, 93.0, "Time >",      0.1, 0.0, 0.0, 0.0],
]
_BLANK_STEP = ["P", 0.0, 93.0, 93.0, "Time >", 5.0, 0.0, 0.0, 0.0]

class ProfileModel(QAbstractListModel):
    ModeRole      = Qt.ItemDataRole.UserRole + 1
    SetValRole    = Qt.ItemDataRole.UserRole + 2
    TwRole        = Qt.ItemDataRole.UserRole + 3
    TgRole        = Qt.ItemDataRole.UserRole + 4
    ExitCondRole  = Qt.ItemDataRole.UserRole + 5
    ExitValRole   = Qt.ItemDataRole.UserRole + 6
    RampTimeRole  = Qt.ItemDataRole.UserRole + 7
    FlowLimitRole     = Qt.ItemDataRole.UserRole + 8
    PressureLimitRole = Qt.ItemDataRole.UserRole + 9

    def __init__(self):
        super().__init__()
        self._steps = [list(s) for s in _DEFAULT_STEPS]

    def roleNames(self):
        return {
            self.ModeRole:      b'stepMode',
            self.SetValRole:    b'setVal',
            self.TwRole:        b'tw',
            self.TgRole:        b'tg',
            self.ExitCondRole:  b'exitCond',
            self.ExitValRole:   b'exitVal',
            self.RampTimeRole:  b'rampTime',
            self.FlowLimitRole:     b'flowLimit',
            self.PressureLimitRole: b'pressureLimit',
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._steps)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._steps):
            return None
        s = self._steps[index.row()]
        return {
            self.ModeRole:      s[0],
            self.SetValRole:    float(s[1]),
            self.TwRole:        float(s[2]),
            self.TgRole:        float(s[3]),
            self.ExitCondRole:  s[4],
            self.ExitValRole:   float(s[5]),
            self.RampTimeRole:  float(s[6]) if len(s) > 6 else 0.0,
            self.FlowLimitRole:     float(s[7]) if len(s) > 7 else 0.0,
            self.PressureLimitRole: float(s[8]) if len(s) > 8 else 0.0,
        }.get(role)

    @pyqtSlot(int, str)
    def setMode(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][0] = value; self._notify(row, self.ModeRole)

    @pyqtSlot(int, float)
    def setSetVal(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][1] = value; self._notify(row, self.SetValRole)

    @pyqtSlot(int, float)
    def setTw(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][2] = value; self._notify(row, self.TwRole)

    @pyqtSlot(int, float)
    def setTg(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][3] = value; self._notify(row, self.TgRole)

    @pyqtSlot(int, str)
    def setExitCond(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][4] = value; self._notify(row, self.ExitCondRole)

    @pyqtSlot(int, float)
    def setExitVal(self, row, value):
        if 0 <= row < len(self._steps):
            self._steps[row][5] = value; self._notify(row, self.ExitValRole)

    @pyqtSlot(int, float)
    def setRampTime(self, row, value):
        if 0 <= row < len(self._steps):
            while len(self._steps[row]) < 7: self._steps[row].append(0.0)
            self._steps[row][6] = value; self._notify(row, self.RampTimeRole)

    @pyqtSlot(int, float)
    def setFlowLimit(self, row, value):
        if 0 <= row < len(self._steps):
            while len(self._steps[row]) < 8: self._steps[row].append(0.0)
            self._steps[row][7] = value; self._notify(row, self.FlowLimitRole)

    @pyqtSlot(int, float)
    def setPressureLimit(self, row, value):
        if 0 <= row < len(self._steps):
            while len(self._steps[row]) < 9: self._steps[row].append(0.0)
            self._steps[row][8] = value; self._notify(row, self.PressureLimitRole)

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

    def get_data(self):  return [list(s) for s in self._steps]

    def set_data(self, data):
        self.beginResetModel()
        self._steps = [list(s) for s in data]
        self.endResetModel()

    def _notify(self, row, role):
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [role])


# ---------------------------------------------------------------------------
# Main controller — Python/QML bridge
# ---------------------------------------------------------------------------

class EspressoController(QObject):
    pressureChanged          = pyqtSignal(float)
    flowChanged              = pyqtSignal(float)
    weightChanged            = pyqtSignal(float)
    tempWaterChanged         = pyqtSignal(float)
    tempGroupChanged         = pyqtSignal(float)
    poweredChanged           = pyqtSignal(bool)
    steamOnChanged           = pyqtSignal(bool)
    flushOnChanged           = pyqtSignal(bool)
    profileRunningChanged    = pyqtSignal(bool)
    statusTextChanged        = pyqtSignal(str)
    stepIndexChanged         = pyqtSignal(int)
    elapsedTimeChanged       = pyqtSignal(float)
    savedProfileNamesChanged = pyqtSignal('QVariantList')
    doseChanged              = pyqtSignal(float)
    brewRatioChanged         = pyqtSignal(float)
    readyStateChanged        = pyqtSignal()
    shotHistoryChanged       = pyqtSignal()
    shotLogDataReady         = pyqtSignal()

    newDataPoint             = pyqtSignal(float, float, float, float, float, float)
    sessionStarted           = pyqtSignal()
    previousShotReady        = pyqtSignal()
    currentStepTargetChanged = pyqtSignal(float)
    shotAvailableChanged     = pyqtSignal(bool)
    shotSaved                = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._pressure    = 0.0
        self._flow        = 0.0
        self._weight      = 0.0
        self._temp_water  = 20.0
        self._temp_group  = 20.0
        self._powered     = False
        self._steam_on    = False
        self._flush_on    = False
        self._profile_running = False
        self._status_text = "STANDBY"
        self._step_index  = 0
        self._elapsed_time = 0.0
        self._saved_profile_names = []
        self._dose_g      = 18.0
        self._brew_ratio  = 0.0

        self._t0             = time.monotonic()
        self._session_start  = None
        self._active_profile = []
        self._current_step_idx = 0
        self._step_start_time  = 0.0
        self._is_heating       = False
        self._saved_profiles   = {}

        self._recording       = False
        self._shot_times      = []; self._shot_pressures = []
        self._shot_flows      = []; self._shot_weights   = []
        self._shot_tw         = []; self._shot_tg        = []
        self._shot_available  = False
        self._ghost_history   = []

        self._last_log_fname  = ""
        self._pending_rating  = 0
        self._pending_notes   = ""
        self._shot_history_list = []
        self._loaded_shot_times     = []
        self._loaded_shot_pressures = []
        self._loaded_shot_flows     = []
        self._loaded_shot_weights   = []
        self._loaded_shot_tw        = []
        self._loaded_shot_tg        = []

        self._current_step_target = 0.0
        self._ramp_start    = 0.0
        self._ramp_target   = 0.0
        self._ramp_duration = 0.0
        self._ready_state   = []

        self._profile_model = ProfileModel()

        self._worker = SerialWorker()
        self._worker.data_available.connect(self._on_data)
        self._worker.start()

        self._state_timer = QTimer()
        self._state_timer.timeout.connect(self._run_state_machine)
        self._state_timer.start(1000 // STATE_MACHINE_HZ)

        self._chart_timer = QTimer()
        self._chart_timer.timeout.connect(self._emit_chart_point)
        self._chart_timer.start(1000 // CHART_HZ)

        self._load_profiles()

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------
    @pyqtProperty(float, notify=pressureChanged)
    def pressure(self):       return self._pressure

    @pyqtProperty(float, notify=flowChanged)
    def flow(self):           return self._flow

    @pyqtProperty(float, notify=weightChanged)
    def weight(self):         return self._weight

    @pyqtProperty(float, notify=tempWaterChanged)
    def tempWater(self):      return self._temp_water

    @pyqtProperty(float, notify=tempGroupChanged)
    def tempGroup(self):      return self._temp_group

    @pyqtProperty(bool, notify=poweredChanged)
    def powered(self):        return self._powered

    @pyqtProperty(bool, notify=steamOnChanged)
    def steamOn(self):        return self._steam_on

    @pyqtProperty(bool, notify=flushOnChanged)
    def flushOn(self):        return self._flush_on

    @pyqtProperty(bool, notify=profileRunningChanged)
    def profileRunning(self): return self._profile_running

    @pyqtProperty(str, notify=statusTextChanged)
    def statusText(self):     return self._status_text

    @pyqtProperty(int, notify=stepIndexChanged)
    def stepIndex(self):      return self._step_index

    @pyqtProperty(float, notify=elapsedTimeChanged)
    def elapsedTime(self):    return self._elapsed_time

    @pyqtProperty('QVariantList', notify=savedProfileNamesChanged)
    def savedProfileNames(self): return self._saved_profile_names

    @pyqtProperty(float, notify=currentStepTargetChanged)
    def currentStepTarget(self): return self._current_step_target

    @pyqtProperty(bool, notify=shotAvailableChanged)
    def shotAvailable(self):  return self._shot_available

    @pyqtProperty(float, notify=doseChanged)
    def dose(self):           return self._dose_g

    @pyqtProperty(float, notify=brewRatioChanged)
    def brewRatio(self):      return self._brew_ratio

    @pyqtProperty('QVariantList', notify=previousShotReady)
    def ghostHistory(self):   return self._ghost_history

    @pyqtProperty('QVariantList', notify=readyStateChanged)
    def readyState(self):     return self._ready_state

    @pyqtProperty(str, notify=shotSaved)
    def lastLogFname(self):   return self._last_log_fname

    @pyqtProperty('QVariantList', notify=shotHistoryChanged)
    def shotHistory(self):    return self._shot_history_list

    @pyqtProperty('QVariantList', notify=shotLogDataReady)
    def loadedShotTimes(self):     return self._loaded_shot_times

    @pyqtProperty('QVariantList', notify=shotLogDataReady)
    def loadedShotPressures(self): return self._loaded_shot_pressures

    @pyqtProperty('QVariantList', notify=shotLogDataReady)
    def loadedShotFlows(self):     return self._loaded_shot_flows

    @pyqtProperty('QVariantList', notify=shotLogDataReady)
    def loadedShotWeights(self):   return self._loaded_shot_weights

    @pyqtProperty('QVariantList', notify=shotLogDataReady)
    def loadedShotTw(self):        return self._loaded_shot_tw

    @pyqtProperty('QVariantList', notify=shotLogDataReady)
    def loadedShotTg(self):        return self._loaded_shot_tg

    @pyqtProperty(QObject, constant=True)
    def profileModel(self):   return self._profile_model

    # -----------------------------------------------------------------------
    # Private helpers
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
    # Data handler — called from SerialWorker via Qt signal
    # -----------------------------------------------------------------------
    def _on_data(self, telemetry: ParsedTelemetry):
        last = telemetry.samples[-1]
        self._set('_pressure',   last.pressure,   self.pressureChanged,  2)
        self._set('_flow',       last.flow,        self.flowChanged,      2)
        self._set('_weight',     last.weight,      self.weightChanged,    1)
        self._set('_temp_water', last.temp_water,  self.tempWaterChanged, 1)
        self._set('_temp_group', last.temp_group,  self.tempGroupChanged, 1)

        new_ratio = round(self._weight / self._dose_g, 2) if self._dose_g > 0 else 0.0
        if new_ratio != self._brew_ratio:
            self._brew_ratio = new_ratio
            self.brewRatioChanged.emit(new_ratio)

        if self._session_start is not None:
            t = time.monotonic() - self._session_start
            self._elapsed_time = t
            self.elapsedTimeChanged.emit(t)

        self._update_ready_state()

    def _emit_chart_point(self):
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
    # Ready-state helper
    # -----------------------------------------------------------------------
    def _update_ready_state(self):
        steps = self._profile_model._steps
        target_tw = float(steps[0][2]) if steps else 93.0
        target_tg = float(steps[0][3]) if steps else 93.0
        n = self._profile_model.rowCount()
        temp_ok = (self._powered
                   and abs(self._temp_water - target_tw) < 3
                   and abs(self._temp_group - target_tg) < 3)
        new = [
            {"label": "Power",   "ok": self._powered,           "detail": ""},
            {"label": "Temp",    "ok": temp_ok,                 "detail": f"{self._temp_water:.0f}°"},
            {"label": "Scale",   "ok": abs(self._weight) < 1.0, "detail": f"{self._weight:.1f}g"},
            {"label": "Profile", "ok": n > 0,                   "detail": f"{n} steps"},
        ]
        if new != self._ready_state:
            self._ready_state = new
            self.readyStateChanged.emit()

    # -----------------------------------------------------------------------
    # Profile state machine
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
                self._t0 = self._session_start
                self._recording = True
                self._shot_times.clear();     self._shot_pressures.clear()
                self._shot_flows.clear();     self._shot_weights.clear()
                self._shot_tw.clear();        self._shot_tg.clear()
                self._last_log_fname  = ""
                self._pending_rating  = 0
                self._pending_notes   = ""
                if self._shot_available:
                    self._shot_available = False
                    self.shotAvailableChanged.emit(False)
                self.sessionStarted.emit()
                self._execute_step(self._active_profile[0])
                self._update_step_index(0)
                self._set_status(f"STEP 1 / {len(self._active_profile)}")
            else:
                self._worker.send_command(CMD_STOP)
                self._worker.send_command(CMD_SET_TW, tgt_tw)
                self._worker.send_command(CMD_SET_TG, tgt_tg)
                self._set_status(f"HEATING  {self._temp_water:.0f}° → {tgt_tw:.0f}°")
            return

        if self._current_step_idx >= len(self._active_profile):
            self.stopProfile()
            return

        elapsed = time.monotonic() - self._step_start_time
        step    = self._active_profile[self._current_step_idx]
        trig, val = step[4], float(step[5])

        if self._ramp_duration > 0 and elapsed < self._ramp_duration:
            frac   = elapsed / self._ramp_duration
            ramped = self._ramp_start + (self._ramp_target - self._ramp_start) * frac
            cmd = CMD_SET_P if step[0] == 'P' else CMD_SET_F
            self._worker.send_command(cmd, ramped)

        w_thresh  = val - PREDICTIVE_STOP_G if trig == "Weight >" else val
        next_step = (
            (trig == "Time >"      and elapsed >= val) or
            (trig == "Weight >"    and self._weight >= w_thresh) or
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
        self._ramp_target     = float(step[1])
        self._ramp_duration   = float(step[6]) if len(step) > 6 else 0.0
        mode_cmd = CMD_SET_P if step[0] == 'P' else CMD_SET_F
        if self._ramp_duration > 0:
            self._ramp_start = self._pressure if step[0] == 'P' else self._flow
            self._worker.send_command(mode_cmd, self._ramp_start)
        else:
            self._ramp_start = float(step[1])
            self._worker.send_command(mode_cmd, float(step[1]))
        self._worker.send_command(CMD_SET_TW, float(step[2]))
        self._worker.send_command(CMD_SET_TG, float(step[3]))
        self._worker.send_command(CMD_SET_FL, float(step[7]) if len(step) > 7 else 0.0)
        self._worker.send_command(CMD_SET_PL, float(step[8]) if len(step) > 8 else 0.0)
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
            self._worker.send_command(CMD_POWER_ON)
            self._set_status("IDLE")
        else:
            if self._profile_running: self.stopProfile()
            if self._flush_on:        self.stopFlush()
            if self._steam_on:
                self._steam_on = False
                self._worker.send_command(CMD_STEAM_OFF)
                self.steamOnChanged.emit(False)
            self._worker.send_command(CMD_POWER_OFF)
            self._set_status("STANDBY")
        self._update_ready_state()

    @pyqtSlot()
    def tare(self):
        self._worker.send_command(CMD_TARE)
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
            self._worker.send_command(CMD_TARE)
            self.profileRunningChanged.emit(True)
            self._update_step_index(0)
            self._set_status("HEATING...")

    @pyqtSlot()
    def stopProfile(self):
        self._profile_running = False
        self._is_heating      = False
        if self._recording and len(self._shot_times) > 0:
            n    = len(self._shot_times)
            step = max(1, n // 300)
            self._ghost_history.insert(0, {
                "t": list(self._shot_times[::step]),
                "p": list(self._shot_pressures[::step]),
                "f": list(self._shot_flows[::step]),
                "w": list(self._shot_weights[::step]),
            })
            if len(self._ghost_history) > 3:
                self._ghost_history = self._ghost_history[:3]
            self.previousShotReady.emit()
            self._shot_available = True
            self.shotAvailableChanged.emit(True)
        self._recording = False
        self._worker.send_command(CMD_STOP)
        self.profileRunningChanged.emit(False)
        self._update_step_target(0.0)
        self._set_status("IDLE")

    @pyqtSlot()
    def startFlush(self):
        if not self._powered:
            return
        self._flush_on      = True
        self._session_start = time.monotonic()
        self._t0            = self._session_start
        self.sessionStarted.emit()
        self._worker.send_command(CMD_SET_P, 3.0)
        self.flushOnChanged.emit(True)
        self._set_status("FLUSHING")

    @pyqtSlot()
    def stopFlush(self):
        self._flush_on = False
        self._worker.send_command(CMD_STOP)
        self.flushOnChanged.emit(False)
        self._set_status("IDLE")

    @pyqtSlot()
    def toggleSteam(self):
        self._steam_on = not self._steam_on
        self._worker.send_command(CMD_STEAM_ON if self._steam_on else CMD_STEAM_OFF)
        self.steamOnChanged.emit(self._steam_on)

    @pyqtSlot(float)
    def setDose(self, val: float):
        val = round(max(1.0, min(40.0, val)), 1)
        if val != self._dose_g:
            self._dose_g = val
            self.doseChanged.emit(val)

    @pyqtSlot(str)
    def saveProfile(self, name):
        if not name: return
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
        if not self._shot_times:
            return
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            ts    = time.strftime("%Y-%m-%d_%H-%M-%S")
            fname = os.path.join(LOG_DIR, f"shot_{ts}.csv")
            n  = len(self._shot_times)
            tw = self._shot_tw if len(self._shot_tw) == n else [0.0] * n
            tg = self._shot_tg if len(self._shot_tg) == n else [0.0] * n
            with open(fname, 'w') as f:
                f.write("time_s,pressure_bar,flow_mls,weight_g,temp_water_c,temp_group_c\n")
                for i in range(n):
                    f.write(f"{self._shot_times[i]:.3f},"
                            f"{self._shot_pressures[i]:.3f},"
                            f"{self._shot_flows[i]:.3f},"
                            f"{self._shot_weights[i]:.3f},"
                            f"{tw[i]:.2f},{tg[i]:.2f}\n")
            self._last_log_fname = os.path.basename(fname)
            duration = (self._shot_times[-1] - self._shot_times[0]
                        if len(self._shot_times) > 1 else 0.0)
            yield_g = self._shot_weights[-1] if self._shot_weights else 0.0
            ratio   = round(yield_g / self._dose_g, 2) if self._dose_g > 0 else 0.0
            meta = {
                "dose_g":     self._dose_g,
                "yield_g":    round(yield_g, 1),
                "ratio":      ratio,
                "duration_s": round(duration, 1),
                "rating":     self._pending_rating,
                "notes":      self._pending_notes,
            }
            self._pending_rating = 0
            self._pending_notes  = ""
            with open(fname.replace(".csv", "_meta.json"), 'w') as f:
                json.dump(meta, f, indent=2)
            self.shotSaved.emit(os.path.basename(fname))
        except Exception as e:
            self.shotSaved.emit(f"ERROR: {e}")

    @pyqtSlot(int, str)
    def saveShotNotes(self, rating: int, notes: str):
        if not self._last_log_fname:
            self._pending_rating = rating
            self._pending_notes  = notes
            return
        try:
            meta_path = os.path.join(
                LOG_DIR, self._last_log_fname.replace(".csv", "_meta.json"))
            meta = {}
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)
            meta["rating"] = rating
            meta["notes"]  = notes
            with open(meta_path, 'w') as f:
                json.dump(meta, f, indent=2)
            self.shotSaved.emit("notes_saved")
        except Exception as e:
            self.shotSaved.emit(f"ERROR: {e}")

    @pyqtSlot(str, int, str)
    def saveHistoryNotes(self, filename: str, rating: int, notes: str):
        try:
            meta_path = os.path.join(LOG_DIR, filename.replace(".csv", "_meta.json"))
            meta = {}
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)
            meta["rating"] = rating
            meta["notes"]  = notes
            with open(meta_path, 'w') as f:
                json.dump(meta, f, indent=2)
            self.shotSaved.emit("notes_saved")
        except Exception as e:
            self.shotSaved.emit(f"ERROR: {e}")

    @pyqtSlot()
    def refreshShotHistory(self):
        try:
            if not os.path.exists(LOG_DIR):
                self._shot_history_list = []
                self.shotHistoryChanged.emit()
                return
            entries = []
            for fname in os.listdir(LOG_DIR):
                if not fname.endswith("_meta.json"):
                    continue
                try:
                    with open(os.path.join(LOG_DIR, fname)) as f:
                        meta = json.load(f)
                    ts_str = fname[5:-10]
                    try:
                        dt = datetime.datetime.strptime(ts_str, "%Y-%m-%d_%H-%M-%S")
                        ts_display = dt.strftime("%b %d %Y  %H:%M")
                        ts_sort    = dt.timestamp()
                    except Exception:
                        ts_display = ts_str; ts_sort = 0
                    entries.append({
                        "filename":          fname.replace("_meta.json", ".csv"),
                        "timestamp_display": ts_display,
                        "dose_g":            meta.get("dose_g",     0.0),
                        "yield_g":           meta.get("yield_g",    0.0),
                        "ratio":             meta.get("ratio",       0.0),
                        "duration_s":        meta.get("duration_s", 0.0),
                        "rating":            meta.get("rating",      0),
                        "notes":             meta.get("notes",       ""),
                        "_ts":               ts_sort,
                    })
                except Exception:
                    continue
            entries.sort(key=lambda e: e["_ts"], reverse=True)
            for e in entries: del e["_ts"]
            self._shot_history_list = entries
            self.shotHistoryChanged.emit()
        except Exception:
            pass

    @pyqtSlot(str)
    def loadShotLog(self, filename: str):
        try:
            path = os.path.join(LOG_DIR, filename)
            times=[]; pressures=[]; flows=[]; weights=[]; tw_list=[]; tg_list=[]
            with open(path) as f:
                next(f)
                for line in f:
                    p = line.strip().split(",")
                    if len(p) < 6: continue
                    times.append(float(p[0]));     pressures.append(float(p[1]))
                    flows.append(float(p[2]));     weights.append(float(p[3]))
                    tw_list.append(float(p[4]));   tg_list.append(float(p[5]))
            self._loaded_shot_times     = times
            self._loaded_shot_pressures = pressures
            self._loaded_shot_flows     = flows
            self._loaded_shot_weights   = weights
            self._loaded_shot_tw        = tw_list
            self._loaded_shot_tg        = tg_list
            self.shotLogDataReady.emit()
        except Exception:
            pass

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

    def shutdown(self):
        self._state_timer.stop()
        self._chart_timer.stop()
        self._worker.stop()
