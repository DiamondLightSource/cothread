#!/usr/bin/env python2.4

import sys

import require
from cothread import *
from cothread.catools import *

from pkg_resources import require as Require
Require('matplotlib')

from pylab import *
from numpy import *

iqt()


ALL_BPMS = [
    'SR%02dC-DI-EBPM-%02d' % (cell+1, n+1)
    for cell in range(24)
    for n in range(7)]

ALL_BPMS = ['SR01C-DI-EBPM-%02d' % (cell+1) for cell in range(2)]


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
        print 'tick'
        draw()

#ioff()
ll = do_plot(caget(pvs, timeout = 10))
m = camonitor(pvs,
    lambda x, n:
        update_plot(ll[n], x),
    all_updates = False)

Spawn(timer)

WaitForQuit()
