#!/usr/bin/env python3

# Simple recursion overflow test, checks that guard pages do indeed guard
# against stack overflow (by generating a segmentation fault).

import os
os.environ['COTHREAD_CHECK_STACK'] = 'yes'

import require
import cothread
from cothread import _coroutine

def recurse(n):
    print('recursing', n)
    stack = _coroutine.stack_use(_coroutine.get_current())
    print('stack', stack)
    assert stack[0] <= stack[2]
    recurse(n + 1)

cothread.Spawn(recurse, 0, stack_size = 8192)
cothread.Yield()
# We're dead
