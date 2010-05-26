# from pkg_resources import require
# require('cothread')

from cothread.catools import *

bpms = [
    'SR%02dC-DI-EBPM-%02d' % (c+1,n+1) for c in range(24) for n in range(7)]

def getall(pv, **kargs): 
    return caget(['%s:%s' % (bpm, pv) for bpm in bpms], **kargs)

# print getall('bogus', timeout=1)
print getall('SA:X')
