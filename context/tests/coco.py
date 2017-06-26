#!/usr/bin/env python

from __future__ import print_function

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from cothread import *

def Task(name, count, result, verbose):
    if verbose: print(name, 'starting')
    for n in range(count):
        Yield()
        if verbose: print(name, 'in control')
    if verbose: print(name, 'done')
    return result

for n in range(20):
    tasks = [Spawn(Task, 'task %d' % n, n, n, False) for n in range(10)]
    result = WaitForAll(tasks)
    print('result', result, sys.gettotalrefcount())
#     print('result', result)
