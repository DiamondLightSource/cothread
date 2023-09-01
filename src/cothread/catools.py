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

'''Pure Python ctypes interface to EPICS libca Channel Access library

Supports the following methods:

    caget(pvs, ...)
        Returns a single snapshot of the current value of each PV.

    caput(pvs, values, ...)
        Writes values to one or more PVs.

    camonitor(pvs, callback, ...)
        Receive notification each time any of the listed PVs changes.

    connect(pvs, ...)
        Can be used to establish PV connection before using the PV.

See the documentation for the individual functions for more details on using
them.'''

from __future__ import print_function

import os
import sys
import atexit
import traceback
import ctypes
import threading

from . import cothread
from . import cadef
from . import dbr
from . import py23

from .dbr import *
from .cadef import *

__all__ = [
    # The core functions.
    'caput',            # Write PVs to channel access
    'caget',            # Read PVs from channel access
    'camonitor',        # Monitor PVs over channel access
    'connect',          # Establish PV connection
    'cainfo',           # Returns ca_info describing PV connection
] + dbr.__all__ + cadef.__all__


def _check_env(name, default):
    '''For stacks that are created at startup we allow the stack size to be
    specified in an environment variable for overriding the default.'''
    return int(os.environ.get(name, default))

# Stack size definitions
K = 1024

# Miscellaneous channel access operations are created using this stack size.  By
# default we use the shared stack to avoid accidents.
CA_ACTION_STACK         = _check_env('CATOOLS_ACTION_STACK', 0)


if sys.version_info < (3,):
    pv_string_types = (str, unicode)
else:
    pv_string_types = str


class ca_nothing(Exception):
    '''This value is returned as a success or failure indicator from caput,
    as a failure indicator from caget, and may be raised as an exception to
    report a data error on caget or caput with wait.'''

    def __init__(self, name, errorcode = cadef.ECA_NORMAL):
        '''Initialise with PV name and associated errorcode.'''
        self.ok = errorcode == cadef.ECA_NORMAL
        self.name = name
        self.errorcode = errorcode

    def __repr__(self):
        return 'ca_nothing(%r, %d)' % (self.name, self.errorcode)

    def __str__(self):
        return '%s: %s' % (self.name, cadef.ca_message(self.errorcode))

    def __bool__(self):
        return self.ok
    __nonzero__ = __bool__   # For python 2

    def __iter__(self):
        '''This is *not* supposed to be an iterable object, but the base class
        appears to have a different opinion.  So enforce this.'''
        raise TypeError('iteration over non-sequence')


def maybe_throw(function):
    '''Function decorator for optionally catching exceptions.  Exceptions
    raised by the wrapped function are normally propagated unchanged, but if
    throw=False is specified as a keyword argument then the exception is
    transformed into an ordinary ca_nothing value!'''

    def throw_wrapper(pv, *args, **kargs):
        if kargs.pop('throw', True):
            return function(pv, *args, **kargs)
        else:
            # We catch all the expected exceptions, converting them into
            # ca_nothing() objects as appropriate.  Any unexpected exceptions
            # will be raised anyway, which seems fair enough!
            try:
                return function(pv, *args, **kargs)
            except ca_nothing as error:
                return error
            except cadef.CAException as error:
                return ca_nothing(pv, error.status)
            except cadef.Disconnected:
                return ca_nothing(pv, cadef.ECA_DISCONN)

    # Make sure the wrapped function looks like its original self.
    throw_wrapper.__name__ = function.__name__
    throw_wrapper.__doc__ = function.__doc__

    return throw_wrapper


def ca_timeout(event, timeout, name):
    '''Converts an ordinary cothread timeout into a more informative
    ca_nothing timeout exception containing the PV name.'''
    try:
        return event.Wait(timeout)
    except cothread.Timedout as timeout:
        py23.raise_from(ca_nothing(name, cadef.ECA_TIMEOUT), timeout)


# ----------------------------------------------------------------------------
#   Channel object and cache


