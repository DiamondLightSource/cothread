# Some simple python2/python3 compatibility tricks.
#
# Some of this is drastically reduced from six.py

import sys
import ctypes


# Exception handling
if sys.version_info < (3,):
    def raise_from(exception, source):
        raise exception

    exec('''
def raise_with_traceback(result):
    raise result[0], result[1], result[2]
''')

else:
    exec('''
def raise_from(exception, source):
    try:
        raise exception from source
    finally:
        exception = None
''')

    def raise_with_traceback(result):
        raise result[1].with_traceback(result[2])


# c_char_p conversion
if sys.version_info < (3,):
    auto_encode = ctypes.c_char_p
    def auto_decode(result, func, args):
        return result
    def decode(s):
        return s

else:
    class auto_encode(ctypes.c_char_p):
        @classmethod
        def from_param(cls, value):
            if value is None:
                return value
            else:
                return value.encode('UTF-8')

    def auto_decode(result, func, args):
        if result is None:
            return result
        else:
            return result.decode('UTF-8', 'replace')

    def decode(s):
        return s.decode('UTF-8', 'replace')
