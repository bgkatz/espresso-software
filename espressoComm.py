### Espreso Machine USB Communication Interface ###

import usb.core
import usb.util
import numpy as np
import struct
import time

class espressoComm():
    def __init__(self, idVend, idProd):
        self.dev = usb.core.find(idVendor=idVend, idProduct=idProd)
        if self.dev is None:
            print('Device not found')
        try:
            self.dev.set_configuration()
        except:
            pass
        self.input_buff = []
        self.output_buff = []
        self.in_floats = []
        self.out_floats = [0, 0, 0, 0, 0]

    def read(self):
        try:
            self.input_buff = self.dev.read(0x81, 80)
            self.in_floats = list(struct.unpack('20f', self.input_buff))
            self.in_floats[0] = time.time()

        except:
            print('USB read failed')
            time.sleep(.1)

    def write(self, ):
        self.output_buff = struct.pack('%sf' % len(self.out_floats), *self.out_floats)
        try:
            self.dev.write(1, self.output_buff)
        except:
            print('USB write failed')