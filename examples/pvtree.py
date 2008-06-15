#!/bin/env python2.4

# Simple tool for viewing the chain of PV dependencies.


import sys
import re

import require
from cothread import Timedout
from cothread.catools import *



def values(*fields):
    return [(field, False) for field in fields]
def links(*fields):
    return [(field, True) for field in fields]

# Special hack: list of DTYP values where we don't follow the links
INP_DTYP_no_follow = set([
    'Libera',
    'ReadFileWaveform',
])
def check_inp(dtyp):
    return dtyp not in INP_DTYP_no_follow
input_rec  = [('INP', check_inp)]


def inp_range(last):
    return links(*[
        'INP%s' % c
        for c in map(chr, range(ord('A'), ord(last)+1))])

output_rec = values('DOL')

record_types = {
    'aao'       : output_rec,
    'ao'        : output_rec,
    'bo'        : output_rec,
    'fanout'    : output_rec,
    'longout'   : output_rec,
    'mbbo'      : output_rec,
    'stringout' : output_rec,
    'ai'        : input_rec,
    'bi'        : input_rec,
    'compress'  : input_rec,
    'longin'    : input_rec,
    'mbbi'      : input_rec,
    'mbbiDirect': input_rec,
    'mbboDirect': input_rec,
    'stringin'  : input_rec,
    'subArray'  : input_rec,
    'waveform'  : input_rec,
    'genSub'    : inp_range('U'),
    'calc'      : values('CALC') + inp_range('L'),
#    'sub': ['calc'],
#    'seq': ['seq'],
    'sel'       : values('SELN') + inp_range('L'),
    'motor'     : values('OUT', 'MSTA'),
    'calcout'   : values('CALC', 'OUT') + inp_range('L'),
#    'seq'       : 
}



def colour(word, col):
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

def print_indent(indent, col, record, *args):
    print '%s%s %s' % (
        '  ' * indent, colour(record, col), ' '.join(map(str, args)))


visited_set = set()
# values_set = set()

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
        print_indent(indent, BRIGHT+RED, record + ': link missing!')
    else:
        if record in visited_set:
            print_indent(indent, GREY, record + ' already visited')
            return
        visited_set.add(record)

        try:
            # value_fields is a list pure value links, while all the entries
            # in link_fields should be true links or constants.
            fields, types = zip(*record_types[rtyp])
        except KeyError:
            print_indent(indent, RED, record, 'type', rtyp, 'not found')
        else:
            values = caget(
                map_fields(record,
                    ('VAL', 'SEVR', 'STAT', 'DTYP') + fields),
                datatype = str, timeout = 2, throw = False, count = 1)
            (val, sevr, stat, dtyp), values = values[:4], values[4:]
                
            print_indent(indent, BOLD, record,
                '(%s, %s)' % (rtyp, dtyp_to_str(dtyp)),
                val, colour(sevr, YELLOW), colour(stat, YELLOW))
            for value, link_type in zip(values, types):
                if callable(link_type):
                    link_type = link_type(dtyp)
                if link_type:
                    if value.ok and value:
                        print_indent(indent, BRIGHT+CYAN, value.name, value)
                        follow_link(indent+1, value)
                else:
                    print_indent(indent, CYAN, value.name, value)


if len(sys.argv) == 2:
    follow_link(0, sys.argv[1])
else:
    print '''Usage: %s <link>

Shows a tree of link dependencies of the given EPICS pv link.
''' % sys.argv[0]
