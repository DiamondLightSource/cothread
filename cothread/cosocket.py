# This file is part of the Diamond cothread library.
#
# Copyright (C) 2011 Michael Abbott, Diamond Light Source Ltd.
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

import coselect
import socket as _socket


__all__ = ['socket', 'socket_hook']


# We need to hang onto this so we can create the real thing when necessary, even
# after socket_hook() has been called.
_socket_socket = _socket.socket


def socket_hook():
    '''Replaces the blocking methods in the socket module with the non-blocking
    methods implemented here.  Not safe to call if other threads need the
    original methods.'''
    _socket.socket = socket


class socket:
    __doc__ = _socket_socket.__doc__

    def __init__(self,
            family=_socket.AF_INET, type=_socket.SOCK_STREAM, proto=0,
            _sock=None):

        if _sock is None:
            _sock = _socket_socket(family, type, proto)
        self.__socket = _sock
        self.__socket.setblocking(0)
        self.__timeout = _socket.getdefaulttimeout()

    def __getattr__(self, name):
        # Delegate all attributes we've not defined to the underlying socket.
        return getattr(self.__socket, name)

    def settimeout(self, timeout):
        self.__timeout = timeout

    def gettimeout(self):
        return self.__timeout

    def setblocking(self, flag):
        if flag:
            self.settimeout(None)
        else:
            self.settimeout(0)


    def connect(self, address):
        # Non blocking connection is a trifle delicate: we fail straightaway
        # with EINPROGRESS, and then need to wait for connection to complete
        # before discovering the true result.
        try:
            self.__socket.connect(address)
        except _socket.error as error:
            if error.errno != errno.EINPROGRESS:
                raise
        self.__poll(coselect.POLLOUT)
        error = self.getsockopt(_socket.SOL_SOCKET, _socket.SO_ERROR)
        if error:
            raise _socket.error(error, os.strerror(error))

    def connect_ex(self, address):
        try:
            self.connect(address)
            return 0
        except _socket.error as error:
            return error.errno


    def __poll(self, event):
        if not coselect.poll_list([(self, event)], self.__timeout):
            raise _socket.error(errno.ETIMEDOUT, 'Timeout waiting for socket')

    def __retry(self, poll, action, args):
        while True:
            try:
                return action(*args)
            except _socket.error as error:
                if error.errno != errno.EAGAIN:
                    raise
            self.__poll(poll)


    def accept(self):
        sock, addr = self.__retry(coselect.POLLIN, self.__socket.accept, ())
        return (socket(_sock = sock), addr)

    def recv(self, *args):
        return self.__retry(coselect.POLLIN, self.__socket.recv, args)

    def recvfrom(self, *args):
        return self.__retry(coselect.POLLIN, self.__socket.recvfrom, args)

    def recvfrom_into(self, *args):
        return self.__retry(coselect.POLLIN, self.__socket.recvfrom_into, args)

    def recv_into(self, *args):
        return self.__retry(coselect.POLLIN, self.__socket.recv_into, args)

    def send(self, *args):
        return self.__retry(coselect.POLLOUT, self.__socket.send, args)

    def sendto(self, *args):
        return self.__retry(coselect.POLLOUT, self.__socket.sendto, args)

    def sendall(self, data, *flags):
        sent = 0
        length = len(data)
        while sent < length:
            sent += self.send(data[sent:], *flags)
