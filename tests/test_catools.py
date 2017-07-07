#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import cothread
from cothread import catools


if __name__ == '__main__':
    import counittest
else:
    from . import counittest

here = os.path.dirname(__file__)


class SoftIocTest(counittest.TestCase):
    iocexe = 'softIoc'
    iocload = (
        (os.path.join(here, 'soft_records.db'), 'P=$(TESTPREFIX)'),
    )
    iocpost = "dbl\r"

    def test_non_existant(self):
        self.assertIOCRunning()

        ne = self.testprefix+'ne'
        with self.assertRaises(catools.ca_nothing) as cm:
            catools.caget(ne, timeout=0.1)

        self.assertEqual(
            repr(cm.exception),
            "ca_nothing('%s', 80)" % ne)
        self.assertEqual(
            str(cm.exception),
            "%s: User specified timeout on IO operation expired" % ne)
        self.assertFalse(bool(cm.exception))
        with self.assertRaises(TypeError):
            for _ in cm.exception:
                pass

    def test_monitor(self):
        self.assertIOCRunning()
        ai = self.testprefix + 'ai'

        values = []

        def callback(value):
            values.append(value)

        m = catools.camonitor(ai, callback, notify_disconnect=True)

        # Wait for connection
        while not values:
            cothread.Sleep(0.1)
        catools.caput(ai, 43, wait=True)
        catools.caput(ai, 44, wait=True)
        self.iocStop()

        # Can't call iocStop twice...
        def iocStop():
            return

        self.iocStop = iocStop
        m.close()

        assert len(values) == 4
        assert values[:3] == [42, 43, 44]
        assert [v.ok for v in values] == [True, True, True, False]

    def test_ai(self):
        # wait for CA server to start
        self.assertIOCRunning()

        ai = self.testprefix+'ai'
        v = catools.caget(ai, timeout=1)

        self.assertEqual(v, 42.0)

    def test_si(self):
        self.assertIOCRunning()
        si = self.testprefix+'si'

        v = catools.caget(si)
        self.assertNotEqual(v, 'hello world')

        catools.caput(si, 'hello world')

        v = catools.caget(si)
        self.assertEqual(v, 'hello world')

    def test_pvtree(self):
        from cothread.tools.pvtree import main
        self.assertIOCRunning()
        calc = self.testprefix + 'calc'
        f = tempfile.TemporaryFile()
        stdout = sys.stdout
        sys.stdout = f
        sys.argv = ["pvtree.py", calc]
        try:
            main()
        finally:
            sys.stdout = stdout
        f.seek(0)
        self.assertMultiLineEqual(f.read(), """%(testprefix)scalc (calc, ) 42 NO_ALARM NO_ALARM
%(testprefix)scalc.CALC A
%(testprefix)scalc.INPA %(testprefix)sai CP NMS
  %(testprefix)sai (ai, 'Soft Channel') 42 INVALID UDF
""" % self.__dict__)


if __name__ == '__main__':
    counittest.main()
