# This file is part of the Diamond cothread library.
#
# Copyright (C) 2007 James Rowland, 2007-2010 Michael Abbott,
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

import ctypes
import numpy
import time


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
    # Fields common to time and ctrl types
    'severity',     # Alarm severity
    'status',       # CA status code: reason for severity
    # Timestamp specific fields
    'raw_stamp',    # Unformatted timestamp in separate seconds and nsecs
    'timestamp',    # Timestamp in seconds
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

# Augmented array used for all return values with more than one element.
class ca_array(numpy.ndarray):
    __doc__ = ca_doc_string
    def __pos__(self):
        return numpy.array(self)

# Augmented basic Python types used for scalar values.
class ca_str(str):
    __doc__ = ca_doc_string
    def __pos__(self):
        return str(self)

class ca_int(int):
    __doc__ = ca_doc_string

class ca_float(float):
    __doc__ = ca_doc_string


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

    other.units = ctypes.string_at(self.units)
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
    scalar = ca_str
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
    scalar = ca_str
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
        other.enums = map(ctypes.string_at, self.raw_strs[:self.no_str])

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
    scalar = ca_str
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
DBR_CHAR_STR = 999


# Lookup table to convert support DBR type codes into the corresponding DBR
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
    'S':    DBR_STRING,     # str_

    # The following type codes are weakly supported by pretending that
    # they're related types.
    '?':    DBR_CHAR,       # bool_
    'B':    DBR_CHAR,       # ubyte  = uint8
    'H':    DBR_SHORT,      # ushort = uint16
    'I':    DBR_LONG,       # uintc  = uint32

    # The following type codes are not supported at all:
    #   q   longlong        Q   ulonglong       g   longfloat
    #   F   csingle         D   complex_        G   clongfloat
    #   O   object_         U   unicode_        V   void
}



# A couple of data types can only be supported on 32-bit platforms
if numpy.int_().itemsize == 4:
    NumpyCharCodeToDbr.update({'l': DBR_LONG, 'L': DBR_LONG})   # int_, uint
if numpy.intp().itemsize == 4:
    NumpyCharCodeToDbr.update({'p': DBR_LONG, 'P': DBR_LONG})   # intp, uintp


# Format codes for type_to_dbr function.
FORMAT_RAW = 0
FORMAT_TIME = 1
FORMAT_CTRL = 2

class InvalidDatatype(Exception):
    '''Invalid datatype requested.'''

def _dtype_to_dbr(dtype):
    '''Converts a dtype into the appropriate corresponding DBR_ value, if
    possible, otherwise raises a helpful exception.'''
    try:
        return NumpyCharCodeToDbr[dtype.char]
    except:
        raise InvalidDatatype(
            'Datatype "%s" not supported for channel access' % dtype)

def _datatype_to_dtype(datatype):
    '''Converts a user specified data type into a numpy dtype value.'''
    if datatype in BasicDbrTypes:
        return DbrCodeToType[datatype].dtype
    else:
        try:
            return numpy.dtype(datatype)
        except:
            raise InvalidDatatype(
                'Datatype "%s" cannot be used for channel access' % datatype)


def type_to_dbr(datatype, format):
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
        if datatype == DBR_CHAR_STR:
            datatype = DBR_CHAR     # Retrieve this type using char array
        elif datatype in [DBR_STSACK_STRING, DBR_CLASS_NAME]:
            return datatype         # format is meaningless in this case
        else:
            datatype = _dtype_to_dbr(numpy.dtype(datatype))

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


