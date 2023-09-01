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

'''Functions imported directly from libca.

See http://www.aps.anl.gov/epics/base/R3-14/11-docs/CAref.html for detailed
documentation of the functions below.

This module is a thin wrapper over the cadef.h file to be found in
    $EPICS_BASE/include/cadef.h
'''

__all__ = [
    # Event type notification codes for camonitor
    'DBE_VALUE',        # Notify normal value changes
    'DBE_LOG',          # Notify archival value changes
    'DBE_ALARM',        # Notify alarm state changes
    'DBE_PROPERTY',     # Notify property change events (3.14.11 and later)
]


import ctypes
from .load_ca import libca
from . import py23



# -----------------------------------------------------------------------------
#   Enumeration and error code definitions.


# Flags used to identify notification events to request for subscription.
DBE_VALUE   = 1
DBE_LOG     = 2
DBE_ALARM   = 4
DBE_PROPERTY = 8

# Connection state as passed to connection handler
CA_OP_CONN_UP   = 6
CA_OP_CONN_DOWN = 7

# Status codes as returned by virtually all ca_ routines.  We only specially
# handle normal return, timeout, or disconnection.
ECA_NORMAL = 1
ECA_TIMEOUT = 80
ECA_DISCONN = 192


# -----------------------------------------------------------------------------
#   Function wrappers.
#   Wrappers for callbacks from C back into Python.


# Event handler for ca_array_get_callback, ca_array_put_callback,
# ca_create_subscription.  The event handler is called when the action
# completes or the data is available.
class event_handler_args(ctypes.Structure):
    _fields_ = [
        ('usr',     ctypes.py_object),  # Associated private data
        ('chid',    ctypes.c_void_p),   # Channel ID for this request
        ('type',    ctypes.c_long),     # DBR type of data returned
        ('count',   ctypes.c_long),     # Number of data points returned
        ('raw_dbr', ctypes.c_void_p),   # Pointer to raw dbr array
        ('status',  ctypes.c_int)]      # ECA_ status code of operation
event_handler = ctypes.CFUNCTYPE(None, event_handler_args)


# Exception handler, called to report asynchronous errors that have no other
# report path.
class exception_handler_args(ctypes.Structure):
    _fields_ = [
        ('usr',     ctypes.c_void_p),   # Associated private data
        ('chid',    ctypes.c_void_p),   # Channel ID or NULL
        ('type',    ctypes.c_long),     # Data type requested
        ('count',   ctypes.c_long),     # Number of data points requested
        ('addr',    ctypes.c_void_p),   # User address for GET operation
        ('stat',    ctypes.c_long),     # Channel access status code
        ('op',      ctypes.c_long),     # CA_OP_ operation code
        ('ctx',     ctypes.c_char_p),   # Context information string
        ('pFile',   ctypes.c_char_p),   # Location in source: file name
        ('lineNo',  ctypes.c_uint)]     #             ... and line number
exception_handler = ctypes.CFUNCTYPE(None, exception_handler_args)


# Connection handler, used to report channel connection status.
class ca_connection_handler_args(ctypes.Structure):
    _fields_ = [
        ('chid',    ctypes.c_void_p),
        ('op',      ctypes.c_long)]
connection_handler = ctypes.CFUNCTYPE(None, ca_connection_handler_args)



# -----------------------------------------------------------------------------
#   Exception handling support
#   The following defines exceptions associated with libca errors together
# with error handling wrappers to detect the errors and raise the appropriate
# exceptions.


class Disconnected(Exception):
    '''The channel is disconnected.'''
    def __init__(self, chid):
        self.name = ca_name(chid)
    def __str__(self):
        return 'Channel %s disconnected' % self.name


class CAException(Exception):
    '''Exception in response to calling ca_ method.'''
    def __init__(self, status, function):
        self.status = status
        self.function = function
    def __str__(self):
        return '%s calling %s' % (
            ca_message(self.status), self.function.__name__)



# For routines which are simply expected to succeed this routine should be
# assigned to the routine's errcheck attribute.
def expect_ECA_NORMAL(status, function, args):
    if status != ECA_NORMAL:
        raise CAException(status, function)


# Routine for testing functions which interrogate the status of a channel and
# return a special sentinel value when the channel is disconnected.
def expect_connected(sentinel, chid = 0):
    '''sentinel is the disconnected notification value to check for, and chid
    is the position in the argument list of the channel being inspected.'''
    def expects(result, function, args):
        if result == sentinel:
            raise Disconnected(args[chid])
        else:
            return result
    return expects


