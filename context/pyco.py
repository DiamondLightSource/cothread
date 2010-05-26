import ctypes

coroutine = ctypes.cdll.LoadLibrary('./coroutine.so')

get_current_coroutine = coroutine.get_current_coroutine
create_coroutine = coroutine.create_coroutine
delete_coroutine = coroutine.delete_coroutine
switch_coroutine = coroutine.switch_coroutine
switch_coroutine.argtypes = [ctypes.c_void_p, ctypes.py_object]
switch_coroutine.restype = ctypes.py_object

coroutine_action = ctypes.CFUNCTYPE(ctypes.py_object, ctypes.py_object)

@coroutine_action
def c_1(arg):
    print 'c1', arg
    for i in range(5):
        print 'switching to c2', i, arg
        arg = switch_coroutine(c2, arg+1)
        print 'c1 in control', i, arg
    print 'c1 returning', arg
    return arg

@coroutine_action
def c_2(arg):
    print 'c2', arg
    for i in range(5):
        print 'switching to c1', i, arg
        arg = switch_coroutine(c1, arg+1)
        print 'c2 in control', i, arg
    print 'c2 returning', arg
    return arg

c0 = get_current_coroutine()
c1 = create_coroutine(c0, c_1, 1<<16)
c2 = create_coroutine(c1, c_2, 1<<16)

print 'about to start'
arg = switch_coroutine(c1, 1)
print 'all done'
