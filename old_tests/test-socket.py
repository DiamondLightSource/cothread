import require
import cothread
import socket
import sys

if sys.version_info >= (3,):
    raw_input = input

# import examples.qt_monitor

cothread.socket_hook()

SERVER = 'localhost'
PORT = 8888

s = socket.create_connection((SERVER, PORT))
print('sending', s.send(b'bogus\n'))
print('recving', repr(s.recv(1024)))

while True:
    input = raw_input('> ')
    s.sendall(input.encode())
    print(s.recv(1024))
