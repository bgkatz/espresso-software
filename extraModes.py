from espressoMachine import *
import time
import math

class bodeMode():
    def __init__(self):
        self.title = 'Temperature Bode Plot'
        self.w = 0.0
        self.t_start = 0
        self.t_last = 0
        self.waterTempCmd = 0
        self.groupTempCmd = 0
    def run(self, em, ui, accel = 1.0, mag = 100.0, bias = 300.0):
        em.log_enabled = True
        em.cmd.setFlowDir(0)        # flow to tank
        em.cmd.setPumpCmdType(2)    # flow control
        new_time = time.time()
        dt = new_time - self.t_last
        self.t_last = new_time
        self.w += accel*dt
        self.groupTempCmd = mag*sin(self.w) + bias
        em.cmd.setPumpCmd(flowCmd)
        em.cmd.setWaterTempCmd(self.waterTempCmd)
        em.cmd.setGroupTempCmd(self.groupTempCmd)
    def start(self):
        self.t_start = time.time()
        self.t_last = t_start
        self.w = 0.0
    def stop(self, em):
        em.log_enabled = False
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
    def exit(self, em):
        em.cmd.cmd_vec = np.zeros(em.cmd.cmd_vec.shape)
        em.log_enabled = False
        em.clearLog()
        return True