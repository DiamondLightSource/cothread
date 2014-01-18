#!/usr/bin/env python


import cothread
from cothread import cosocket, coserver
cosocket.socket_hook()

import unittest

import socket
import http.server as http
from http.client import HTTPConnection
from urllib.request import urlopen

A, B = socket.socketpair()

assert(isinstance(A, cosocket.socket))
assert(isinstance(B, cosocket.socket))

print(A, B)

print('Test basic I/O')

@cothread.Spawn
def tx():
    for i in  range(10):
        print('>>>', i)
        A.send(chr(i).encode('ascii'))
    A.close()

while True:
    c = B.recv(100)
    print('<<<', repr(c))
    if not c:
        break

B.close()

print('test makefile')

A, B = socket.socketpair()

A, B = A.makefile('wb'), B.makefile('rb')

@cothread.Spawn
def tx2():
    for i in range(10):
        A.writelines([str(i).encode('ascii')])
    A.close()

for L in B.readlines():
    print(L)

B.close()

print('test http')

class handler(http.BaseHTTPRequestHandler):
    def do_GET(self):
        print('Serving reply')
        msg = 'Request handled'
        self.send_response(200)
        self.send_header('Content-Length', str(len(msg)))
        self.end_headers()
        self.wfile.write(msg.encode('ascii'))
        print('Served reply')

#Note: can't use HTTPServer.serve_forever() as this uses a threading.Event
# and the select module
serv = coserver.HTTPServer(('127.0.0.1', 0), handler)
evt = cothread.Event()

def doservone():
    serv.handle_request()
    evt.Signal()

cothread.Spawn(doservone)

print('low-level httplib request')

conn = HTTPConnection('127.0.0.1', serv.server_port)

conn.connect()
assert isinstance(conn.sock, cosocket.socket)
print('socket', conn.sock)
conn.request('GET', '/')

#import pdb; pdb.set_trace()
resp = conn.getresponse()

print('status', resp.status, resp.reason, resp.isclosed())

print('got back', resp.read())

conn.close()

evt.Wait()

print('with urllib2')

cothread.Spawn(doservone)

url='http://127.0.0.1:%d'%serv.server_port

resp = urlopen(url)
print('Response is', resp.read())

resp.close()

evt.Wait()

serv.server_close()

print('Done')
