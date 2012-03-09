# This file is part of the Diamond cothread library.
#
# Copyright (C) 2010-2012 Michael Abbott, Diamond Light Source Ltd.
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

'''Implementation of poll() for Windows.'''

# Note that pywin32 needs to be installed for the win32event import below to
# succeed.  This can be downloaded from
#   http://sourceforge.net/projects/pywin32/
# import win32file
# import win32pipe
from . import _winlib
import msvcrt
import time

from . import coselect


def poll_block_win32(poll_list, timeout = None):
    if poll_list:
        # Convert timeout into Windows wait compatible form.
        if timeout is None:
            timeout = _winlib.INFINITE
        else:
            timeout = int(1000 * timeout)

        # Actually, we have a serious problem here.  We can convert the file
        # identifiers we've been passed into waitable handles ... but I can't
        # see how to wait on the selected events.
        #
        # For the moment, so that at least something happens, we just wait on
        # whatever Windows gives us and pretend that whatever the user was
        # really waiting for is ready.  Not great, but perhaps a start...
        handles = [msvcrt.get_osfhandle(h) for (h, mask) in poll_list]
        ready = _winlib.WaitForMultipleObjects(handles, 0, timeout)
        if 0 <= ready < len(poll_list):
            # Normal case, something is ready, we don't know about the rest but
            # can at least report the first ready item.  Unfortunately we don't
            # know *why* it's ready, but for the moment this is the best I know
            # how to do.
            return poll_list[ready:ready+1]
        elif ready == 0x102:        # WAIT_TIMEOUT
            # Timeout is easy.
            return []
        else:
            # Hm.  Wait abandoned.  Convert into error code.  Not really right,
            # but the best I can do.
            ready -= 0x80           # WAIT_ABANDONED_0
            assert 0 <= ready < len(poll_list)
            return [(poll_list[ready][0], coselect.POLLERR)]
    else:
        # Empty poll list, just a sleep.  Need to handle separately.
        time.sleep(timeout)
        return []

# So let's try and make some record of the issues here.  The code above doesn't
# work properly, but perhaps it's a start.
#
# The specification of poll_block(ll, timeout) is pretty straighforward: ll is a
# list of (handle, mask) pairs where handle is a file handle (common Posix
# interface for devices (including stdin, stdout, stderr), files, pipes and
# sockets and mask is a mask of events we're interested in drawn from the
# following list: POLLIN, POLLPRI, POLLOUT, POLLERR, POLLHUP, POLLNVAL, though
# in truth we'll be satisfied with implementing just the first three (that's all
# that select can do).
#   poll_block() should then block until at least one of the selected conditions
# occurs, at which point it should return a list of (handle, mask) pairs
# reporting which events are ready on which handles.  There are some subtle
# guarantees expected by the code which need to be documented properly...
#
# Alas doing this under Windows seems peculiarly painful.  We can use
# msvcrt.get_osfhandle() to convert file descriptors (as returned by
# file.fileno() and understood by Posix) into file handles understood by
# Windows, and we can wait on these.  Unfortunately controlling *what* we're
# waiting for seems a bit harder, and the other problem is we need to be able to
# interrogate the state of our handles.
#
# If a handle really is a socket then we can use this code:
#   ev = win32event.CreateEvent(None, 0, 0, None)
#   win32file.WSAEventSelect(handle, ev, wsa_mask)
# to ensure that ev is signalled when the selected events become ready.
# Unfortunately:  this only works on sockets;  this call permanently changes the
# state of the socket (so probably needs to be called once globally, probably in
# a cothread socket wrapper, which really needs to be written anyway); the extra
# event is annoying; we *still* don't know how to interrogate the state of the
# handle.
#
# Another trick seen is to use win32pipe.PeekNamedPipe() which tells us if there
# is data in a pipe ... but only for pipes.  More promising perhaps is to use
# ReadFileEx with a zero byte read request and a completion routine (with all
# the lifetime complications that entails) ... but it's not in pywin32.
#
# This is clearly a can of worms.  It's likely enough the whole cothread event
# notification mechanism may need to be revisited to make this work.  In
# particular it seems that Windows requires persistent event source specific
# notification mechanisms to be in place for each event source.  Not an
# unworkable idea, but going to be difficult to rewire.  Clearly I need to look
# at other related implementations such as:
#
#   twisted     http://twistedmatrix.com
#   concurrence http://opensource/hyves.org/concurrence
#   eventlet    http://eventlet.net
#   gevent      http://www.gevent.org
#   libevent    http://monkey.org/~provos/libevent
#   mongrel2    http://mongrel2.org/home
#   libtask     http://swtch.com/libtask/
#               http://code.google.com/p/libtask/
#               http://code.google.com/p/libtask-win32/
#
# Some final links to record here:
#   http://sourceware.org/pthreads-win32    Pthreads for Win32
#   http://www.mingw.org                    GNU for Windows
#
# Also take a look at http://www.kegel.com/poller/ -- this is a common
# abstraction over /dev/poll, kqueue(), /dev/epoll and Linux realtime ready
# signals, which probably provides useful ideas.
