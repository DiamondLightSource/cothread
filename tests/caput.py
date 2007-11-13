#!/usr/bin/env python2.4
# Simple example of caget tool using greenlets etcetera.

from cothread.catools import *

import sys
from numpy import *
import optparse



# print caput('ENUM', 'Zero')
# print repr(caget('ENUM'))
# 
# print caput('STRIN', 'test string')
# print repr(caget('STRIN'))
# 
# print caput('STROUT', 'another test')
# print repr(caget('STROUT'))
# 
# # print caput('STROUT', 'x' * 40)
# # print caget('STROUT')
# 
# sys.exit()


def SetAndTest(pv, value):
    print caput(pv, value)
    print caget(pv, count = 6)

SetAndTest('TESTWF', zeros(6))
SetAndTest('TESTWF', ones(6))
SetAndTest('TESTWF', map(str, 2*ones(6)))
SetAndTest('TESTWF', 'rubbish')

sys.exit()


value = numpy.arange(6, dtype = float)

for i in 0.2 + numpy.arange(3) * 0.1:
#     print catools.caput('SR-DI-DCCT-01:SIGNAL', value + i, wait = True,
#         throw = False)
    output = map(str, value + i)
#    output = '1234'
#    output = value + i
    print caput('TESTWF', output, wait = True)
    print caget('TESTWF', count = 6)
