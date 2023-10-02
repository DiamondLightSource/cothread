# -*- coding: utf-8 -*-

from __future__ import print_function

import unittest as _unittest

import re
import sys, os, pty, errno, tempfile

from signal import SIGKILL

import socket as _socket
from cothread import coselect, cosocket
from cothread import Spawn, Sleep, Event, Timedout
from cothread.load_ca import epics_host_arch

__all__ = [
    'IOCTestCaseMixin',
    'TestCase',
    'main',
]

_ioc_dbd = """
dbLoadDatabase("dbd/%(exe)s.dbd")
%(exe)s_registerRecordDeviceDriver(pdbbase)
"""

_ioc_init = "iocInit()"

_ioc_run = """epicsEnvSet("TESTPREFIX","%(prefix)s")
%(phase_env)s
"""+_ioc_dbd+"""
%(phase_load)s
"""+_ioc_init+"""
%(phase_post)s
"""

class copipe(object):
    def __init__(self, fd, timeout=1.0):
        import fcntl
        self._fd, self.__timeout = fd, timeout
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags|os.O_NONBLOCK)
    def __retry(self, event, action, args):
        while True:
            try:
                return action(*args)
            except OSError as error:
                if error.errno != errno.EAGAIN:
                    raise
            if not coselect.poll_list([(self, event)], self.__timeout):
                raise OSError(errno.ETIMEDOUT, 'Timeout waiting for socket')
    def read(self, *args):
        return self.__retry(coselect.POLLIN, os.read, (self._fd,)+args)
    def write(self, *args):
        return self.__retry(coselect.POLLOUT, os.write, (self._fd,)+args)
    def fileno(self):
        return self._fd
    def close(self):
        os.close(self._fd)

class TestTCPServer(object):
    def __init__(self, **kws):
        self.args = kws
        self._listen = False
        self._reset()
        self.socket = cosocket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
        self.socket.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
        if kws.get('listen', False):
            self.listen()

    def _reset(self):
        self.socket = self.port = self.client = self.peer = None

    def listen(self):
        kws, S = self.args, self.socket
        port = kws.get('port',0)
        S.settimeout(kws.get('timeout',5))
        S.bind(('127.0.0.1', port))
        S.listen(kws.get('backlog',2))
        self.server, self.port = S, S.getsockname()
        self._listen = True

    def shutdown(self):
        assert self._listen
        self.close()
        self.socket.close()
        self._reset()
        self._listen = False

    def accept(self):
        assert self._listen
        self.close()
        self.client, self.peer = self.socket.accept()

    def close(self):
        if self.client:
            self.client.close()
        self.client = None

    def recvall(self, N):
        assert self.client
        R = ''
        while len(R)<N:
            M = self.client.recv(N-len(R))
            if not M:
                self.close()
                raise RuntimeError("Client disconect")
            R += M
        return R

    def sendall(self, msg):
        assert self.client
        self.client.sendall(msg)

