'''Simple readline hook to allow the scheduler to run while we're waiting
for input from the interpreter command line.  Also includes optional support
for the Qt event loop.'''

import cothread
import ctypes
import select
import sys
import os
import traceback

from ctypes import *

# The order of these two is rather important: we are effectively patching
# readline to use our own hook.
import readline
import call_readline


__all__ = ['iqt']


call_readline_lib = cdll.LoadLibrary(os.path.abspath(call_readline.__file__))

# Don't really know which of these is right!
hook_function = CFUNCTYPE(c_int, c_int)
#hook_function = PYFUNCTYPE(c_int, c_int)

call_readline_InputHookP = pointer(hook_function.in_dll(
    call_readline_lib, 'call_readline_InputHook'))


@hook_function
def readline_hook(stdin):
    try:
        iwtd, owtd, ewtd = [], [], []
        while True:
            # Let the scheduler run.  We tell it which sockets are ready, and
            # it returns with a new list of sockets to watch.  We add our own
            # stdin socket to the set.
            iwtd, owtd, ewtd, timeout = \
                cothread.PollScheduler(iwtd, owtd, ewtd)
            iwtd.append(stdin)
            # Wait until either stdin or the scheduler are ready.
            iwtd, owtd, ewtd = select.select(iwtd, owtd, ewtd, timeout)
            if stdin in iwtd:
                break
    except KeyboardInterrupt:
        return True
    except:
        # If any other kind of exception gets here then we have a real
        # problem.  The return value will be undefined, and the scheduler
        # will be broken.  Best to record that we're now dead, create the
        # traceback, and disable the hook.
        print 'Exception raised by scheduler: scheduler abandoned'
        traceback.print_exc()

        # Now disable any further hooking by resetting the hook.  We have to
        # set it to zero, so this requires a certain amount of fakery so the
        # type system will play properly.
        cast(call_readline_InputHookP, POINTER(c_int))[0] = 0
        return False
    else:
        return False

call_readline_InputHookP[0] = readline_hook


def poll_iqt(poll_interval):
    import qt
    if qt.qApp.startingUp():
        # If the Qt application hasn't been created yet then build it now.
        # We need to hang onto the pointer, otherwise it will go away!
        global _qapp
        _qapp = qt.QApplication(sys.argv)

    while True:
        qt.qApp.processEvents(poll_interval)
        cothread.Sleep(poll_interval / 1000.)
        

def iqt(poll_interval = 10):
    '''Installs Qt event handling hook.  The polling interval is in
    milliseconds.'''

    cothread.Spawn(poll_iqt, poll_interval)
