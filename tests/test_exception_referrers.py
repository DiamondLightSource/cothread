# Module imports
import unittest

# Add cothread onto file and import
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import cothread


class T(object):
    def t1(self, name):
        try:
            raise Exception
        except Exception as e:
            pass

        cothread.Yield()

class ExceptionTest(unittest.TestCase):

    def test_exception_referrers(self):
        fg = T()
        bg = T()
        cothread.Spawn(bg.t1, 'background')
        fg.t1('foreground')
        self.assertEqual(sys.getrefcount(fg), 2)
        
if __name__ == '__main__':
    unittest.main(verbosity=2)
