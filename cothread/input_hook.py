'''Simple readline hook to allow the scheduler to run while we're waiting
for input from the interpreter command line.
'''

import cothread
import ctypes
import select
import sys
import os

# The order of these two is rather important: we are effectively patching
# readline to use our own hook.
import readline
import call_readline


__all__ = []


readline_lib = ctypes.cdll.LoadLibrary(os.path.abspath(call_readline.__file__))

# Don't really know which of these is right!
hook_function = ctypes.CFUNCTYPE(None)
#hook_function = ctypes.PYFUNCTYPE(None)


PyOS_InputHook = ctypes.pointer(hook_function.in_dll(
    ctypes.pythonapi, 'PyOS_InputHook'))

PyOS_Readline_Interrupted = ctypes.pointer(ctypes.c_int.in_dll(
    readline_lib, 'PyOS_Readline_Interrupted'))


@hook_function
def my_hook():
    try:
        while True:
            # Let the scheduler run.
            delay = cothread.PollScheduler()
            # Wait until either stdin or the scheduler are ready.
            if select.select([sys.stdin], [], [], delay)[0]:
                break
    except KeyboardInterrupt:
        PyOS_Readline_Interrupted[0] = 1

PyOS_InputHook[0] = my_hook


def iqt(maxtime = 10):
    '''Installs Qt event handling hook.'''

    import qt
    if qt.qApp.startingUp():
        # If the Qt application hasn't been created yet then build it now.
        # We need to hang onto the pointer, otherwise it will go away!
        global _qapp
        _qapp = qt.QApplication(sys.argv)

    cothread.InstallHook(lambda: qt.qApp.processEvents(maxtime))
    