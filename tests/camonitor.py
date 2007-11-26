#!/usr/bin/env python2.4
# Simple example of camonitor tool using greenlets etcetera.

from cothread.cothread import *
from cothread.catools import *
import sys


def value_callback(value, index):
    print value.timestamp, value.name, value


pv_list = [
#    'TS-DI-EBPM-03:CF:KY_S',
    'SR01C-DI-EBPM-03:SA:X',
    'SR01C-DI-EBPM-03:FT:WFA',
    'SR01C-DI-EBPM-03:SA:MAXADC',
#     'TS-DI-EBPM-03:SA:X',
#     'TS-DI-EBPM-03:FT:WFA',
#     'TS-DI-EBPM-03:SA:MAXADC',
    'bogus'
]


subscriptions = camonitor(
    pv_list, value_callback, datatype = float, count = 3, format = FORMAT_TIME)

Sleep(1)
print 'Deleting subscription', subscriptions[0].name
subscriptions[0].close()
del subscriptions[0]

WaitForQuit()
