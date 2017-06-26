#!/usr/bin/env python3

import greenlet
import time

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'cothread'))
import _coroutine


def nothing(i):
    pass


def make_greenlet(i):
    return greenlet.greenlet(nothing)

def call_greenlet(g):
    return g.switch(0)

current = _coroutine.get_current()
def make_coroutine(i):
    return _coroutine.create(current, nothing, 0)

def call_coroutine(c):
    return _coroutine.switch(c, 0)

def timing_test(name, action, count):
    if isinstance(count, int):
        count = range(count)
    now = time.time()
    result = map(action, count)
    duration = time.time() - now
    print('%s took %g ns' % (name, 1e9 * duration / len(count)))
    return result

N = 1000000
timing_test('nothing', nothing, N)
greenlets = timing_test('create greenlet', make_greenlet, N)
timing_test('switch greenlet', call_greenlet, greenlets)
coroutines = timing_test('create coroutine', make_coroutine, N)
timing_test('switch coroutine', call_coroutine, coroutines)
