#C:\Users\Ben\AppData\Local\Programs\Python\Python39\Scripts\pyuic6.exe -x gui.ui -o gui.py

from gui import *
from PyQt6 import QtGui, QtCore
from PyQt6.QtCore import QThread, pyqtSignal
import pyqtgraph as pg
import numpy as np
import sys
import time
import struct
import time

from espressoMachine import *
from espressoModes import *
from espressoFSM import *
from theme import *

logdir = 'logs/'


PLOT_POINTS = 1000
PLOT_NTH_POINT = 1




tStart = time.time();
tVec = [0]
ts = .005;


t_last = time.time()

class MainWindow(Ui_EspressoGUI):
    def __init__(self):
        self.mw = QtGui.QMainWindow()
        self.setupUi(self.mw)

        self.machine = fakeEspressoMachine()
        self.machine.startIO()
        self.fsm = espressoFSM()

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

        # Add plotting to a thread #

        # Main UI Timer #
        self.runTimer = QtCore.QTimer()
        self.runTimer.timeout.connect(self.run)
        self.runTimer.start(20)

        # Connect buttons #
        self.startButton.clicked.connect(self.startPressed)
        self.saveButton.clicked.connect(self.saveLogPressed)
        self.pressureSlider.valueChanged.connect(self.pressureSliderChanged)
        self.tempBox.valueChanged.connect(self.tempBoxChanged)
        self.manualButton.clicked.connect(self.manualPressed)
        self.flushButton.clicked.connect(self.flushPressed)
        self.steamButton.clicked.connect(self.steamPressed)
        self.presPushButton.clicked.connect(self.pressurePressed)
        self.flowPushButton.clicked.connect(self.flowPressed)
        self.idleButton.clicked.connect(self.idlePressed)
        self.preheatButton.clicked.connect(self.preheatPressed)
        self.tareButton.clicked.connect(self.tarePressed)
        self.modeList.itemClicked.connect(self.modeListPressed)
        self.updateButtons()

        # Add modes to list #
        for mode in custom_modes:
            self.modeList.addItem(mode().title)

        self.t_last = time.time()

    def run(self):
        self.fsm.run(self.machine)
        self.updateGraphics()

        t_now = time.time()
        dt = t_now - self.t_last
        self.t_last = t_now
        #print('FPS: ', 1.0/dt)

    def startPressed(self):
        if(self.fsm.mode_running):
            self.textLog.appendPlainText('stop pressed')
            self.fsm.mode_running = False 
        else:
            self.textLog.appendPlainText('start pressed')
            self.fsm.mode_running = True 
        self.updateButtons()

    def idlePressed(self):
        print('idle pressed')
        self.fsm.transition(self.machine, idleMode)
        self.updateButtons()

    def preheatPressed(self):
        print('preheat pressed')
        self.fsm.transition(self.machine, preheatMode)
        self.updateButtons()

    def manualPressed(self):
        self.textLog.appendPlainText('manual pressed')
        self.fsm.transition(self.machine, manualMode)
        self.updateButtons()

    def flushPressed(self):
        self.textLog.appendPlainText('flush pressed')
        self.fsm.transition(self.machine, flushMode)
        self.updateButtons()

    def steamPressed(self):
        self.textLog.appendPlainText('steam pressed')

    def pressurePressed(self):
        pass#if(self.fsm.mode.name == 'MANUAL'):
            #self.fsm.mode.pumpCmdType = 'PRESSURE'

    def flowPressed(self):
        pass#if(self.fsm.mode.name == 'MANUAL'):
            #self.fsm.mode.pumpCmdType = 'FLOW'

    def saveLogPressed(self):
        self.textLog.appendPlainText('save pressed')
        self.machine.saveLog()

    def tarePressed(self):
        self.textLog.appendPlainText('taring')
        self.machine.cmd.tare(1)

    def pressureSliderChanged(self):
        pass

    def tempBoxChanged(self):
        pass

    def modeListPressed(self, item):
        self.textLog.appendPlainText(item.text())
        self.fsm.transition(self.machine, self.fsm.mode_list[item.text()])
        self.updateButtons()
        #print(item.text())
        #if(self.fsm.mode.name == 'TRAJECTORY'):
        #    if(item.text()=='Flat 9 Bar'):
        #        self.fsm.mode.traj = nineBarTraj()
        #    if(item.text()=='Flat 6 Bar'):
        #        self.fsm.mode.traj = sixBarTraj()

    def updateButtons(self):
        ### Buttons ###
        if(self.fsm.mode_running):
            self.startButton.setText('Stop')
            self.startButton.setStyleSheet(on_button_style)
        else:
            self.startButton.setText('Start')
            self.startButton.setStyleSheet(off_button_style)

        self.idleButton.setStyleSheet(off_button_style)    
        self.preheatButton.setStyleSheet(off_button_style)
        self.manualButton.setStyleSheet(off_button_style)
        self.flushButton.setStyleSheet(off_button_style)
        self.steamButton.setStyleSheet(off_button_style)
        self.saveButton.setStyleSheet(off_button_style)
        self.tareButton.setStyleSheet(off_button_style)

        if(self.fsm.active_mode.title == 'Idle'):
            self.idleButton.setStyleSheet(on_button_style)
        elif(self.fsm.active_mode.title == 'Preheat'):
            self.preheatButton.setStyleSheet(on_button_style)
        elif(self.fsm.active_mode.title == 'Manual'):
            self.manualButton.setStyleSheet(on_button_style)
        elif(self.fsm.active_mode.title == 'Flush'):
            self.flushButton.setStyleSheet(on_button_style)

    def updateGraphics(self):

        ### text ###
        self.pLabel.setText('Pressure:\n%02.2f'%self.machine.state.pressure())
        self.fLabel.setText('Flow:\n%02.2f'%self.machine.state.flow())
        self.wtLabel.setText('Water Temp:\n%02.2f'%self.machine.state.waterTemp())
        self.gtLabel.setText('Group Temp:\n%02.2f'%self.machine.state.groupTemp())
        self.htLabel.setText('Heater Temp:\n%02.2f'%self.machine.state.heaterTemp())
        self.psLabel.setText('Pump Speed:\n%03.1f'%(self.machine.state.pumpVel()*60/(2*np.pi)))
        self.ptLabel.setText('Pump Torque:\n%02.5f'%self.machine.state.pumpTorque())
        self.wLabel.setText('Weight:\n%02.2f'%self.machine.state.weight())
        self.whpLabel.setText('WH Power:\n%03.1f'%self.machine.state.waterHeaterPower())
        self.ghpLabel.setText('WH Power:\n%03.1f'%self.machine.state.groupHeaterPower())

        self.plot1.clear()
        #self.plot2.clear()
        self.plot3.clear()
        
        maxpoints = 500

        if(len(self.machine.log.shape)>1):

            ### Plot 1 ###
            ind_p = np.nonzero(self.machine.log[:,3] == 1)      # log points where command type is pressure
            ind_f = np.nonzero(self.machine.log[:,3] == 2)      # log points where command type is flow
            c1 = pg.PlotCurveItem(self.machine.log[ind_p,6].flatten(), self.machine.log[ind_p,0].flatten(), name='Pressure Cmd')    # pressure commands
            #print(self.machine.log[ind_f,6].shape)
            #print(self.machine.log[ind_f,0].shape)
            c2 = pg.PlotCurveItem(self.machine.log[ind_f,6].flatten(), self.machine.log[ind_f,0].flatten(), name='Flow Cmd')        # flow commands
            c3 = pg.PlotCurveItem(self.machine.log[:,6], self.machine.log[:,7], name='Pressure')                # pressure
            c4 = pg.PlotCurveItem(self.machine.log[:,6], self.machine.log[:,8], name='Flow')                    # flow
            c1.setPen(color = blue1, width = lw, style=QtCore.Qt.DashLine)
            c2.setPen(color = green1, width = lw, style=QtCore.Qt.DashLine)
            c3.setPen(color = blue7, width = lw)
            c4.setPen(color = green2, width = lw)
            self.plot1.addItem(c1)
            self.plot1.addItem(c2)
            self.plot1.addItem(c3)
            self.plot1.addItem(c4)


            ### Plot 2 ###
            c5 = pg.PlotCurveItem(self.machine.log[:,6], self.machine.log[:,1], name='Water Temp Cmd')    # pressure commands
            c6 = pg.PlotCurveItem(self.machine.log[:,6], self.machine.log[:,2], name='Group Temp Cmd')    # flow commands
            c7 = pg.PlotCurveItem(self.machine.log[:,6], self.machine.log[:,9], name='Water Temp')          # pressure
            c8 = pg.PlotCurveItem(self.machine.log[:,6], self.machine.log[:,10], name='Heater Temp')             # flow
            c9 = pg.PlotCurveItem(self.machine.log[:,6], self.machine.log[:,11], name='Group Temp')             # flow
            c5.setPen(color = red1, width = lw, style=QtCore.Qt.DashLine)
            c6.setPen(color = orange1, width = lw, style=QtCore.Qt.DashLine)
            c7.setPen(color = red1, width = lw)
            c8.setPen(color = orange2, width = lw)
            c9.setPen(color = orange1, width = lw)
            self.plot3.addItem(c5)
            self.plot3.addItem(c6)
            self.plot3.addItem(c7)
            self.plot3.addItem(c8)
            self.plot3.addItem(c9)


def main():
    app = QtGui.QApplication(sys.argv)
    GUI = MainWindow()
    GUI.mw.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()