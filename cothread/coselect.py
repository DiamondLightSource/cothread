# This file is part of the Diamond cothread library.
#
# Copyright (C) 2007-2012 Michael Abbott, Diamond Light Source Ltd.
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

'''Support for cooperative select functions.  Replaces the functionality of
the standard select module.'''

from __future__ import absolute_import

import select as _select
import cothread


__all__ = [
    'select',           # Non-blocking select function
    'poll',             # Non-blocking emulation of poll object
    'poll_list',        # Simpler interface to non-blocking polling
    'poll_block',       # Simpler interface to blocking polling

    'SelectError',      # Exception raised by select()

    # Poll constants
    'POLLIN',           # Data ready to read
    'POLLPRI',          # Urgent data ready to read
    'POLLOUT',          # Ready for writing
    'POLLERR',          # Error condition
    'POLLHUP',          # Hangup: socket has disconnected
    'POLLNVAL',         # Invalid request, not open.

    'POLLEXTRA',        # If any of these are set there is a socket problem

    'select_hook',      # Replaces select methods
]


def select_hook():
    '''Replaces the blocking methods in the select module with the non-blocking
    methods implemented here.  Not safe to call if other threads need the
    original methods.'''
    _select.select = select
    _select.poll = poll


# A helpful routine to ensure that our select() behaves as much as possible
# like the real thing!
def _AsFileDescriptor(file):
    if isinstance(file, int):
        return file
    else:
        return file.fileno()

# We need these names from _select, but unfortunately it has a bad habit of not
# always providing them, particularly if poll() is broken.  So we define
# defaults to use internally if they can't be read.
_poll_values = [
    ('POLLIN',   1),    ('POLLPRI',  2),    ('POLLOUT',  4),
    ('POLLERR',  8),    ('POLLHUP',  16),   ('POLLNVAL', 32)]
for _name, _default in _poll_values:
    globals()[_name] = getattr(_select, _name, _default)

# These three flags are always treated as of interest and are never consumed.
POLLEXTRA = POLLERR | POLLHUP | POLLNVAL

# The following extra symbols define poll names that aren't present on all
# platforms, so we only export them if they exist.
_poll_extra = [
    'POLLRDNORM', 'POLLRDBAND', 'POLLWRNORM', 'POLLWRBAND', 'POLLMSG']
for _name in _poll_extra:
    if hasattr(_select, _name):
        globals()[_name] = getattr(_select, _name)
        __all__.append(_name)


def poll_block_poll(poll_list, timeout = None):
    '''A simple wrapper for the poll method to provide actually directly
    useful functionality.  This will block non-cooperatively, so should only
    be used in a scheduler loop.
        Note that the timeout is in seconds.'''
    p = _select_poll()
    for file, events in poll_list:
        p.register(file, events)
    if timeout is not None:
        # Convert timeout into ms for calling poll() method.
        timeout *= 1000
    try:
        return p.poll(timeout)
    except _select.error:
        # Convert a select error into an empty list of events.  This will
        # occur if a signal is caught, for example if we're suspended and
        # then resumed!
        return []


def poll_block_select(poll_list, timeout = None):
    '''This reimplements the functionality of poll_block but using select
    instead.  This is intended to be used
        1. where poll is not available
        2. on OSX where poll is broken, does not work on all file descriptors,
           in particular not on stdin.
    '''
    flag_mapping = (POLLIN, POLLOUT, POLLPRI)

    # Generate list of arguments for select from poll arguments.
    selects = ([], [], [])
    for file, events in poll_list:
        for wtd, event in zip(selects, flag_mapping):
            if events & event:
                wtd.append(file)

    result = {}
    try:
        selected = _select_select(*selects + (timeout,))
    except _select.error:
        # Oh dear.  *Something* is wrong, but I don't know which file handle
        # is broken.  This is not good: going to have to probe each file in
        # turn to find out.
        for file, events in poll_list:
            selects = ([], [], [])
            for wtd, event in zip(selects, flag_mapping):
                if events & event:
                    wtd.append(file)
            try:
                selected = _select_select(*selects + (0,))
            except _select.error:
                # Still don't really know what's wrong, but it's a safe bet
                # the problem is the file handle.
                result[file] = POLLNVAL
            else:
                for wtd, event in zip(selected, flag_mapping):
                    if file in wtd:
                        result[file] = result.get(file, 0) | event
    else:
        # Map select result into poll list result.
        for file, events in poll_list:
            for wtd, event in zip(selected, flag_mapping):
                if file in wtd:
                    result[file] = result.get(file, 0) | event

    return result.items()


_select_select = _select.select     # Keep a copy of original select for hooking
import platform as _platform
if hasattr(_select, 'poll'):
    _select_poll = _select.poll     # Similarly get copy of original poll
    if _platform.system() == 'Darwin':
        # Unfortunately it would appear that Apple's implementation of the
        # poll() system call is incomplete: it returns POLLNVAL for devices!
        # Apparently kqueue and poll fail on anything in /dev (I suppose they
        # work on ordinary files and sockets?)
        #   So if this is your platform, sorry, we have to use select.
        poll_block = poll_block_select
    else:
        # This is the preferred case.
        poll_block = poll_block_poll