class Channel(object):
    '''Wraps a single channel access channel object.'''
    __slots__ = [
        'name',
        '__subscriptions',  # Set of listening subscriptions
        '__connected',      # Status of channel connection
        '__connect_event',  # Connection event used to notify changes
        '_as_parameter_'    # Associated channel access channel handle
    ]

    @cadef.connection_handler
    def on_ca_connect(args):
        '''This routine is called every time the connection status of the
        channel changes.  This is called directly from channel access, which
        means that user callbacks should not be called directly.'''

        self = cadef.ca_puser(args.chid)
        op = args.op
        cothread.Callback(self.on_ca_connect_, op)

    def on_ca_connect_(self, op):
        assert op in [cadef.CA_OP_CONN_UP, cadef.CA_OP_CONN_DOWN]
        connected = op == cadef.CA_OP_CONN_UP

        self.__connected = connected
        if connected:
            # Trigger wakeup of all listeners
            self.__connect_event.Signal()

        # Inform all the connected subscriptions
        for subscription in self.__subscriptions:
            subscription._on_connect(connected)

    def __init__(self, name):
        '''Creates a channel access channel with the given name.'''
        self.name = name
        self.__subscriptions = set()
        self.__connected = False
        self.__connect_event = cothread.Pulse()

        chid = ctypes.c_void_p()
        cadef.ca_create_channel(
            name, self.on_ca_connect, ctypes.py_object(self),
            0, ctypes.byref(chid))
        # Setting this allows a channel object to autoconvert into the chid
        # when passed to ca_ functions.
        self._as_parameter_ = chid.value
        _flush_io()

    def __del__(self):
        '''Ensures the associated channel access is closed.'''
        # Note that Channel objects are normally only deleted on process
        # shutdown, so perhaps this call is redundant.
        if hasattr(self, '_as_parameter_'):
            cadef.ca_clear_channel(self)

    def _purge(self):
        '''Forcible purge of channel.  As well as closing the channels,
        ensures that all subscriptions attached to the channel are also
        closed.'''
        for subscription in list(self.__subscriptions):
            subscription.close()
        cadef.ca_clear_channel(self)
        del self._as_parameter_

    def _add_subscription(self, subscription):
        '''Adds the given subscription to the list of receivers of connection
        notification.'''
        self.__subscriptions.add(subscription)

    def _remove_subscription(self, subscription):
        '''Removes the given subscription from the list of receivers.'''
        self.__subscriptions.remove(subscription)

    def Wait(self, timeout = None):
        '''Waits for the channel to become connected if not already connected.
        Raises a Timeout exception if the timeout expires first.'''
        timeout = cothread.AbsTimeout(timeout)
        while not self.__connected:
            ca_timeout(self.__connect_event, timeout, self.name)

    def WakeableWait(self, timeout):
        '''Waits for channel to connect or any event.  Returns True if channel
        is connected, raises Timedout exception on timeout.'''
        if not self.__connected:
            self.__connect_event.Wait(timeout)
        return self.__connected

    def Wakeup(self):
        self.__connect_event.Signal()


class ChannelCache(object):
    '''A cache of all open channels.  If a channel is not present in the
    cache it is automatically opened.  The cache needs to be purged to
    ensure a clean shutdown.'''

    def __init__(self):
        self.__channels = {}

    def __getitem__(self, name):
        try:
            # When the channel already exists, just return that
            return self.__channels[name]
        except KeyError:
            # Have to create a new channel
            channel = Channel(name)
            self.__channels[name] = channel
            return channel

    def purge(self):
        '''Purges all the channels in the cache: closes them right now.  Will
        cause other channel access to fail, so only to be done on shutdown.'''
        for channel in self.__channels.values():
            channel._purge()
        self.__channels = {}



# ----------------------------------------------------------------------------
#   camonitor


