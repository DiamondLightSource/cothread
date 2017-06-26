#!/usr/bin/env python3

import sys

import require
from cothread import *
from cothread.catools import *

import pkg_resources
pkg_resources.require('matplotlib')

from pylab import *
from numpy import *

iqt()


ALL_BPMS = [
    'SR%02dC-DI-EBPM-%02d' % (cell+1, n+1)
    for cell in range(24)
    for n in range(7)]

ALL_BPMS = ['BR01C-DI-EBPM-%02d' % (cell+1) for cell in range(2)]


pvs = ['%s:%s' % (bpm, pv)
    for bpm in ALL_BPMS
    for pv in ('FR:WFX', 'FR:WFY')]


def do_plot(xs):
    return plot(*[xy for x in xs for xy in (arange(len(x)), x)])

def update_plot(l, x):
    l.set_ydata(x)
    draw()

    from cothread import catools
    print((len(Callback.values), x.update_count), end='')
    sys.stdout.flush()
    Yield()     # Needed here or in Callback queue

ll = do_plot(caget(pvs, timeout = 10))
show()

print(pvs)
m = camonitor(pvs, lambda x, n: update_plot(ll[n], x))

WaitForQuit()
