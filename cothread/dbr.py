# This file is part of the Diamond cothread library.
#
# Copyright (C) 2007 James Rowland, 2007-2012 Michael Abbott,
# Diamond Light Source Ltd.
#
# The Diamond cothread library is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License,
# or (at your option) any later version.
#
# The Diamond cothread library is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
# Contact:
#      Dr. Michael Abbott,
#      Diamond Light Source Ltd,
#      Diamond House,
#      Chilton,
#      Didcot,
#      Oxfordshire,
#      OX11 0DE
#      michael.abbott@diamond.ac.uk

'''Channel access datatype support.  Derived from definitions in the EPICS
header file db_access.h
'''

import sys
import ctypes
import numpy
import datetime

from . import cadef
from . import py23


__all__ = [
    # Basic DBR request codes: any one of these can be used as part of a
    # datatype request.
    'DBR_STRING',       # 40 character strings
    'DBR_SHORT',        # 16 bit signed
    'DBR_FLOAT',        # 32 bit float
    'DBR_ENUM',         # 16 bit unsigned
    'DBR_CHAR',         # 8 bit unsigned
    'DBR_LONG',         # 32 bit signed
    'DBR_DOUBLE',       # 64 bit float

    'DBR_CHAR_STR',     # Long strings as char arrays
    'DBR_CHAR_UNICODE', # Long unicode strings as char arrays
    'DBR_ENUM_STR',     # Enums as strings, default otherwise
    'DBR_CHAR_BYTES',   # Long byte strings as char arrays

    'DBR_PUT_ACKT',     # Configure global alarm acknowledgement
    'DBR_PUT_ACKS',     # Acknowledge global alarm
    'DBR_STSACK_STRING', # Returns status ack structure
    'DBR_CLASS_NAME',   # Returns record type (same as .RTYP?)

    # Data type format requests
    'FORMAT_RAW',       # Request the underlying data only
    'FORMAT_TIME',      # Request alarm status and timestamp
    'FORMAT_CTRL',      # Request graphic and control fields

    'ca_extra_fields',  # List of all possible augmented field names
]

# List of all the field names that can be added to an augmented field.
ca_extra_fields = [
    # Fields common to all data types
    'name',         # Name of the PV used to create this value
    'ok',           # True for normal data, False for error code
    'datatype',     # Underlying DBR_ code
    'element_count', # Underlying length of original data
    # Fields common to time and ctrl types
    'severity',     # Alarm severity
    'status',       # CA status code: reason for severity
    # Timestamp specific fields
    'raw_stamp',    # Unformatted timestamp in separate seconds and nsecs
    'timestamp',    # Timestamp in seconds
    'datetime',     # Timestamp converted to datetime
    # Control specific fields
    'units',        # Units for display
    'upper_disp_limit',
    'lower_disp_limit',
    'upper_alarm_limit',
    'lower_alarm_limit',
    'upper_warning_limit',
    'lower_warning_limit',
    'upper_ctrl_limit',
    'lower_ctrl_limit',
    'precision',    # Display precision for floating point values
    # Other
    'enums',        # Enumeration strings for ENUM type
]


# Standard hard-wired EPICS array sizes.
MAX_STRING_SIZE = 40        # Size of string type
MAX_UNITS_SIZE = 8          # Size of units string
MAX_ENUM_STRING_SIZE = 26   # Size of individual enumeration strings
MAX_ENUM_STATES = 16        # Numer of possible enumeration strings


ca_doc_string = \
'''All values returned from channel access are returned as "augmented"
types with extra fields.  The following fields are always present:
    name
    ok

The followiong fields are present if ok is True:
    datatype
    element_count

Depending on the request type, the following extra fields may be present:

If timestamps requested:
    status, severity,
    timestamp, raw_stamp

    The timestamp is returned in two forms:
        timestamp
            This is the time stamp in the system epoch in seconds represented
            as a double.  Rounding leads to errors at the resolution of
            sub-microseconds, so this result is rounded to the nearest
            microsecond.
        raw_stamp
            This is a tuple of the time stamp as (secs, nsec) with separate
            integer fields .secs and .nsec for the seconds and nanoseconds.

If control values requested (and datatype is not DBR_ENUM):
    status, severity, units,
    upper_disp_limit, lower_disp_limit,
    upper_alarm_limit, lower_alarm_limit,
    upper_warning_limit, lower_warning_limit,
    upper_ctrl_limit, lower_ctrl_limit,
    precision (if floating point type)

If control values requested and datatype is DBR_ENUM:
    status, severity,
    enums (list of possible enumeration strings)
'''

