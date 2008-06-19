# Channel access datatype support.  Derived from definitions in the EPICS
# header file db_access.h

import ctypes
import numpy
import time


__all__ = [
    # DBR type request codes.  Only these ones can be used from outside.
    'DBR_STRING',   'DBR_SHORT',    'DBR_FLOAT',    'DBR_ENUM',
    'DBR_CHAR',     'DBR_LONG',     'DBR_DOUBLE',
    # Format types
    'FORMAT_RAW',   'FORMAT_TIME',  'FORMAT_CTRL',
    # Published functions
    'type_to_dbr',  # Convert data type request into DBR datatype
    'dbr_to_value', # Convert dbr value into user value (array or scalar)
    'value_to_dbr', # Convert Python value into dbr format

    'ca_extra_fields',
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
MAX_STRING_SIZE = 40
MAX_UNITS_SIZE = 8
MAX_ENUM_STRING_SIZE = 26
MAX_ENUM_STATES = 16 


ca_doc_string = \
'''All values returned from channel access are returned as an "augmented"
types with extra fields.  The following field is always present:
    name

Depending on the request type, the following extra fields may be present:

If timestamps requested:
    status, severity,
    timestamp, raw_stamp

    The timestamp is returned in all three possible forms because of problems
    with each representation:
        timestamp
            This is the time stamp in the system epoch in seconds represented
            as a double.  Rounding leads to errors at the resolution of
            sub-microseconds.
        raw_stamp
            This structure has the raw time stamp (in system epoch) with
            separate integer fields .secs and .nsec for the seconds and
            nanoseconds.

If control values requested (and datatype is not DBR_ENUM):
    status, severity, units,
    upper_disp_limit, lower_disp_limit,
    upper_alarm_limit, lower_alarm_limit,
    upper_warning_limit, lower_warning_limit,
    upper_ctrl_limit, lower_ctrl_limit,
    precision (if floating point type)

If control values requested and datatype is DBR_ENUM:
    status, severity, 
    strs (list of possible enumeration strings)
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


# The EPICS epoch begins 1st January 1990.
EPICS_epoch = int(time.mktime((1990, 1, 1, 0, 0, 0, 0, 0, 0)))

    
class ca_timestamp(ctypes.Structure):
    _fields_ = [
        ('secs',                ctypes.c_long),
        ('nsec',                ctypes.c_long)]

    def __str__(self):
        return '%d.%09d' % (self.secs, self.nsec)
        
        
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
    # is awkward for computation
    raw_stamp = self.raw_stamp
    raw_stamp.secs += EPICS_epoch
    other.raw_stamp = raw_stamp
    # The timestamp is rounded to microseconds, both to avoid confusion
    # (because the ns part is rounded already) and to avoid an excruciating
    # bug in the .fromtimestamp() function.
    other.timestamp = round(raw_stamp.secs + raw_stamp.nsec * 1e-9, 6)

def copy_attributes_ctrl(self, other):
    other.status = self.status
    other.severity = self.severity

    other.units = truncate_string(self.units)
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
    _fields_ = [('raw_value', ctypes.c_byte * MAX_STRING_SIZE)]
    
class dbr_short(ctypes.Structure):
    dtype = numpy.int16
    scalar = ca_int
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', ctypes.c_short * 1)]
    
class dbr_float(ctypes.Structure):
    dtype = numpy.float32
    scalar = ca_float
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', ctypes.c_float * 1)]
    
class dbr_enum(ctypes.Structure):
    dtype = numpy.uint16
    scalar = ca_int
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', ctypes.c_ushort * 1)]
    
class dbr_char(ctypes.Structure):
    dtype = numpy.uint8
    scalar = ca_int
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', ctypes.c_byte * 1)]
    
class dbr_long(ctypes.Structure):
    dtype = numpy.int32
    scalar = ca_int
    copy_attributes = copy_attributes_none
    _fields_ = [('raw_value', ctypes.c_long * 1)]
    
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
        ('status',    ctypes.c_short),
        ('severity',  ctypes.c_short),
        ('raw_stamp', ca_timestamp),
        ('raw_value', ctypes.c_byte * MAX_STRING_SIZE)]

class dbr_time_short(ctypes.Structure):
    dtype = numpy.int16
    scalar = ca_int
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_short),
        ('severity',  ctypes.c_short),
        ('raw_stamp', ca_timestamp),
        ('RISC_pad',  ctypes.c_short),
        ('raw_value', ctypes.c_short * 1)]
    
class dbr_time_float(ctypes.Structure):
    dtype = numpy.float32
    scalar = ca_float
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_short),
        ('severity',  ctypes.c_short),
        ('raw_stamp', ca_timestamp),
        ('raw_value', ctypes.c_float * 1)]
    
class dbr_time_enum(ctypes.Structure):
    dtype = numpy.uint16
    scalar = ca_int
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_short),
        ('severity',  ctypes.c_short),
        ('raw_stamp', ca_timestamp),
        ('RISC_pad',  ctypes.c_short),
        ('raw_value', ctypes.c_ushort * 1)]
    
class dbr_time_char(ctypes.Structure):
    dtype = numpy.uint8
    scalar = ca_int
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_short),
        ('severity',  ctypes.c_short),
        ('raw_stamp', ca_timestamp),
        ('RISC_pad0', ctypes.c_short),
        ('RISC_pad1', ctypes.c_byte),
        ('raw_value', ctypes.c_byte * 1)]
    
class dbr_time_long(ctypes.Structure):
    dtype = numpy.int32
    scalar = ca_int
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_short),
        ('severity',  ctypes.c_short),
        ('raw_stamp', ca_timestamp),
        ('raw_value', ctypes.c_long * 1)]
    
class dbr_time_double(ctypes.Structure):
    dtype = numpy.float64
    scalar = ca_float
    copy_attributes = copy_attributes_time
    _fields_ = [
        ('status',    ctypes.c_short),
        ('severity',  ctypes.c_short),
        ('raw_stamp', ca_timestamp),
        ('RISC_pad',  ctypes.c_long),
        ('raw_value', ctypes.c_double * 1)]

# DBR types with full control and graphical fields

class dbr_ctrl_short(ctypes.Structure):
    dtype = numpy.int16
    scalar = ca_int
    copy_attributes = copy_attributes_ctrl
    _fields_ = [
        ('status',              ctypes.c_short),
        ('severity',            ctypes.c_short),
        ('units',               ctypes.c_char * MAX_UNITS_SIZE),
        ('upper_disp_limit',    ctypes.c_short),
        ('lower_disp_limit',    ctypes.c_short),
        ('upper_alarm_limit',   ctypes.c_short),
        ('upper_warning_limit', ctypes.c_short),
        ('lower_warning_limit', ctypes.c_short),
        ('lower_alarm_limit',   ctypes.c_short),
        ('upper_ctrl_limit',    ctypes.c_short),
        ('lower_ctrl_limit',    ctypes.c_short),
        ('raw_value',           ctypes.c_short * 1)]
    
class dbr_ctrl_float(ctypes.Structure):
    dtype = numpy.float32
    scalar = ca_float
    copy_attributes = copy_attributes_ctrl
    _fields_ = [
        ('status',              ctypes.c_short),
        ('severity',            ctypes.c_short),
        ('precision',           ctypes.c_short),
        ('RISC_pad',            ctypes.c_short),
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
        ('status',   ctypes.c_short),
        ('severity', ctypes.c_short),
        ('no_str',   ctypes.c_short),
        ('raw_strs', (ctypes.c_char * MAX_ENUM_STRING_SIZE) * MAX_ENUM_STATES),
        ('raw_value', ctypes.c_ushort * 1)]
    
    def copy_attributes(self, other):
        other.status = self.status
        other.severity = self.severity
        other.enums = [
            truncate_string(s[:])
            for s in self.raw_strs[:self.no_str]]
        
class dbr_ctrl_char(ctypes.Structure):
    dtype = numpy.uint8
    scalar = ca_int
    copy_attributes = copy_attributes_ctrl
    _fields_ = [
        ('status',              ctypes.c_short),
        ('severity',            ctypes.c_short),
        ('units',               ctypes.c_char * MAX_UNITS_SIZE),
        ('upper_disp_limit',    ctypes.c_byte),
        ('lower_disp_limit',    ctypes.c_byte),
        ('upper_alarm_limit',   ctypes.c_byte),
        ('upper_warning_limit', ctypes.c_byte),
        ('lower_warning_limit', ctypes.c_byte),
        ('lower_alarm_limit',   ctypes.c_byte),
        ('upper_ctrl_limit',    ctypes.c_byte),
        ('lower_ctrl_limit',    ctypes.c_byte),
        ('RISC_pad',            ctypes.c_byte),
        ('raw_value',           ctypes.c_byte * 1)]
    
class dbr_ctrl_long(ctypes.Structure):
    dtype = numpy.int32
    scalar = ca_int
    copy_attributes = copy_attributes_ctrl
    _fields_ = [
        ('status',              ctypes.c_short),
        ('severity',            ctypes.c_short),
        ('units',               ctypes.c_char * MAX_UNITS_SIZE),
        ('upper_disp_limit',    ctypes.c_long),
        ('lower_disp_limit',    ctypes.c_long),
        ('upper_alarm_limit',   ctypes.c_long),
        ('upper_warning_limit', ctypes.c_long),
        ('lower_warning_limit', ctypes.c_long),
        ('lower_alarm_limit',   ctypes.c_long),
        ('upper_ctrl_limit',    ctypes.c_long),
        ('lower_ctrl_limit',    ctypes.c_long),
        ('raw_value',           ctypes.c_long * 1)]
    
class dbr_ctrl_double(ctypes.Structure):
    dtype = numpy.float64
    scalar = ca_float
    copy_attributes = copy_attributes_ctrl
    _fields_ = [
        ('status',              ctypes.c_short),
        ('severity',            ctypes.c_short),
        ('precision',           ctypes.c_short),
        ('RISC_pad0',           ctypes.c_short),
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

    
# No idea what this is for, and at the moment we provide no support for it!
class dbr_stsack_string(ctypes.Structure):
    _fields_ = [
        ('status', ctypes.c_ushort),
        ('severity', ctypes.c_ushort),
        ('ackt', ctypes.c_ushort),
        ('acks', ctypes.c_ushort),
        ('raw_value', ctypes.c_byte * MAX_STRING_SIZE)]


    
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

DBR_STSACK_STRING = 37


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
}


# List of basic DBR types that we can process directly.
BasicDbrTypes = set([
    DBR_STRING,     DBR_SHORT,      DBR_FLOAT,      DBR_ENUM,
    DBR_CHAR,       DBR_LONG,       DBR_DOUBLE,
])


# Conversion from numpy character codes to DBR types.
NumpyCharCodeToDbr = {
    # The following type codes are supported directly:
    'B':    DBR_CHAR,       # byte
    'h':    DBR_SHORT,      # short
    'i':    DBR_LONG,       # intc
    'l':    DBR_LONG,       # int_
    'f':    DBR_FLOAT,      # single
    'd':    DBR_DOUBLE,     # float_
    'S':    DBR_STRING,     # str_
    
    # The following type codes are weakly supported by pretending that
    # they're related types.
    '?':    DBR_CHAR,       # bool_
    'b':    DBR_CHAR,       # byte
    'p':    DBR_LONG,       # intp
    'H':    DBR_SHORT,      # ushort
    'I':    DBR_LONG,       # uintc
    'L':    DBR_LONG,       # uint
    'P':    DBR_LONG,       # uintp
    
    # The following type codes are not supported at all:
    #   q   longlong        Q   ulonglong       g   longfloat
    #   F   csingle         D   complex_        G   clongfloat
    #   O   object_         U   unicode_        V   void
}


def truncate_string(string):
    '''Takes a C-format string from a fixed length buffer and returns a Python
    string truncated at the first null character.'''
    return string.split('\0', 1)[0]


# Format codes for type_to_dbr function.
FORMAT_RAW = 0
FORMAT_TIME = 1
FORMAT_CTRL = 2

class InvalidDatatype(Exception):
    '''Invalid datatype requested.'''

def type_to_dbr(datatype, format = FORMAT_RAW):
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
        # See if numpy can help us out
        try:
            datatype = NumpyCharCodeToDbr[numpy.dtype(datatype).char]
        except:
            raise InvalidDatatype('Datatype not supported for channel access')

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
            return datatype + 14
        else:
            # Return corresponding DBR_CTRL_XXX value
            return datatype + 28
    else:
        raise InvalidDatatype('Format not recognised')


def dbr_to_value(raw_dbr, datatype, count, name):
    '''Convert a raw DBR structure into a packaged Python value.  All values
    are returned as augmented types.'''

    # Reinterpret the raw_dbr as a pointer to the appropriate structure as
    # identified by the given datatype.  We can then cast the raw_dbr
    # structure into an instance of this datatype: the data we want is then
    # available in the .raw_dbr field of this structure.
    dbr_type = DbrCodeToType[datatype]
    raw_dbr = ctypes.cast(raw_dbr, ctypes.POINTER(dbr_type))[0]

    # Build a fresh dbr_array to receive a copy of the raw data in the dbr.
    # We have to take a copy, because the dbr is transient, and it is helpful
    # to use a numpy array as a container, because of the support it
    # provides.
    #     It is essential that the dtype correctly matches the memory layout
    # of the raw dbr, and of course that the count is accurate.
    result = ca_array(shape = (count,), dtype = dbr_type.dtype)
    ctypes.memmove(result.ctypes.data, raw_dbr.raw_value, result.nbytes)

    # String types need to be cleaned up: anything past the first
    # null is garbage and needs to be deleted.
    if dbr_type.dtype is str_dtype:
        for i in range(count):
            result[i] = truncate_string(result[i])

    # Unit length arrays are treated specially: we return the associated
    # scalar instead.
    #    It is possible to instead simply reshape the result to a zero
    # dimensional array, but unfortunately such values don't behave enough
    # like their underlying scalars.  This way we're really returning a
    # subtype of the appropriate data type.
    if count == 1:
        result = raw_dbr.scalar(result[0])

    # Finally copy across any attributes togethe with the pv name and a
    # success indicator.
    raw_dbr.copy_attributes(result)
    result.name = name
    result.ok = True
    return result


def value_to_dbr(value):
    '''Takes an ordinary Python value and converts it into a value in dbr
    format suitable for sending to channel access.  Returns the target
    datatype and the number of elements as well as a pointer to the raw
    data.'''

    # First convert the data directly into an array.  This will help in
    # subsequent processing: this does most of the type coercion.
    value = numpy.require(value, requirements = 'C')
    if value.shape == ():
        value.shape = (1,)
    assert value.ndim == 1, 'Can\'t put multidimensional arrays!'

    if value.dtype.char == 'S' and value.itemsize != MAX_STRING_SIZE:
        # Need special processing to hack the array so that characters are
        # actually 40 characters long.
        new_value = numpy.empty(value.shape, numpy.dtype('S40'))
        new_value[:] = value
        value = new_value
    
    datatype = NumpyCharCodeToDbr[value.dtype.char]
    count = len(value)
    return datatype, count, value
