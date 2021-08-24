#C:\Users\Ben\AppData\Local\Programs\Python\Python39\Scripts\pyuic5.exe -x gui.ui -o gui.py

from gui import *
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QThread, pyqtSignal
import pyqtgraph as pg
import numpy as np
import scipy.signal as signal
import sys
import time
import struct
import time
import threading

from espressoMachine import *
from espressoModes import *
from espressoFSM import *
from theme import *

logdir = 'logs/'


class MainWindow(Ui_EspressoGUI):
    def __init__(self):
        self.mw = QtWidgets.QMainWindow()
        self.setupUi(self.mw)

        self.machine = espressoMachine()
        #self.machine = fakeEspressoMachine()
        self.machine.startIO()
        self.fsm = espressoFSM(self.machine)
        self.fsm.start()

        '''
        self.mode = nineBarShot()
        self.machine.startIO()
        #self.machine.log_enabled = True
        while(not self.mode.done):
            self.mode.run(self.machine)
            time.sleep(.1)
        #self.machine.log_enabled = False
        '''
        self.textLog.setReadOnly(True)

        # Add Plots #
        self.plot1 = pg.PlotWidget(background=bg_color, title='Pressure/Flow')
        #self.plot2 = pg.PlotWidget(background=bg_color, title='Flow (mL/s)')
        self.plot3 = pg.PlotWidget(background=bg_color, title='Temperature (C)')
        self.plot1.showAxis('right')
        self.plot1.getAxis('right').setLabel('Pressure (Bar)', color=blue1)
        #self.plot2.showAxis('right')
        #self.plot2.getAxis('right').setLabel('Flow (mL/s)', color=white3)
        self.plot3.showAxis('right')
        self.plot3.getAxis('right').setLabel('Temperature (C)', color=orange1)
        self.plotLayout.addWidget(self.plot1)
        #self.plotLayout.addWidget(self.plot2)
        self.plotLayout.addWidget(self.plot3)
        self.plot1.addLegend()
        #self.plot2.addLegend()
        self.plot3.addLegend()

        self.c1 = pg.PlotCurveItem(name='Pressure Cmd')    # pressure commands
        self.c2 = pg.PlotCurveItem(name='Flow Cmd')        # flow commands
        self.c3 = pg.PlotCurveItem(name='Pressure')                # pressure
        self.c4 = pg.PlotCurveItem(name='Flow')                    # flow
        self.c1.setPen(color = blue1, width = lw, linestyle='dashed')
        self.c2.setPen(color = green1, width = lw, linestyle='dashed')
        self.c3.setPen(color = blue7, width = lw)
        self.c4.setPen(color = green2, width = lw)
        self.plot1.addItem(self.c1)
        self.plot1.addItem(self.c2)
        self.plot1.addItem(self.c3)
        self.plot1.addItem(self.c4)


        ### Plot 2 ###
        self.c5 = pg.PlotCurveItem(name='Water Temp Cmd')    # pressure commands
        self.c6 = pg.PlotCurveItem(name='Group Temp Cmd')    # flow commands
        self.c7 = pg.PlotCurveItem(name='Water Temp')          # pressure
        self.c8 = pg.PlotCurveItem(name='Heater Temp')             # flow
        self.c9 = pg.PlotCurveItem(name='Group Temp')             # flow
        self.c5.setPen(color = red1, width = lw, linestyle='dashed')
        self.c6.setPen(color = orange1, width = lw, linestyle='dashed')
        self.c7.setPen(color = red1, width = lw)
        self.c8.setPen(color = orange2, width = lw)
        self.c9.setPen(color = orange1, width = lw)
        self.plot3.addItem(self.c5)
        self.plot3.addItem(self.c6)
        self.plot3.addItem(self.c7)
        self.plot3.addItem(self.c8)
        self.plot3.addItem(self.c9)



        # Main UI Timer #
        self.runTimer = QtCore.QTimer()
        self.runTimer.timeout.connect(self.run)
        self.runTimer.start(20)

        # Connect buttons #
        self.startButton.clicked.connect(self.startPressed)
        self.saveButton.clicked.connect(self.saveLogPressed)
        self.tareButton.clicked.connect(self.tarePressed)
        self.customButton.clicked.connect(self.customize)
        self.modeList.itemClicked.connect(self.modeListPressed)
        self.updateButtons()

        # Add modes to list #
        for mode in custom_modes:
            self.modeList.addItem(mode().title)

        self.t_last = time.time()

        

    def run(self):
        #self.fsm.run(self.machine, False)
        self.updateGraphics()

        t_now = time.time()
        dt = t_now - self.t_last
        self.t_last = t_now
        print('FPS: ', 1.0/dt)

    def startPressed(self):
        if(self.fsm.mode_running):
            self.textLog.appendPlainText('stop pressed')
            self.fsm.mode_running = False 
        else:
            self.textLog.appendPlainText('start pressed')
            self.fsm.start_mode()
            self.fsm.mode_running = True 
        self.updateButtons()

    def customize(self):
        self.textLog.appendPlainText('customize pressed')

    def saveLogPressed(self):
        self.textLog.appendPlainText('save pressed')
        self.machine.saveLog()

    def tarePressed(self):
        self.textLog.appendPlainText('taring')
        self.machine.cmd.tare(1)

    def modeListPressed(self, item):
        self.textLog.appendPlainText(item.text())
        self.fsm.transition(self.machine, self.fsm.mode_list[item.text()])
        self.updateButtons()

    def updateButtons(self):
        ### Buttons ###

        if(self.fsm.mode_running):
            self.startButton.setText('Stop')
            self.startButton.setStyleSheet(on_button_style)
        else:
            self.startButton.setText('Start')
            self.startButton.setStyleSheet(off_button_style)
        '''
        self.idleButton.setStyleSheet(off_button_style)    
        self.preheatButton.setStyleSheet(off_button_style)
        self.manualButton.setStyleSheet(off_button_style)
        self.flushButton.setStyleSheet(off_button_style)
        self.steamButton.setStyleSheet(off_button_style)
        '''
        self.saveButton.setStyleSheet(off_button_style)
        self.tareButton.setStyleSheet(off_button_style)
        
        '''
        if(self.fsm.active_mode.title == 'Idle'):
            self.idleButton.setStyleSheet(on_button_style)
        elif(self.fsm.active_mode.title == 'Preheat'):
            self.preheatButton.setStyleSheet(on_button_style)
        elif(self.fsm.active_mode.title == 'Manual'):
            self.manualButton.setStyleSheet(on_button_style)
        elif(self.fsm.active_mode.title == 'Flush'):
            self.flushButton.setStyleSheet(on_button_style)
        '''
    def updateGraphics(self):
        ### text ###
        t1 = time.time()
        self.pLabel.setText('Pressure:\n%02.2f'%self.machine.state.pressure())
        self.fLabel.setText('Flow:\n%02.2f'%self.machine.state.flow())
        self.wtLabel.setText('Water Temp:\n%02.2f'%self.machine.state.waterTemp())
        self.gtLabel.setText('Group Temp:\n%02.2f'%self.machine.state.groupTemp())
        self.htLabel.setText('Heater Temp:\n%02.2f'%self.machine.state.heaterTemp())
        self.psLabel.setText('Pump Speed:\n%03.1f'%(self.machine.state.pumpVel()*60/(2*np.pi)))
        self.ptLabel.setText('Pump Torque:\n%02.5f'%self.machine.state.pumpTorque())
        self.wLabel.setText('Weight:\n%02.2f'%self.machine.state.weight())
        self.whpLabel.setText('WH Power:\n%03.1f'%self.machine.state.waterHeaterPower())
        self.ghpLabel.setText('GH Power:\n%03.1f'%self.machine.state.groupHeaterPower())

        t3 = time.time()

        
        
        max_points = 500

        if(len(self.machine.log.shape)>1):

            #self.plot1.disableAutoRange()
            #self.plot3.disableAutoRange()
            
            ### Format plot data ###
            data = self.machine.log # copy data to avoid it changing size while manipulating
            data_length = data.shape[0]
            inds = np.arange(0, data_length, 1)
            if(data_length > max_points):
                inds = np.linspace(0, data_length-1, max_points, dtype=int)
            plot_time = data[inds,6] - data[0,6]
            p0 = signal.medfilt(data[inds, 3], 3)
            p1 = data[inds, 0]
            p3 = signal.medfilt(data[inds, 7])
            p4 = signal.medfilt(data[inds, 8])
            p5 = data[inds, 1]
            p6 = data[inds, 2]
            p7 = signal.medfilt(data[inds, 9])
            p8 = signal.medfilt(data[inds, 10])
            p9 = signal.medfilt(data[inds, 11])

            xmax = np.max(plot_time)
            ymax1 = np.max((data[:,7:9]).flatten())+ 1
            ymax2 = np.max((data[:,9:12]).flatten())+ 1
            ymin2 = np.min((data[:,9:12]).flatten())- 1

            ### Plot 1 ###
            ds = 1
            ind_p = np.nonzero(p0 == 1)      # log points where command type is pressure
            ind_f = np.nonzero(p0 == 2)      # log points where command type is flow
            self.c1.setData(plot_time[ind_p], p1[ind_p])
            self.c2.setData(plot_time[ind_f], p1[ind_f])
            self.c3.setData(plot_time, p3)
            self.c4.setData(plot_time, p4)
            self.c5.setData(plot_time, p5)
            self.c6.setData(plot_time, p6)
            self.c7.setData(plot_time, p7)
            self.c8.setData(plot_time, p8)
            self.c9.setData(plot_time, p9)
            
            self.plot1.setYRange(0, ymax1)
            self.plot1.setXRange(0, xmax)
            self.plot3.setYRange(ymin2, ymax2)
            self.plot3.setXRange(0, xmax)

            t2 = time.time()
            #print('log length: ', len(self.machine.log[:,1]), '  text time: ', t3-t1, ' plot time: ', t2-t1)


class userInput():
    def __init__(self):
        pass

def main():
    app = QtWidgets.QApplication(sys.argv)
    GUI = MainWindow()
    GUI.mw.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()