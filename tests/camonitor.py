#!/usr/bin/env python2.4
# Simple example of camonitor tool using greenlets etcetera.

#from auto_loop import *
#import threads
from cothread import *
import catools
import sys


#threads.SpawnScheduler()

        
def value_callback(value, context):
    print value.name, value


pv_list = [
#    'TS-DI-EBPM-03:CF:KY_S',
    'TS-DI-EBPM-03:SA:X',
    'TS-DI-EBPM-03:FT:WFA',
    'TS-DI-EBPM-03:SA:MAXADC',
    'bogus'
]
#pv_list = pv_list[:1]


# This call raises a very interesting question: what do we do when scheduler
# calls are made before the scheduler is running (that is, in the scheduler's
# own task)?
subscriptions = catools.camonitor(
    pv_list, value_callback, datatype = float, count = 3)
#            datatype = str, count = 3))

#Spawn(OtherThread)

Sleep(1)
print 'Deleting subscription', subscriptions[0].name
subscriptions[0].close()
del subscriptions[0]

# Sleep(2)
# for pv in sys.argv[1:]:
#     print 'deleting', pv
#     del catools.channel_cache[pv]

#threads.InstallHook(lambda: catools.ca_pend_event(1e-9))
#threads.ScheduleLoop(1e-2)

#WaitForQuit()
Sleep(2)


# Sleep(2)
# # del subscriptions
# print 'Calling Quit()'
# Quit()
# print 'quitting'
