import socket

import require
import cothread

# Bring up background activity to show that we're not blocking
import examples.qt_monitor

PORT = 8888

cothread.socket_hook()


def run_service(sock, addr):
    print('run_service', addr)

    sock.send('Echo server running\n')
    while True:
        input = sock.recv(1024)
        if input:
            sock.sendall('Echo: ' + input)
        else:
            break
    sock.close()
    print('service', addr, 'closed')


@cothread.Spawn
def server():
    server = socket.socket()
    server.bind(('localhost', PORT))
    server.listen(5)

    print('Running echo server')
    while True:
        sock, addr = server.accept()
        cothread.Spawn(run_service, sock, addr)


cothread.WaitForQuit()
