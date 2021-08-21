### Espresso Machine Mode Functions ###
# Each mode has the inputs:
#   espressoMachineState: sensor measurements, etc.
#   ui Input: inputs from the GUI
# and outputs:
#   espressoMachineCommands: commands to the macine - pressure, temperature, etc.

from espressoMachine import *

class idleMode():
    # Idle mode does nothing #
    def __init__(self):
        self.title = 'Idle'
    def run(self, em, ui):
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
        #print('running idle mode')
    def start(self):
        pass
    def stop(self, em):
        self.run(em, False)
    def exit(self, em):
        return True

class preheatMode():
    # Cycles water through tank and heats #
    def __init__(self):
        self.title = 'Preheat'
        self.flowCmd = 2.0
        self.tempCmd = 0.0
    def run(self, em, ui):
        em.cmd.setFlowDir(0)          # flow to tank
        em.cmd.setPumpCmdType(2)     # flow control
        em.cmd.setPumpCmd(self.flowCmd) 
        em.cmd.setWaterTempCmd(self.tempCmd)
        em.cmd.setGroupTempCmd(self.tempCmd)
    def start(self):
        pass
    def stop(self, em):
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
    def exit(self, em):
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
        return True

class flushMode():
    # Flushes water through group #
    def __init__(self):
        self.title = 'Flush'
    def run(self, em, ui, flowCmd = 4.0):
        em.cmd.setFlowDir(1)      # flow to group
        em.cmd.setPumpCmdType(2)  # flow control
        em.cmd.setPumpCmd(flowCmd)
    def start(self):
        pass
    def stop(self, em):
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
    def exit(self, em):
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
        return True

class manualMode():
    # Manual control from GUI #
    def __init__(self):
        self.title = 'Manual'
        self.cmds = esspressoMachineCommands()
    def run(self, em, ui):
        em.cmd = self.cmds
    def start(self):
        em.log_enabled = True
    def stop(self, em):
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
        em.log_enabled = False
    def exit(self, em):
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
        em.log_enabled = False
        return True

class preheatPlot():
    def __init__(self):
        self.title = 'Plot Preheat'
    def run(self, em, ui, flowCmd = 2.0, waterTempCmd = 20.0, groupTempCmd = 90.0):
        em.log_enabled = True
        em.cmd.setFlowDir(0)        # flow to tank
        em.cmd.setPumpCmdType(2)    # flow control
        em.cmd.setPumpCmd(flowCmd)
        em.cmd.setWaterTempCmd(waterTempCmd)
        em.cmd.setGroupTempCmd(groupTempCmd)
    def start(self):
        pass
    def stop(self, em):
        em.log_enabled = False
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
    def exit(self, em):
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
        em.log_enabled = False
        em.clearLog()
        return True

class nineBarShot():
    # Standard 9-bar shot with 1-bar pre-infusion
    def __init__(self):
        self.title = 'Nine Bar - Flow Preinfusion'
        self.started = False
        self.preheat_done = False
        self.pi_done = False
        self.shot_done = False
        self.done = False

        self.t_start = 0
        self.t_pi = 10.0
        self.water_temp = 15.0
        self.group_temp = 60.0
        self.preheat_flow = 2.0
        self.pi_flow = 0.0
        self.pi_end_pressure = 6.0
        self.shot_pressure = 6.0
        self.shot_weight = 32.0
        self.temp_tol = 50

    def run(self, em, ui):
        if(not self.started):
            pass
        elif(not self.preheat_done):
            self.preheat(em)
        elif(not self.pi_done):
            self.preinfuse(em)
        elif(not self.shot_done):
            self.shot(em)
        elif(not self.done):
            self.end(em)
        else:
            pass

    def stop(self, em):
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
        self.pi_flow = 0.00
        em.log_enabled = False

    def start(self):
        self.preheat_done = False
        self.pi_done = False
        self.shot_done = False
        self.done = False
        self.started = True

    def exit(self, em):
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
        return True

    def preheat(self, em):
        em.clearLog()
        #print('preheating.  wt: ', em.state.waterTemp(), ' gt ', em.state.groupTemp())
        em.cmd.setFlowDir(0)                     # flow to tank during preheat
        em.cmd.setPumpCmdType(2)                 # pump in flow control
        em.cmd.setPumpCmd(self.preheat_flow)     # preheat flow
        em.cmd.setWaterTempCmd(self.water_temp)  # heat water
        em.cmd.setGroupTempCmd(self.group_temp)  # heat group 
        em.cmd.tare(1)
        if ((np.abs(em.state.waterTemp() - self.water_temp)<self.temp_tol) and (np.abs(em.state.groupTemp() - self.group_temp)<self.temp_tol)):
            self.t_start = em.state.time()
            self.preheat_done = True

    def preinfuse(self, em):
        #print('preinfusion.  flow: ', em.state.flow(), ' pr ', em.state.pressure())
        if((em.state.time()-self.t_start)<2.0): # flow to drip tray to purge air
            em.cmd.setFlowDir(2)
        else:
            em.log_enabled = True
            em.cmd.setFlowDir(1)                     # flow to group
            self.pi_flow += .01
        em.cmd.setPumpCmdType(2)                 # pump in flow control
        em.cmd.setPumpCmd(self.pi_flow)      # preinfusion flow
        #if(state.time() > (self.t_start + self.t_pi)):
        em.cmd.tare(1)
        if(em.state.pressure() >= self.pi_end_pressure):
            em.cmd.tare(1)                       # tare scale after preinfusion
            self.pi_done = True
        
    def shot(self, em):
        #print('shot.  flow: ', em.state.flow(), ' pr ', em.state.pressure(), ' w ', em.state.weight())
        em.cmd.setPumpCmdType(1)
        em.cmd.setPumpCmd(self.shot_pressure)    # shot pressure
        if(em.state.weight()>self.shot_weight):
            self.shot_done = True

    def end(self, em):
        print('done')
        em.log_enabled = False
        em.cmd.setFlowDir(2)                     # Bleed group to drip tray
        em.cmd.setPumpCmd(0)                     # zero pressure command
        #time.sleep(1.0)
        time.sleep(2.0)
        em.cmd.setFlowDir(0)
        em.cmd.setPumpCmdType(0)
        self.pi_flow = 0
        self.done = True
        self.started = False


