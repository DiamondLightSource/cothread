#!/usr/bin/env python3

import time
import sys
import os

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import cothread
from cothread.catools import *

if sys.argv[1:]:
    count = int(sys.argv[1])
else:
    count = 0

callbacks = 0

def callback(value):
    global callbacks
    callbacks += 1
    if value.update_count != 1:
        print('update_count', value.update_count)

camonitor("ARAVISCAM1:ARR:ArrayData", callback, count=count, all_updates=True)

@cothread.Spawn
def timer():
    last = time.time()
    last_callbacks = 0
    while True:
        cothread.Sleep(1)
        now = time.time()
        print("%d callbacks" % callbacks, callbacks - last_callbacks)
        last = now
        last_callbacks = callbacks

cothread.WaitForQuit()
