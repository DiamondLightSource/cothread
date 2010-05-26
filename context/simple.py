#!/dls_sw/tools/python2.4-debug/bin/python2.4

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from cothread import *

def Task():
    pass

def f1(arg):
    print 'f1', sys.getrefcount(arg)
    f2(arg)
def f2(arg):
    print 'f2', sys.getrefcount(arg)
    f3(arg)
def f3(arg):
    print 'f3', sys.getrefcount(arg)

# blah = 'test string'
# print 'blah', sys.getrefcount(blah)
# f1(blah)

for i in range(2):
    t = Spawn(Task)
    t.Wait()