class IOCTestCaseMixin(object):
    timeout = None
    echo = False

    iocexe = None
    iocenv = None
    iocload = None
    iocpost = None

    iocscript = _ioc_run

    def iocStart(self):
        """Start the IOC child process
        """
        assert getattr(self, '_ttyrecv', None) is None, \
               "IOC already running"
        assert self.iocexe is not None, \
               "Must set iocexe to executable file name"

        # get a random-ish string
        self.testprefix = tempfile.mktemp(dir='')+':'

        self._iocexe = exe = self._find_executable(self.iocexe)

        script = self._build_script()

        pid, ttyfd = pty.fork()
        if pid==0:
            # child
            os.execl(exe, exe)
            os.abort() # never gets here

        elif pid<0:
            raise RuntimeError("fork error %s"%pid)

        # parent
        self._child_pid = pid

        # make the TTY FD non-blocking
        self._tty = copipe(ttyfd, timeout=None)

        self._tty_in = ''
        self._tty_more = Event(auto_reset=True)
        self._ttyrecv = Spawn(self._tty_read)

        for cmd in script.splitlines():
            self.iocCmd(cmd)

    def iocStop(self):
        """Stop the IOC child process
        """
        assert getattr(self, '_ttyrecv', None) is not None, \
               "IOC not running"

        if not self.kill(self._child_pid, 0):
            print('IOC process already stopped')

        else:
            self.iocCmd("exit")

            if not self.waitpid(self._child_pid):
                print('iocStop timeout, killing IOC')
                self.kill(self._child_pid, SIGKILL)

        self._ttyrecv.AbortWait()
        self._tty.close()
        self._ttyrecv = self._tty = None

        self._tty_more, E = None, self._tty_more
        E.SignalException(RuntimeError("IOC stopping"))
        E.AbortWait() # wake all?

    def iocCmd(self, cmd):
        """Enter a command string to the IOC shell
        """
        self._tty.write((cmd.lstrip()+'\r').encode())

    def waitFor(self, lines, regex=False, timeout=None):
        """Wait for the given text to appear on the IOC stdout or stderr
        Returns the text which appears.
        'lines' may be a single entry or a list of entries.
        Each entry may be a string or pre-compiled regular expression.
        The matched text (regex=False) or a match object (regex=True)
        is returned.
        Raises Timeout.
        """
        if timeout is None:
            timeout = self.timeout
        if not isinstance(lines, (list, tuple)):
            lines = [lines]
        for i in range(len(lines)):
            if isinstance(lines[i], str):
                if not regex:
                    lines[i] = re.escape(lines[i])
                lines[i] = re.compile(lines[i], re.MULTILINE)

        while True:
            for line in lines:
                ret = M = line.search(self._tty_in)
                if M is None:
                    continue

                if not regex:
                    ret = self._tty_in[M.start():M.end()]

                # consume everything up to and including the match
                #self._tty_in = self._tty_in[M.end():]
                return ret

            # no matches yet.  Need more input
            self._tty_more.Wait(timeout=self.timeout)

    def assertIOCRunning(self):
        M = self.waitFor('All initialization complete')
        self.assertEqual(M, 'All initialization complete')
        print(M)

    def assertPVEqual(self, pv, value, msg=None, timeout=None):
        """Check the the value of the named PV is exactly equal
        to the given value.
        The PV may not initially be equal, and is allowed to change
        once before a failure is decided.
        """
        from .catools import camonitor
        if timeout is None:
            timeout = self.timeout
        E = Event(auto_reset=False)
        first = [None]
        def newval(val):
            if val==value or first[0] is not None:
                E.Signal(val)
            first[0] = val
        M = camonitor(pv, newval)
        try:
            V = E.Wait(timeout=timeout)
            self.assertEqual(V, value, msg)
        except Timedout:
            raise Timedout("Timeout waiting for %s to become %s (last value %s)"\
                           %(pv, value, first[0]))
        finally:
            M.close()

    # internal methods

    def waitpid(self, pid, timeout=None, consume=False):
        import time
        if timeout is None:
            timeout = self.timeout
        S = time.time()
        while time.time()-S<timeout:
            try:
                cpid, sts = os.waitpid(pid, os.WNOHANG)
                if cpid!=0:
                    return True
            except OSError as e:
                if e.errno==errno.EINTR:
                    pass
                elif consume:
                    return True
                else:
                    raise
            Sleep(0.05)
        return False

    @staticmethod
    def kill(pid, sig):
        try:
            os.kill(pid, sig)
            return True
        except OSError as e:
            if e.errno==errno.ESRCH:
                return False
            raise

    def _tty_read(self):
        # seperate cothread
        try:
            while True:
                T = self._tty.read(1024).decode('UTF-8', 'replace')
                if not T:
                    return
                self._tty_in += T
                if self.echo:
                    sys.stderr.write(T)
                self._tty_more.Signal()
        except OSError as e:
            # Linux gives EIO when read() after child exits
            if e.errno!=errno.EIO:
                raise

    def _find_executable(self, exe):
        import os.path
        from shutil import which

        path = os.path.join('bin', epics_host_arch, exe)

        for N in [exe, path]:
            F = which(N)
            if F:
                return F
        raise ValueError("Can't find executable '%s'"%exe)

    def _build_script(self):
        iocenv = self.iocenv or ''
        if isinstance(iocenv, (list, tuple)):
            X = []
            for name, val in iocenv:
                X.append('epicsEnvSet("%s","%s")\n'%(name,val))
            iocenv = ''.join(X)

        iocload = self.iocload or ''
        if isinstance(iocload, (list, tuple)):
            X = []
            for file, args in iocload:
                X.append('dbLoadRecords("%s","%s")\n'%(file,args))
            iocload = ''.join(X)

        iocpost = self.iocpost or ''
        if isinstance(iocpost, (list, tuple)):
            iocpost = ''.join(map(lambda cmd:cmd+'\n', iocpost))        

        D = {
            'exe':self.iocexe,
            'prefix':self.testprefix,
            'phase_env':iocenv,
            'phase_load':iocload,
            'phase_post':iocpost,
        }
        return self.iocscript%D

class TestCase(_unittest.TestCase, IOCTestCaseMixin):
    timeout = 5
    def setUp(self):
        self.iocStart()
    def tearDown(self):
        self.iocStop()

def main(*args, **kws):
    if 'EPICS_CA_ADDR_LIST' not in os.environ:
        os.environ['EPICS_CA_ADDR_LIST'] = 'localhost'
    if 'EPICS_CA_AUTO_ADDR_LIST' not in os.environ:
        os.environ['EPICS_CA_AUTO_ADDR_LIST'] = 'NO'
    _unittest.main(*args, **kws)