def dbr_to_value(raw_dbr, datatype, count, name, as_string):
    '''Convert a raw DBR structure into a packaged Python value.  All values
    are returned as augmented types.'''

    # Reinterpret the raw_dbr as a pointer to the appropriate structure as
    # identified by the given datatype.  We can then cast the raw_dbr
    # structure into an instance of this datatype: the data we want is then
    # available in the .raw_dbr field of this structure.
    dbr_type = DbrCodeToType[datatype]
    raw_dbr = ctypes.cast(raw_dbr, ctypes.POINTER(dbr_type))[0]

    if as_string and raw_dbr.dtype is numpy.uint8:
        # Special case hack for long strings returned as DBR_CHAR arrays.
        # Need string_at() twice to ensure string is size limited *and* null
        # terminated.
        result = ca_str(ctypes.string_at(
            ctypes.string_at(raw_dbr.raw_value, count)))
    elif count == 1:
        # Single scalar values can be created directly from the raw value
        result = raw_dbr.raw_value[0]
        if dbr_type.dtype is str_dtype:
            # string_at() ensures the string is properly null terminated.
            result = ctypes.string_at(result)
        result = raw_dbr.scalar(result)
    else:
        # Build a fresh ca_array to receive a copy of the raw data in the
        # dbr.  We have to take a copy, because the dbr is transient, and it
        # is helpful to use a numpy array as a container, because of the
        # support it provides.
        #     It is essential that the dtype correctly matches the memory
        # layout of the raw dbr, and of course that the count is accurate.
        result = ca_array(shape = (count,), dtype = dbr_type.dtype)

        if dbr_type.dtype is str_dtype:
            # Copy strings one by one so that we can ensure that each string
            # is properly null terminated.
            p_raw_value = ctypes.pointer(raw_dbr.raw_value[0])
            for i in range(count):
                result[i] = ctypes.string_at(p_raw_value[i])
        else:
            # For normal waveforms copy the underlying data directly.
            ctypes.memmove(
                result.ctypes.data, raw_dbr.raw_value, result.nbytes)

    # Finally copy across any attributes together with the pv name and a
    # success indicator.
    raw_dbr.copy_attributes(result)
    result.name = name
    result.ok = True
    return result


def value_to_dbr(value, datatype):
    '''Takes an ordinary Python value and converts it into a value in dbr
    format suitable for sending to channel access.  Returns the target
    datatype and the number of elements together with a pointer to the raw
    data and (for lifetime management) the object containing the data.'''

    if datatype is not None:
        if datatype == DBR_CHAR_STR:
            # DBR_CHAR_STR is handled specially: strings are converted to char
            # arrays.
            value = str(value)      # Ensure the value to write is a string
            count = len(value) + 1
            value = ctypes.create_string_buffer(value)
            return DBR_CHAR, count, ctypes.byref(value), value
        elif datatype in [DBR_PUT_ACKT, DBR_PUT_ACKS]:
            # For DBR_PUT_ACKT and DBR_PUT_ACKS we return an integer
            value = ctypes.c_int32(value)
            return datatype, 1, ctypes.byref(value), value
        else:
            datatype = _datatype_to_dtype(datatype)

    # First convert the data directly into an array.  This will help in
    # subsequent processing: this does most of the type coercion.
    value = numpy.require(value, requirements = 'C', dtype = datatype)
    if value.shape == ():
        value.shape = (1,)
    assert value.ndim == 1, 'Can\'t put multidimensional arrays!'

    if value.dtype.char == 'S' and value.itemsize != MAX_STRING_SIZE:
        # Need special processing to hack the array so that strings are
        # actually 40 characters long.
        new_value = numpy.empty(value.shape, str_dtype)
        new_value[:] = value
        value = new_value

    try:
        dbrtype = _dtype_to_dbr(value.dtype)
    except:
        # One more special case.  caput() of a list of integers on a 64-bit
        # system will fail at this point because they were automatically
        # converted to 64-bit integers.  Catch this special case and fix it
        # up by silently converting to 32-bit integers.  Not really the right
        # thing to do (as data can be quietly lost), but the alternative
        # isn't nice to use either.
        #     If the user explicitly specified int then let the exception
        # through: I'm afraid int isn't supported by ca on 64-bit!
        if datatype is None and value.dtype.char == 'l':
            value = numpy.require(value, dtype = numpy.int32)
            dbrtype = DBR_LONG
        else:
            raise

    return dbrtype, len(value), value.ctypes.data, value
