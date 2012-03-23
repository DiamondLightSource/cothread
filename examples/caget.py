#!/usr/bin/env python3
# Simple example of caget tool using cothread.

import sys
import optparse

import require
from cothread.catools import *
import numpy


parser = optparse.OptionParser(
    usage = 'Usage: %prog pv-list\nRetrieve PV values over channel access')
parser.add_option(
    '-d', dest = 'datatype', type = 'int', default = None,
    help = '''\
Define datatype to fetch.  The default is the native data type,
options are:  0 => DBR_STRING, 1 => DBR_SHORT, 2 => DBR_FLOAT,
3 => DBR_ENUM, 4 => DBR_CHAR, 5 => DBR_LONG, 6 => DBR_DOUBLE, 
999 => char array as string.''')
parser.add_option(
    '-n', dest = 'count', default = 0, type = 'int',
    help = 'Define number of elements to fetch for each value')
parser.add_option(
    '-f', dest = 'format', default = FORMAT_RAW, type = 'int',
    help = '''\
Select format option.  Options are 0 => FORMAT_RAW, 1 => FORMAT_TIME,
2 => FORMAT_CTRL.  Default is 0.''')
parser.add_option(
    '-t', dest = 'timeout', default = 5, type = 'float',
    help = 'Specify caget timeout in seconds.  Default is 5 seconds.')
parser.add_option(
    '-c', dest = 'throw', default = True, action = 'store_false',
    help = '''\
Catch exception.  If not set any failing PV will case a traceback
to be generated.''')
parser.add_option(
    '-W', dest = 'timeout', action = 'store_const', const = None,
    help = 'Wait forever.  Overrides -t option')

options, arglist = parser.parse_args()
if not arglist:
    parser.print_help()
    sys.exit()


# Discard the first two names, 'name' and 'ok', as we show these anyway.
extra_fields = ca_extra_fields[2:]

get = caget(arglist,
    timeout = options.timeout, datatype = options.datatype,
    format = options.format, count = options.count, throw = options.throw)
for result in get:
    if result.ok:
        print(result.name, end = ' ')
        if isinstance(result, numpy.ndarray):
            print('[', ', '.join(map(repr, result)), ']')
        else:
            print(repr(result))

        for field in extra_fields:
            if hasattr(result, field):
                print(field, getattr(result, field))
    else:
        print(result.name, 'failed:', result)