@property
def timestamp_to_datetime(self):
    return datetime.datetime.fromtimestamp(self.timestamp)

# Augmented array used for all return values with more than one element.
class ca_array(numpy.ndarray):
    __doc__ = ca_doc_string
    datetime = timestamp_to_datetime
    def __pos__(self):
        return numpy.array(self)
    __hash__ = None

# Augmented basic Python types used for scalar values.
class ca_str(str):
    __doc__ = ca_doc_string
    datetime = timestamp_to_datetime
    def __pos__(self):
        return str(self)


# Overlapping handling for python 2 and python 3.  We have three types with two
# different semantics: str, bytes, unicode.  In python2 str is bytes, while in
# python3 str is unicode.  We walk a delicate balancing act to get the right
# behaviour in both environments!
if sys.version_info < (3,):
    ca_bytes = ca_str
    class ca_unicode(bytes):
        __doc__ = ca_doc_string
        datetime = timestamp_to_datetime
        def __pos__(self):
            return unicode(self)
    str_char_code = 'S'
else:
    class ca_bytes(bytes):
        __doc__ = ca_doc_string
        datetime = timestamp_to_datetime
        def __pos__(self):
            return bytes(self)
    ca_unicode = ca_str
    str_char_code = 'U'
    unicode = str


class ca_int(int):
    __doc__ = ca_doc_string
    datetime = timestamp_to_datetime

class ca_float(float):
    __doc__ = ca_doc_string
    datetime = timestamp_to_datetime


# The EPICS epoch begins midnight first thing on 1st January 1990 and is in UTC.
# We convert all EPICS timestamps to the Python epoch.  This is not defined in
# the language documentation but in practice is the ANSI epoch, midnight 1st
# January 1970.  Strictly we should compute
#   EPICS_epoch = calendar.timegm((1990, 1, 1, 0, 0, 0, 0, 0, 0))
# but that pulls in an extra module dependency and the number is constant:
EPICS_epoch = 631152000             # Seconds from 1970 to 1990


class ca_timestamp(ctypes.Structure):
    _fields_ = [
        ('secs',    ctypes.c_uint32),
        ('nsec',    ctypes.c_uint32)]


# ----------------------------------------------------------------------------
#   DBR type definitions

# All the following types are used to overlay dbr data returned from channel
# access or passed into channel access.

def copy_attributes_none(self, other):
    pass

def copy_attributes_time(self, other):
    other.status = self.status
    other.severity = self.severity

    # Handling the timestamp is a little awkward.  We provide both a
    # raw_stamp and a timestamp value as there is loss of ns precision in
    # the timestamp value (represented as a double) and the raw_stamp value
    # is awkward for computation.
    secs = self.raw_stamp.secs + EPICS_epoch
    nsec = self.raw_stamp.nsec
    other.raw_stamp = (secs, nsec)
    # The timestamp is rounded to microseconds, both to avoid confusion
    # (because the ns part is rounded already) and to avoid an excruciating
    # bug in the .fromtimestamp() function.
    other.timestamp = round(secs + nsec * 1e-9, 6)

def copy_attributes_ctrl(self, other):
    other.status = self.status
    other.severity = self.severity

    other.units = py23.decode(ctypes.string_at(self.units))
    other.upper_disp_limit = self.upper_disp_limit
    other.lower_disp_limit = self.lower_disp_limit
    other.upper_alarm_limit = self.upper_alarm_limit
    other.lower_alarm_limit = self.lower_alarm_limit
    other.upper_warning_limit = self.upper_warning_limit
    other.lower_warning_limit = self.lower_warning_limit
    other.upper_ctrl_limit = self.upper_ctrl_limit
    other.lower_ctrl_limit = self.lower_ctrl_limit

    if hasattr(self, 'precision'):
        other.precision = self.precision

# This particular dtype is used for strings, and indeed identity to this
# value is used to recognise the string type!
str_dtype = numpy.dtype('S%d' % MAX_STRING_SIZE)


