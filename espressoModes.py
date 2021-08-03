### Espresso Machine Mode Functions ###
# Each mode has the inputs:
#   espressoMachineState: sensor measurements, etc.
#   ui Input: inputs from the GUI
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
        cmds.cmd_vec = np.zeros(cmds.cmd_vec.shape)
        #print('running idle mode')

class preheatMode():
    # Cycles water through tank and heats #
    def __init__(self):
        pass
    def run(self, state, cmds, waterTempCmd=93.0, groupTempCmd=93.0, flowCmd=2.0):
        cmds.setFlowDir(0)          # flow to tank
        cmds.setPumpCmdTypoe(2)     # flow control
        cmds.setPumpCmd(flowCmd) 
        cmds.setWaterTempCmd(waterTempCmd)
        cmds.setGroupTempCMd(groupTempCmd)

class flushMode():
    # Flushes water through group #
    def __init__(self):
        pass
    def run(self, state, cmds, flowCmd = 4.0):
        cmds.setFlowDir(1)      # flow to group
        cmds.setPumpCmdType(2)  # flow control
        cmds.setPumpCmd(flowCmd)

class manualMode():
    # Manual control from GUI #
    def __init__(self):
        self.cmds = espressoMachineCommands()
    def run(self, state, cmds):
        cmds = self.cmds

class nineBarShot():
    # Standard 9-bar shot with 1-bar pre-infusion
    def __init__(self):
        self.preheat_done = False
        self.pi_done = False
        self.shot_done = False
        self.done = False

        self.t_start = 0
        self.t_pi = 10.0
        self.water_temp = 15.0
        self.group_temp = 15.0
        self.preheat_flow = 2.0
        self.pi_flow = 4.0
        self.pi_end_pressure = 2.0;
        self.shot_pressure = 2.0
        self.shot_weight = 32.0

    def run(self, state, cmds):
        if(not self.preheat_done):
            self.preheat(state, cmds)
        elif(not self.pi_done):
            self.preinfuse(state, cmds)
        elif(not self.shot_done):
            self.shot(state, cmds)
        else:
            self.end(state, cmds)

    def preheat(self, state, cmds):
        print('preheating.  wt: ', state.waterTemp(), ' gt ', state.groupTemp())
        cmds.setFlowDir(0)                     # flow to tank during preheat
        cmds.setPumpCmdType(2)                 # pump in flow control
        cmds.setPumpCmd(self.preheat_flow)     # preheat flow
        cmds.setWaterTempCmd(self.water_temp)  # heat water
        cmds.setGroupTempCmd(self.group_temp)  # heat group 
        if ((state.waterTemp() >= self.water_temp) and (state.groupTemp() >= self.group_temp)):
            self.t_start = state.time()
            self.preheat_done = True

    def preinfuse(self, state, cmds):
        print('preinfusion.  flow: ', state.flow(), ' pr ', state.pressure())
        if((state.time()-self.t_start)<1.0):
            cmds.setFlowDir(2)
        else:
            cmds.setFlowDir(1)                     # flow to group
        cmds.setPumpCmdType(2)                 # pump in pressure control
        cmds.setPumpCmd(self.pi_flow)      # preinfusion flow
        #if(state.time() > (self.t_start + self.t_pi)):
        if(state.pressure() >= self.pi_end_pressure):
            cmds.tare(1)                       # tare scale after preinfusion
            time.sleep(.2)
            self.pi_done = True
        
    def shot(self, state, cmds):
        print('shot.  flow: ', state.flow(), ' pr ', state.pressure(), ' w ', state.weight())
        cmds.setPumpCmdType(1)
        cmds.setPumpCmd(self.shot_pressure)    # shot pressure
        if(state.weight()>self.shot_weight):
            self.shot_done = True

    def end(self, state, cmds):
        print('done')
        cmds.setPumpCmd(0)                     # zero pressure command
        time.sleep(1)
        cmds.setFlowDir(2)                     # Bleed group to drip tray
        time.sleep(1)
        cmds.setFlowDir(0)
        self.done = True