# -*- coding: utf-8 -*-

import os, os.path, pty, signal
import threading
import tempfile
import time

import unittest

import cothread
from cothread import catools
from cothread.epicsarch import epics_host_arch

_test_db = """
record(ao, "$(P)ao") {
    field(TPRO, "1")
}
"""

class TestCA(unittest.TestCase):

    def setUp(self):
        # random name prefix
        self.P = tempfile.mktemp(dir="")+":"
        self.ioc = SoftIoc(_test_db, "P="+self.P)
        self.ioc.start(1.0)

    def tearDown(self):
        self.ioc.join(1.0)

    def test_getput(self):
        cothread.PrepareThread() # no-op here, but required for test_mt_getput
        V = catools.caget(self.P+'ao')
        self.assertEqual(V, 0)

        catools.caput(self.P+'ao', 42, wait=True)

        V = catools.caget(self.P+'ao')
        self.assertEqual(V, 42)

    def test_monitor(self):
        cothread.PrepareThread()
        E = cothread.Event()
        S = catools.camonitor(self.P+'ao', E.Signal)

        V = E.Wait(2.0)
        self.assertEqual(V, 0)

        catools.caput(self.P+'ao', 42)

        V = E.Wait(2.0)
        self.assertEqual(V, 42)
        S.close()

    def test_mt_getput(self):

        T = threading.Thread(target=self.test_getput)
        T.start()
        T.join(5.0)

    def test_mt_monitor(self):

        T = threading.Thread(target=self.test_monitor)
        T.start()
        T.join(5.0)

class SoftIoc(threading.Thread):
    def __init__(self, db,macros=None):
        super(SoftIoc,self).__init__()
        self.db, self.macros = db, macros
        self._rd, self._wt = os.pipe()
        self._exe = self._find_exe()

    def start(self, timeout=None):
        assert not self.isAlive()
        self._start_event = cothread.ThreadedEventQueue()
        super(SoftIoc,self).start()
        R = self._start_event.Wait(timeout)
        self._start_event = None
        return R

    def join(self, timeout=None):
        os.kill(self._ioc_pid, signal.SIGKILL)
        if self.isAlive():
            super(SoftIoc,self).join(timeout)

    def run(self):
        try:
            self._run()
        except:
            import traceback
            traceback.print_exc()
            print 'exception in IOC worker'

    def _run(self):
        self._start_event.Signal(1)
        T = tempfile.NamedTemporaryFile()
        T.write(self.db)
        T.flush()

        cmd = [self._exe]
        if self.macros:
            cmd.extend(['-m', self.macros])
        cmd.extend(['-d', T.name])

        pid, rawfd = pty.fork()
        if pid==0:
            # child
            os.execv(self._exe, cmd)
            os.abort() # never gets here

        fd = os.fdopen(rawfd, "r+")

        self._ioc_pid = pid

        lines = []
        start, timeout = time.time(), 5
        while time.time()-start < timeout:
            try:
                L = fd.readline()
            except IOError:
                # pipe closed
                break
            #print '>>',L,
            lines.append(L)
            if not L:
                print lines
                raise RuntimeError("IOC stopped early")

        fd.close()

    def _find_exe(self):
        from distutils.spawn import find_executable

        names = ['softIoc', os.path.join('bin',epics_host_arch,'softIoc')]

        path = os.environ.get('PATH','')
        if 'EPICS_BASE' in os.environ:
            path = '%s%s%s'%(path, os.pathsep, os.environ['EPICS_BASE'])

        for N in names:
            exe = find_executable(N, path=path)
            if exe:
                return exe
        raise RuntimeError("Failed to locate softIoc executable")

if __name__=='__main__':
    unittest.main()
