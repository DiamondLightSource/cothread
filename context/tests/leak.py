#!/usr/bin/env python3

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from cothread import *

def Task():
    pass

def run(N):
    print('start', sys.gettotalrefcount())
    tasks = [Spawn(Task) for n in range(N)]
    for t in tasks:
        t.Wait()
    print('done', sys.gettotalrefcount())

for i in range(5):
    run(10)
    print('None', sys.getrefcount(None))
