#!/usr/bin/env python3

'''camonitor minimal example'''

import require
from cothread.catools import *
from cothread import WaitForQuit

def callback(value):
    '''monitor callback'''
    print(value.name, value)

camonitor('TS-DI-EBPM-01:FR:WFX', callback)

WaitForQuit()
