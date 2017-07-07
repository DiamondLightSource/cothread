#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import tempfile
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

    def test_ai(self):
        # wait for CA server to start
        self.assertIOCRunning()

        ai = self.testprefix+'ai'
        V = catools.caget(ai, timeout=1)

        self.assertEqual(V, 42.0)

    def test_si(self):
        self.assertIOCRunning()
        si = self.testprefix+'si'

        V = catools.caget(si)
        self.assertNotEqual(V, 'hello world')

        catools.caput(si, 'hello world')

        V = catools.caget(si)
        self.assertEqual(V, 'hello world')

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
