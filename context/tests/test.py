import sys, os
sys.path.append(
    os.path.join(os.path.dirname(__file__), '../..'))

import cothread
from cothread.catools import *
cothread.cothread._coroutine.enable_check_stack(True)

CELLS = 24
bpms = [
    'SR%02dC-DI-EBPM-%02d' % (c+1,n+1) for c in range(CELLS) for n in range(7)]

def getall(pv, **kargs): 
    return caget(['%s:%s' % (bpm, pv) for bpm in bpms], **kargs)

# print(getall('bogus', timeout=1)))
print(getall('SA:X', count=1))
