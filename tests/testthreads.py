#!/usr/bin/env python3

import require
from cothread.cothread import *
from time import time as time_time

def time():
    return time_time() - start


def thread_one():
    print('thread one starting', time())
    Sleep(0.5)
    print('thread one woken', time())
    Sleep(0.5)
    print('thread one woken and ending', time())

def thread_two():
    print('thread two starting', time())
    Sleep(2)
    print('bye bye', time())
#    Quit()

def thread_three():
    Sleep(1.5)
    print('thread three ending')
    end_event.Signal()

def ticker(name):
    while True:
        print('tick', name, time())
        Sleep(0.5)


def wait_for(event, timeout):
    print('wait_for', event, 'starting')
    while True:
        try:
            e = event.Wait(timeout)
        except Timedout:
            print('Timed out')
        else:
            print('Got event', e)
#        Yield()

def signaller(event):
    print('signaller', event, 'starting')
    while True:
        Sleep(0.9)
        print('Signalling')
        event.Signal()


if __name__ == '__main__':
#    threads.SpawnScheduler()

    start = time_time()

#     Spawn(thread_one)
    thread_two = Spawn(thread_two)
    Spawn(thread_three)

#     Spawn(ticker, 'ticker one')
#     Spawn(ticker, 'ticker two')

    event = Event()
    Spawn(wait_for, event, 0.5)
    Spawn(signaller, event)

    end_event = Event()
    ok = end_event.Wait()
    print('saw end_event', ok)
#     Sleep(2)
#     print('sleep ended')
#    Sleep(1)

#     ScheduleLoop()
#    WaitForQuit()
    thread_two.Wait()
    print('Normal exit')
