# This file is part of the Diamond cothread library.
#
# Copyright (C) 2007 James Rowland, 2007-2012 Michael Abbott,
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

import sys
import os

from . import cothread
from . import coselect


__all__ = [
    'iqt',              # Enable interactive Qt loop
]


# When Qt is running in its own stack it really needs quite a bit of room.
QT_STACK_SIZE = int(os.environ.get('COTHREAD_QT_STACK', 1024 * 1024))


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

    from ._coroutine import install_readline_hook
    if enable_hook:
        install_readline_hook(_readline_hook)
    else:
        install_readline_hook(None)



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
    from .qt import QtCore
    timer = QtCore.QTimer()
    timer.timeout.connect(timeout)
    timer.start(poll_interval * 1e3)

    return timer


# There are a number of issues with this function... needs to be properly
# idempotent, need to ensure that run_exec doesn't create an app instance?  Or
# some other mechanism for same.
#
# Currently Ian's widget import includes the following code:
#
#   if not hasattr(cothread.input_hook, '_timer'):
#       cothread.iqt(run_exec = False)
#
# This is used to ensure that if widgets are imported directly into designer
# then cothread works.  Note that things are not too complicated in this
# particular case as the Qt application is required to exist already.
def iqt(poll_interval = 0.05, run_exec = True, argv = None):
    '''Installs Qt event handling hook.  The polling interval is in
    seconds.'''

    from .qt import QtCore, QtWidgets
    global _qapp, _timer

    # Importing PyQt4 has an unexpected side effect: it removes the input hook!
    # So we put it back again...
    _install_readline_hook(True)

    # Repeated calls to iqt() are (silent) no-ops.  Is it more friendly do this
    # than to assert fail?  Not sure to be honest.
    if _qapp is not None:
        return _qapp

    # Ensure that there is a QtApplication instance, creating one if necessary.
    _qapp = QtCore.QCoreApplication.instance()
    if _qapp is None:
        if argv is None:
            argv = sys.argv
        _qapp = QtWidgets.QApplication(argv)

    # Arrange to get a Quit event when the last window goes.  This allows the
    # application to simply rest on WaitForQuit().
    _qapp.aboutToQuit.connect(cothread.Quit)

    # Create timer.  Hang onto the timer to prevent it from vanishing.
    _timer = _timer_iqt(poll_interval)

    # Finally, unless we've been told not to, spawn our own exec loop.
    if run_exec:
        cothread.Spawn(_qapp.exec_, stack_size = QT_STACK_SIZE)
        cothread.Yield()

    return _qapp

_qapp = None


# Automatically install the readline hook.  This is the safest thing to do.
_install_readline_hook(True)
