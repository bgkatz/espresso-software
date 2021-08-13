### Espresso Machine Fininte State Machine ###
# Manages switching between different modes

from espressoMachine import *
from espressoModes import *

mode_list = (idleMode, preheatMode, manualMode, nineBarShot)
custom_modes = (idleMode, nineBarShot)

class espressoFSM():
    def __init__(self):
        self.mode_list = {
                    idleMode().title:idleMode, 
                    manualMode().title:manualMode, 
                    preheatMode().title:preheatMode,
                    flushMode().title:flushMode,
                    nineBarShot().title:nineBarShot,
                    }
        self.active_mode = idleMode()
        self.mode_running = False

    def run(self, machine, user_input):
        if(self.mode_running):
            self.active_mode.run(machine, user_input)
        else:
            self.active_mode.stop(machine)

            #time.sleep(.1)
            
    def start_mode(self):
        self.active_mode.start()
    
    def transition(self, machine, nextMode):
        print(nextMode)
        if((nextMode in self.mode_list.values()) and (nextMode().title != self.active_mode.title)):
            if(self.active_mode.exit(machine)):
                self.active_mode = nextMode()
                print('Transitioning to: ', self.active_mode.title)
                self.mode_running = False