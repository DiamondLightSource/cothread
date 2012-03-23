import time
import sys, os
sys.path.append(
    os.path.join(os.path.dirname(__file__), '../..'))

from cothread.catools import *

version_pvs = [
    'VERSION',
    'BUILD',
    'EPICS',
    'COMPILER',
    'LIBRARY',

    # These are extracted from environment variables
    'ABI',
    'UNAME',
    'LIBC',
    'DRIVER',
    'MSP',
    'FPGA',
    'ARCH',
    'ROOTFS',

    # These are all FPGA registers
    'COMPILED',
    'BUILDNO',
    'CUSTID',
    'DDCDEC',
    'FADEC',
    'CUSTOMER',
    'ITECH',
    # Customer Id as a string
    'CUSTIDSTR',

    'BR',
    'BRHW',
    'OLDBR',
    'DLS',
    'FF',
    'GBETH',
    'MAF',
    'ITMAXADC',
    'FPGA2',
    'DRIVER2',
]


bpms = [
    'SR%02dC-DI-EBPM-%02d' % (c+1,n+1) for c in range(24) for n in range(7)]
pvs = [
    'VE:%s' % v for v in version_pvs]

#     '%s:WF%s' % (z, a) for z in ['FR', 'TT'] for a in 'ABCDSQXY']

def getall(pvs, **kargs):
    return caget(['%s:%s' % (bpm, pv) for bpm in bpms for pv in pvs], **kargs)

def fetch():
    print('fetching', len(bpms) * len(pvs), 'pvs')
    start = time.time()
    val = getall(pvs, count=1, throw=False, timeout=20)
    end = time.time()
    print('fetched', len(val), 'pvs in', end - start, 'seconds')

    failed = [v for v in val if not v.ok]
    if failed:
        print('failed to fetch')
        for v in failed:
            print(v.name, v)

fetch()
fetch()
fetch()
