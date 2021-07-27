from espressoMachine import *
from espressoModes import *
import time

x = espressoMachine()
x.cmd.setFlowDir(2)     # flow to drip tray
x.cmd.setPumpCmdType(1)    # pressure
x.cmd.setPumpCmd(1)
x.log_enabled = True
time.sleep(.5)
x.cmd.setFlowDir(1)
p_des = 6
cmd = 1
alpha = .8
while(cmd<(p_des-.03)):
    cmd = alpha*cmd + (1-alpha)*p_des
    x.cmd.setPumpCmd(cmd)
    time.sleep(.001)
time.sleep(1.5)
x.saveLog()
x.log_enabled = False
x.cmd.setPumpCmd(0)
x.cmd.setPumpCmdType(0)
x.cmd.setFlowDir(0)
time.sleep(1)