#!/usr/bin/env python

import sys


from pkg_resources import require as Require
Require('matplotlib')
Require('cothread')

from cothread import *
from cothread.catools import *

from pylab import *
from numpy import *

readline_hook()
iqt()


ALL_BPMS = [
    'SR%02dC-DI-EBPM-%02d' % (cell+1, n+1)
    for cell in range(24)
    for n in range(7)]


pvs = ['SR01C-DI-EBPM-01:FR:WFX', 'SR01C-DI-EBPM-01:FR:WFY']

pvs = ['%s:%s' % (bpm, pv)
    for bpm in ALL_BPMS
    for pv in ('FR:WFX', 'FR:WFY')]


def do_plot(xs):
    return plot(*[xy for x in xs for xy in (arange(len(x)), x)])

def update_plot(l, x):
    l.set_ydata(x)
#    draw()
    
    from cothread import catools
    print (len(catools._Subscription._Subscription__callback_queue),
        x.update_count), 
    sys.stdout.flush()

def timer():
    while True:
        Sleep(0.5)
        draw()

ll = do_plot(caget(pvs, timeout = 10))
m = camonitor(pvs,
    lambda x, n:
        update_plot(ll[n], x),
    all_updates = False)

Spawn(timer)

WaitForQuit()