# Base DBR types
class dbr_string(ctypes.Structure):
    dtype = str_dtype
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', (ctypes.c_byte * MAX_STRING_SIZE) * 1)]

class dbr_short(ctypes.Structure):
    dtype = numpy.int16
    scalar = ca_int
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', ctypes.c_int16 * 1)]

class dbr_float(ctypes.Structure):
    dtype = numpy.float32
    scalar = ca_float
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', ctypes.c_float * 1)]

class dbr_enum(ctypes.Structure):
    dtype = numpy.uint16
    scalar = ca_int
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', ctypes.c_uint16 * 1)]

class dbr_char(ctypes.Structure):
    dtype = numpy.uint8
    scalar = ca_int
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', ctypes.c_uint8 * 1)]

class dbr_long(ctypes.Structure):
    dtype = numpy.int32
    scalar = ca_int
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', ctypes.c_int32 * 1)]

class dbr_double(ctypes.Structure):
    dtype = numpy.float64
    scalar = ca_float
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', ctypes.c_double * 1)]

# DBR types with timestamps.

class dbr_time_string(ctypes.Structure):
    dtype = str_dtype
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_int16),
        ('severity',  ctypes.c_int16),
        ('raw_stamp', ca_timestamp),
        ('raw_value', (ctypes.c_byte * MAX_STRING_SIZE) * 1)]

class dbr_time_short(ctypes.Structure):
    dtype = numpy.int16
    scalar = ca_int
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_int16),
        ('severity',  ctypes.c_int16),
        ('raw_stamp', ca_timestamp),
        ('RISC_pad',  ctypes.c_int16),
        ('raw_value', ctypes.c_int16 * 1)]

class dbr_time_float(ctypes.Structure):
    dtype = numpy.float32
    scalar = ca_float
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_int16),
        ('severity',  ctypes.c_int16),
        ('raw_stamp', ca_timestamp),
        ('raw_value', ctypes.c_float * 1)]

class dbr_time_enum(ctypes.Structure):
    dtype = numpy.uint16
    scalar = ca_int
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_int16),
        ('severity',  ctypes.c_int16),
        ('raw_stamp', ca_timestamp),
        ('RISC_pad',  ctypes.c_int16),
        ('raw_value', ctypes.c_uint16 * 1)]

class dbr_time_char(ctypes.Structure):
    dtype = numpy.uint8
    scalar = ca_int
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_int16),
        ('severity',  ctypes.c_int16),
        ('raw_stamp', ca_timestamp),
        ('RISC_pad0', ctypes.c_int16),
        ('RISC_pad1', ctypes.c_uint8),
        ('raw_value', ctypes.c_uint8 * 1)]

class dbr_time_long(ctypes.Structure):
    dtype = numpy.int32
    scalar = ca_int
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_int16),
        ('severity',  ctypes.c_int16),
        ('raw_stamp', ca_timestamp),
        ('raw_value', ctypes.c_int32 * 1)]

class dbr_time_double(ctypes.Structure):
    dtype = numpy.float64
    scalar = ca_float
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_int16),
        ('severity',  ctypes.c_int16),
        ('raw_stamp', ca_timestamp),
        ('RISC_pad',  ctypes.c_int32),
        ('raw_value', ctypes.c_double * 1)]

# DBR types with full control and graphical fields

class dbr_ctrl_short(ctypes.Structure):
    dtype = numpy.int16
    scalar = ca_int
    copy_attributes = copy_attributes_ctrl
    _fields_ = [
        ('status',              ctypes.c_int16),
        ('severity',            ctypes.c_int16),
        ('units',               ctypes.c_char * MAX_UNITS_SIZE),
        ('upper_disp_limit',    ctypes.c_int16),
        ('lower_disp_limit',    ctypes.c_int16),
        ('upper_alarm_limit',   ctypes.c_int16),
        ('upper_warning_limit', ctypes.c_int16),
        ('lower_warning_limit', ctypes.c_int16),
        ('lower_alarm_limit',   ctypes.c_int16),
        ('upper_ctrl_limit',    ctypes.c_int16),
        ('lower_ctrl_limit',    ctypes.c_int16),
        ('raw_value',           ctypes.c_int16 * 1)]