else:
    if _platform.system() == 'Windows':
        # Oops.  Has to be the Windows way, how horrid.
        from poll_win32 import poll_block_win32 as poll_block
    else:
        # If poll not available use select instead.  Guess this is going to be
        # an ancient Unix with select but no poll, or Darwin on a newer Python
        # version where the broken poll is excluded.
        poll_block = poll_block_select


def _compute_poll_list(poll_queue):
    '''Computes a list of (file, event_mask) pairs of all descriptor events
    of interest, according to the given poll_queue, which is itself a
    dictionary mapping descriptors to lists of pollers.
        Returns the list together with a new dictionary with all inactive, ie
    woken, pollers removed.'''
    poll_list = []
    new_poll_queue = {}
    for file, pollers in poll_queue.items():
        active = [poller
            for poller in pollers
            if not poller.wakeup.woken()]
        if active:
            event_mask = 0
            for poller in active:
                event_mask |= poller.events[file]
            poll_list.append((file, event_mask))
            new_poll_queue[file] = active
    return poll_list, new_poll_queue


class _Poller(object):
    '''Wrapper for handling poll wakeup.'''

    def __init__(self, event_list):
        # .events is a dictionary mapping each descriptor we're interested in
        # to the bit mask of interesting events.
        self.events = {}
        self.__ready_list = {}
        for file, events in event_list:
            file = _AsFileDescriptor(file)
            self.events[file] = self.events.get(file, 0) | events

    def notify_wakeup(self, file, events):
        '''This is called from the scheduler as each file becomes ready.  We
        add the file to our list of ready descriptors and wake ourself up.
        We return a mask of the events that we've consumed.'''
        # Mask out only the events we're really interested in.
        events &= self.events[file] | POLLEXTRA
        if events:
            # We're interested!  Record the event flag and wake our task.
            self.__ready_list[file] = self.__ready_list.get(file, 0) | events
            self.wakeup.wakeup(cothread.cothread._WAKEUP_NORMAL)
        # Return the events we've actually consumed here.  The extra events
        # don't count, as everybody gets those.
        return events & ~POLLEXTRA

    def event_list(self):
        return self.events.items()

    def ready_list(self):
        return self.__ready_list.items()


def poll_list(event_list, timeout = None):
    '''event_list is a list of pairs, each consisting of a waitable
    descriptor and an event mask (generated by oring together POLL...
    constants).  This routine will cooperatively block until any descriptor
    signals a selected event (or any event from HUP, ERR, NVAL) or until
    the timeout (in seconds) occurs.'''
    cothread.cothread._validate_thread()
    poller = _Poller(event_list)
    cothread.cothread._scheduler.poll_until(
        poller, cothread.cothread.GetDeadline(timeout))
    return poller.ready_list()


class poll(object):
    '''Emulates select.poll(), but implements a cooperative non-blocking
    version for use with the cothread library.'''

    def __init__(self):
        self.__watch_list = {}

    def register(self, file, events = POLLIN | POLLPRI | POLLOUT):
        '''Adds file to the list of objects to be polled.  The default set
        of events is POLLIN|POLLPRI|POLLOUT.'''
        file = _AsFileDescriptor(file)
        self.__watch_list[file] = events

    def unregister(self, file):
        '''Removes file from the polling list.'''
        file = _AsFileDescriptor(file)
        del self.__watch_list[file]

    def poll(self, timeout = None):
        '''Blocks until any of the registered file events become ready.

        Beware: the timeout here is in milliseconds.  This is consistent
        with the select.poll().poll() function which this is emulating,
        but inconsistent with all the other cothread routines!

        Consider using poll_list() instead for polling.'''
        return poll_list(self.__watch_list.items(), timeout / 1000.)


class SelectError(Exception):
    def __init__(self, flags):
        self.flags = flags
    def __str__(self):
        reasons = [
            (POLLERR,  'Error on file descriptor'),
            (POLLHUP,  'File descriptor disconnected'),
            (POLLNVAL, 'Invalid descriptor')]
        return 'Select error: ' + \
            ', '.join([reason
                for flag, reason in reasons
                if self.flags & flag])


def select(iwtd, owtd, ewtd, timeout = None):
    '''Non blocking select() function.  The interface should be as for the
    standard library select.select() function (though it raises different
    exceptions).'''

    inputs = (iwtd, owtd, ewtd)
    flag_mapping = (POLLIN, POLLOUT, POLLPRI)

    # First convert the descriptors into a format suitable for poll.
    interest = [(file, flag)
        for files, flag in zip(inputs, flag_mapping)
        for file in files]

    # Now wait until at least one of our interests occurs.
    poll_result = dict(poll_list(interest, timeout))

    # Now convert the results back.
    results = ([], [], [])
    for result, input, flag in zip(results, inputs, flag_mapping):
        for object in input:
            file = _AsFileDescriptor(object)
            events = poll_result.get(file, 0)
            if events & POLLEXTRA:
                # If any of the extra events come up, raise an exception.
                # This corresponds to errors raised by the os select().
                raise SelectError(events)
            elif events & flag:
                result.append(object)
    return results
