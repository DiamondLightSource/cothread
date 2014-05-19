#!/usr/bin/env python


import cothread
from cothread import cosocket, coserver
cosocket.socket_hook()

import unittest

import os
import socket
import http.server as http
from http.client import HTTPConnection
from urllib.request import urlopen

os.environ.pop('http_proxy', None)
os.environ.pop('HTTP_PROXY', None)

# Set some timeout on all operations to prevent the tests from hanging
# This must be larger than all timeouts below
# except the test of default timeout in TestSocket.test_timeout
socket.setdefaulttimeout(1.5)

class TestSocket(unittest.TestCase):
    def test_socket(self):
        "Check that socket_hook works for socket() creation"
        A = socket.socket()
        self.assertTrue(isinstance(A, cosocket.socket))
        A.close()

    def test_pair(self):
        "Check that socket_hook works for socketpair()"
        A, B = socket.socketpair()

        self.assertTrue(isinstance(A, cosocket.socket))
        self.assertTrue(isinstance(B, cosocket.socket))

        A.close()
        B.close()

    def test_timeout(self):
        A, B = socket.socketpair()

        # specific user timeout
        A.settimeout(0.1)

        # some games so that the test won't hang if recv() never times out
        def op(sock):
            try:
                sock.recv(10)
                assert False, "Missed expected Timeout"
            except socket.error:
                return sock

        opA = cothread.Spawn(op, A, raise_on_wait=True)

        try:
            V = opA.Wait(1.0)
        except:
            opA.AbortWait()
            raise
        self.assertTrue(V is A)

        opB = cothread.Spawn(op, B, raise_on_wait=True)

        try:
            V = opB.Wait(2.0)
        except:
            opB.AbortWait()
            raise
        self.assertTrue(V is B)


        A.close()
        B.close()

    def test_txrx(self):
        "Check that we can actually send/recv bewtween cothreads"
        A, B = socket.socketpair()

        def tx():
            for i in  range(10):
                A.send(chr(i).encode('ascii'))
            A.close()
        tx = cothread.Spawn(tx, raise_on_wait=True)

        data = b''
        while True:
            c = B.recv(100)
            if not c:
                break
            data += c

        B.close()

        tx.Wait(1.0)

        self.assertEqual(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09',
                         data)

    def test_server_txrx(self):
        A = socket.socket()
        A.bind(('localhost',0))
        A.listen(1)

        B = socket.socket()
        B.bind(('localhost',0))

        Sname = A.getsockname()
        Cname = B.getsockname()

        def server():
            C, peer = A.accept()
            self.assertEqual(peer, Cname)
            C.send(b'hello')
            C.close()

        server = cothread.Spawn(server, raise_on_wait=True)

        try:
            B.connect(Sname)
            msg = B.recv(100)
            B.close()
        except socket.error:
            # ensure we capture server exceptions...
            server.Wait(1.0)
            raise # only get here if no server exception
        else:
            server.Wait(1.0)

        A.close()

        self.assertEqual(msg, b'hello')

    def test_pair_makefile(self):
        """Test makefile() with socketpair()
        which behaves the same as plain socket() in python 3.X

        Underlying socket is a reference count.  So the socket in actually
        closed when the last reference is released.
        """

        sA, sB = socket.socketpair()

        A, B = sA.makefile('w'), sB.makefile('r')
        sA.close()
        sB.close()
        self.assertNotEqual(A.name, -1)
        self.assertNotEqual(B.name, -1)

        def tx2():
            for i in range(10):
                print(i, file=A)
            A.close() # flush and close

        tx2 = cothread.Spawn(tx2, raise_on_wait=True)

        Ls = B.readlines()
        B.close()

        tx2.Wait(1.0)

        self.assertEqual(Ls, ['0\n','1\n','2\n','3\n','4\n','5\n','6\n','7\n',
                              '8\n','9\n'])

    def test_server_makefile(self):
        """Test makefile() with socket()
        which behaves the same as plain socketpair() in python 3.X
        """
        A = socket.socket()
        A.bind(('localhost',0))
        A.listen(1)

        B = socket.socket()
        B.bind(('localhost',0))

        Sname = A.getsockname()
        Cname = B.getsockname()

        def server():
            C, peer = A.accept()
            self.assertEqual(peer, Cname)
            F = C.makefile(mode='w')
            C.close()
            F.write('hello')
            F.close()

        server = cothread.Spawn(server, raise_on_wait=True)

        try:
            B.connect(Sname)
            fB = B.makefile(mode='r')
            B.close()
            msg = fB.readline()
            fB.close()
        except socket.error:
            # ensure we capture server exceptions...
            server.Wait(1.0)
            raise # only get here if no server exception
        else:
            server.Wait(1.0)

        A.close()

        self.assertEqual(msg, 'hello')

class handler(http.BaseHTTPRequestHandler):
    def do_GET(self):
        msg = b'Request handled'
        self.send_response(200)
        self.send_header('Content-Length', str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)
        self.server.N += 1


class TestHTTPServer(unittest.TestCase):
    def setUp(self):
        self.serv = coserver.HTTPServer(('127.0.0.1', 0), handler)
        self.assertTrue(isinstance(self.serv.socket, cosocket.socket))

    def tearDown(self):
        self.serv.server_close()

    def test_immediate_shutdown(self):
        self.serv.shutdown()

        task = cothread.Spawn(self.serv.serve_forever, raise_on_wait=True)

        task.Wait(1.0)

    def test_run_shutdown(self):
        task = cothread.Spawn(self.serv.serve_forever, raise_on_wait=True)

        # Ensure we don't fall through immediately
        self.assertRaises(cothread.Timedout, task.Wait, 0.1)

        self.serv.shutdown()

        task.Wait(1.0)

class TestHTTPClient(unittest.TestCase):
    def setUp(self):
        self.serv = coserver.HTTPServer(('127.0.0.1', 0), handler)
        self.serv.N = 0
        self.task = cothread.Spawn(self.serv.serve_forever, raise_on_wait=True)

    def tearDown(self):
        self.serv.shutdown()
        self.task.Wait(1.0)
        self.serv.server_close()

    def test_httplib(self):
        conn = HTTPConnection('127.0.0.1', self.serv.server_port)

        conn.connect()
        self.assertTrue(isinstance(conn.sock, cosocket.socket))

        conn.request('GET', '/')

        resp = conn.getresponse()

        self.assertEqual(resp.status, 200)
        self.assertFalse(resp.isclosed())
        raw = resp.read()

        conn.close()

        self.assertEqual(raw, b'Request handled')

        self.assertEqual(self.serv.N, 1)

    def test_urllib2(self):

        url='http://127.0.0.1:%d'%self.serv.server_port

        resp = urlopen(url)
        self.assertEqual(resp.getcode(), 200)
        raw = resp.read()
        resp.close()

        self.assertEqual(raw, b'Request handled')

        self.assertEqual(self.serv.N, 1)

if __name__=="__main__":
    unittest.main()
