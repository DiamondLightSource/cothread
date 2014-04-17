# This file is part of the Diamond cothread library.
#
# Copyright (C) 2014 Michael Davidsaver, Brookhaven National Laboratory
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

"""
cothread friendly versions of the socket servers
from the SocketServer and BaseHTTPServer modules
"""

import SocketServer, BaseHTTPServer, SimpleHTTPServer

import cothread
import cosocket
import coselect

__all__ = [
    'BaseServer',
    'TCPServer',
    'UDPServer',
    'HTTPServer',
    'CoThreadingMixIn',
    'CoThreadingTCPServer',
    'CoThreadingUDPServer',
    'CoThreadingHTTPServer',
]


# We must patch out use of the socket, threading, and select modules
def _patch(cls):
    def wrap(fun):
        fun.__doc__ = getattr(cls, fun.__name__).__doc__
        return fun

    class WrappedServer(cls):
        __doc__ = cls.__doc__

        @wrap
        def __init__(self, *args, **kws):
            if hasattr(cls, 'address_family'): # All except BaseServer
                baact = kws.get('bind_and_activate', True)
                kws['bind_and_activate'] = False

            cls.__init__(self, *args, **kws)

            self.__shut = cosocket.socketpair()

            if hasattr(cls, 'address_family'):
                self.socket = cosocket.socket(None, None, None, self.socket)
                if baact:
                    self.server_bind()
                    self.server_activate()

        @wrap
        def serve_forever(self, poll_interval=0.5):
            while True:
                A, B = self.fileno(), self.__shut[1].fileno()
                for S, E in coselect.poll_list(
                        [(A, coselect.POLLIN), (B, coselect.POLLIN)]):
                    if S == B:
                        self.__shut[1].read(100)
                        return
                    elif S == A:
                        self._handle_request_noblock()

        @wrap
        def shutdown(self):
            self.__shut[0].send('\0')

        @wrap
        def handle_request(self):
            L = coselect.poll_list(
                [(self, coselect.POLLIN)],
                self.timeout or self.socket.gettimeout())
            if not L:
                self.handle_timeout()
            else:
                self._handle_request_noblock()

    return WrappedServer


BaseServer = _patch(SocketServer.BaseServer)
TCPServer  = _patch(SocketServer.TCPServer)
UDPServer  = _patch(SocketServer.UDPServer)
HTTPServer = _patch(BaseHTTPServer.HTTPServer)


class CoThreadingMixIn(SocketServer.ThreadingMixIn):
    def process_request(self, request, client_address):
        cothread.Spawn(self.process_request_thread, request, client_address)

class CoThreadingUDPServer(CoThreadingMixIn, UDPServer): pass
class CoThreadingTCPServer(CoThreadingMixIn, TCPServer): pass
class CoThreadingHTTPServer(CoThreadingMixIn, HTTPServer): pass

def test(HandlerClass = SimpleHTTPServer.SimpleHTTPRequestHandler,
         ServerClass = CoThreadingHTTPServer):
    BaseHTTPServer.test(HandlerClass, ServerClass)


if __name__ == '__main__':
    test()
