#!/usr/bin/env python2.4
# Simple example of caget tool using greenlets etcetera.


import sys
import optparse
import traceback

from cothread.catools import *



parser = optparse.OptionParser(
    usage = 'Usage: %prog ioc-list\nRetrieve PV values over channel access')
parser.add_option(
    '-d', dest = 'datatype', type = 'int',
    help = 'Define datatype to fetch')
parser.add_option(
    '-n', dest = 'count', default = 0, type = 'int',
    help = 'Define number of elements to fetch for each value')
parser.add_option(
    '-f', dest = 'format', default = FORMAT_RAW, type = 'int',
    help = 'Select format option')
parser.add_option(
    '-t', dest = 'timeout', default = None, type = 'float',
    help = 'Specify caget timeout')
parser.add_option(
    '-c', dest = 'throw', default = True, action = 'store_false',
    help = 'Catch exception')
options, arglist = parser.parse_args()
if not arglist:
    parser.print_help()
    sys.exit()


extra_fields = [
    'status',
    'severity',
    'timestamp',
    'units',
    'upper_disp_limit',
    'lower_disp_limit',
    'upper_alarm_limit',
    'lower_alarm_limit',
    'upper_warning_limit',
    'lower_warning_limit',
    'upper_ctrl_limit',
    'lower_ctrl_limit',
    'precision',
    'enums',
]
    

get = caget(arglist,
    timeout = options.timeout, datatype = options.datatype,
    format = options.format, count = options.count, throw = options.throw)
for result in get:
    if result.ok:
        print result.name, type(result), repr(result)
        for field in extra_fields:
            if hasattr(result, field):
                print field, getattr(result, field)
    else:
        print result.name, 'failed', result