class dbr_ctrl_float(ctypes.Structure):
    dtype = numpy.float32
    scalar = ca_float
    copy_attributes = copy_attributes_ctrl
    _fields_ = [
        ('status',              ctypes.c_int16),
        ('severity',            ctypes.c_int16),
        ('precision',           ctypes.c_int16),
        ('RISC_pad',            ctypes.c_int16),
        ('units',               ctypes.c_char * MAX_UNITS_SIZE),
        ('upper_disp_limit',    ctypes.c_float),
        ('lower_disp_limit',    ctypes.c_float),
        ('upper_alarm_limit',   ctypes.c_float),
        ('upper_warning_limit', ctypes.c_float),
        ('lower_warning_limit', ctypes.c_float),
        ('lower_alarm_limit',   ctypes.c_float),
        ('upper_ctrl_limit',    ctypes.c_float),
        ('lower_ctrl_limit',    ctypes.c_float),
        ('raw_value',           ctypes.c_float * 1)]

class dbr_ctrl_enum(ctypes.Structure):
    dtype = numpy.uint16
    scalar = ca_int
    _fields_ = [
        ('status',   ctypes.c_int16),
        ('severity', ctypes.c_int16),
        ('no_str',   ctypes.c_int16),
        ('raw_strs', (ctypes.c_char * MAX_ENUM_STRING_SIZE) * MAX_ENUM_STATES),
        ('raw_value', ctypes.c_uint16 * 1)]

    def copy_attributes(self, other):
        other.status = self.status
        other.severity = self.severity
        other.enums = [
            py23.decode(ctypes.string_at(s))
            for s in self.raw_strs[:self.no_str]]

class dbr_ctrl_char(ctypes.Structure):
    dtype = numpy.uint8
    scalar = ca_int
    copy_attributes = copy_attributes_ctrl
    _fields_ = [
        ('status',              ctypes.c_int16),
        ('severity',            ctypes.c_int16),
        ('units',               ctypes.c_char * MAX_UNITS_SIZE),
        ('upper_disp_limit',    ctypes.c_uint8),
        ('lower_disp_limit',    ctypes.c_uint8),
        ('upper_alarm_limit',   ctypes.c_uint8),
        ('upper_warning_limit', ctypes.c_uint8),
        ('lower_warning_limit', ctypes.c_uint8),
        ('lower_alarm_limit',   ctypes.c_uint8),
        ('upper_ctrl_limit',    ctypes.c_uint8),
        ('lower_ctrl_limit',    ctypes.c_uint8),
        ('RISC_pad',            ctypes.c_uint8),
        ('raw_value',           ctypes.c_uint8 * 1)]

class dbr_ctrl_long(ctypes.Structure):
    dtype = numpy.int32
    scalar = ca_int
    copy_attributes = copy_attributes_ctrl
    _fields_ = [
        ('status',              ctypes.c_int16),
        ('severity',            ctypes.c_int16),
        ('units',               ctypes.c_char * MAX_UNITS_SIZE),
        ('upper_disp_limit',    ctypes.c_int32),
        ('lower_disp_limit',    ctypes.c_int32),
        ('upper_alarm_limit',   ctypes.c_int32),
        ('upper_warning_limit', ctypes.c_int32),
        ('lower_warning_limit', ctypes.c_int32),
        ('lower_alarm_limit',   ctypes.c_int32),
        ('upper_ctrl_limit',    ctypes.c_int32),
        ('lower_ctrl_limit',    ctypes.c_int32),
        ('raw_value',           ctypes.c_int32 * 1)]

class dbr_ctrl_double(ctypes.Structure):
    dtype = numpy.float64
    scalar = ca_float
    copy_attributes = copy_attributes_ctrl
    _fields_ = [
        ('status',              ctypes.c_int16),
        ('severity',            ctypes.c_int16),
        ('precision',           ctypes.c_int16),
        ('RISC_pad0',           ctypes.c_int16),
        ('units',               ctypes.c_char * MAX_UNITS_SIZE),
        ('upper_disp_limit',    ctypes.c_double),
        ('lower_disp_limit',    ctypes.c_double),
        ('upper_alarm_limit',   ctypes.c_double),
        ('upper_warning_limit', ctypes.c_double),
        ('lower_warning_limit', ctypes.c_double),
        ('lower_alarm_limit',   ctypes.c_double),
        ('upper_ctrl_limit',    ctypes.c_double),
        ('lower_ctrl_limit',    ctypes.c_double),
        ('raw_value',           ctypes.c_double * 1)]


