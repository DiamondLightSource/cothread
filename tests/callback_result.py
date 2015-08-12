# Simple test of CallbackResult class

import threading
import sys
import traceback

import require

import cothread
from cothread.catools import *

def Thread():
    for pv in sys.argv[1:]:
        print(pv, '=>', end = ' ')
        try:
            v = cothread.CallbackResult(caget, pv)
            print(v)
        except:
            print('failed')
            traceback.print_exc()

    cothread.Callback(cothread.Quit)

threading.Thread(target = Thread).start()
cothread.WaitForQuit()
