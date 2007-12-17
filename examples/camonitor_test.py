#!/usr/bin/env python2.4

"camonitor minimal example"

from pkg_resources import require
require('cothread')
from cothread.catools import *
from cothread import *

def callback(value):
    "monitor callback"
    print value.name, value
    
camonitor("SR21C-DI-EBPM-01:FR:WFX", callback)

WaitForQuit()