class dbr_stsack_string(ctypes.Structure):
    dtype = str_dtype
    _fields_ = [
        ('status',              ctypes.c_int16),
        ('severity',            ctypes.c_int16),
        ('ackt',                ctypes.c_int16),
        ('acks',                ctypes.c_int16),
        ('raw_value',           (ctypes.c_byte * MAX_STRING_SIZE) * 1)]
    def copy_attributes(self, other):
        other.status = self.status
        other.severity = self.severity
        other.ackt = self.ackt
        other.acks = self.acks


# DBR request codes.  These correspond precisely to the types above, as
# identified in the DbrCodeToType lookup table below.
DBR_STRING = 0
DBR_SHORT = 1
DBR_FLOAT = 2
DBR_ENUM = 3
DBR_CHAR = 4
DBR_LONG = 5
DBR_DOUBLE = 6

DBR_TIME_STRING = 14
DBR_TIME_SHORT = 15
DBR_TIME_FLOAT = 16
DBR_TIME_ENUM = 17
DBR_TIME_CHAR = 18
DBR_TIME_LONG = 19
DBR_TIME_DOUBLE = 20

DBR_CTRL_SHORT = 29
DBR_CTRL_FLOAT = 30
DBR_CTRL_ENUM = 31
DBR_CTRL_CHAR = 32
DBR_CTRL_LONG = 33
DBR_CTRL_DOUBLE = 34

DBR_PUT_ACKT = 35       # Configure global alarm acknowledgement
DBR_PUT_ACKS = 36       # Acknowledge global alarm
DBR_STSACK_STRING = 37
DBR_CLASS_NAME = 38

# Special value for DBR_CHAR as str special processing.
DBR_ENUM_STR = 996
DBR_CHAR_BYTES = 997
DBR_CHAR_UNICODE = 998
DBR_CHAR_STR = 999


# Lookup table to convert supported DBR type codes into the corresponding DBR
# datatype.
DbrCodeToType = {
    DBR_STRING : dbr_string,
    DBR_SHORT : dbr_short,
    DBR_FLOAT : dbr_float,
    DBR_ENUM : dbr_enum,
    DBR_CHAR : dbr_char,
    DBR_LONG : dbr_long,
    DBR_DOUBLE : dbr_double,

    DBR_TIME_STRING : dbr_time_string,
    DBR_TIME_SHORT : dbr_time_short,
    DBR_TIME_FLOAT : dbr_time_float,
    DBR_TIME_ENUM : dbr_time_enum,
    DBR_TIME_CHAR : dbr_time_char,
    DBR_TIME_LONG : dbr_time_long,
    DBR_TIME_DOUBLE : dbr_time_double,

    DBR_CTRL_SHORT : dbr_ctrl_short,
    DBR_CTRL_FLOAT : dbr_ctrl_float,
    DBR_CTRL_ENUM : dbr_ctrl_enum,
    DBR_CTRL_CHAR : dbr_ctrl_char,
    DBR_CTRL_LONG : dbr_ctrl_long,
    DBR_CTRL_DOUBLE : dbr_ctrl_double,

    DBR_STSACK_STRING : dbr_stsack_string,
    DBR_CLASS_NAME : dbr_string,
}


# List of basic DBR types that we can process directly.
BasicDbrTypes = set([
    DBR_STRING,     DBR_SHORT,      DBR_FLOAT,      DBR_ENUM,
    DBR_CHAR,       DBR_LONG,       DBR_DOUBLE,
])


