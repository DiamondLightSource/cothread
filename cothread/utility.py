# Some random stuff without a proper home yet

import ctypes


def keyword_argument(dictionary, keyword, default=None):
    '''Looks for the specified keyword in the dictionary.  If found, it is
    deleted from the dictionary, otherwise the specified default value is
    returned.

    This is useful for transparently adding extra keyword arguments to a
    function.'''
    if keyword in dictionary:
        result = dictionary[keyword]
        del dictionary[keyword]
        return result
    else:
        return default



def dump(thing):
    '''Function to print a hex dump of the given object.  Must support the
    ctypes interface.'''

    s = ctypes.string_at(ctypes.addressof(thing), ctypes.sizeof(thing))
    for l in [s[n:n+16] for n in range(0, len(s), 16)]:
        for c in l:
            print '%02x' % ord(c),
        print ''.ljust(3 * (16 - len(l))),
        print ''.join([
            ord(' ') <= ord(c) < 127 and c or '.'
            for c in l])
    