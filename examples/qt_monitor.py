#!/usr/bin/env python3

'''minimal Qt example'''

if __name__ == '__main__':
    import require

import cothread
from cothread.catools import *

from PyQt4.QtGui import QLabel

cothread.iqt()


# make a label widget (None is the parent, this is top-level widget)
label = QLabel('Hello World', None)
label.resize(200, 50)
# must show top-level widgets manually
label.show()

# animate label
def signal(value):
    label.setText('DCCT %f %s' % (value, value.units))

camonitor('SR21C-DI-DCCT-01:SIGNAL', signal, format = FORMAT_CTRL)

if __name__ == '__main__':
    cothread.WaitForQuit()
