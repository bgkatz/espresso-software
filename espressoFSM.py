### Espresso Machine Fininte State Machine ###
# Manages switching between different modes

import threading
from espressoMachine import *
from espressoModes import *


mode_list = (idleMode, preheatMode, manualMode, nineBarShot)
custom_modes = (idleMode, nineBarShot)

class espressoFSM():
    def __init__(self, machine, user_input=False):
        self.mode_list = {
                    idleMode().title:idleMode, 
                    manualMode().title:manualMode, 
                    preheatMode().title:preheatMode,
                    flushMode().title:flushMode,
                    nineBarShot().title:nineBarShot,
                    }
        self.active_mode = idleMode()
        self.mode_running = False
        self.machine = machine
        self.ui = user_input

        self.run_thread = threading.Thread(target=self.run)
        self.run_thread.daemon = True


    def run(self):
        while(True):
            if(self.mode_running):
                self.active_mode.run(self.machine, self.ui)
            else:
                self.active_mode.stop(self.machine)
            time.sleep(.01)

            #time.sleep(.1)

    def start(self):
        self.run_thread.start()
    def stop(self):
        self.run_thread.stop()
            
    def start_mode(self):
        self.active_mode.start()
    
    def transition(self, machine, nextMode):
        print(nextMode)
        if((nextMode in self.mode_list.values()) and (nextMode().title != self.active_mode.title)):
            if(self.active_mode.exit(machine)):
                self.active_mode = nextMode()
                print('Transitioning to: ', self.active_mode.title)
                self.mode_running = False