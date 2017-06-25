#!/usr/bin/env python

# Simple tool for viewing the chain of PV dependencies.

from __future__ import print_function

import sys
import re
import os

if __name__ == '__main__':
    sys.path.append(
        os.path.join(os.path.dirname(__file__), '../..'))
    try:
        import numpy
    except ImportError:
        from pkg_resources import require
        require('numpy')

from cothread import Timedout
from cothread.catools import *



def values(*fields):
    return [(field, False) for field in fields]
def links(*fields):
    return [(field, True) for field in fields]

def inp_range(last):
    return links(*[
        'INP%s' % c
        for c in map(chr, range(ord('A'), ord(last)+1))])

def calc_rec(*fields):
    return values(*fields) + inp_range('L')

output_rec = links('DOL')
input_rec  = links('INP')

record_types = {
    'aai':          input_rec,
    'aao':          output_rec,
    'acalcout':     calc_rec(),
    'ai':           input_rec,
    'ao':           output_rec,
    'aSub':         inp_range('U'),
    'asyn':         [],
    'bi':           input_rec,
    'bo':           output_rec,
    'busy':         output_rec,
    'calc':         calc_rec('CALC'),
    'calcout':      calc_rec('CALC', 'OUT'),
    'compress':     input_rec,
    'dfanout':      output_rec,
    'eg':           [],
    'egevent':      [],
    'er':           [],
    'erevent':      [],
    'event':        input_rec,
    'fanout':       output_rec,
    'funcgen':      [],
    'genSub':       inp_range('U'),
    'longin':       input_rec,
    'longout':      output_rec,
    'mbbi':         input_rec,
    'mbbiDirect':   input_rec,
    'mbbo':         output_rec,
    'mbboDirect':   output_rec,
    'motor':        values('OUT', 'MSTA'),
    'permissive':   [],
    'scalcout':     calc_rec(),
    'scanparm':     [],
    'sel':          calc_rec() + links('SELN'),
    'seq':          links(*['DOL%d' % (n+1) for n in range(10)] + ['DOLA']),
    'sscan':        [],
    'state':        [],
    'stringin':     input_rec,
    'stringout':    output_rec,
    'sub':          calc_rec(),
    'subArray':     input_rec,
    'swait':        [],
    'transform':    inp_range('P'),
    'waveform':     input_rec,
}


def colour(col, word):
    if options.raw:
        return word
    else:
        esc = 27
        return '%(esc)c[%(col)dm%(word)s%(esc)c[0m' % locals()

BLACK   = 30
RED     = 31
GREEN   = 32
YELLOW  = 33
BLUE    = 34
MAGENTA = 35
CYAN    = 36
GREY    = 37
BRIGHT  = 60    # Add to colours for bright colours
BOLD    = 1

def print_indent(priority, indent, col, record, *args):
    if options.quiet:
        indent = 0
    if priority > 0 or not options.quiet:
        print('%s%s %s' % (
            '  ' * indent, colour(col, record), ' '.join(map(str, args))))


# Set of PVs that we've visited so we can avoid repeating ourself.
visited_set = set()

# As well as numbers, match on anything starting with @ or # -- these look
# like addresses.
NUMBER = re.compile(
    r'@|#|([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][-+]?[0-9]+)?$')

def recognise_value(value):
    '''Implements some heuristics for recognising a value.'''
    if not isinstance(value, str):
        # An array is certainly not a link!
        return True
    if NUMBER.match(value):
        # Numbers certainly aren't links!
        return True
    return False


def map_fields(record, fields):
    return ['%s.%s' % (record, field) for field in fields]

def dtyp_to_str(dtyp):
    if dtyp.ok:
        return repr(dtyp)
    else:
        return ''

def follow_link(indent, link):
    '''The link may be a pure value, or may be a link specifier.  We
    discover which by trying to access its RTYP field -- if this fails this
    must be an ordinary value, in which case we have nothing to do.  Otherwise
    all associated links of the record are followed and displayed.'''

    if recognise_value(link):
        return

    # If this really is a record then split off any modifiers and any field
    # name before trying to follow it.
    record = link.split(' ', 1)[0].split('.', 1)[0]

    try:
        rtyp = caget('%s.RTYP' % record, datatype = str, timeout = 1)
    except Timedout:
        # No RTYP: presumably an ordinary value, not a link
        print_indent(0, indent, BRIGHT+RED, record + ': RTYP missing!')
    else:
        if record in visited_set:
            print_indent(0, indent, GREY, record + ' already visited')
            return
        visited_set.add(record)

        try:
            # value_fields is a list pure value links, while all the entries
            # in link_fields should be true links or constants.
            fields, types = zip(*record_types[rtyp])
        except KeyError:
            print_indent(0, indent, RED, record, 'type', rtyp, 'not found')
        else:
            values = caget(
                map_fields(record,
                    ('VAL', 'SEVR', 'STAT', 'DTYP') + fields),
                datatype = str, timeout = 2, throw = False, count = 1)
            (val, sevr, stat, dtyp), values = values[:4], values[4:]

            print_indent(0, indent, BOLD, record,
                '(%s, %s)' % (rtyp, dtyp_to_str(dtyp)),
                val, colour(YELLOW, sevr), colour(YELLOW, stat))
            for value, link_type in zip(values, types):
                if link_type:
                    if value.ok and value:
                        ms_check = ()
                        priority = 0
                        if options.check_ms and 'NMS' in value.split(' '):
                            ms_check = ':', colour(BRIGHT+RED, 'MS missing')
                            priority = 1
                        print_indent(priority,
                            indent, BRIGHT+CYAN, value.name, value, *ms_check)
                        follow_link(indent+1, value)
                else:
                    print_indent(0, indent, CYAN, value.name, value)


# Determines whether output supports colour
def dumb_terminal():
    term = os.getenv('TERM')
    return not sys.stdout.isatty() or term is None or term == 'dumb'

def main():
    # Argument parsing
    from optparse import OptionParser
    parser = OptionParser(
        usage = '%prog [options] <link> ...',
        description =
            'Shows a tree of link dependencies of the given EPICS pv link.')

    parser.add_option(
        '-m', '--nms',
        dest = 'check_ms', default = False, action = 'store_true',
        help = 'Check for missing maximise severity (MS) links')
    parser.add_option(
        '-q', '--quiet',
        dest = 'quiet', default = False, action = 'store_true',
        help = 'Only show errors, suppress normal output')
    parser.add_option(
        '-r', '--raw',
        dest = 'raw', default = dumb_terminal(), action = 'store_true',
        help = 'Print raw text without colour codes')
    parser.add_option(
        '-c', '--colour',
        dest = 'raw', action = 'store_false',
        help = 'Force colour coded output on unsupported destination')

    global options
    options, args = parser.parse_args()
    if args:
        for arg in args:
            follow_link(0, arg)
    else:
        parser.print_usage()


if __name__ == '__main__':
    main()
