### Espresso Machine Fininte State Machine ###
# Manages switching between different modes

from espressoMachine import *
from espressoModes import *

mode_list = (idleMode, manualMode, nineBarShot)

class espressoFSM():
    def __init__(self):
        self.mode_list = {
                    'IDLE':idleMode, 
                    'MANUAL':manualMode, 
                    'PREHEAT':preheatMode,
                    'FLUSH':flushMode,
                    'NINE_BAR':nineBarShot,
                    }
        self.active_mode = idleMode