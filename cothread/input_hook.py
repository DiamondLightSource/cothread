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


def iqt(poll_interval = 0.05, use_timer = True, argv = sys.argv):
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

        except ImportError:
            import qt
            from qt import SIGNAL, QTimer, QApplication
            QCoreApplication = qt.qApp

            @classmethod
            def instance(cls):  return cls.QCoreApplication

            exec_ = QCoreApplication.exec_loop
            unlock = QCoreApplication.unlock

    global _qapp
    assert QT.QCoreApplication.startingUp(), \
        'Must use iqt() to create initial QApplication object.'
    _qapp = QT.QApplication(argv)

    QT.QCoreApplication.connect(
        QT.instance(), QT.SIGNAL('lastWindowClosed()'), cothread.Quit)

    if use_timer:
        iqt_thread = _run_iqt
    else:
        iqt_thread = _poll_iqt
    cothread.Spawn(iqt_thread,  QT, poll_interval, stack_size = QT_STACK_SIZE)
    cothread.Yield()

    return _qapp


# Automatically install the readline hook.  This is the safest thing to do.
_install_readline_hook(True)
