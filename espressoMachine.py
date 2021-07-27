### Espresso Machine Interface ###

# Commands:
# Pump command
# Water temperature command
# Group temperature command
# Pump command type (0=Disabled, 1=Pressure (bar), 2=Flow (mL/s), 3=Velocity (rad/s), 4=torque (N-m))
# Flow direction (0=Tank, 1=Group, 2=Drip, 3=Spout, 4=Steam)
# Tare (1 = tare)

# State: 
# Sample timestamp
# Pressure                  (Bar)
# Flow                      (mL/s)
# Water Temp                (C)
# Heater Temp               (C)
# Group Temp                (C)
# Pump velocity             (rad/s)
# Pump torque command       (N-m)
# Pump torque               (N-m)
# Weight since scale tare   (g)

from espressoComm import *

import time
import numpy as np 
import scipy
import threading

logdir = 'logs/'
pID = 1155
vID = 0xC1B0

class espressoMachineState():
    # Sensor measurements and estimates #

    def __init__(self):
        self.state_vec = np.zeros([10])
    def time(self):
        return self.state_vec[0]
    def pressure(self):
        return self.state_vec[1]
    def flow(self):
        return self.state_vec[2]
    def waterTemp(self):
        return self.state_vec[3]
    def heaterTemp(self):
        return self.state_vec[4]
    def groupTemp(self):
        return self.state_vec[5]
    def pumpVel(self):
        return self.state_vec[6]
    def pumpTorqueCmd(self):
        return self.state_vec[7]
    def pumpTorque(self):
        return self.state_vec[8]
    def weight(self):
        return self.state_vec[9]

class esspressoMachineCommands():
    # Commands #
    def __init__(self):
        self.cmd_vec = np.zeros([6])

    def setCommands(pumpCmd, waterTempCmd, groupTempCmd, pumpCmdType, flowDir, tare):
        self.cmd_vec = np.array([pumpCmd, waterTempCmd, groupTempCmd, pumpCmdType, flowDir, tare])
    def setPumpCmd(self, cmd):
        self.cmd_vec[0] = cmd
    def setWaterTempCmd(self, cmd):
        self.cmd_vec[1] = cmd
    def setGroupTempCmd(self, cmd):
        self.cmd_vec[2] = cmd
    def setPumpCmdType(self, cmd):
        self.cmd_vec[3] = cmd
    def setFlowDir(self, cmd):
        self.cmd_vec[4] = cmd
    def tare(self, cmd):
        self.cmd_vec[5] = cmd


class espressoMachine():
    # Machine interface #

    def __init__(self):
        self.comm = espressoComm(pID, vID)
        self.state = espressoMachineState()
        self.cmd = esspressoMachineCommands()
        self.log = np.zeros((np.hstack((self.cmd.cmd_vec, self.state.state_vec))).shape);
        self.log_enabled = False

        # IO thread #
        self.io_thread = threading.Thread(target = self.ioLoop)
        self.io_thread.daemon = True
        self.io_thread.start()


    def sample(self):
        # Read data from USB, update machine.state #
        self.comm.read()
        self.state.state_vec = np.array(self.comm.in_floats[0:10])

    def sendCommands(self):
        # Send cmds over USB #
        self.comm.out_floats = self.cmd.cmd_vec
        self.comm.write()
        self.cmd.tare(0)    # reset tare to zero

    def logState(self):
        # Append current state to log #
        row = np.hstack((self.cmd.cmd_vec, self.state.state_vec))
        if(np.all(self.log==0)):
            self.log = row
        else:
            self.log = np.vstack((self.log, row))

    def clearLog(self):
        # Empties the log #
        self.log = np.zeros((np.hstack((self.cmd.cmd_vec, self.state.state_vec))).shape);

    def saveLog(self):
        # Save log data to CSV #
        filename = logdir + time.strftime("%Y%m%d-%H%M%S") + '.csv'
        np.savetxt(filename, self.log, delimiter=',')

    def ioLoop(self):
        while(True):
            self.sample()
            self.sendCommands()
            if(self.log_enabled):
                self.logState()
