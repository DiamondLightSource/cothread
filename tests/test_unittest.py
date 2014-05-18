#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cothread import counittest, catools

class SoftIocTest(counittest.TestCase):
    iocexe = 'softIoc'
    iocload = (
        ('tests/test_unittest.db', 'P=$(TESTPREFIX)'),
    )
    iocpost = "dbl\r"

    def test_nothing(self):
        self.assertTrue(True)

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
