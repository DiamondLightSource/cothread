import input_hook

from cothread import *

def Reader(queue):
    while True:
        x = queue.Wait()
        print('got', x)

e1 = Event()
e2 = Event()
q = EventQueue()

Spawn(Reader, e1)
s = Spawn(Reader, e2, raise_on_wait = True)
Spawn(Reader, q)

e1.Signal()
e2.Signal()
map(q.Signal, 'testing')

print('Signalling e1')
e1.SignalException(Exception)

print('Signalling e2')
e2.SignalException(Exception)

# print('Waiting for stuff')
# s.Wait()

import time

def run_ticker(delay = 1):
    def Ticker():
        while True:
            time.sleep(delay)
            Sleep(delay)
    Spawn(Ticker)
