import os

import numpy

from cothread import Sleep
from cothread.pv import PV, PV_array

if __name__ == '__main__':
    import counittest
else:
    from . import counittest

here = os.path.dirname(__file__)

TIMEOUT = 5

class PVTest(counittest.TestCase):
    """Test class for pv.py"""
    maxDiff=None
    iocexe = 'softIoc'
    iocload = (
        (os.path.join(here, 'soft_records.db'), 'P=$(TESTPREFIX)'),
    )
    iocpost = "dbl\r"

    def test_pv_get(self):
        self.assertIOCRunning()
        pv = PV(self.testprefix + 'rec1')
        Sleep(0.2)
        pv.sync(TIMEOUT)

        self.assertEqual(pv.get(), 123)

    def test_pv_ticking(self):
        self.assertIOCRunning()
        pv = PV(self.testprefix + 'inc1')
        Sleep(0.2)
        pv.sync(TIMEOUT)

        first = pv.get()
        Sleep(0.2)
        second = pv.get()

        assert second > first

    def test_pv_caput(self):
        self.assertIOCRunning()
        pv = PV(self.testprefix + 'rec1')
        Sleep(0.2)
        pv.sync(TIMEOUT)

        pv.caput(111)
        pv.reset()

        pv.get_next(TIMEOUT)

        self.assertEqual(pv.get(), 111)

    def test_pv_on_update(self):
        self.assertIOCRunning()

        update_val = None
        def my_update(val):
            nonlocal update_val
            update_val = val.get()

        pv = PV(self.testprefix + 'rec1', on_update=my_update)
        Sleep(0.2)
        pv.sync(TIMEOUT)
        pv.caput(111)

        # Give background caput/ioc processing chance to update
        Sleep(0.1)

        self.assertEqual(update_val, 111)

    def test_pv_array_get(self):
        self.assertIOCRunning()

        pvs = [self.testprefix + 'rec1', self.testprefix + 'rec2']

        pva = PV_array(pvs)
        Sleep(0.2)
        pva.sync()

        assert numpy.array_equal(pva.get(), [123, 456])

    def test_pv_array_properties(self):
        self.assertIOCRunning()

        pvs = [self.testprefix + 'rec1', self.testprefix + 'rec2']

        pva = PV_array(pvs)
        Sleep(0.2)
        pva.sync()

        assert numpy.array_equal(pva.ok, [True, True])
        # assert numpy.array_equal(pva.timestamp, []) Can't easily test timestamps
        assert numpy.array_equal(pva.severity, [0, 0])
        assert numpy.array_equal(pva.status, [0, 0])

    def test_pv_array_ticking(self):
        self.assertIOCRunning()

        pvs = [self.testprefix + 'inc1', self.testprefix + 'inc2']

        pva = PV_array(pvs)
        Sleep(0.2)
        pva.sync()

        first = pva.get()
        Sleep(0.2)
        second = pva.get()

        assert all(numpy.greater(second, first))


    def test_pv_array_put(self):
        self.assertIOCRunning()

        pvs = [self.testprefix + 'rec1', self.testprefix + 'rec2']

        pva = PV_array(pvs)
        Sleep(0.2)
        pva.sync()

        new_vals = [444, 555]

        pva.caput(new_vals)
        Sleep(0.2)

        assert (pva.get()== new_vals).all()
