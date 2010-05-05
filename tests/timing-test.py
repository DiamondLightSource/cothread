#!/usr/bin/env python2.4

from greenlet import *
from time import *


def nothing(i):
    pass


def make_greenlet(i):
    return greenlet(nothing)

def call_greenlet(g):
    return g.switch(0)


def timing_test(name, action, count):
    if isinstance(count, int):
        count = range(count)
    now = time()
#    result = [action(i) for i in count]
    result = map(action, count)
    duration = time() - now
    print action, 'took', 1e9 * duration / len(count), 'ns'
    return result

timing_test('nothing', nothing, 100000)
greenlets = timing_test('greenlet', make_greenlet, 100000)
timing_test('switch', call_greenlet, greenlets)
