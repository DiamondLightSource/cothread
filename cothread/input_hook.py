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


__all__ = [
    'iqt',              # Enable interactive Qt loop
    'readline_hook',    # Enable readline with interactive Python
]


# Don't really know which of these is right!
hook_function = CFUNCTYPE(c_int, c_int)
#hook_function = PYFUNCTYPE(c_int, c_int)


@hook_function
def _readline_hook(stdin):
    '''Runs the scheduler hook until either input is available on stdin or a
    keyboard interrupt occurs.  Returns True iff an interrupt is caught.'''
    try:
        ready_list = []
        while True:
            # Let the scheduler run.  We tell it which sockets are ready, and
            # it returns with a new list of sockets to watch.  We add our own
            # stdin socket to the set.
            poll_list, timeout = cothread.PollScheduler(ready_list)
            # Oh blast: we have to do some hacking here to add stdin to the
            # poll_list.
            for i in range(len(poll_list)):
                if poll_list[i][0] == stdin:
                    poll_list[i] = (stdin, poll_list[i][1] | coselect.POLLIN)
                    break
            else:
                poll_list.append((stdin, coselect.POLLIN))
                
            # Wait until either stdin or the scheduler are ready.
            ready_list = coselect.poll_block(poll_list, timeout)

            # Check for input on stdin
            for file, events in ready_list:
                if file == stdin and events & coselect.POLLIN:
                    return False
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


def readline_hook():
    '''Install readline hook.  This allows the scheduler to run in parallel
    with interactive python: while readline is waiting for input, the
    scheduler still operates.'''
    
    # The order of these two is rather important: we are effectively patching
    # readline to use our own hook.
    import readline
    import call_readline

    call_readline_lib = cdll.LoadLibrary(
        os.path.abspath(call_readline.__file__))
    global call_readline_InputHookP
    call_readline_InputHookP = pointer(hook_function.in_dll(
        call_readline_lib, 'call_readline_InputHook'))
    
    call_readline_InputHookP[0] = _readline_hook


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