# Conversion from numpy character codes to DBR types.
NumpyCharCodeToDbr = {
    # The following type codes are supported directly:
    'b':    DBR_CHAR,       # byte   = int8
    'h':    DBR_SHORT,      # short  = int16
    'i':    DBR_LONG,       # intc   = int32
    'f':    DBR_FLOAT,      # single = float32
    'd':    DBR_DOUBLE,     # float_ = float64
    'S':    DBR_STRING,     # bytes_

    # The following type codes are weakly supported by pretending that
    # they're related types.
    '?':    DBR_CHAR,       # bool_
    'B':    DBR_CHAR,       # ubyte  = uint8
    'H':    DBR_SHORT,      # ushort = uint16
    'I':    DBR_LONG,       # uintc  = uint32

    # Unicode is supported by decoding from DBR_STRING
    'U':    DBR_STRING,     # str => unicode

    # We translate machine native integers to DBR_LONG as EPICS has no support
    # for 64-bit integers, but not allowing int as an argument is too confusing.
    'l':    DBR_LONG,       # int_ => int32, truncate as necessary
    'L':    DBR_LONG,       # uint => int32

    # The following type codes are not supported at all:
    #   q   longlong        Q   ulonglong       g   longfloat
    #   F   csingle         D   complex_        G   clongfloat
    #   O   object_         V   void            p, P    pointer types
}



# Format codes for type_to_dbr function.
FORMAT_RAW = 0
FORMAT_TIME = 1
FORMAT_CTRL = 2

class InvalidDatatype(Exception):
    '''Invalid datatype requested.'''

def _datatype_to_dbr(datatype):
    '''Converts Python datatype into a dbrcode and numpy dtype if possible,
    otherwise raises appropriate exception.'''
    try:
        # Rely on numpy for generic datatype recognition and conversion together
        # with filtering through our array of acceptable types.
        return NumpyCharCodeToDbr[numpy.dtype(datatype).char]
    except Exception as error:
        py23.raise_from(
            InvalidDatatype(
                'Datatype "%s" not supported for channel access' % datatype),
            error)

def _type_to_dbrcode(datatype, format):
    '''Converts a datatype and format request to a dbr value, or raises an
    exception if this cannot be done.

    datatype can be either a DBF_XXXX value as returned by ca_field_type() or
    data type supported by numpy

    format can be one of
      - FORMAT_RAW: retrieve the raw format only
      - FORMAT_TIME: retrieve timestamp and alarm status data
      - FORMAT_CTRL: retrieve limit and control data
    '''
    if datatype not in BasicDbrTypes:
        if datatype in [DBR_CHAR_STR, DBR_CHAR_BYTES, DBR_CHAR_UNICODE]:
            datatype = DBR_CHAR     # Retrieve this type using char array
        elif datatype in [DBR_STSACK_STRING, DBR_CLASS_NAME]:
            return datatype         # format is meaningless in this case
        else:
            datatype = _datatype_to_dbr(datatype)

    # Now take account of the format
    if format == FORMAT_RAW:
        # Use the raw datatype
        return datatype
    elif format == FORMAT_TIME:
        # Return corresponding DBR_TIME_XXXX value
        return datatype + 14
    elif format == FORMAT_CTRL:
        if datatype == DBR_STRING:
            # There is no ctrl option for strings, so in this case provide
            # the richest format we have available.
            return DBR_TIME_STRING
        else:
            # Return corresponding DBR_CTRL_XXX value
            return datatype + 28
    else:
        raise InvalidDatatype('Format not recognised')


# Helper functions for string arrays used in _convert_str_{str,bytes} below.
def _make_strings(raw_dbr, count):
    p_raw_value = ctypes.pointer(raw_dbr.raw_value[0])
    return [ctypes.string_at(p_raw_value[n]) for n in range(count)]

def _string_array(strings, count, dtypechar):
    if strings:
        n = max(len(s) for s in strings)
    else:
        # Zero length array of strings!  Very rare, but possible, but numpy
        # won't allow a dtype of S0, so we need to fake up something
        n = 1
    result = ca_array((count,), dtype = '%s%d' % (dtypechar, n))
    for i, s in enumerate(strings):
        result[i] = s
    return result

def _string_at(raw_value, count):
    # Need string_at() twice to ensure string is size limited *and* null
    # terminated.
    return ctypes.string_at(ctypes.string_at(raw_value, count))


# Conversion functions from raw_dbr to specified format.  These all take a
# raw_dbr and compute the appropriate selected Python type.  One of these
# conversion functions is selected internally with type_to_dbr below.

# Conversion from char array to strings
def _convert_char_str(raw_dbr, count):
    return ca_str(py23.decode(_string_at(raw_dbr.raw_value, count)))

