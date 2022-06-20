# Module imports
import unittest

# Add cothread onto file and import
import sys
import os
import subprocess
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import cothread


class T(object):
    def t1(self):
        try:
            raise Exception
        except Exception as e:
            pass

        cothread.Yield()


class ExceptionTest(unittest.TestCase):

    # This test captures a bug fix to exception info lifetimes.
    def test_exception_referrers(self):
        fg = T()
        bg = T()
        cothread.Spawn(bg.t1)
        fg.t1()
        self.assertEqual(sys.getrefcount(fg), 2)

    # This test checks for the correct transfer of exceptions between cothreads.
    def test_exception_type_gets_passed_through(self):
        pid = os.getpid()
        # Generate a Ctrl-C signal and check that we receive it
        p = subprocess.Popen("sleep 1 && kill -2 %s" % pid, shell=True)
        self.assertRaises(KeyboardInterrupt, cothread.Sleep, 2)


class EventQueueTest(unittest.TestCase):
    def setUp(self):
        self.o = cothread.EventQueue()

    def test_signalled(self):
        l = []

        def waiter():
            l.append(self.o.Wait())

        s = cothread.Spawn(waiter)

        # Check that it's blocked
        self.assertRaises(cothread.Timedout, s.Wait, 0.1)
        self.o.Signal(46)
        s.Wait(0.1)
        assert l == [46]

    def test_iter(self):
        self.o.Signal(4)
        self.o.Signal("boo")
        self.o.Signal({})
        self.o.close()
        self.assertEqual(list(self.o), [4, "boo", {}])


class TimerTest(unittest.TestCase):
    def test_oneshot(self):
        l = []

        def tick():
            l.append(1)

        t = cothread.Timer(0.1, tick, reuse=True)
        self.assertEqual(l, [])
        cothread.Sleep(0.2)
        self.assertEqual(l, [1])
        cothread.Sleep(0.2)
        self.assertEqual(l, [1])
        t.reset(0.05)
        self.assertEqual(l, [1])
        cothread.Sleep(0.1)
        self.assertEqual(l, [1, 1])
        cothread.Sleep(0.1)
        self.assertEqual(l, [1, 1])

    def test_multi(self):
        l = [1]

        def tick():
            l.append(l[-1] + 2)

        t = cothread.Timer(0.1, tick, retrigger=True)
        self.assertEqual(l, [1])
        cothread.Sleep(0.15)
        self.assertEqual(l, [1, 3])
        cothread.Sleep(0.1)
        self.assertEqual(l, [1, 3, 5])
        t.cancel()
        cothread.Sleep(0.15)
        self.assertEqual(l, [1, 3, 5])



class RLockTest(unittest.TestCase):
    def setUp(self):
        self.v = None
        self.o = cothread.RLock()

    def test_spawn_unlocked(self):
        def set_v1():
            self.v = 1

        # check our setter works in isolation
        cothread.Spawn(set_v1).Wait()
        assert self.v == 1

        # now do a long running task works
        with self.o:
            self.v = 2
            assert self.v == 2
            cothread.Spawn(set_v1).Wait()
            assert self.v == 1

        assert self.v == 1

    def test_spawn_locked(self):
        def set_v1():
            with self.o:
                self.v = 1

        # check our setter works in isolation
        assert self.v is None
        cothread.Spawn(set_v1).Wait()
        assert self.v == 1

        # now do a long running task works
        with self.o:
            self.v = 2
            assert self.v == 2
            # start our thing that will be blocked, then sleep to make sure
            # it can't do its thing
            s = cothread.Spawn(set_v1)
            cothread.Sleep(0.2)
            assert self.v == 2

        # now wait for the other to complete, and check it could
        s.Wait()
        assert self.v == 1



if __name__ == '__main__':
    unittest.main(verbosity=2)
