#!/usr/bin/env python3

# Designed to test late loading of Qt input hook.

import require
import sys

from PyQt4 import QtGui

def pressed(state):
    import cothread
    from cothread import catools

    cothread.iqt(run_exec = False)

    global label
    label = QtGui.QLabel('Hello there', None)
    label.show()

    catools.camonitor('SR21C-DI-DCCT-01:SIGNAL', signal)

def signal(value):
    label.setText('%f' % value)

qapp = QtGui.QApplication(sys.argv)

button = QtGui.QPushButton('Button', None)
button.clicked.connect(pressed)
button.show()

qapp.exec_()
