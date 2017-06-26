#!/usr/bin/env python3

'''Channel Access Get Structure'''

import require
from cothread.catools import *

def show_result(result):
    '''show structure of channel access get results'''
    print('channel name:', result.name)
    print('channel access status:', result.ok)
    print('value:', result)

    for field in ca_extra_fields:
        if hasattr(result, field):
            print('%s: %s' % (field, getattr(result, field)))
    print()


PV = 'SR21C-DI-DCCT-01:SIGNAL'

for format in [FORMAT_RAW, FORMAT_TIME, FORMAT_CTRL]:
    show_result(caget(PV, format = format))

