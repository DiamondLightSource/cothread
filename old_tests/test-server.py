import sys
import socket

import require
import cothread


PORT = 8888

cothread.socket_hook()


def run_service(sock, addr):
    print('run_service', addr)

    sock.send(b'Echo server running\n')
    while True:
        input = sock.recv(1024)
        if input:
            sock.sendall(b'Echo: ' + input)
        else:
            break
    sock.close()
    print('service', addr, 'closed')


def run_until_disconnect(sock, addr):
    try:
        run_service(sock, addr)
    except ConnectionResetError:
        print('Closed by peer')


@cothread.Spawn
def server():
    server = socket.socket()
    server.bind(('localhost', PORT))
    server.listen(5)

    print('Running echo server')
    while True:
        sock, addr = server.accept()
        cothread.Spawn(run_until_disconnect, sock, addr)


# Bring up background activity to show that we're not blocking
@cothread.Spawn
def ticker():
    while True:
        sys.stdout.write('.')
        sys.stdout.flush()
        cothread.Sleep(5)


cothread.WaitForQuit()
