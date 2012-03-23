import sys, os

sys.path.append(
    os.path.join(os.path.dirname(__file__), '../../cothread'))
from _coroutine import *


def c_1(arg):
    print('c1', arg)
    for i in range(5):
        print('switching to c2', i, arg)
        arg = switch(c2, arg+1)
        print('c1 in control', i, arg)
    print('c1 returning', arg)
    return arg

def c_2(arg):
    print('c2', arg)
    for i in range(5):
        print('switching to c1', i, arg)
        arg = switch(c1, arg+1)
        print('c2 in control', i, arg)
    print('c2 returning', arg)
    return arg

c0 = get_current()
c1 = create(c0, c_1, 1<<16)
c2 = create(c1, c_2, 1<<16)

print('about to start')
arg = switch(c1, 1)
print('all done')