class _Subscription(object):
    '''A _Subscription object wraps a single channel access subscription, and
    notifies all updates through an event queue.'''
    __slots__ = [
        'name',             # Name of the PV subscribed to
        'callback',         # The user callback function
        'dbr_to_value',     # Conversion from dbr
        'channel',          # The associated channel object
        '__state',          # Whether the subscription is active
        '_as_parameter_',   # Associated channel access subscription handle
        'all_updates',      # True iff all updates delivered without merging
        'notify_disconnect', # Whether to report disconnect events
        '__value',          # Most recent update if merging updates
        '__update_count',   # Number of updates seen since last notification
    ]

    # _Subscription state values:
    __OPENING = 0       # Subscription not complete yet
    __OPEN    = 1       # Normally active
    __CLOSED  = 2       # Closed but not yet deleted

    # Mapping from format to event mask for default events
    __default_events = {
        FORMAT_RAW:  DBE_VALUE,
        FORMAT_TIME: DBE_VALUE | DBE_ALARM,
        FORMAT_CTRL: DBE_VALUE | DBE_ALARM | DBE_PROPERTY }

    __lock = threading.Lock()   # Used for update merging.

    # Create our own callback queue so that camonitor() callbacks can be handled
    # concurrently with other asynchronous callbacks.
    __Callback = cothread._Callback()

    @cadef.event_handler
    def __on_event(args):
        '''This is called each time the subscribed value changes.  As this is
        called asynchronously, a signal must be queued for later dispatching
        to the monitoring user.'''
        self = args.usr

        if args.status == cadef.ECA_NORMAL:
            # Good data: extract value from the dbr.  Note that this can fail,
            # for example if there is malformed UTF-8 in the result.
            try:
                value = self.dbr_to_value(args.raw_dbr, args.type, args.count)
            except:
                # If there is an error, bypass update merging and force this
                # exception tuple into the processing chain.
                self.__Callback(self.__signal, sys.exc_info())
                return
        elif self.notify_disconnect:
            # Something is wrong: let the subscriber know, if they've requested
            # disconnect nofication.
            value = ca_nothing(self.name, args.status)
        else:
            return
        self.__maybe_signal(value)

    def __maybe_signal(self, value):
        '''Performs update merging and callback notification if appropriate.'''
        if self.all_updates:
            value.update_count = 1
            self.__Callback(self.__signal, value)
        else:
            with self.__lock:
                self.__value = value
                if self.__update_count == 0:
                    self.__Callback(self.__signal, None)
                self.__update_count += 1

    def __signal(self, value):
        '''Wrapper for performing callbacks safely: only performs the callback
        if the subscription is open and reports and handles any exceptions that
        might arise.'''
        if self.__state != self.__CLOSED:
            if value is None:
                # This arises from a merged update.
                with self.__lock:
                    value = self.__value
                    value.update_count = self.__update_count
                    self.__value = None
                    self.__update_count = 0

            try:
                if isinstance(value, tuple):
                    # This should only happen if the asynchronous callback
                    # caught an exception for us to re-raise here.
                    py23.raise_with_traceback(value)
                else:
                    self.callback(value)
            except:
                # We try and be robust about exceptions in handlers, but to
                # prevent a perpetual storm of exceptions, we close the
                # subscription after reporting the problem.
                print('Subscription %s callback raised exception' % self.name,
                    file = sys.stderr)
                traceback.print_exc()
                print('Subscription %s closed' % self.name, file = sys.stderr)
                self.close()

    def _on_connect(self, connected):
        '''This is called each time the connection state of the underlying
        channel changes.  Note that this is also called asynchronously.'''
        if not connected and self.notify_disconnect:
            # Channel has become disconnected: tell the subscriber.
            self.__maybe_signal(ca_nothing(self.name, cadef.ECA_DISCONN))

    def close(self):
        '''Closes the subscription and releases any associated resources.
        Note that no further callbacks will occur on a closed subscription,
        not even callbacks currently queued for execution.'''
        if self.__state == self.__OPENING:
            self.channel.Wakeup()   # Wakes up __wait_for_channel() below
        elif self.__state == self.__OPEN:
            self.channel._remove_subscription(self)
            cadef.ca_clear_subscription(self)
            _flush_io()

        # Delete the callback to avoid possible circular references.
        self.callback = None
        self.__state = self.__CLOSED

        # Horrid hack to ensure self continues to exist for a short time: this
        # will prevent callbacks raised before it was closed being mis-processed
        # when they arrive by a recycled area of memory.  This will be fixed
        # after EPICS 3.14.12.3.
        cothread.Spawn(self.__delete)

    def __delete(self):
        cothread.Sleep(0.1)


    def __init__(self, name, callback,
            events = None,
            datatype = None, format = FORMAT_RAW, count = 0,
            all_updates = False, notify_disconnect = False,
            connect_timeout = None):
        '''Subscription initialisation.'''

        self.name = name
        self.callback = callback
        self.all_updates = all_updates
        self.notify_disconnect = notify_disconnect
        self.__update_count = 0

        # If events not specified then compute appropriate default corresponding
        # to the requested format.
        if events is None:
            events = self.__default_events[format]

        # Trigger channel connection if channel not already known.
        self.channel = _channel_cache[name]

        # Spawn the actual task of creating the subscription into the
        # background, as we may have to wait for the channel to become
        # connected.
        self.__state = self.__OPENING
        cothread.Spawn(self.__create_subscription,
            events, datatype, format, count, connect_timeout,
            stack_size = CA_ACTION_STACK)

    # Waiting for the channel is a bit more tangled than it might otherwise be
    # so that we can handle the subscription being closed before the connection
    # completes.  Alas, the implementation here is horribly entangled with the
    # Channel implementation
    def __wait_for_channel(self, timeout):
        timeout = cothread.AbsTimeout(timeout)
        while self.__state == self.__OPENING:
            try:
                if self.channel.WakeableWait(timeout):
                    return self.__state == self.__OPENING
            except cothread.Timedout:
                # Connection timeout.  Let the caller know and now just block
                # until we connect (if ever).  Note that in this case the caller
                # is notified even if notify_disconnect=False is set.
                self.__maybe_signal(ca_nothing(self.name, cadef.ECA_DISCONN))
                timeout = None
        return False

    def __create_subscription(self,
            events, datatype, format, count, connect_timeout):
        '''Creates the channel subscription with the specified parameters:
        event mask, datatype and format, array count.  Waits for the channel
        to become connected.'''

        # Need to first wait for the channel to connect before we can do
        # anything else.  If this fails then there's nothing more to do.
        if not self.__wait_for_channel(connect_timeout):
            return

        self.__state = self.__OPEN

        # Treat a negative count as a request for the complete data
        if count < 0:
            count = cadef.ca_element_count(self.channel)

        # Connect to the channel to be kept informed of connection updates.
        self.channel._add_subscription(self)
        # Convert the datatype request into the subscription datatype.
        dbrcode, self.dbr_to_value = \
            dbr.type_to_dbr(self.channel, datatype, format)

        # Finally create the subscription with all the requested properties
        # and hang onto the returned event id as our implicit ctypes
        # parameter.
        event_id = ctypes.c_void_p()
        cadef.ca_create_subscription(
            dbrcode, count, self.channel, events,
            self.__on_event, ctypes.py_object(self), ctypes.byref(event_id))
        _flush_io()
        self._as_parameter_ = event_id.value