# Conversion from char array to bytes strings
def _convert_char_bytes(raw_dbr, count):
    return ca_bytes(_string_at(raw_dbr.raw_value, count))

# Conversion from char array to unicode strings
def _convert_char_unicode(raw_dbr, count):
    return ca_unicode(_string_at(raw_dbr.raw_value, count).decode('UTF-8'))


# Arrays of standard strings.
def _convert_str_str(raw_dbr, count):
    return ca_str(py23.decode(_make_strings(raw_dbr, count)[0]))
def _convert_str_str_array(raw_dbr, count):
    strings = [py23.decode(s) for s in _make_strings(raw_dbr, count)]
    return _string_array(strings, count, str_char_code)

# Arrays of bytes strings.
def _convert_str_bytes(raw_dbr, count):
    return ca_bytes(_make_strings(raw_dbr, count)[0])
def _convert_str_bytes_array(raw_dbr, count):
    return _string_array(_make_strings(raw_dbr, count), count, 'S')

# Arrays of unicode strings.
def _convert_str_unicode(raw_dbr, count):
    return ca_str(_make_strings(raw_dbr, count)[0].decode('UTF-8'))
def _convert_str_unicode_array(raw_dbr, count):
    strings = [s.decode('UTF-8') for s in _make_strings(raw_dbr, count)]
    return _string_array(strings, count, 'U')


# For everything that isn't a string we either return a scalar or a ca_array
def _convert_other(raw_dbr, count):
    # Single elements are always returned as scalars.
    return raw_dbr.scalar(raw_dbr.raw_value[0])
def _convert_other_array(raw_dbr, count):
    # Build a fresh ca_array to receive a copy of the raw data in the dbr.
    # We have to take a copy, because the dbr is transient, and it is
    # helpful to use a numpy array as a container, because of the support it
    # provides.  It is essential that the dtype correctly matches the memory
    # layout of the raw dbr, and of course that the count is accurate.
    result = ca_array(shape = (count,), dtype = raw_dbr.dtype)
    ctypes.memmove(result.ctypes.data, raw_dbr.raw_value, result.nbytes)
    return result


def type_to_dbr(channel, datatype, format):
    '''Converts data request into the appropriate dbr code and conversion.  The
    channel must be ready so that its field type can be interrogated.  Returns
    dbr code together with conversion function for transforming dbr values of
    that type back into Python values.'''

    name = channel.name
    if datatype is None:
        # Use natural channel data type if no type specified.
        datatype = cadef.ca_field_type(channel)
        # A special hack for char arrays with PV name ending in $ -- these are
        # handled specially by EPICS as long strings.
        if datatype == DBR_CHAR and name[-1] == '$':
            datatype = DBR_CHAR_STR
    elif datatype == DBR_ENUM_STR:
        # A similar hack: for DBR_ENUM_STR use natural channel data type except
        # for enums which are fetched as strings.
        datatype = cadef.ca_field_type(channel)
        if datatype == DBR_ENUM:
            datatype = DBR_STRING

    # Prepare as much beforehand for conversion.
    dbrcode = _type_to_dbrcode(datatype, format)
    dbr_type = DbrCodeToType[dbrcode]
    dtype = dbr_type.dtype
    element_count = cadef.ca_element_count(channel)

    # Determine precisely which conversion from dbr to Python is required: all
    # the options for strings add a lot of complexity, ordinary numeric values
    # are all handled uniformly.
    if dtype is numpy.uint8 and datatype == DBR_CHAR_STR:
        # Conversion from char array to strings
        convert = _convert_char_str
    elif dtype is numpy.uint8 and datatype == DBR_CHAR_BYTES:
        # Conversion from char array to bytes strings
        convert = _convert_char_bytes
    elif dtype is numpy.uint8 and datatype == DBR_CHAR_UNICODE:
        # Conversion from char array to unicode strings
        convert = _convert_char_unicode
    else:
        if dtype is str_dtype:
            # String arrays, either unicode or normal.
            if isinstance(datatype, type) and issubclass(datatype, bytes):
                convert = (_convert_str_bytes, _convert_str_bytes_array)
            elif isinstance(datatype, type) and issubclass(datatype, unicode):
                convert = (_convert_str_unicode, _convert_str_unicode_array)
            else:
                convert = (_convert_str_str, _convert_str_str_array)
        else:
            convert = (_convert_other, _convert_other_array)

        # The conversion to scalar or array is determined by the original
        # element count of the underlying data source.
        if element_count == 1:
            convert = convert[0]
        else:
            convert = convert[1]


    # We return this function to perform conversion from dbr to Python value.
    def dbr_to_value(raw_dbr, dbrcode_in, count):
        # If the dbrcode has changed (this really shouldn't happen) then we've
        # got a problem!  If this does happen I'll need to handle this better,
        # as this is a pretty poor place to raise an exception.
        assert dbrcode_in == dbrcode, 'Oops, I didn\'t expect CA to do that'

        # Reinterpret the raw_dbr as a pointer to the appropriate structure as
        # identified by the given dbrcode.  We can then cast the raw_dbr
        # structure into an instance of this dbr: the data we want is then
        # available in the .raw_dbr field of this structure.
        raw_dbr = ctypes.cast(raw_dbr, ctypes.POINTER(dbr_type))[0]
        result = convert(raw_dbr, count)

        # Finally copy across any attributes together with the pv name and a
        # success indicator.
        raw_dbr.copy_attributes(result)
        result.name = name
        result.ok = True
        result.element_count = element_count
        result.datatype = datatype
        return result

    return dbrcode, dbr_to_value


