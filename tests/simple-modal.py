#!/usr/bin/env python3

# Simple demonstration that timers and modal windows interact badly: if a modal
# window is created from within a timer then the timer is killed and the exec()
# loop exits.
#
# This means that the current iqt() implementation is incompatible with Qt modal
# windows.

import sys
from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QApplication, QMessageBox

qapp = QApplication(sys.argv)
timer = QTimer()

counts = 0
def timeout():
    global counts
    counts += 1
    print('tick', counts)

    if counts == 10:
        QMessageBox.information(None, 'My caption', 'This is a test')

timer.timeout.connect(timeout)
timer.start(100)

qapp.exec_()
