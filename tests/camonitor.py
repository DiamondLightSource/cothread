#!/usr/bin/env python2.4
# Simple example of camonitor tool catools library

import sys
import optparse

import require
from cothread.cothread import *
from cothread.catools import *

parser = optparse.OptionParser(
    usage = 'Usage: %prog pv-list\nMonitor PVs using channel access')
parser.add_option(
    '-d', dest = 'datatype', type = 'int',
    help = 'Define datatype to monitor')
parser.add_option(
    '-n', dest = 'count', default = 0, type = 'int',
    help = 'Define number of elements to fetch for each value')
parser.add_option(
    '-f', dest = 'format', default = FORMAT_RAW, type = 'int',
    help = 'Select format option')
parser.add_option(
    '-e', dest = 'events', default = DBE_VALUE,
    help = 'Define set of events to monitor')
parser.add_option(
    '-a', dest = 'all_updates', default = False, action = 'store_true',
    help = 'Report all available updates')
options, arglist = parser.parse_args()
if not arglist:
    parser.print_help()
    sys.exit()


def value_callback(value, index):
    if value.ok:
        print value.name, value
        for field in ca_extra_fields[2:]:   # Skip over name, ok.
            if hasattr(value, field):
                print field, getattr(value, field)
    else:
        print value.name, 'disconnected:', value

subscriptions = camonitor(arglist, value_callback,
    format = options.format, events = options.events,
    datatype = options.datatype, count = options.count,
    all_updates = options.all_updates)


WaitForQuit()