# We set things up so that the data type returned by ca_puser() below is a
# Python object (to be precise, the argument passed in to ca_create_channel),
# but this means that we need to get the reference counting right.
#    The ctypes library assumes when a routine returns a py_object type that
# the called routine has already incremented the object's reference count.
# If the object is just a void* then this isn't going to be so: this routine
# when assigned to errcheck will resolve this problem.
def convert_py_object(object, function, args):
    ctypes.pythonapi.Py_IncRef(object)
    return object


# Let the library know that Py_IncRef and Py_DecRef take a raw PyObject*
# (otherwise it converts the argument to a fresh int() object which receives
# the reference count: not so useful!)
ctypes.pythonapi.Py_IncRef.argtypes = [ctypes.py_object]
ctypes.pythonapi.Py_DecRef.argtypes = [ctypes.py_object]



# -----------------------------------------------------------------------------
#   libca function definitions


#   error_message = ca_message(status_code)
#
# Converts channel access status code (an int) into a printable error message.
ca_message = libca.ca_message
ca_message.argtypes = [ctypes.c_long]
ca_message.restype = ctypes.c_char_p
ca_message.errcheck = py23.auto_decode


#   channel_name = ca_name(channel)
#
# Returns name associated with channel id
ca_name = libca.ca_name
ca_name.argtypes = [ctypes.c_void_p]
ca_name.restype = ctypes.c_char_p
ca_name.errcheck = py23.auto_decode


#   @exception_handler
#   def handler(args): ...
#
#   ca_add_exception_event(handler, context)
#
# Adds global exception handler: called for all asynchronous errors.
ca_add_exception_event = libca.ca_add_exception_event
ca_add_exception_event.argtypes = [exception_handler, ctypes.c_void_p]
ca_add_exception_event.errcheck = expect_ECA_NORMAL


#   chtype = ca_field_type(channel_id)
#
# Returns the native data type (a dbf_ code) of the data associated with the
# channel, or returns TYPENOTCONN if the channel is not connected.
TYPENOTCONN = -1
ca_field_type = libca.ca_field_type
ca_field_type.argtypes = [ctypes.c_void_p]
ca_field_type.restype = ctypes.c_short
ca_field_type.errcheck = expect_connected(TYPENOTCONN)


#   count = ca_element_count(channel_id)
#
# Returns the array element count for the data array associated with the
# channel.  Returns 0 if the channel is not connected.
ca_element_count = libca.ca_element_count
ca_element_count.argtypes = [ctypes.c_void_p]
ca_element_count.errcheck = expect_connected(0)


#   @connection_handler
#   def handler(args): ...
#
#   ca_create_channel(
#       pv, handler, context, priority, byref(channel_id))
#
# Initiates the creation of a channel with name pv.  The handler will be
# called when the state of the channel changes.  The context argument can be
# recovered by calling ca_puser(channel_id).
ca_create_channel = libca.ca_create_channel
ca_create_channel.argtypes = [
    py23.auto_encode, connection_handler, ctypes.py_object,
    ctypes.c_int, ctypes.c_void_p]
ca_create_channel.errcheck = expect_ECA_NORMAL


#   status = ca_clear_channel(channel_id)
#
# Closes the given channel.
ca_clear_channel = libca.ca_clear_channel
ca_clear_channel.argtypes = [ctypes.c_void_p]
ca_clear_channel.errcheck = expect_ECA_NORMAL


#   puser = ca_puser(channel_id)
#
# Returns the private user context associated with the channel.
ca_puser = libca.ca_puser
ca_puser.argtypes = [ctypes.c_void_p]
ca_puser.restype = ctypes.py_object
ca_puser.errcheck = convert_py_object


#   @event_handler
#   def handler(args): ...
#
#   ca_array_get_callback(
#       channel_type, count, channel_id, handler, context)
#
# Makes a request to receive data from the given channel.  The handler will
# be called if data is retrieved or the channel becomes disconnected.
ca_array_get_callback = libca.ca_array_get_callback
ca_array_get_callback.argtypes = [
    ctypes.c_long, ctypes.c_long, ctypes.c_void_p, event_handler,
    ctypes.py_object]
