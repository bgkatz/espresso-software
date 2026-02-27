#!/usr/bin/env python3
"""
PiEspresso — QML-based espresso machine controller.
Entry point: sets environment, creates the QML engine, wires the controller.
"""
import sys
import os

# Must be set before QApplication is created
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")

from PyQt6.QtWidgets import QApplication      # QApplication needed on Windows for platform integration
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QUrl
from PyQt6 import QtCharts  # noqa: F401 — registers QtCharts QML plugin

from controller import EspressoController


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PiEspresso")

    controller = EspressoController()

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("controller", controller)
    # Register the profile model separately — more reliable than pyqtProperty(QObject)
    engine.rootContext().setContextProperty("profileModel", controller.profileModel)

    qml_path = os.path.join(os.path.dirname(__file__), "qml", "main.qml")
    engine.load(QUrl.fromLocalFile(qml_path))

    if not engine.rootObjects():
        print("ERROR: Failed to load QML — check qml/main.qml and imports.")
        controller.shutdown()
        sys.exit(-1)

    ret = app.exec()
    controller.shutdown()
    sys.exit(ret)


if __name__ == "__main__":
    main()
