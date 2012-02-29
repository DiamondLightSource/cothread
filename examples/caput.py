#!/usr/bin/env python3
# Simple example of caget tool using cothread.

import require
from cothread.catools import *

import sys
from numpy import *
import optparse


parser = optparse.OptionParser(
    usage = 'Usage: %prog [options] pv value\nWrite value to PV')
parser.add_option(
    '-t', dest = 'timeout', default = 5, type = 'float',
    help = 'Specify caput timeout, default 5 seconds')
parser.add_option(
    '-c', dest = 'throw', default = True, action = 'store_false',
    help = 'Catch exception')
parser.add_option(
    '-d', dest = 'datatype', type = 'int', default = None,
    help = '''\
Define datatype to write.  The default from the command line is string,
options are:  0 => DBR_STRING, 1 => DBR_SHORT, 2 => DBR_FLOAT,
3 => DBR_ENUM, 4 => DBR_CHAR, 5 => DBR_LONG, 6 => DBR_DOUBLE,
999 => char array as string.''')
parser.add_option(
    '-w', dest = 'wait', default = False, action = 'store_true',
    help = 'Use caput with callback')
parser.add_option(
    '-W', dest = 'timeout', action = 'store_const', const = None,
    help = 'Wait forever.  Overrides -t option')
options, arglist = parser.parse_args()
if len(arglist) < 2:
    parser.print_help()
    sys.exit()

args = arglist[1:]
if len(args) == 1: args = args[0]
print(caput(arglist[0], args, datatype = options.datatype,
    timeout = options.timeout, wait = options.wait, throw = options.throw))
