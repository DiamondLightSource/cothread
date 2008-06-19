#!/usr/bin/env python2.4
# Simple example of caget tool using greenlets etcetera.

import require
from cothread.catools import *

import sys
from numpy import *
import optparse


parser = optparse.OptionParser(
    usage = 'Usage: %prog [options] pv value\nWrite value to PV')
parser.add_option(
    '-t', dest = 'timeout', default = None, type = 'float',
    help = 'Specify caget timeout')
parser.add_option(
    '-c', dest = 'throw', default = True, action = 'store_false',
    help = 'Catch exception')
parser.add_option(
    '-w', dest = 'wait', default = False, action = 'store_true',
    help = 'Use caput with callback')
options, arglist = parser.parse_args()
if len(arglist) < 2:
    parser.print_help()
    sys.exit()

print caput(arglist[0], arglist[1:],
    timeout = options.timeout, wait = options.wait, throw = options.throw)
