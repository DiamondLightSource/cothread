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
    maxDiff=None
    iocexe = 'softIoc'
    iocload = (
        (os.path.join(here, 'soft_records.db'), 'P=$(TESTPREFIX)'),
    )
    iocpost = "dbl\r"

    def test_non_existant(self):
        self.assertIOCRunning()

        if sys.version_info > (2, 7):
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
        longout = self.testprefix + 'longout'

        values = []

        def callback(value):
            values.append(value)

        m = catools.camonitor(longout, callback, notify_disconnect=True)

        # Wait for connection
        while not values:
            cothread.Sleep(0.1)
        catools.caput(longout, 43, wait=True)
        catools.caput(longout, 44, wait=True)
        self.iocStop()

        # Can't call iocStop twice...
        def iocStop():
            return

        self.iocStop = iocStop
        m.close()

        self.assertEqual(len(values), 4)
        self.assertEqual(values[:3], [42, 43, 44])
        self.assertEqual([v.ok for v in values], [True, True, True, False])

    def test_longout(self):
        # wait for CA server to start
        self.assertIOCRunning()

        longout = self.testprefix+'longout'
        v = catools.caget(longout, timeout=1, format=catools.FORMAT_CTRL)
        self.assertEqual(v.__dict__, dict(
            datatype=catools.DBR_LONG,
            element_count=1,
            lower_alarm_limit=2,
            lower_ctrl_limit=10,
            lower_disp_limit=0,
            lower_warning_limit=5,
            name=longout,
            ok=True,
            severity=0,
            status=0,
            units='',
            upper_alarm_limit=98,
            upper_ctrl_limit=90,
            upper_disp_limit=100,
            upper_warning_limit=96))
        self.assertEqual(v, 42)

    def test_requested_dbr(self):
        # wait for CA server to start
        self.assertIOCRunning()

        longout = self.testprefix+'longout'
        v = catools.caget(longout, timeout=1, datatype=int, format=catools.FORMAT_CTRL)
        self.assertEqual(v.datatype, catools.DBR_LONG)

    def test_si(self):
        self.assertIOCRunning()
        si = self.testprefix+'si'

        v = catools.caget(si)
        self.assertNotEqual(v, 'hello world')

        catools.caput(si, 'hello world')

        v = catools.caget(si)
        self.assertEqual(v, 'hello world')

        catools.caput(si, 'hello € world')

        v = catools.caget(si)
        self.assertEqual(v, 'hello € world')

    def test_info(self):
        self.assertIOCRunning()
        si = self.testprefix+'si'
        longout = self.testprefix + 'longout'
        infos = catools.cainfo([longout, si])
        self.assertEqual([v.ok for v in infos], [True, True])
        self.assertEqual(str(infos[0]), """%s:
    State: connected
    Host: %s
    Access: True, True
    Data type: long
    Count: 1""" % (longout, infos[0].host))
        self.assertEqual(str(infos[1]), """%s:
    State: connected
    Host: %s
    Access: True, True
    Data type: string
    Count: 1""" % (si, infos[1].host))

    def test_pvtree(self):
        from cothread.tools.pvtree import main
        self.assertIOCRunning()
        calc = self.testprefix + 'calc'
        f = tempfile.TemporaryFile(mode="w+t")
        stdout = sys.stdout
        sys.stdout = f
        sys.argv = ["pvtree.py", calc]
        try:
            main()
        finally:
            sys.stdout = stdout
        f.seek(0)


        self.assertEqual(f.read(), """%(testprefix)scalc (calc, '') 42 NO_ALARM NO_ALARM
%(testprefix)scalc.CALC A
%(testprefix)scalc.INPA %(testprefix)slongout CP NMS
  %(testprefix)slongout (longout, 'Soft Channel') 42 NO_ALARM NO_ALARM
""" % self.__dict__)

        f.close()


if __name__ == '__main__':
    counittest.main()
