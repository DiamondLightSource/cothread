#!/usr/bin/env python3

'''camonitor minimal example'''

from __future__ import print_function

import require
from cothread.catools import *
from cothread import WaitForQuit

def callback(value):
    '''monitor callback'''
    print(value.name, value)

camonitor('TS-DI-EBPM-01:FR:WFX', callback)

WaitForQuit()