def camonitor(pvs, callback, **kargs):
    '''camonitor(pvs, callback,
        events = None,
        datatype = None, format = FORMAT_RAW, count = 0,
        all_updates = False, notify_disconnect = False,
        connect_timeout = None)

    Creates a subscription to one or more PVs, returning a subscription
    object for each PV.  If a single PV is given then a single subscription
    object is returned, otherwise a list of subscriptions is returned.

    Subscriptions will remain active until the close() method is called on
    the returned subscription object.

    The precise way in which the callback routine is called on updates
    depends on whether pvs is a single name or a list of names.  If it is
    single name then it is called as

        callback(value)

    for each update.  If pvs is a list of names then each update is
    reported as

        callback(value, index)

    where index is the position in the original array of pvs of the name
    generating this update.

    Every value has .name and .ok fields: if the channel has disconnected
    then .ok will be False, otherwise the value is an augmented
    representation of the updated value; for more detail on values see the
    documentation for caget.

    The parameters modify the behaviour as follows:

    events
        This identifies the type of update which will be notified.  A
        bit-wise or of any the following are possible:

        DBE_VALUE       Notify normal value changes
        DBE_LOG         Notify archive value changes
        DBE_ALARM       Notify alarm state changes
        DBE_PROPERTY    Notify property changes

        The default mask selected for events depends on the requested format.

    datatype
    format
    count
        These all specify the format in which data is returned.  See the
        documentation for caget for details.

    all_updates
        If this is True then every update received from channel access will
        be delivered to the callback, otherwise multiple updates received
        between callback queue dispatches will be merged into the most recent
        value.
            If updates are being merged then the value returned will be
        augmented with a field .update_count recording how many updates
        occurred on this value.

    notify_disconnect
        If this is True then IOC disconnect events will be reported by
        calling the callback with a ca_nothing error with .ok False,
        otherwise only valid values will be passed to the callback routine.

    connect_timeout
        If a connection timeout is specified then the camonitor will report a
        disconnection event after the specified interval if connection has not
        completed by this time.  Note that this notification will be made even
        if notify_disconnect is False, and that if the PV subsequently connects
        it will update as normal.
    '''
    if isinstance(pvs, pv_string_types):
        return _Subscription(pvs, callback, **kargs)
    else:
        return [
            _Subscription(pv, lambda v, n=n: callback(v, n), **kargs)
            for n, pv in enumerate(pvs)]


