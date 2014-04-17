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
    class WrappedServer(cls):
        __doc__ = cls.__doc__

        def __init__(self, *args, **kws):
            if hasattr(cls, 'address_family'): # All except BaseServer
                baact = kws.get('bind_and_activate', True)
                kws['bind_and_activate'] = False

            cls.__init__(self, *args, **kws)

            self.__shut = cosocket.socketpair()

            if hasattr(cls, 'address_family'):
                self.socket = cosocket.socket(None,None,None,self.socket)
                if baact:
                    self.server_bind()
                    self.server_activate()
        __init__.__doc__ = cls.__init__.__doc__

        def serve_forever(self, poll_interval=0.5):
            while True:
                print 'waiting for',self,self.__shut[1]
                A, B = self.fileno(), self.__shut[1].fileno()
                for S,E in coselect.poll_list([(A,coselect.POLLIN),(B,coselect.POLLIN)]):
                    print 'have',S,E
                    if S == B:
                        print 'stopping'
                        self.__shut[1].read(100)
                        return
                    elif S == A:
                        print 'handling'
                        self._handle_request_noblock()
        serve_forever.__doc__ = cls.serve_forever.__doc__

        def shutdown(self):
            self.__shut[0].send('\0')
        shutdown.__doc__ = cls.shutdown.__doc__

        def handle_request(self):
            L = coselect.poll_list([(self,coselect.POLLIN)], self.timeout or self.socket.gettimeout())
            if not L:
                self.handle_timeout()
            else:
                self._handle_request_noblock()
        handle_request.__doc__ = cls.handle_request.__doc__
    return WrappedServer

BaseServer = _patch(SocketServer.BaseServer)
TCPServer = _patch(SocketServer.TCPServer)
UDPServer = _patch(SocketServer.UDPServer)
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
