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


def _poll_iqt(poll_interval, qt_timer, qt_quit, qt_exec):
    while True:
        try:
            qt_timer(poll_interval, qt_quit)
            qt_exec()
            cothread.Yield()
        except KeyboardInterrupt:
            print 'caught keyboard interrupt'

        
def iqt(poll_interval = 50):
    '''Installs Qt event handling hook.  The polling interval is in
    milliseconds.'''

    # Unfortunately the two versions of Qt that we support have subtly
    # different interfaces, so we have to figure out which one we've got and
    # implement the event hook accordingly.
    global _qapp
    try:
        # Try for Qt4 first.
        from PyQt4.QtCore import QCoreApplication, QTimer, SIGNAL
        from PyQt4.QtGui import QApplication

        # Qt4 startup
        if QCoreApplication.startingUp():
            _qapp = QApplication(sys.argv)

        QCoreApplication.connect(
            QCoreApplication.instance(),
            SIGNAL('lastWindowClosed()'), cothread.Quit)
            
        # Qt4 polling
        cothread.Spawn(
            _poll_iqt, poll_interval,
            QTimer.singleShot, QCoreApplication.quit, QCoreApplication.exec_)
    except ImportError:
        # No Qt4 found, so try for qt (version 3) instead.  If this fails then
        # we'll just let the error propagate
        import qt

        # Qt3 startup
        if qt.qApp.startingUp():
            _qapp = qt.QApplication(sys.argv)

        qt.qApp.connect(
            qt.qApp, qt.SIGNAL('lastWindowClosed()'), cothread.Quit)
            
        # Qt3 polling
        cothread.Spawn(
            _poll_iqt, poll_interval,
            qt.QTimer.singleShot, qt.qApp.quit, qt.qApp.exec_loop)


# Automatically install the readline hook.  This is the safest thing to do.
_install_readline_hook(True)
