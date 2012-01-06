# This file is part of the Diamond cothread library.
#
# Copyright (C) 2007 James Rowland, 2007-2010 Michael Abbott,
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

import select
import sys
import os
import traceback

import cothread
import coselect


__all__ = [
    'iqt',              # Enable interactive Qt loop
]


# When Qt is running in its own stack it really needs quite a bit of room.
QT_STACK_SIZE = 1024 * 1024


def _readline_hook():
    '''Runs other cothreads until input is available.'''
    coselect.poll_list([(0, coselect.POLLIN)])


def _install_readline_hook(enable_hook = True):
    '''Install readline hook.  This allows the scheduler to run in parallel
    with interactive python: while readline is waiting for input, the
    scheduler still operates.
        This routine can also be used to disable the input hook by setting the
    enable_hook parameter to False -- for example, this can be helpful if a
    background activity is causing a nuisance.'''

    from _coroutine import install_readline_hook
    if enable_hook:
        install_readline_hook(_readline_hook)
    else:
        install_readline_hook(None)



def _poll_iqt(poll_interval):
    from PyQt4 import QtCore
    while True:
        try:
            QtCore.QTimer.singleShot(poll_interval * 1e3, _qapp.quit)
            _qapp.exec_()
            cothread.Yield(poll_interval)
        except KeyboardInterrupt:
            print 'caught keyboard interrupt'


# This is used by the _run_iqt timeout() function to avoid nested returns.
_global_timeout_depth = 0

def _timer_iqt(poll_interval):
    def timeout():
        # To avoid nested returns from timeout (which effectively means we
        # would resume the main Qt thread from within a Qt message box -- not
        # a good idea!) we keep track of how many nested calls to timeout()
        # there are.  Then we refuse to return until we're at the top of the
        # stack.
        global _global_timeout_depth
        _global_timeout_depth += 1
        timeout_depth = _global_timeout_depth

        cothread.Yield(poll_interval)
        while _global_timeout_depth > timeout_depth:
            cothread.Sleep(poll_interval)

        _global_timeout_depth -= 1

    # Set up a timer so that Qt polls cothread.  All the timer needs to do
    # is to yield control to the coroutine system.
    from PyQt4 import QtCore
    timer = QtCore.QTimer()
    timer.timeout.connect(timeout)
    timer.start(poll_interval * 1e3)

    return timer


def _run_iqt(poll_interval):
    # Start the cothread polling timer before handing control over to Qt.  Note
    # that we need to hang onto the timer, otherwise it will go away!
    timer = _timer_iqt(poll_interval)
    _qapp.exec_()


def iqt(poll_interval = 0.05, use_timer = True, run_exec = True, argv = None):
    '''Installs Qt event handling hook.  The polling interval is in
    seconds.'''

    global _qapp
    if _qapp is not None:
        return _qapp

    from PyQt4 import QtCore, QtGui

    # Enusre that there is a QtApplication instance.
    _qapp = QtCore.QCoreApplication.instance()
    if _qapp is None:
        if argv is None:
            argv = sys.argv
        _qapp = QtGui.QApplication(argv)

    # Ensure we get a Quit event when the last window goes.  This allows the
    # application to simply rest on WaitForQuit().
    _qapp.lastWindowClosed.connect(cothread.Quit)

    if run_exec:
        # We run our own exec loop.
        if use_timer:
            iqt_thread = _run_iqt
        else:
            iqt_thread = _poll_iqt
        cothread.Spawn(iqt_thread, poll_interval, stack_size = QT_STACK_SIZE)
        cothread.Yield()
    else:
        # There is, presumably, an exec loop already running elsewhere.
        assert use_timer, 'Cannot use polling without own exec loop'
        global _timer
        _timer = _timer_iqt(poll_interval)

    return _qapp

_qapp = None


# Automatically install the readline hook.  This is the safest thing to do.
_install_readline_hook(True)
