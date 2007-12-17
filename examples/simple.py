#!/bin/env python2.4

'''Channel Access Example'''

# load correct version of catools
from pkg_resources import require
require('cothread')
from cothread.catools import *

print caget('SR21C-DI-DCCT-01:SIGNAL')
