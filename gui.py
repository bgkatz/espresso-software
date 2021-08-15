# Form implementation generated from reading ui file 'gui.ui'
#
# Created by: PyQt6 UI code generator 6.1.1
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_EspressoGUI(object):
    def setupUi(self, EspressoGUI):
        EspressoGUI.setObjectName("EspressoGUI")
        EspressoGUI.resize(1920, 1080)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(EspressoGUI.sizePolicy().hasHeightForWidth())
        EspressoGUI.setSizePolicy(sizePolicy)
        EspressoGUI.setMinimumSize(QtCore.QSize(1920, 1080))
        EspressoGUI.setMaximumSize(QtCore.QSize(1920, 1080))
        EspressoGUI.setStyleSheet("background-color: #FFFFFF;")
        EspressoGUI.setInputMethodHints(QtCore.Qt.InputMethodHint.ImhDigitsOnly)
        self.centralwidget = QtWidgets.QWidget(EspressoGUI)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setMinimumSize(QtCore.QSize(1024, 768))
        self.centralwidget.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalWidget = QtWidgets.QWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalWidget.sizePolicy().hasHeightForWidth())
        self.verticalWidget.setSizePolicy(sizePolicy)
        self.verticalWidget.setMinimumSize(QtCore.QSize(400, 0))
        self.verticalWidget.setMaximumSize(QtCore.QSize(400, 16777215))
        self.verticalWidget.setObjectName("verticalWidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalWidget)
        self.verticalLayout_2.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.gridWidget = QtWidgets.QWidget(self.verticalWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.gridWidget.sizePolicy().hasHeightForWidth())
        self.gridWidget.setSizePolicy(sizePolicy)
        self.gridWidget.setMinimumSize(QtCore.QSize(0, 20))
        self.gridWidget.setObjectName("gridWidget")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.gridWidget)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.idleButton = QtWidgets.QPushButton(self.gridWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.idleButton.sizePolicy().hasHeightForWidth())
        self.idleButton.setSizePolicy(sizePolicy)
        self.idleButton.setMinimumSize(QtCore.QSize(0, 75))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.idleButton.setFont(font)
        self.idleButton.setStyleSheet("QPushButton{\n"
"border-style: solid;\n"
"border-color: #343434;\n"
"border-width: 5px;\n"
"border-radius: 10px;\n"
"}")
        self.idleButton.setObjectName("idleButton")
        self.gridLayout_3.addWidget(self.idleButton, 0, 0, 1, 1)
        self.preheatButton = QtWidgets.QPushButton(self.gridWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.preheatButton.sizePolicy().hasHeightForWidth())
        self.preheatButton.setSizePolicy(sizePolicy)
        self.preheatButton.setMinimumSize(QtCore.QSize(0, 75))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.preheatButton.setFont(font)
        self.preheatButton.setStyleSheet("QPushButton{\n"
"border-style: solid;\n"
"border-color: #343434;\n"
"border-width: 5px;\n"
"border-radius: 10px;\n"
"}")
        self.preheatButton.setObjectName("preheatButton")
        self.gridLayout_3.addWidget(self.preheatButton, 0, 1, 1, 1)
        self.flushButton = QtWidgets.QPushButton(self.gridWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.flushButton.sizePolicy().hasHeightForWidth())
        self.flushButton.setSizePolicy(sizePolicy)
        self.flushButton.setMinimumSize(QtCore.QSize(0, 75))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.flushButton.setFont(font)
        self.flushButton.setStyleSheet("QPushButton{\n"
"border-style: solid;\n"
"border-color: #343434;\n"
"border-width: 5px;\n"
"border-radius: 10px;\n"
"}")
        self.flushButton.setCheckable(True)
        self.flushButton.setObjectName("flushButton")
        self.gridLayout_3.addWidget(self.flushButton, 1, 0, 1, 1)
        self.steamButton = QtWidgets.QPushButton(self.gridWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.steamButton.sizePolicy().hasHeightForWidth())
        self.steamButton.setSizePolicy(sizePolicy)
        self.steamButton.setMinimumSize(QtCore.QSize(0, 75))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.steamButton.setFont(font)
        self.steamButton.setStyleSheet("QPushButton{\n"
"border-style: solid;\n"
"border-color: #343434;\n"
"border-width: 5px;\n"
"border-radius: 10px;\n"
"}")
        self.steamButton.setObjectName("steamButton")
        self.gridLayout_3.addWidget(self.steamButton, 1, 1, 1, 1)
        self.verticalLayout_2.addWidget(self.gridWidget)
        self.manualButton = QtWidgets.QPushButton(self.verticalWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.manualButton.sizePolicy().hasHeightForWidth())
        self.manualButton.setSizePolicy(sizePolicy)
        self.manualButton.setMinimumSize(QtCore.QSize(0, 75))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.manualButton.setFont(font)
        self.manualButton.setStyleSheet("QPushButton{\n"
"border-style: solid;\n"
"border-color: #343434;\n"
"border-width: 5px;\n"
"border-radius: 10px;\n"
"}")
        self.manualButton.setCheckable(True)
        self.manualButton.setChecked(False)
        self.manualButton.setFlat(False)
        self.manualButton.setObjectName("manualButton")
        self.verticalLayout_2.addWidget(self.manualButton)
        self.modeList = QtWidgets.QListWidget(self.verticalWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.modeList.sizePolicy().hasHeightForWidth())
        self.modeList.setSizePolicy(sizePolicy)
        self.modeList.setMinimumSize(QtCore.QSize(0, 300))
        font = QtGui.QFont()
        font.setFamily("MS Shell Dlg 2")
        font.setPointSize(20)
        self.modeList.setFont(font)
        self.modeList.setObjectName("modeList")
        self.verticalLayout_2.addWidget(self.modeList)
        self.saveButton = QtWidgets.QPushButton(self.verticalWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.saveButton.sizePolicy().hasHeightForWidth())
        self.saveButton.setSizePolicy(sizePolicy)
        self.saveButton.setMinimumSize(QtCore.QSize(0, 75))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.saveButton.setFont(font)
        self.saveButton.setStyleSheet("QPushButton{\n"
"border-style: solid;\n"
"border-color: #343434;\n"
"border-width: 5px;\n"
"border-radius: 10px;\n"
"}")
        self.saveButton.setObjectName("saveButton")
        self.verticalLayout_2.addWidget(self.saveButton)
        self.tareButton = QtWidgets.QPushButton(self.verticalWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tareButton.sizePolicy().hasHeightForWidth())
        self.tareButton.setSizePolicy(sizePolicy)
        self.tareButton.setMinimumSize(QtCore.QSize(0, 75))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.tareButton.setFont(font)
        self.tareButton.setStyleSheet("QPushButton{\n"
"border-style: solid;\n"
"border-color: #343434;\n"
"border-width: 5px;\n"
"border-radius: 10px;\n"
"}")
        self.tareButton.setObjectName("tareButton")
        self.verticalLayout_2.addWidget(self.tareButton)
        self.textLog = QtWidgets.QPlainTextEdit(self.verticalWidget)
        self.textLog.setMaximumSize(QtCore.QSize(16777215, 100))
        self.textLog.setObjectName("textLog")
        self.verticalLayout_2.addWidget(self.textLog)
        self.horizontalLayout.addWidget(self.verticalWidget)
        self.verticalWidget1 = QtWidgets.QWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalWidget1.sizePolicy().hasHeightForWidth())
        self.verticalWidget1.setSizePolicy(sizePolicy)
        self.verticalWidget1.setMaximumSize(QtCore.QSize(1200, 16777215))
        self.verticalWidget1.setObjectName("verticalWidget1")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalWidget1)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridWidget1 = QtWidgets.QWidget(self.verticalWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.gridWidget1.sizePolicy().hasHeightForWidth())
        self.gridWidget1.setSizePolicy(sizePolicy)
        self.gridWidget1.setMaximumSize(QtCore.QSize(1150, 75))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.gridWidget1.setFont(font)
        self.gridWidget1.setObjectName("gridWidget1")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.gridWidget1)
        self.gridLayout_5.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetDefaultConstraint)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.fLabel = QtWidgets.QLabel(self.gridWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fLabel.sizePolicy().hasHeightForWidth())
        self.fLabel.setSizePolicy(sizePolicy)
        self.fLabel.setMaximumSize(QtCore.QSize(16777215, 100))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.fLabel.setFont(font)
        self.fLabel.setObjectName("fLabel")
        self.gridLayout_5.addWidget(self.fLabel, 0, 1, 1, 1)
        self.wtLabel = QtWidgets.QLabel(self.gridWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.wtLabel.sizePolicy().hasHeightForWidth())
        self.wtLabel.setSizePolicy(sizePolicy)
        self.wtLabel.setMaximumSize(QtCore.QSize(16777215, 100))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.wtLabel.setFont(font)
        self.wtLabel.setObjectName("wtLabel")
        self.gridLayout_5.addWidget(self.wtLabel, 0, 3, 1, 1)
        self.ptLabel = QtWidgets.QLabel(self.gridWidget1)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.ptLabel.setFont(font)
        self.ptLabel.setObjectName("ptLabel")
        self.gridLayout_5.addWidget(self.ptLabel, 0, 7, 1, 1)
        self.psLabel = QtWidgets.QLabel(self.gridWidget1)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.psLabel.setFont(font)
        self.psLabel.setObjectName("psLabel")
        self.gridLayout_5.addWidget(self.psLabel, 0, 6, 1, 1)
        self.whpLabel = QtWidgets.QLabel(self.gridWidget1)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.whpLabel.setFont(font)
        self.whpLabel.setObjectName("whpLabel")
        self.gridLayout_5.addWidget(self.whpLabel, 0, 8, 1, 1)
        self.htLabel = QtWidgets.QLabel(self.gridWidget1)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.htLabel.setFont(font)
        self.htLabel.setObjectName("htLabel")
        self.gridLayout_5.addWidget(self.htLabel, 0, 5, 1, 1)
        self.gtLabel = QtWidgets.QLabel(self.gridWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.gtLabel.sizePolicy().hasHeightForWidth())
        self.gtLabel.setSizePolicy(sizePolicy)
        self.gtLabel.setMaximumSize(QtCore.QSize(16777215, 100))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.gtLabel.setFont(font)
        self.gtLabel.setObjectName("gtLabel")
        self.gridLayout_5.addWidget(self.gtLabel, 0, 4, 1, 1)
        self.pLabel = QtWidgets.QLabel(self.gridWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pLabel.sizePolicy().hasHeightForWidth())
        self.pLabel.setSizePolicy(sizePolicy)
        self.pLabel.setMaximumSize(QtCore.QSize(16777215, 100))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.pLabel.setFont(font)
        self.pLabel.setObjectName("pLabel")
        self.gridLayout_5.addWidget(self.pLabel, 0, 0, 1, 1)
        self.ghpLabel = QtWidgets.QLabel(self.gridWidget1)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.ghpLabel.setFont(font)
        self.ghpLabel.setObjectName("ghpLabel")
        self.gridLayout_5.addWidget(self.ghpLabel, 0, 9, 1, 1)
        self.wLabel = QtWidgets.QLabel(self.gridWidget1)
        self.wLabel.setMaximumSize(QtCore.QSize(16777215, 100))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.wLabel.setFont(font)
        self.wLabel.setObjectName("wLabel")
        self.gridLayout_5.addWidget(self.wLabel, 0, 2, 1, 1)
        self.verticalLayout.addWidget(self.gridWidget1)
        self.plotLayout = QtWidgets.QVBoxLayout()
        self.plotLayout.setObjectName("plotLayout")
        self.verticalLayout.addLayout(self.plotLayout)
        self.horizontalLayout.addWidget(self.verticalWidget1)
        self.verticalWidget2 = QtWidgets.QWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalWidget2.sizePolicy().hasHeightForWidth())
        self.verticalWidget2.setSizePolicy(sizePolicy)
        self.verticalWidget2.setMinimumSize(QtCore.QSize(250, 0))
        self.verticalWidget2.setMaximumSize(QtCore.QSize(220, 16777215))
        self.verticalWidget2.setObjectName("verticalWidget2")
        self.PlotLayout = QtWidgets.QVBoxLayout(self.verticalWidget2)
        self.PlotLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
        self.PlotLayout.setObjectName("PlotLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
        self.gridLayout.setObjectName("gridLayout")
        self.tempBox = QtWidgets.QDoubleSpinBox(self.verticalWidget2)
        self.tempBox.setMinimumSize(QtCore.QSize(150, 120))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.tempBox.setFont(font)
        self.tempBox.setMaximum(100.0)
        self.tempBox.setObjectName("tempBox")
        self.gridLayout.addWidget(self.tempBox, 6, 0, 1, 1)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.presPushButton = QtWidgets.QPushButton(self.verticalWidget2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.presPushButton.sizePolicy().hasHeightForWidth())
        self.presPushButton.setSizePolicy(sizePolicy)
        self.presPushButton.setMinimumSize(QtCore.QSize(100, 100))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.presPushButton.setFont(font)
        self.presPushButton.setStyleSheet("QPushButton{\n"
"border-style: solid;\n"
"border-color: #343434;\n"
"border-width: 5px;\n"
"border-radius: 20px;\n"
"}")
        self.presPushButton.setCheckable(True)
        self.presPushButton.setObjectName("presPushButton")
        self.gridLayout_2.addWidget(self.presPushButton, 2, 0, 1, 1)
        self.flowPushButton = QtWidgets.QPushButton(self.verticalWidget2)
        self.flowPushButton.setMinimumSize(QtCore.QSize(100, 100))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.flowPushButton.setFont(font)
        self.flowPushButton.setStyleSheet("QPushButton{\n"
"border-style: solid;\n"
"border-color: #343434;\n"
"border-width: 5px;\n"
"border-radius: 20px;\n"
"}")
        self.flowPushButton.setCheckable(True)
        self.flowPushButton.setObjectName("flowPushButton")
        self.gridLayout_2.addWidget(self.flowPushButton, 2, 1, 1, 1)
        self.gridLayout.addLayout(self.gridLayout_2, 2, 0, 1, 1)
        self.pressureSlider = QtWidgets.QSlider(self.verticalWidget2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pressureSlider.sizePolicy().hasHeightForWidth())
        self.pressureSlider.setSizePolicy(sizePolicy)
        self.pressureSlider.setMinimumSize(QtCore.QSize(0, 500))
        self.pressureSlider.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        self.pressureSlider.setAutoFillBackground(False)
        self.pressureSlider.setStyleSheet("\n"
"QSlider::groove:vertical { \n"
"    border: 5px solid #424242; \n"
"    height: 450px; \n"
"    border-radius: 30px;\n"
"}\n"
"\n"
"QSlider::handle:vertical { \n"
"    background-color: #343434; \n"
"    border: 10px #343434; \n"
"    width: 40px; \n"
"    height: 150px; \n"
"    line-height: 20px; \n"
"    margin-top: -5px; \n"
"    margin-bottom: -5px; \n"
"    border-radius: 25px; \n"
"}")
        self.pressureSlider.setMaximum(100)
        self.pressureSlider.setPageStep(1)
        self.pressureSlider.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.pressureSlider.setInvertedAppearance(False)
        self.pressureSlider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksAbove)
        self.pressureSlider.setTickInterval(10)
        self.pressureSlider.setObjectName("pressureSlider")
        self.gridLayout.addWidget(self.pressureSlider, 4, 0, 1, 1)
        self.pressureText = QtWidgets.QLabel(self.verticalWidget2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pressureText.sizePolicy().hasHeightForWidth())
        self.pressureText.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(20)
        self.pressureText.setFont(font)
        self.pressureText.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        self.pressureText.setObjectName("pressureText")
        self.gridLayout.addWidget(self.pressureText, 5, 0, 1, 1)
        self.startButton = QtWidgets.QPushButton(self.verticalWidget2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.startButton.sizePolicy().hasHeightForWidth())
        self.startButton.setSizePolicy(sizePolicy)
        self.startButton.setMinimumSize(QtCore.QSize(220, 180))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.startButton.setFont(font)
        self.startButton.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.startButton.setStyleSheet("QPushButton{\n"
"border-style: solid;\n"
"border-color: #343434;\n"
"border-width: 5px;\n"
"border-radius: 40px;\n"
"}")
        self.startButton.setCheckable(True)
        self.startButton.setObjectName("startButton")
        self.gridLayout.addWidget(self.startButton, 0, 0, 1, 1)
        self.PlotLayout.addLayout(self.gridLayout)
        self.horizontalLayout.addWidget(self.verticalWidget2)
        EspressoGUI.setCentralWidget(self.centralwidget)

        self.retranslateUi(EspressoGUI)
        QtCore.QMetaObject.connectSlotsByName(EspressoGUI)

    def retranslateUi(self, EspressoGUI):
        _translate = QtCore.QCoreApplication.translate
        EspressoGUI.setWindowTitle(_translate("EspressoGUI", "Closed Loop Espresso"))
        self.idleButton.setText(_translate("EspressoGUI", "Idle"))
        self.preheatButton.setText(_translate("EspressoGUI", "Preheat"))
        self.flushButton.setText(_translate("EspressoGUI", "Flush"))
        self.steamButton.setText(_translate("EspressoGUI", "Steam"))
        self.manualButton.setText(_translate("EspressoGUI", "Manual"))
        self.saveButton.setText(_translate("EspressoGUI", "Save Log"))
        self.tareButton.setText(_translate("EspressoGUI", "Tare"))
        self.fLabel.setText(_translate("EspressoGUI", "Flow\n"
"0.00"))
        self.wtLabel.setText(_translate("EspressoGUI", "Water Temp\n"
"0.00"))
        self.ptLabel.setText(_translate("EspressoGUI", "Pump Torque\n"
"0.00"))
        self.psLabel.setText(_translate("EspressoGUI", "Pump Speed\n"
"0.00"))
        self.whpLabel.setText(_translate("EspressoGUI", "WH Power\n"
"0.00"))
        self.htLabel.setText(_translate("EspressoGUI", "Heater Temp\n"
"0.00"))
        self.gtLabel.setText(_translate("EspressoGUI", "Group Temp\n"
"0.00"))
        self.pLabel.setText(_translate("EspressoGUI", "Pressure\n"
"0.00"))
        self.ghpLabel.setText(_translate("EspressoGUI", "GH Power\n"
"0.00"))
        self.wLabel.setText(_translate("EspressoGUI", "Weight\n"
"0.00"))
        self.presPushButton.setText(_translate("EspressoGUI", "Pressure"))
        self.flowPushButton.setText(_translate("EspressoGUI", "Flow"))
        self.pressureText.setText(_translate("EspressoGUI", "0.0"))
        self.startButton.setText(_translate("EspressoGUI", "Start"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    EspressoGUI = QtWidgets.QMainWindow()
    ui = Ui_EspressoGUI()
    ui.setupUi(EspressoGUI)
    EspressoGUI.show()
    sys.exit(app.exec())
