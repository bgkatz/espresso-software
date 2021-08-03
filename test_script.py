from espressoMachine import *
from espressoModes import *
from espressoFSM import *
import time

'''
x = espressoMachine()
x.start()
x.log_enabled = False
#x.sample()



time.sleep(1)

print('Pressure:  ', x.state.pressure())
print('Flow:      ', x.state.flow())
print('Water Temp:', x.state.waterTemp())
print('Group Temp:', x.state.groupTemp())

print(x.log)
x.saveLog()
x.clearLog()
print(x.log)
'''


x = fakeEspressoMachine()
x.startIO()
y = nineBarShot()
#y = idleMode()
x.log_enabled = True
while(not y.done):
    #print(x.state.pressure(), x.state.flow(),x.state.waterTemp(), x.state.groupTemp(), x.state.weight())
    y.run(x.state, x.cmd)
    time.sleep(.1)
x.saveLog()
x.clearLog()
x.log_enabled = False
