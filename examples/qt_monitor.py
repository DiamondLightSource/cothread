#!/usr/bin/env python2.4

'''minimal Qt example'''

import require
import cothread
from cothread import catools

try:
    from qt import QLabel
except ImportError:
    from PyQt4.QtGui import QLabel

cothread.iqt()


# make a label widget (None is the parent, this is top-level widget)
label = QLabel('Hello World', None)
label.resize(200, 50)
# must show top-level widgets manually
label.show()

# animate label
def signal(value):
    if value.ok:
        label.setText('DCCT %f' % value)


catools.camonitor('SR21C-DI-DCCT-01:SIGNAL', signal)
cothread.WaitForQuit()
