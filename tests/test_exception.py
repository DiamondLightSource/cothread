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

if __name__ == '__main__':
    unittest.main(verbosity=2)