# ----------------------------------------------------------------------------
#   caget


@cadef.event_handler
def _caget_event_handler(args):
    '''This will be called when a caget request completes, either with a
    brand new data value or with failure.  The result is communicated back
    to the original caller.'''

    # We are called exactly once, so can consume the context right now.  Note
    # that we have to do some manual reference counting on the user context,
    # as this is a python object that is invisible to the C api.
    pv, dbr_to_value, done = args.usr
    ctypes.pythonapi.Py_DecRef(args.usr)

    if args.status == cadef.ECA_NORMAL:
        try:
            value = dbr_to_value(args.raw_dbr, args.type, args.count)
        except:
            cothread.Callback(done.SignalException, sys.exc_info()[1])
        else:
            cothread.Callback(done.Signal, value)
    else:
        cothread.Callback(done.SignalException, ca_nothing(pv, args.status))


@maybe_throw
def caget_one(pv, timeout=5, datatype=None, format=FORMAT_RAW, count=0):
    '''Retrieves a value from a single PV in the requested format.  Blocks
    until the request is complete, raises an exception if any problems
    occur.'''

    # Start by converting the timeout into an absolute timeout.  This allows
    # us to do repeated timeouts without actually extending the timeout
    # deadline.
    timeout = cothread.AbsTimeout(timeout)
    # Retrieve the requested channel and ensure it's connected.
    channel = _channel_cache[pv]
    channel.Wait(timeout)

    # A count of zero will be treated by EPICS in a version dependent manner,
    # either returning the entire waveform (equivalent to count=-1) or a data
    # dependent waveform length.
    if count < 0:
        # Treat negative count request as request for fixed underlying channel
        # size.
        count = cadef.ca_element_count(channel)
    elif count > 0:
        # Need to ensure we don't ask for more than the channel can provide as
        # otherwise may get API error.
        count = min(count, cadef.ca_element_count(channel))

    # Assemble the callback context.  Note that we need to explicitly
    # increment the reference count so that the context survives until the
    # callback routine gets to see it.
    dbrcode, dbr_to_value = dbr.type_to_dbr(channel, datatype, format)
    done = cothread.Event()
    context = (pv, dbr_to_value, done)
    ctypes.pythonapi.Py_IncRef(context)

    # Perform the actual put as a non-blocking operation: we wait to be
    # informed of completion, or time out.
    cadef.ca_array_get_callback(
        dbrcode, count, channel,
        _caget_event_handler, ctypes.py_object(context))
    _flush_io()
    return ca_timeout(done, timeout, pv)


def caget_array(pvs, **kargs):
    # Spawn a separate caget task for each pv: this allows them to complete
    # in parallel which can speed things up considerably.
    #    The raise_on_wait flag means that any exceptions raised by any of
    # the spawned caget_one() calls will appear as exceptions to WaitForAll().
    return cothread.WaitForAll([
        cothread.Spawn(
            caget_one, pv, raise_on_wait = True,
            stack_size = CA_ACTION_STACK, **kargs)
        for pv in pvs])


