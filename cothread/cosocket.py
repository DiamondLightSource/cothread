# This file is part of the Diamond cothread library.
#
# Copyright (C) 2011-2012 Michael Abbott, Diamond Light Source Ltd.
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

'''Support for cooperative sockets.  Replaces the functionality of the
standard socket module.'''

import os
import errno

from . import coselect
import socket as _socket

__all__ = ['socket', 'socket_hook', 'socketpair', 'create_connection']


# We need to hang onto this so we can create the real thing when necessary, even
# after socket_hook() has been called.
_socket_socket = _socket.socket
_socket_pair = _socket.socketpair


def socket_hook():
    '''Replaces the blocking methods in the socket module with the non-blocking
    methods implemented here.  Not safe to call if other threads need the
    original methods.'''
    _socket.socket = socket
    _socket.socketpair = socketpair

def socketpair(*args):
    A, B = _socket_pair(*args)
    A = socket(A.family, A.type, A.proto, A.detach())
    B = socket(B.family, B.type, B.proto, B.detach())
    return A, B

def create_connection(*args, **kargs):
    sock = _socket.create_connection(*args, **kargs)
    return socket(_sock = sock)
create_connection.__doc__ = _socket.create_connection.__doc__

class socket(_socket_socket):
    __doc__ = _socket_socket.__doc__

    def wrap(fun):
        fun.__doc__ = getattr(_socket_socket, fun.__name__).__doc__
        return fun

    def __init__(self,
            family=_socket.AF_INET, type=_socket.SOCK_STREAM, proto=0,
            fileno=None):
        _socket_socket.__init__(self, family, type, proto, fileno)
        _socket_socket.setblocking(self, 0)
        self.__timeout = _socket.getdefaulttimeout()

    @wrap
    def settimeout(self, timeout):
        self.__timeout = timeout

    @wrap
    def gettimeout(self):
        return self.__timeout

    @wrap
    def setblocking(self, flag):
        if flag:
            self.settimeout(None)
        else:
            self.settimeout(0)

    @wrap
    def connect(self, address):
        # Non blocking connection is a trifle delicate: we fail straightaway
        # with EINPROGRESS, and then need to wait for connection to complete
        # before discovering the true result.
        try:
            _socket_socket.connect(self, address)
        except _socket.error as error:
            if error.errno != errno.EINPROGRESS:
                raise
        self.__poll(coselect.POLLOUT)
        error = self.getsockopt(_socket.SOL_SOCKET, _socket.SO_ERROR)
        if error:
            raise _socket.error(error, os.strerror(error))

    @wrap
    def connect_ex(self, address):
        try:
            self.connect(address)
            return 0
        except _socket.error as error:
            return error.errno


    def __poll(self, event):
        if not coselect.poll_list([(self, event)], self.__timeout):
            raise _socket.error(errno.ETIMEDOUT, 'Timeout waiting for socket')

    def __retry(self, event, action, args):
        while True:
            try:
                return action(self, *args)
            except _socket.error as error:
                if error.errno != errno.EAGAIN:
                    raise
            self.__poll(event)


    @wrap
    def accept(self):
        sock, addr = self.__retry(coselect.POLLIN, _socket_socket.accept, ())
        return (socket(sock.family, sock.type, sock.proto, sock.detach()), addr)

    @wrap
    def recv(self, *args):
        return self.__retry(coselect.POLLIN, _socket_socket.recv, args)

    @wrap
    def recvfrom(self, *args):
        return self.__retry(coselect.POLLIN, _socket_socket.recvfrom, args)

    @wrap
    def recvfrom_into(self, *args):
        return self.__retry(coselect.POLLIN, _socket_socket.recvfrom_into, args)

    @wrap
    def recv_into(self, *args):
        return self.__retry(coselect.POLLIN, _socket_socket.recv_into, args)

    @wrap
    def send(self, *args):
        return self.__retry(coselect.POLLOUT, _socket_socket.send, args)

    @wrap
    def sendto(self, *args):
        return self.__retry(coselect.POLLOUT, _socket_socket.sendto, args)

    @wrap
    def sendall(self, data, *flags):
        sent = 0
        length = len(data)
        while sent < length:
            sent += self.send(data[sent:], *flags)

    del wrap
