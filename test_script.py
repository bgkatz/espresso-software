from espressoMachine import *
import time

x = espressoMachine()
x.log_enabled = True
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