def caget(pvs, **kargs):
    '''caget(pvs,
        timeout = 5, datatype = None,
        format = FORMAT_RAW, count = 0, throw = True)

    Retrieves the value from one or more PVs.  If a single PV is given then
    a single value is returned, otherwise a list of values is returned.

    Every value returned has the following fields:

        .ok     Set to True if the data is good, False if there was an error
                (and throw=False has been selected).

        .name   Name of the pv.

    If ok is False then the .errorcode field is set to the appropriate ECA_
    error code and str(value) will return an appropriate error message.

    The various arguments control the behaviour of caget as follows:

    timeout
        Timeout for the caget operation.  This can be a timeout interval
        in seconds, an absolute deadline (in time() format) as a single
        element tuple, or None to specify that no timeout will occur.  Note
        that a timeout of 0 will timeout immediately if any waiting is
        required.

    datatype
        This controls the format of the data that will be requested.  This
        can be any of the following:

        1.  None (the default).  In this case the "native" datatype provided
            by the channel will be returned.

        2.  A DBR_ value, one of DBR_STRING, DBR_SHORT, DBR_FLOAT, DBR_ENUM,
            DBR_CHAR, DBR_LONG or DBR_DOUBLE.

        3.  A python type compatible with any of the above values, such as
            int, float or str.

        4.  Any numpy dtype compatible with any of the above values.

        5.  The special value DBR_CHAR_STR.  This is used to request a char
            array which is then converted to a Python string on receipt.  It
            is not sensible to specify count with this option.

        6.  One of the special values DBR_STSACK_STRING or DBR_CLASS_NAME.

    format
        This controls how much auxilliary information will be returned with
        the retrieved data, and can be one of the following:

        FORMAT_RAW
            The data is returned unaugmented except for the .name field.

        FORMAT_TIME
            The data is augmented by the data timestamp together with
            .alarm .status and .severity fields.

        FORMAT_CTRL
            The data is augmented by channel access "control" fields.  This
            set of fields depends on the underlying datatype:

            DBR_SHORT, DBR_CHAR, DBR_LONG
                The alarm .status and .severity fields together with .units
                and limit fields:
                .upper_disp_limit, .lower_disp_limit,
                .upper_alarm_limit, .lower_alarm_limit,
                .upper_warning_limit, .lower_warning_limit,
                .upper_ctrl_limit, .lower_ctrl_limit.

            DBR_FLOAT, DBR_DOUBLE
                As above together with a .precision field.

            DBR_ENUM
                Alarm .status and .severity fields together with .enums, a
                list of possible enumeration strings.

            DBR_STRING
                _CTRL format is not supported for this field type, and
                FORMAT_TIME data is returned instead.

    count
        If specified this can be used to limit the number of waveform values
        retrieved from the server.  The default value of 0 requests server and
        data dependent waveform length, while a value of -1 requests the full
        data length.

    throw
        Normally an exception will be raised if the channel cannot be
        connected to or if there is a data error.  If this is set to False
        then instead for each failing PV an empty value with .ok == False is
        returned.

    The format of values returned depends on the number of values requested
    for each PV.  If only one value is requested then the value is returned
    as a scalar, otherwise as a numpy array.'''
    if isinstance(pvs, pv_string_types):
        return caget_one(pvs, **kargs)
    else:
        return caget_array(pvs, **kargs)



# ----------------------------------------------------------------------------
#   caput

@cadef.event_handler
def _caput_event_handler(args):
    '''Event handler for caput with callback completion.  Returns status
    code to caller.'''

    # This is called exactly once when a caput request completes.  Extract
    # our context information and discard the context immediately.
    pv, done, callback = args.usr
    ctypes.pythonapi.Py_DecRef(args.usr)

    if done is not None:
        if args.status == cadef.ECA_NORMAL:
            cothread.Callback(done.Signal)
        else:
            cothread.Callback(done.SignalException, ca_nothing(pv, args.status))
    if callback is not None:
        cothread.Callback(callback, ca_nothing(pv, args.status))


@maybe_throw
def caput_one(pv, value, datatype=None, wait=False, timeout=5, callback=None):
    '''Writes a value to a single pv, waiting for callback on completion if
    requested.'''

    # Connect to the channel and wait for connection to complete.
    timeout = cothread.AbsTimeout(timeout)
    channel = _channel_cache[pv]
    channel.Wait(timeout)

    # Note: the unused value returned below needs to be retained so that
    # dbr_array, a pointer to C memory, has the right lifetime: it has to
    # survive until ca_array_put[_callback] has been called.
    dbrtype, count, dbr_array, value = \
        dbr.value_to_dbr(channel, datatype, value)
    if wait or callback is not None:
        # Assemble the callback context and give it an extra reference count
        # to keep it alive until the callback handler sees it.
        if wait:
            done = cothread.Event()
        else:
            done = None
        context = (pv, done, callback)
        ctypes.pythonapi.Py_IncRef(context)

        # caput with callback requested: need to wait for response from
        # server before returning.
        cadef.ca_array_put_callback(
            dbrtype, count, channel, dbr_array,
            _caput_event_handler, ctypes.py_object(context))
        _flush_io()
        if wait:
            ca_timeout(done, timeout, pv)
    else:
        # Asynchronous caput, just do it now.
        cadef.ca_array_put(dbrtype, count, channel, dbr_array)
        _flush_io()

    # Return a success code for compatibility with throw=False code.
    return ca_nothing(pv)


