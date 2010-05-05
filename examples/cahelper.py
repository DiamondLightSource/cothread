'''Helper functions for channel access.'''

import cothread
from cothread import catools
import numpy


def maybe_throw(function):
    def throw_wrapper(pv, *args, **kargs):
        if kargs.pop('throw', True):
            return function(pv, *args, **kargs)
        else:
            try:
                return function(pv, *args, **kargs)
            except cothread.Timedout:
                return None

    # Make sure the wrapped function looks like its original self.
    throw_wrapper.__name__ = function.__name__
    throw_wrapper.__doc__ = function.__doc__

    return throw_wrapper


@maybe_throw
def fill_buffer_one(pv, length, datatype=float, timeout=None):
    '''Performs a camonitor on pv to fill a buffer.'''

    count = [0]
    result = numpy.empty(length, dtype = datatype)
    done = cothread.Event()

    def on_update(value):
        result[count[0]] = value
        count[0] += 1
        if count[0] >= length:
            done.Signal()
            subscription.close()

    subscription = catools.camonitor(pv, on_update, datatype = datatype)
    try:
        done.Wait(timeout)
    finally:
        subscription.close()
    return result


def fill_buffer_array(pvs, length, **kargs):
    return cothread.WaitForAll([
        cothread.Spawn(fill_buffer_one, pv, length,
            raise_on_wait = True, **kargs)
        for pv in pvs])


def fill_buffer(pvs, length, **kargs):
    '''fill_buffer(pvs, length,
        datatype = float, timeout = None, throw = True)

    Runs camonitor on one or more pvs and returns an array filled with the
    requested number of updates.  Runs until length updates have occurred on
    all pvs, or until the specified timeout occurs.'''
    if isinstance(pvs, str):
        return fill_buffer_one(pvs, length, **kargs)
    else:
        return fill_buffer_array(pvs, length, **kargs)
