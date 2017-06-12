#!/usr/bin/env python3

'''Tests for memory leaks.'''

import sys
sys.path.append('/scratch/local/python-debug')

import os

import require
from cothread import *
from cothread import select


# e = Event()
# Timer(0, e.Signal)
# e.Wait(0.1)


last_ref_count = sys.gettotalrefcount()
def Log(who=''):
    global last_ref_count
    this_ref_count = sys.gettotalrefcount()
    delta = this_ref_count - last_ref_count
    print(who, 'refs:', this_ref_count, 'delta:', delta)
    last_ref_count = this_ref_count

def Reset():
    global last_ref_count
    last_ref_count = sys.gettotalrefcount()

def TopTest(function):
    end_ref_count = 0
    start_ref_count = sys.gettotalrefcount()
    Reset()
    function()
    end_ref_count = sys.gettotalrefcount()
    print(function.__name__, end_ref_count - start_ref_count)



def Waiter(event, timeout, who = 'Waiter', count = 100):
    for i in xrange(count):
        try:
            event.Wait(timeout)
        except Timedout:
            pass
#             print('timeout', timeout,)
#     Log(who)


class MyFail(Exception): pass
def Fail():
    raise MyFail


# Leaks from unexpired timers.
def testUnexpiredTimers():
    e1 = Event()
    t = Spawn(Waiter, e1, 1000, 'Unexpired', 5)
    Reset()
    for i in range(5):
        e1.Signal()
        Yield()
    t.Wait()

# Leaks from timeouts
def testTimeouts():
    e1 = Event()
    t = Spawn(Waiter, e1, 0.01, 'Timeout', 1)
    Sleep(0.1)
    t.Wait()

# Leaks from WaitForAll
def testWaitForAll():
    for i in range(5):
        try:
            WaitForAll([Spawn(Fail, raise_on_wait = True) for j in range(5)])
        except MyFail:
            pass
#             print('Failed',)
#         Log('WaitForAll')


# Hopefully no leaks from spawn
def testSpawnFail():
    for i in range(5):
        try:
            task = Spawn(Fail, raise_on_wait = True)
            task.Wait()
        except MyFail:
            pass
#             print('Failed',)
#         Log('Spawn')

def testSpawnOk():
    def Succeed():
        return True
    tasks = [Spawn(Succeed) for i in range(5)]
    for t in tasks:
        t.Wait()


def testSelect():
    r, w = os.pipe()
    Reset()
    for i in range(5):
        select([r, w], [w], [], 1)
#     os.close(r)
#     os.close(w)


TopTest(testTimeouts)

#
TopTest(testUnexpiredTimers)
TopTest(testTimeouts)
TopTest(testWaitForAll)
TopTest(testSpawnFail)
TopTest(testSpawnOk)

TopTest(testSelect)
TopTest(testSelect)