def caput_array(pvs, values, repeat_value=False, **kargs):
    # Bring the arrays of pvs and values into alignment.
    if repeat_value or isinstance(values, pv_string_types):
        # If repeat_value is requested or the value is a string then we treat
        # it as a single value.
        values = [values] * len(pvs)
    else:
        try:
            values = list(values)
        except TypeError:
            # If the value can't be treated as a list then again we treat it
            # as a single value
            values = [values] * len(pvs)
    assert len(pvs) == len(values), 'PV and value lists must match in length'

    return cothread.WaitForAll([
        cothread.Spawn(
            caput_one, pv, value, raise_on_wait = True,
            stack_size = CA_ACTION_STACK, **kargs)
        for pv, value in zip(pvs, values)])


def caput(pvs, values, **kargs):
    '''caput(pvs, values,
        repeat_value = False, datatype = None, wait = False, callback = None,
        timeout = 5, throw = True)

    Writes values to one or more PVs.  If multiple PVs are given together
    with multiple values then both lists or arrays should match in length,
    and values[i] is written to pvs[i].  Otherwise, if a single value is
    given or if repeat_value=True is specified, the same value is written
    to all PVs.

    The arguments control the behavour of caput as follows:

    repeat_value
        When writing an array value to an array of PVs ensures that the
        same array of values is written to each PV.  Otherwise this flag
        can be ignored.

    timeout
        Timeout for the caput operation.  This can be a timeout interval
        in seconds, an absolute deadline (in time() format) as a single
        element tuple, or None to specify that no timeout will occur.  Note
        that a timeout of 0 will timeout immediately if any waiting is
        required.

    wait, callback
        If wait=True or a callback is specified then channel access put with
        callback is invoked.  If wait is True then the caput operation will wait
        until the server acknowledges successful completion before returning, if
        callback is set then callback(status) is called, where status has fields
        .ok and .name.  Both wait and callback can be set.

    datatype
        If a datatype is specified then the values being written will be
        coerced to the specified datatype before been transmitted.  As well
        as standard datatypes (see caget), DBR_PUT_ACKT or DBR_PUT_ACKS can
        be specified.

    throw
        Normally an exception will be raised if the channel cannot be
        connected to or if an error is reported.  If this is set to False
        then instead for each failing PV a sentinel value with .ok == False
        is returned.

    The return value for each PV is a structure with two fields: .ok and
    .name, and possibly a third field .errorcode.  If multiple PVs are
    specified then a list of values is returned.

    If caput completed succesfully then .ok is True and .name is the
    corresponding PV name.  If throw=False was specified and a put failed
    then .errorcode is set to the appropriate ECA_ error code.'''
    if isinstance(pvs, pv_string_types):
        return caput_one(pvs, values, **kargs)
    else:
        return caput_array(pvs, values, **kargs)



# ----------------------------------------------------------------------------
#   connect

class ca_info(object):
    state_strings = [
        'never connected', 'previously connected', 'connected', 'closed']
    datatype_strings = [
        'string', 'short', 'float', 'enum', 'char', 'long', 'double',
        'no access']

    def __init__(self, pv, channel):
        self.ok = True
        self.name = pv
        self.state = cadef.ca_state(channel)
        self.host  = cadef.ca_host_name(channel)
        self.read  = cadef.ca_read_access(channel)
        self.write = cadef.ca_write_access(channel)
        if self.state == cadef.cs_conn:
            self.count    = cadef.ca_element_count(channel)
            self.datatype = cadef.ca_field_type(channel)
        else:
            self.count = 0
            self.datatype = 7       # DBF_NO_ACCESS

    def __str__(self):
        return '''%s:
    State: %s
    Host: %s
    Access: %s, %s
    Data type: %s
    Count: %d''' % (
        self.name, self.state_strings[self.state], self.host,
        self.read, self.write, self.datatype_strings[self.datatype],
        self.count)


