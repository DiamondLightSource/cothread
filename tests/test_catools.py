#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from cothread import counittest, catools

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

if __name__=='__main__':
    counittest.main()