# -----------------------------------------------------------------------------
# From Python value to DBR encoding, used by caput()

def _datatype_to_dtype(datatype):
    '''Converts any user specified datatype into dbrcode and dtype.'''
    if datatype not in BasicDbrTypes:
        datatype = _datatype_to_dbr(datatype)
    return datatype, DbrCodeToType[datatype].dtype


def _require_value(value, dtype):
    '''Use numpy to convert value into specified target type ready for transport
    over channel access.'''
    result = numpy.require(value, requirements = 'C', dtype = dtype)
    if result.shape == ():
        result.shape = (1,)
    assert result.ndim == 1, 'Can\'t put multidimensional arrays!'
    return result


def value_to_dbr(channel, datatype, value):
    '''Takes an ordinary Python value and converts it into a value in dbr
    format suitable for sending to channel access.  Returns the target
    datatype and the number of elements together with a pointer to the raw
    data and (for lifetime management) the object containing the data.'''

    # If no datatype specified then use the target datatype.
    if datatype is None:
        if isinstance(value, (str, bytes, unicode)):
            # Give strings with no datatype special treatment, let the IOC do
            # the decoding.  It's safer this way.
            datatype = DBR_STRING
        else:
            datatype = cadef.ca_field_type(channel)
            if datatype == DBR_CHAR and channel.name[-1] == '$':
                # Treat char arrays with name ending in $ as long strings.
                datatype = DBR_CHAR_STR

    if datatype == DBR_CHAR_STR:
        # Char arrays as strings need special treatment.
        count = cadef.ca_element_count(channel)
        try:
            result = _require_value(value, 'S%d' % count)
        except UnicodeEncodeError:
            # Unicode needs to be encoded
            result = _require_value(value.encode('UTF-8'), 'S%d' % count)
        assert result.shape[0] == 1, \
            'Can\'t put array of strings as char array'
        return DBR_CHAR, count, result.ctypes.data, result
    elif datatype in [DBR_PUT_ACKT, DBR_PUT_ACKS]:
        # For DBR_PUT_ACKT and DBR_PUT_ACKS we return an integer
        value = ctypes.c_int32(value)
        return datatype, 1, ctypes.byref(value), value
    else:
        # For all other types compute the appropriate transport type
        dbrcode, dtype = _datatype_to_dtype(datatype)
        if dbrcode is DBR_STRING:
            try:
                # We'll let numpy do most of the heavy lifting.
                result = _require_value(value, str_dtype)
            except UnicodeEncodeError:
                # Whoops, looks like unicode, need to encode each string.
                value = _require_value(value, None)
                result = numpy.empty(value.shape, str_dtype)
                for n, s in enumerate(value):
                    result[n] = s.encode('UTF-8')
        else:
            # Numpy can do all the conversion for all the remaining data types.
            result = _require_value(value, dtype)

        return dbrcode, len(result), result.ctypes.data, result
