#!/usr/bin/env python2.4
# Simple example of camonitor tool using greenlets etcetera.

import sys

from numpy import *

from cothread.cothread import *
from cothread.catools import *


BPMS = ['SR%02dC-DI-EBPM-%02d' % (c+1, n+1)
    for c in range(24) for n in range(7)]
BPM_count = len(BPMS)

def BPMpvs(name):
    return ['%s:%s' % (bpm, name) for bpm in BPMS]


class MonitorWaveform:
    '''The MonitorWaveform class is the basic building block for monitoring an
    array of PVs, one per BPM.  The PV value read from each BPM is written into
    self.array.
    '''
    def __init__(self, name, tick=0.2, datatype = float):
        self.name = name
        self.value = zeros(BPM_count, dtype = datatype)
        self.changed = 0

        camonitor(BPMpvs(name), self.MonitorCallback, datatype = datatype)
        Spawn(self.timer, tick)
#        server.Timer(tick, self.Update)

    def timer(self, tick):
        while True:
            Sleep(tick)
            self.Update()

    def MonitorCallback(self, value, index):
        '''This routine is called each time any of the monitored elements
        changes.'''
        self.value[index] = value
        self.changed += 1

    def Update(self):
        '''This is called on a timer and is used to generate a collected update
        for the entire waveform.'''
        print 'tick', self.name, self.changed
        self.changed = 0


MonitorWaveform('SA:X')
MonitorWaveform('SA:Y')

Sleep(2)

# # Run until interrupted.
# WaitForQuit()