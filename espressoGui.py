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
from fsm import*
from usb_comm import *
from shot_trajectory import *


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

        # Add Plots #
        self.plot1 = pg.PlotWidget(background=(34, 34, 34), title='Pressure (Pa)')
        self.plot2 = pg.PlotWidget(background=(34, 34, 34), title='Flow (mL/s)')
        self.plot3 = pg.PlotWidget(background=(34, 34, 34), title='Temperature (C)')
        self.plot1.showAxis('right')
        self.plot1.getAxis('right').setLabel('Pressure (Bar)', color=(0x00, 0x3f, 0x5c))
        self.plot2.showAxis('right')
        self.plot2.getAxis('right').setLabel('Flow (mL/s)', color=(0x7a, 0x51, 0x95))
        self.plot3.showAxis('right')
        self.plot3.getAxis('right').setLabel('Temperature (C)', color=(0xef, 0x56, 0x75))
        self.plotLayout.addWidget(self.plot1)
        self.plotLayout.addWidget(self.plot2)
        self.plotLayout.addWidget(self.plot3)
        self.plot1.addLegend()
        self.plot2.addLegend()
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
        self.trajButton.clicked.connect(self.trajPressed)
        self.manualButton.clicked.connect(self.manualPressed)
        self.flushButton.clicked.connect(self.flushPressed)
        self.presPushButton.clicked.connect(self.pressurePressed)
        self.flowPushButton.clicked.connect(self.flowPressed)

        self.t_last = time.time()

        self.offButtonStyle = 'QPushButton{\nborder-style: solid;\nborder-color: #343434;\nborder-width: 5px;\nborder-radius: 10px;\n background-color : #FFFFFF;}'
        self.onButtonStyle = 'QPushButton{\nborder-style: solid;\nborder-color: #343434;\nborder-width: 5px;\nborder-radius: 10px;\n background-color : #AFAFAF ;}'

    def run(self):
        #self.fsm.run()
        self.updateGraphics()

        t_now = time.time()
        dt = t_now - self.t_last
        self.t_last = t_now
        #print('FPS: ', 1.0/dt)

    def startPressed(self):
        pass

    def manualPressed(self):
        pass#self.fsm.transition('MANUAL')

    def trajPressed(self):
        pass#self.fsm.transition('TRAJECTORY')

    def flushPressed(self):
        pass#self.fsm.transition('FLUSH')

    def pressurePressed(self):
        pass#if(self.fsm.mode.name == 'MANUAL'):
            #self.fsm.mode.pumpCmdType = 'PRESSURE'

    def flowPressed(self):
        pass#if(self.fsm.mode.name == 'MANUAL'):
            #self.fsm.mode.pumpCmdType = 'FLOW'

    def saveLogPressed(self):
        pass#fname = logdir + time.strftime("%Y%m%d-%H%M%S") + '.csv'
        #np.savetxt(fname, self.fsm.io.data, delimiter=',')

    def pressureSliderChanged(self):
        pass#if(self.fsm.mode.name == 'MANUAL'):
            #pressure_des = self.pressureSlider.value()*.1
            #self.fsm.mode.pumpCmd = pressure_des
            ##self.fsm.io.out_floats[0] = pressure_des
            #self.pressureText.setText('%.2f'%pressure_des)
    def tempBoxChanged(self):
        if(self.fsm.mode.name == 'MANUAL'):
            temp_des = self.tempBox.value()
            self.fsm.io.out_floats[1] = temp_des

    def selectTraj(self, item):
        pass#print(item.text())
        #if(self.fsm.mode.name == 'TRAJECTORY'):
        #    if(item.text()=='Flat 9 Bar'):
        #        self.fsm.mode.traj = nineBarTraj()
        #    if(item.text()=='Flat 6 Bar'):
        #        self.fsm.mode.traj = sixBarTraj()


    def updateGraphics(self):
        pass
        '''
        if(self.fsm.mode.name == 'TRAJECTORY'):
            self.trajButton.setStyleSheet(self.onButtonStyle)
            self.manualButton.setStyleSheet(self.offButtonStyle)
            self.flushButton.setStyleSheet(self.offButtonStyle)
        elif(self.fsm.mode.name == 'MANUAL'):
            self.trajButton.setStyleSheet(self.offButtonStyle)
            self.manualButton.setStyleSheet(self.onButtonStyle)
            self.flushButton.setStyleSheet(self.offButtonStyle)
        elif(self.fsm.mode.name == 'FLUSH'):
            self.trajButton.setStyleSheet(self.offButtonStyle)
            self.manualButton.setStyleSheet(self.offButtonStyle)
            self.flushButton.setStyleSheet(self.onButtonStyle)
        else:
            self.trajButton.setStyleSheet(self.offButtonStyle)
            self.manualButton.setStyleSheet(self.offButtonStyle)
            self.flushButton.setStyleSheet(self.offButtonStyle)

        if(self.fsm.mode.pumpCmdType == 'PRESSURE'):
            self.presPushButton.setStyleSheet(self.onButtonStyle)
            self.flowPushButton.setStyleSheet(self.offButtonStyle)
        elif(self.fsm.mode.pumpCmdType == 'FLOW'):
            self.presPushButton.setStyleSheet(self.offButtonStyle)
            self.flowPushButton.setStyleSheet(self.onButtonStyle)
        else:
            self.presPushButton.setStyleSheet(self.offButtonStyle)
            self.flowPushButton.setStyleSheet(self.offButtonStyle)
        #try:
        self.plot1.clear()
        self.plot2.clear()
        self.plot3.clear()
        lw = 10
        maxpoints = 500

        if(self.fsm.mode.name == 'TRAJECTORY'):
            ind_p = np.where(self.fsm.mode.traj.pumpCmdTypeVec == 1)
            ind_f = np.where(self.fsm.mode.traj.pumpCmdTypeVec == 2)
            curve1 = pg.PlotCurveItem(self.fsm.mode.traj.timeVec[ind_p], self.fsm.mode.traj.pumpCmdVec[ind_p], name='Pessure Trajectory')
            curve1.setPen(color=(0x00, 0x3f, 0x5c), width=lw, style=QtCore.Qt.DashLine)
            curve2 = pg.PlotCurveItem(self.fsm.mode.traj.timeVec[ind_f], self.fsm.mode.traj.pumpCmdVec[ind_f], name='Flow Trajectory')
            curve2.setPen(color=(0x7a, 0x51, 0x95), width=lw, style=QtCore.Qt.DashLine)
            #curve1 = pg.PlotCurveItem(self.fsm.mode.traj.timeVec, self.traj.pumpCmdVec, name='Pressure Trajectory')
            #curve1.setPen(color=(0x00, 0x3f, 0x5c), width=lw)
            curve3 = pg.PlotCurveItem(self.fsm.mode.traj.timeVec, self.fsm.mode.traj.tempCmdVec, name = 'Temperature Trajectory')
            curve3.setPen(color=(0xef, 0x56, 0x75), width=lw, style=QtCore.Qt.DashLine)
            self.plot1.setRange(xRange=[0, np.max(self.fsm.mode.traj.timeVec)])
            self.plot2.setRange(xRange=[0, np.max(self.fsm.mode.traj.timeVec)])
            self.plot3.setRange(xRange=[0, np.max(self.fsm.mode.traj.timeVec)])
            self.plot1.addItem(curve1, clear=True)
            self.plot2.addItem(curve2, clear=True)
            self.plot3.addItem(curve3, clear=True)

            if(self.fsm.mode.traj.running or self.fsm.mode.traj.ended):
                data = self.fsm.io.data
                x = data[:,0]     # Time
                x = x-x[0]
                x = list(x)
                y1 = list(data[:,1])    # Pressure
                y2 = list(data[:,2])    # Flow
                y3 = list(data[:,3])    # Temp
                curve4 = pg.PlotCurveItem(x, y1)
                curve4.setPen(color=(0x10, 0x4f, 0x6c), width=lw)
                curve5 = pg.PlotCurveItem(x, y2)
                curve5.setPen(color=(0x8a, 0x61, 0xa5), width=lw)
                curve6 = pg.PlotCurveItem(x, y3)
                curve6.setPen(color=(0xff, 0x66, 0x85), width=lw)
                self.plot1.addItem(curve4)
                self.plot2.addItem(curve5)
                self.plot3.addItem(curve6)
        elif(self.fsm.mode.name == 'MANUAL'):
            if(self.fsm.io.start_logging):
                data = self.fsm.io.data
                cmds = self.fsm.io.cmds
                x = data[:,0]     # Time
                x = x-x[0]
                c1 = cmds[:,0]    # Pump command
                c2 = cmds[:,1]    # Temp command
                y1 = data[:,1]    # Pressure
                y2 = data[:,2]    # Flow
                y3 = data[:,3]    # Water Temp
                y4 = data[:,4]    # Heater Temp
                y5 = data[:,5]    # Group Temp
                if(len(x)>maxpoints):
                    inds = np.linspace(0, len(x)-2, maxpoints)
                    inds = inds.astype(np.int)
                    x = x[inds]
                    c1 = c1[inds]
                    c2 = c2[inds]
                    y1 = y1[inds]
                    y2 = y2[inds]
                    y3 = y3[inds]
                    y4 = y4[inds]
                    y5 = y5[inds]
                x = list(x)
                c1 = list(c1)
                c2 = list(c2)
                y1 = list(y1)
                y2 = list(y2)
                y3 = list(y3)
                y4 = list(y4)
                y5 = list(y5)
                curve1 = pg.PlotCurveItem(x, c1)
                curve1.setPen(color=(0x00, 0x3f, 0x5c), width=lw, style=QtCore.Qt.DashLine)
                curve2 = pg.PlotCurveItem(x, c2)
                curve2.setPen(color=(0xbf, 0x26, 0x85), width=lw, style=QtCore.Qt.DashLine)
                curve4 = pg.PlotCurveItem(x, y1)
                curve4.setPen(color=(0x10, 0x4f, 0x6c), width=lw)
                curve5 = pg.PlotCurveItem(x, y2)
                curve5.setPen(color=(0x8a, 0x61, 0xa5), width=lw)
                curve6 = pg.PlotCurveItem(x, y3, name='Water Temperature')
                curve6.setPen(color=(0xff, 0x66, 0x85), width=lw)
                curve7 = pg.PlotCurveItem(x, y4, name='Heater Temperature')
                curve7.setPen(color=(0xdf, 0x46, 0x85), width=lw)
                curve8 = pg.PlotCurveItem(x, y5, name='Group Temperature')
                curve8.setPen(color=(0xbf, 0x26, 0x85), width=lw)
                self.plot1.setRange(yRange=[0, 12])
                self.plot2.setRange(yRange=[0, 10])
                self.plot1.setRange(xRange=[0, np.max(x)])
                self.plot2.setRange(xRange=[0, np.max(x)])
                self.plot3.setRange(xRange=[0, np.max(x)])
                self.plot1.addItem(curve1)
                self.plot3.addItem(curve2)
                self.plot1.addItem(curve4)
                self.plot2.addItem(curve5)
                self.plot3.addItem(curve6)
                self.plot3.addItem(curve7)
                self.plot3.addItem(curve8)
'''

def main():
    app = QtGui.QApplication(sys.argv)
    GUI = MainWindow()
    GUI.mw.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()