@maybe_throw
def connect_one(pv, cainfo = False, wait = True, timeout = 5):
    channel = _channel_cache[pv]
    if wait:
        channel.Wait(timeout)
    if cainfo:
        return ca_info(pv, channel)
    else:
        return ca_nothing(pv)


def connect_array(pvs, **kargs):
    return cothread.WaitForAll([
        cothread.Spawn(
            connect_one, pv, raise_on_wait = True,
            stack_size = CA_ACTION_STACK, **kargs)
        for pv in pvs])


def connect(pvs, **kargs):
    '''connect(pvs, cainfo=False, wait=True, timeout=5, throw=True)

    Establishes a connection to one or more PVs.  A single PV or a list of PVs
    can be given.  This does not normally need to be called, as the ca...()
    routines will establish their own connections as required, but after a
    successful connection we can guarantee that caput(..., wait=False) will
    complete immediately without suspension.

    This routine can safely be called repeatedly without any extra side
    effects.

    The following arguments affect the behaviour of connect as follows:

    cainfo
        By default a simple ca_nothing value is returned, but if this flag is
        set then a ca_info structure is returned recording the following
        information about the connection:

        .ok         True iff the channel was successfully connected
        .name       Name of PV
        .state      State of channel as an integer.  Look up
                    .state_strings[.state] for textual description.
        .host       Host name and port of server providing this PV
        .read       True iff read access to this PV
        .write      True iff write access to this PV
        .count      Data count of this channel
        .datatype   Underlying channel datatype as DBR_ value.  Look up
                    .datatype_strings[.datatype] for description.

    wait
        Normally the connect routine will not return until the requested
        connection is established.  If wait=False is set then a connection
        request will be queued and connect will unconditionally succeed.

    timeout
        How long to wait for the connection to be established.

    throw
        Normally an exception will be raised if the channel cannot be
        connected to.  If this is set to False then instead for each failing
        PV a sentinel value with .ok == False is returned.
    '''
    if isinstance(pvs, pv_string_types):
        return connect_one(pvs, **kargs)
    else:
        return connect_array(pvs, **kargs)


def cainfo(pvs, **args):
    '''Returns a ca_info structure for the given PVs.  See the documentation
    for connect() for more detail.'''
    return connect(pvs, cainfo = True, wait = True, **args)



# ----------------------------------------------------------------------------
#   Final module initialisation


_channel_cache = ChannelCache()

@atexit.register
def _catools_atexit():
    # On exit we do our best to ensure that channel access shuts down cleanly.
    # We do this by shutting down all channels and clearing the channel access
    # context: this should reduce the risk of unexpected errors during
    # application exit.
    #    One reason that it's rather important to do this properly is that we
    # can't safely do *any* ca_ calls once ca_context_destroy() is called!
    _channel_cache.purge()
    cadef.ca_flush_io()
    cadef.ca_context_destroy()


# EPICS Channel Access event dispatching needs to done with a little care.  In
# previous versions the solution was to repeatedly call ca_pend_event() in
# polling mode, but this does not appear to be efficient enough when receiving
# large amounts of data.  Instead we enable preemptive Channel Access callbacks,
# which means we need to cope with all of our channel access events occuring
# asynchronously.
cadef.ca_context_create(1)

# Another delicacy arising from relying on asynchronous CA event dispatching is
# that we need to manually flush IO events such as caget commands.  To ensure
# that large blocks of channel access activity really are aggregated we ensure
# that ca_flush_io() is only called once in any scheduling cycle by requesting
# IO flushing via a _flush_io_event object.
class _FlushIo:
    def __init__(self):
        self._flush_io_event = cothread.Event()
        cothread.Spawn(self._dispatch_flush_io, stack_size = CA_ACTION_STACK)

    def _dispatch_flush_io(self):
        while True:
            self._flush_io_event.Wait()
            cadef.ca_flush_io()

    def __call__(self):
        '''This should be called after any Channel Access method which generates
        buffered requests.  ca_flush_io() will now be called during the next
        scheduler cycle.'''
        self._flush_io_event.Signal()

_flush_io = _FlushIo()
