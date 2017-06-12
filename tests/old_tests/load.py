#!/usr/bin/env python3

import require

from cothread import *
from cothread.catools import *


def BPMS(pv):
    return ['SR%02dC-DI-EBPM-%02d:%s' % (cell+1, id+1, pv)
        for cell in range(24)
        for id in range(7)]


class MonitorWf:
    def __init__(self, pv, dtype = float):
        camonitor(BPMS(pv), self.on_update,
            datatype = dtype, all_updates = True)

    def on_update(self, value, index):
        pass

Monitors = [
    ('SA:X',        float),
    ('SA:Y',        float),
    ('SA:MAXADC',   int),
    ('FR:STDX',     float),   ('FR:PPX',      float),
    ('FR:STDY',     float),   ('FR:PPY',      float),

    # Postmortem statistics
    ('PM:X_OFFSET',   int),     ('PM:X_OFL',      bool),
    ('PM:Y_OFFSET',   int),     ('PM:Y_OFL',      bool),
    ('PM:ADC_OFFSET', int),     ('PM:ADC_OFL',    bool),
]

for name, datatype in Monitors:
    MonitorWf(name, datatype)

print('going')
WaitForQuit()
