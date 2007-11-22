'''Cooperative threading utilities.  This package contains the following
modules:

    cothread
        Support for cooperative threading tasks with a full event handling
        system.

    catools
        Channel access support tools for client access to EPICS records.

    iqt
        Support for interactive Qt
'''

def _ImportModule(module_name):
    '''Helper routine to import a sub-module and automatically accumulate
    its export list onto our own export list.'''
    module = __import__(module_name, globals())
    for name in module.__all__:
        globals()[name] = getattr(module, name)
    __all__.extend(module.__all__)

    
__all__ = []
_ImportModule('cothread')
_ImportModule('input_hook')

# The coselect functions aren't exported by default but are available.
from coselect import *