ca_array_get_callback.errcheck = expect_ECA_NORMAL


#   @event_handler
#   def handler(args): ...
#
#   ca_array_put_callback(
#       channel_type, count, channel_id, value, handler, context)
#
# Writes data to the given channel.  The handler is called once server side
# processing is complete, or if a failure occurs.
ca_array_put_callback = libca.ca_array_put_callback
ca_array_put_callback.argtypes = [
    ctypes.c_long, ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p,
    event_handler, ctypes.py_object]
ca_array_put_callback.errcheck = expect_ECA_NORMAL


#   ca_array_put(channel_type, count, channel_id, value)
#
# Writes data to the given channel, returning immediately.  There may be no
# notification if this fails.
ca_array_put = libca.ca_array_put
ca_array_put.argtypes = [
    ctypes.c_long, ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p]
ca_array_put.errcheck = expect_ECA_NORMAL


#   @event_handler
#   def handler(args): ...
#
#   ca_create_subscription(
#       channel_type, count, channel_id, event_mask, handler, context,
#       byref(event_id))
#
# Creates a subscription to receive notification whenever significant changes
# occur to a channel.  Arguments are:
#
#   channel_type: DBR type of data to be passed to handler callback
#
#   count: the number of points to be read from the underlying data array in
#       the channel, or 0 to specify native length.
#
#   channel_id: the identifier of a previously created channel.  Note that
#       subscriptions can be created on a disconnected channel.
#
#   event_mask: mask of events to receive, any combination of DBE_ values.
#
#   handler: callback function to receive updates, receives an
#       event_handler_args structure as argument.
#
#   context: callback context passed as .usr field of handler arguments.
#
#   event_id: an identifier for this subscription, used for subsequently
#       cancelling this subscription.
ca_create_subscription = libca.ca_create_subscription
ca_create_subscription.argtypes = [
    ctypes.c_long, ctypes.c_long, ctypes.c_void_p, ctypes.c_long,
    event_handler, ctypes.py_object, ctypes.c_void_p]
ca_create_subscription.errcheck = expect_ECA_NORMAL


#   ca_clear_subscription(event_id)
#
# Cancels a previously established subscription using the returned event_id.
ca_clear_subscription = libca.ca_clear_subscription
ca_clear_subscription.argtypes = [ctypes.c_void_p]
ca_clear_subscription.errcheck = expect_ECA_NORMAL


#   ca_context_create(enable_preemptive_callback)
#
# To be called on initialisation, specifying whether asynchronous callbacks
# are to be enabled.
ca_context_create = libca.ca_context_create
ca_context_create.argtypes = [ctypes.c_int]
ca_context_create.errcheck = expect_ECA_NORMAL


#   ca_context_destroy()
#
# To be called at exit.
ca_context_destroy = libca.ca_context_destroy
ca_context_destroy.argtypes = []


#   status = ca_pend_event(timeout)
#
# Flushes the send buffer and processes background activities until the
# specified timeout (in seconds) expires.
ca_pend_event = libca.ca_pend_event
ca_pend_event.argtypes = [ctypes.c_double]


#   ca_flush_io()
#
# Flush outstanding IO requests to the server.  Needs to be called after CA
# calls which require interaction with a CA server.
ca_flush_io = libca.ca_flush_io
ca_flush_io.argtypes = []
ca_flush_io.errcheck = expect_ECA_NORMAL


#   state = ca_state(channel_id)
#
# Returns an enumeration indicating the state of the channel.
cs_never_conn = 0
cs_prev_conn = 1
cs_conn = 2
cs_closed = 3
ca_state = libca.ca_state
ca_state.argtypes = [ctypes.c_void_p]


#   host = ca_host_name(channel_id)
#
# Returns the host name of the connected server
ca_host_name = libca.ca_host_name
ca_host_name.argtypes = [ctypes.c_void_p]
ca_host_name.restype = ctypes.c_char_p
ca_host_name.errcheck = py23.auto_decode


#   read = ca_read_access(channel_id)
#   write = ca_write_access(channel_id)
#
# Returns whether the channel can be read or written by this client.
ca_read_access = libca.ca_read_access
ca_read_access.argtypes = [ctypes.c_void_p]
ca_read_access.restype = bool

ca_write_access = libca.ca_write_access
ca_write_access.argtypes = [ctypes.c_void_p]
ca_write_access.restype = bool
