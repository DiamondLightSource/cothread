# Functions imported directly from libca.
#
# See http://he3.dartmouth.edu/manuals/CAref.html for detailed documentation
# of the functions below.
#
# Actually, see http://www.aps.anl.gov/epics/base/R3-14/8-docs/CAref.html
#
# This module is a thin wrapper over the cadef.h file to be found in
#   /dls_sw/epics/R3.14.8.2/base/include/cadef.h

import ctypes


# channel access
# note 3.14.8.2 some threading problems when multiple with same name found
libca = ctypes.cdll.LoadLibrary(
    '/dls_sw/epics/R3.14.8.2/base/lib/linux-x86/libca.so')



# -----------------------------------------------------------------------------
#   Enumeration and error code definitions.


# Operation codes use to identify CA operations, return in exception handler
# to identify failing operation
CA_OP_GET            = 0
CA_OP_PUT            = 1
CA_OP_CREATE_CHANNEL = 2
CA_OP_ADD_EVENT      = 3
CA_OP_CLEAR_EVENT    = 4
CA_OP_OTHER          = 5
# Connection state as passed to connection halder
CA_OP_CONN_UP        = 6
CA_OP_CONN_DOWN      = 7

# Flags used to identify notificaton events to request for subscription.
DBE_VALUE = 1
DBE_LOG = 2
DBE_ALARM = 4

# Status codes as returned by virtually all ca_ routines
ECA_NORMAL = 1
ECA_MAXIOC = 10
ECA_UKNHOST = 18
ECA_UKNSERV = 26
ECA_SOCK = 34
ECA_CONN = 40
ECA_ALLOCMEM = 48
ECA_UKNCHAN = 56
ECA_UKNFIELD = 64
ECA_TOLARGE = 72
ECA_TIMEOUT = 80
ECA_NOSUPPORT = 88
ECA_STRTOBIG = 96
ECA_DISCONNCHID = 106
ECA_BADTYPE = 114
ECA_CHIDNOTFND = 123
ECA_CHIDRETRY = 131
ECA_INTERNAL = 142
ECA_DBLCLFAIL = 144
ECA_GETFAIL = 152
ECA_PUTFAIL = 160
ECA_ADDFAIL = 168
ECA_BADCOUNT = 176
ECA_BADSTR = 186
ECA_DISCONN = 192
ECA_DBLCHNL = 200
ECA_EVDISALLOW = 210
ECA_BUILDGET = 216
ECA_NEEDSFP = 224
ECA_OVEVFAIL = 232
ECA_BADMONID = 242
ECA_NEWADDR = 248
ECA_NEWCONN = 259
ECA_NOCACTX = 264
ECA_DEFUNCT = 278
ECA_EMPTYSTR = 280
ECA_NOREPEATER = 288
ECA_NOCHANMSG = 296
ECA_DLCKREST = 304
ECA_SERVBEHIND = 312
ECA_NOCAST = 320
ECA_BADMASK = 330
ECA_IODONE = 339
ECA_IOINPROGRESS = 347
ECA_BADSYNCGRP = 354
ECA_PUTCBINPROG = 362
ECA_NORDACCESS = 368
ECA_NOWTACCESS = 376
ECA_ANACHRONISM = 386
ECA_NOSEARCHADDR = 392
ECA_NOCONVERT = 400
ECA_BADCHID = 410
ECA_BADFUNCPTR = 418
ECA_ISATTACHED = 424
ECA_UNAVAILINSERV = 432
ECA_CHANDESTROY = 440
ECA_BADPRIORITY = 450
ECA_NOTTHREADED = 458
ECA_16KARRAYCLIENT = 464
ECA_CONNSEQTMO = 472
ECA_UNRESPTMO = 480


# -----------------------------------------------------------------------------
#   Function wrappers.
#   Wrappers for callbacks from C back into Python.


# Event handler for ca_array_get_callback, ca_array_put_callback,
# ca_create_subscription.  The event handler is called when the action
# completes or the data is available.
class event_handler_args(ctypes.Structure):
    _fields_ = [
        ('usr', ctypes.py_object),      # Associated private data
        ('chid', ctypes.c_int),         # Channel ID for this request
        ('type', ctypes.c_int),         # DBR type of data returned
        ('count', ctypes.c_int),        # Number of data points returned
        ('raw_dbr', ctypes.c_void_p),   # Pointer to raw dbr array
        ('status', ctypes.c_int)]       # ECA_ status code of operation
event_handler = ctypes.CFUNCTYPE(None, event_handler_args)
    

# Exception handler, called to report asynchronous errors that have no other
# report path.
class exception_handler_args(ctypes.Structure):
    _fields_ = [
        ('usr', ctypes.c_void_p),       # Associated private data
        ('chid', ctypes.c_void_p),      # Channel ID or NULL
        ('type', ctypes.c_int),         # Data type requested
        ('count', ctypes.c_int),        # Number of data points requested
        ('addr', ctypes.c_void_p),      # User address for GET operation
        ('stat', ctypes.c_int),         # Channel access status code
        ('op',  ctypes.c_int),          # CA_OP_ operation code
        ('ctx', ctypes.c_char_p),       # Context information string
        ('pFile', ctypes.c_char_p),     # Location in source: file name
        ('lineNo', ctypes.c_int)]       #             ... and line number
