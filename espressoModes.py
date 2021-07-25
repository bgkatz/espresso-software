### Espresso Machine Mode Functions ###
# Each mode has the inputs:
#   espressoMachineState: sensor measurements, etc.
#   uiInput: inputs from the GUI
# and outputs:
#   espressoMachineCommands: commands to the macine - pressure, temperature, etc.
#   displayData: data to be shown by the GUI

from espressoMachine import *

class displayData():
    def __init__(self):
        pass

class idleMode():
    # Idle mode does nothing #
    def __init__(self):
        pass
    def run(self, state, cmds):
        cmds.cmd_vec = np.zeros([5])
        print('running idle mode')

class manualMode():
    def __init__(self):
        self.cmds = espressoMachineCommands()
    def run(self, state, cmds):
        cmds = self.cmds

class nineBarShot():
    # Standard 9-bar shot with 1-bar pre-infusion
    def __init__(self):
        self.preheatDone = False
        self.piDone = False
        self.shotDone = False

        self.t_start = 0
        self.t_pi = 10.0
        self.water_temp = 93.0
        self.group_temp = 93.0
        self.preheat_flow = 1.0
        self.pi_pressure = 1.0
        self.shot_presure = 1.0
        self.shot_weight = 32.0

    def run(self, state, cmds):
        if(!self.preheatDone):
            self.preheat(state, cmds)
        elif(!self.piDone):
            self.preinfuse(state, cmds)
        elif(!self.shotDOne):
            self.shot(state, cmds)
        else:
            self.end(state, cmds)

    def preheat(self, state, cmds):
        self.cmds.setFlowDir(0)                     # flow to tank during preheat
        self.cmds.setPumpCmdType(2)                 # pump in flow control
        self.cmds.setPumpCmd(self.preheat_flow)     # preheat flow
        self.cmds.setWaterTempCmd(self.water_temp)  # heat water
        self.cmds.setGroupTempCmd(self.group_temp)  # heat group 
        if ((state.waterTemp()>=self.water_temp) and (state.groupTemp()>=self.group_temp)):
            self.t_start = state.time()
            self.preheatDone = True

    def preinfuse(self, state, cmds):
        self.cmds.setFlowDir(1)                     # flow to group
        self.cmds.setPumpCmdType(1)                 # pump in pressure control
        self.cmds.setPumpCmd(self.pi_pressure)      # preinfusion pressure
        if(state.time() > (self.start_time + self.t_pi)):
            self.cmds.tare(1)                       # tare scale after preinfusion
            self.piDone = True
        
    def shot(self, state, cmds):
        self.cmds.setPumpCmd(self.shot_pressure)    # shot pressure
        if(state.weight()>self.shot_weight):
            self.shotDone = True

    def end(self, state, cmds):
        self.cmds.setPumpCmd(0)                     # zero pressure command
        self.cmds.setFlowDir(3)                     # Bleed group to drip tray