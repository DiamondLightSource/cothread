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


hook_function = CFUNCTYPE(None)

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


        
def _poll_iqt(QT, poll_interval):
    while True:
        try:
            QT.QTimer.singleShot(
                poll_interval * 1e3, QT.QCoreApplication.quit)
            QT.exec_()
            cothread.Yield(poll_interval)
        except KeyboardInterrupt:
            print 'caught keyboard interrupt'


# This is used by the _run_iqt timeout() function to avoid nested returns.
_global_timeout_depth = 0

def _run_iqt(QT, poll_interval):
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

    def at_exit():
        QT.QCoreApplication.quit()
        qt_done.Wait(5) # Give up after five seconds if no response

    # Set up a timer so that Qt polls cothread.  All the timer needs to do
    # is to yield control to the coroutine system.
    timer = QT.QTimer()
    QT.QCoreApplication.connect(timer, QT.SIGNAL('timeout()'), timeout)
    timer.start(poll_interval * 1e3)

    # To ensure we shut down cleanly a little delicacy is required before we
    # dive into the QT exec loop.
    #   First of all, we register an atexit method to tell Qt to quit on
    # program exit.  This enables Qt to do most of its cleaning up, and we
    # handshake with the Qt exit to ensure this completes.
    qt_done = cothread.Event()
    import atexit
    atexit.register(at_exit)

    # Hand control over to Qt -- we'll now get it back through periodic calls
    # to timeout().
    QT.exec_()
    # This is a hack to hopefully eliminate the annoying message on exit:
    #   Mutex destroy failure: Device or resource busy
    QT.unlock()
    qt_done.Signal()

        
def iqt(poll_interval = 0.05, use_timer = False):
    '''Installs Qt event handling hook.  The polling interval is in
    seconds.'''

    # Unfortunately there are some annoying incompatibilities between the Qt3
    # and Qt4 interfaces.  This little class captures the fragments we need
    # from one or the other library in a common interface.
    class QT:
        try:
            from PyQt4.QtCore import QCoreApplication, QTimer, SIGNAL
            from PyQt4.QtGui import QApplication

            instance = QCoreApplication.instance
            exec_ = QCoreApplication.exec_

            @classmethod
            def unlock(cls):    pass

            # Remove the PyQt input hook, which messes us up!
            from PyQt4 import QtCore
            QtCore.pyqtRemoveInputHook()
            _install_readline_hook(True)

            if use_timer:
                print >>sys.stderr, 'Experimental Qt timer enabled'
            
        except ImportError:
            import qt
            from qt import SIGNAL, QTimer, QApplication
            QCoreApplication = qt.qApp

            @classmethod
            def instance(cls):  return cls.QCoreApplication

            exec_ = QCoreApplication.exec_loop
            unlock = QCoreApplication.unlock

    global _qapp
    if QT.QCoreApplication.startingUp():
        _qapp = QT.QApplication(sys.argv)

    QT.QCoreApplication.connect(
        QT.instance(), QT.SIGNAL('lastWindowClosed()'), cothread.Quit)
    
    if use_timer:
        cothread.Spawn(_run_iqt,  QT, poll_interval)
    else:
        cothread.Spawn(_poll_iqt, QT, poll_interval)
    cothread.Yield()


# Automatically install the readline hook.  This is the safest thing to do.
_install_readline_hook(True)