exception_handler = ctypes.CFUNCTYPE(None, exception_handler_args)


# Connection handler, used to report channel connection status.
class ca_connection_handler_args(ctypes.Structure):
    _fields_ = [
        ('chid', ctypes.c_void_p),
        ('op', ctypes.c_int)]
connection_handler = ctypes.CFUNCTYPE(None, ca_connection_handler_args)


# File descriptor handler for handling select.  Called as
#   handler(context, fd, opened)
#       context     Caller's context
#       fd          File handler being added or removed
#       opened      True => new file added, False => file being deleted
# This mirrors the CAFDHANDLER type and is passed to ca_add_fd_registration.
fd_handler = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_int, ctypes.c_int)



# -----------------------------------------------------------------------------
#   Exception handling support
#   The following defines exceptions associated with libca errors together
# with error handling wrappers to detect the errors and raise the appropriate
# exceptions.


class Disconnected(Exception):
    '''The channel is disconnected.'''
    def __init__(self, chid):
        self.chid = chid
    def __str__(self):
        return 'Channel %s disconnected' % ca_name(self.chid)


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
    if status == ECA_DISCONN:
        # Raise a separate exception for disconnection, as we often want to
        # handle this case specially.
        raise Disconnected
    elif status != ECA_NORMAL:
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
ca_message.restype = ctypes.c_char_p


#   @exception_handler
#   def handler(args): ...
#
#   ca_add_exception_event(handler, context)
#
# Adds global exception handler: called for all asynchronous errors.
ca_add_exception_event = libca.ca_add_exception_event
ca_add_exception_event.errcheck = expect_ECA_NORMAL


#   @fd_handler
#   def handler(context, fd, connected): ...
#
#   ca_add_fd_registration(handler, context)
#
# Adds function to be called when files are created or deleted.
ca_add_fd_registration = libca.ca_add_fd_registration
ca_add_fd_registration.errcheck = expect_ECA_NORMAL


#   name = ca_name(channel_id)
#
# Returns the name associated with the given channel id.
ca_name = libca.ca_name
ca_name.restype = ctypes.c_char_p


#   state = ca_state(channel_id)
#
# Returns the state of the given channel, one of the following values:
cs_never_conn = 0           # IOC not found
cs_prev_conn  = 1           # IOC found but now disconnected
cs_conn       = 2           # IOC connected
cs_closed     = 3           # Channel deleted by user
ca_state = libca.ca_state


#   chtype = ca_field_type(channel_id)
#
# Returns the native data type (a dbf_ code) of the data associated with the
# channel, or returns TYPENOTCONN if the channel is not connected.
TYPENOTCONN = -1
ca_field_type = libca.ca_field_type
ca_field_type.errcheck = expect_connected(TYPENOTCONN)


#   count = ca_element_count(channel_id)
#
# Returns the array element count for the data array associated with the
# channel.  Returns 0 if the channel is not connected.
ca_element_count = libca.ca_element_count
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
ca_create_channel.errcheck = expect_ECA_NORMAL


#   status = ca_clear_channel(channel_id)
#
# Closes the given channel.
ca_clear_channel = libca.ca_clear_channel
ca_clear_channel.errcheck = expect_ECA_NORMAL


#   puser = ca_puser(channel_id)
#
# Returns the private user context associated with the channel.
ca_puser = libca.ca_puser
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
ca_array_put_callback.errcheck = expect_ECA_NORMAL


#   ca_array_put(channel_type, count, channel_id, value)
#
# Writes data to the given channel, returning immediately.  There may be no
# notification if this fails.
ca_array_put = libca.ca_array_put
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
ca_create_subscription.errcheck = expect_ECA_NORMAL


#   ca_clear_subscription(event_id)
#
# Cancels a previously established subscription using the returned event_id.
ca_clear_subscription = libca.ca_clear_subscription
ca_clear_subscription.errcheck = expect_ECA_NORMAL


#   ca_context_create(enable_preemptive_callback)
#
# To be called on initialisation, specifying whether asynchronous callbacks
# are to be enabled.
ca_context_create = libca.ca_context_create
ca_context_create.errcheck = expect_ECA_NORMAL


#   context = ca_current_context()
#
# Returns the channel access context or NULL.
ca_current_context = libca.ca_current_context
ca_current_context.restype = ctypes.c_void_p


#   status = ca_attach_context(context)
#
# Attach this thread to the given context.
ca_attach_context = libca.ca_attach_context


#   ca_context_destroy()
#
# To be called at exit.
ca_context_destroy = libca.ca_context_destroy


#   status = ca_pend_event(timeout)
#
# Flushes the send buffer and processes background activities until the
# specified timeout (in seconds) expires.
ca_pend_event = libca.ca_pend_event
ca_pend_event.argtypes = [ctypes.c_double]


#   status = ca_flush_io()
#
# Flushes all requests to server, but returns immediately without processing
# incoming data.
ca_flush_io = libca.ca_flush_io

