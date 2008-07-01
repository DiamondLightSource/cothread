# This file is part of the Diamond cothread library.
#
# Copyright (C) 2007 James Rowland, 2007-2008 Michael Abbott,
# Diamond Light Source Ltd.
#
# The Diamond cothread library is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License,
# or (at your option) any later version.
#
# The Diamond cothread library is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
# Contact:
#      Dr. Michael Abbott,
#      Diamond Light Source Ltd,
#      Diamond House,
#      Chilton,
#      Didcot,
#      Oxfordshire,
#      OX11 0DE
#      michael.abbott@diamond.ac.uk

'''Simple readline hook to allow the scheduler to run while we're waiting
for input from the interpreter command line.  Also includes optional support
for the Qt event loop.'''

import ctypes
import select
import sys
import os
import traceback

from ctypes import *

import cothread
import coselect

from cothread import _scheduler


__all__ = [
    'iqt',              # Enable interactive Qt loop
]


hook_function = CFUNCTYPE(c_int)


@hook_function
def _readline_hook():
    '''Runs the scheduler hook until either input is available on stdin or a
    keyboard interrupt occurs.'''
    stdin = 0
    try:
        ready_list = []
        while True:
            # Let the scheduler run.  We tell it which sockets are ready, and
            # it returns with a new list of sockets to watch.  We add our own
            # stdin socket to the set.
            poll_list, timeout = _scheduler.poll_scheduler(ready_list)
            # Oh blast: we have to do some hacking here to add stdin to the
            # poll_list.
            for i in range(len(poll_list)):
                if poll_list[i][0] == stdin:
                    poll_list[i] = (stdin, poll_list[i][1] | coselect.POLLIN)
                    break
            else:
                poll_list.append((stdin, coselect.POLLIN))
                
            # Wait until either stdin or the scheduler are ready.
            ready_list = _scheduler._poll_block(poll_list, timeout)

            # Check for input on stdin
            for file, events in ready_list:
                if file == stdin and events & coselect.POLLIN:
                    return
    except KeyboardInterrupt:
        print 'Control C (probably) ignored'
    except:
        print 'Exception raised from scheduler'
        traceback.print_exc()


def _install_readline_hook(enable_hook = True):
    '''Install readline hook.  This allows the scheduler to run in parallel
    with interactive python: while readline is waiting for input, the
    scheduler still operates.
        This routine can also be used to disable the input hook by setting the
    enable_hook parameter to False -- for example, this can be helpful if a
    background activity is causing a nuisance.'''
    
    PyOS_InputHookP = pointer(hook_function.in_dll(
        pythonapi, 'PyOS_InputHook'))
    if enable_hook:
        PyOS_InputHookP[0] = _readline_hook
    else:
        cast(PyOS_InputHookP, POINTER(c_void_p))[0] = 0


def _poll_iqt(qt, poll_interval):
    while True:
        qt.qApp.processEvents(poll_interval)
        cothread.Sleep(poll_interval / 1000.)


def iqt(poll_interval = 10):
    '''Installs Qt event handling hook.  The polling interval is in
    milliseconds.'''
    import qt
    if qt.qApp.startingUp():
        # If the Qt application hasn't been created yet then build it now.
        # We need to hang onto the pointer, otherwise it will go away!
        global _qapp
        _qapp = qt.QApplication(sys.argv)

    # Ensure a quit request is made when the last Qt window is closed.
    qt.qApp.connect(qt.qApp, qt.SIGNAL('lastWindowClosed()'), cothread.Quit)
    # Run the Qt event loop.  Unfortunately we have to run it in polling
    # mode: connecting up all the sockets might be feasible, but anyway,
    # that's how it's done now.
    cothread.Spawn(_poll_iqt, qt, poll_interval)


# Automatically install the readline hook.  This is the safest thing to do.
_install_readline_hook(True)
