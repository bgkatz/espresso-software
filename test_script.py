from espressoMachine import *
from espressoModes import *
import time

'''
x = espressoMachine()
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

x = espressoMachine()
y = idleMode()

while(True):
    print(x.state.pressure())
    y.run(x.state, x.cmd)
    time.sleep(.5)