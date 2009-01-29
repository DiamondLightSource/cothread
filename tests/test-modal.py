#!/usr/bin/env python2.4

import require
import cothread
from cothread import *
import time
import readline
import os
import sys

def FakeIqt(sleep_time, yield_time):
    while True:
        time.sleep(sleep_time)
        Yield(yield_time)
# Spawn(FakeIqt, 0.0001, 0.05)

if False:
    r, w = os.pipe()
    @Spawn
    def Waiter():
        while True:
            cothread.select([r], [], [])
            rx = os.read(r, 1)
            print 'read', rx
    @Spawn
    def Writer():
        for n in xrange(1000):
            Sleep(0.2)
            os.write(w, str(n))

iqt(use_timer = int(sys.argv[1]))

try:
    from qt import QMessageBox
except ImportError:
    from PyQt4.QtGui import QMessageBox

@Spawn
def MessageBox():
    Sleep(1)
    print 'Creating message box'
    QMessageBox.information(None, 'My caption', 'This is a test')
    print 'Message box done'


x = raw_input('> ')
print 'read', repr(x)
