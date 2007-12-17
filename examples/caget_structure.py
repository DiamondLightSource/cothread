#!/bin/env python2.4

"Channel Access Get Structure"

from pkg_resources import require
require('cothread')
from cothread.catools import *

def show_result(result):
    "show structure of channel access get results"
#    print "request type:", result.dbr.__class__
    print "channel name:", result.name
    print "channel access status:", result.ok
    # print "scalar value:", result.value
    print "value:", result

    for field in [
        'units', 'upper_alarm_limit', 'upper_ctrl_limit', 'upper_disp_limit',
        'upper_warning_limit', 'lower_alarm_limit', 'lower_ctrl_limit',
        'lower_disp_limit', 'lower_warning_limit', 'precision']:

        if hasattr(result, field):
            print "%s: %s" % (field, getattr(result, field))

    print

                 
result = caget("SR21C-DI-DCCT-01:SIGNAL")
show_result(result)

# for datatype in [dbr_double,
#                  dbr_time_double,
#                  dbr_ctrl_double,
#                  dbr_string,
#                  dbr_long]:
for format in [FORMAT_RAW, FORMAT_TIME, FORMAT_CTRL]:

    result = caget("SR21C-DI-DCCT-01:SIGNAL", format = format)
    show_result(result)

