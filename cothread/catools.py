# This file is part of the Diamond cothread library.
#
# Copyright (C) 2007 James Rowland, 2007-2008 Michael Abbott,
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

import sys
import atexit
import traceback
import ctypes

import cothread
import cadef
import dbr

from dbr import *
from cadef import *

__all__ = [
    # The core functions.
    'caput',            # Write PVs to channel access
    'caget',            # Read PVs from channel access
    'camonitor',        # Monitor PVs over channel access
    'connect',          # Establish PV connection
] + dbr.__all__ + cadef.__all__



class ca_nothing(Exception):
    '''This value is returned as a success or failure indicator from caput,
    as a failure indicator from caget, and may be raised as an exception to
    report a data error on caget or caput with wait.'''

    def __init__(self, name, errorcode = cadef.ECA_NORMAL):
        '''Initialise with PV name and associated errorcode.'''
        self.ok = errorcode == cadef.ECA_NORMAL
        self.name = name
        self.errorcode = errorcode

    def __str__(self):
        return '%s: %s' % (self.name, cadef.ca_message(self.errorcode))

    def __nonzero__(self):
        return self.ok

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
            except ca_nothing, error:
                return error
            except cadef.CAException, error:
                return ca_nothing(pv, error.status)
            except cadef.Disconnected, error:
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
    except cothread.Timedout:
        raise ca_nothing(name, cadef.ECA_TIMEOUT)


# ----------------------------------------------------------------------------
#   Channel object and cache


class Channel(object):
    '''Wraps a single channel access channel object.'''
    __slots__ = [
        'name',
        '__subscriptions',  # Set of listening subscriptions
        '__connected',      # Event for waiting for channel connection
        '_as_parameter_'    # Associated channel access channel handle
    ]

    @cadef.connection_handler
    def on_ca_connect(args):
        '''This routine is called every time the connection status of the
        channel changes.  This is called directly from channel access, which
        means that user callbacks should not be called directly.'''

        self = cadef.ca_puser(args.chid)
        op = args.op
        assert op in [cadef.CA_OP_CONN_UP, cadef.CA_OP_CONN_DOWN]
        connected = op == cadef.CA_OP_CONN_UP

        if connected:
            self.__connected.Signal()
        else:
            self.__connected.Reset()

        # Inform all the connected subscriptions
        for subscription in self.__subscriptions:
            subscription._on_connect(connected)

    def __init__(self, name):
        '''Creates a channel access channel with the given name.'''
        self.name = name
        self.__subscriptions = set()
        self.__connected = cothread.Event(auto_reset = False)

        chid = ctypes.c_void_p()
        cadef.ca_create_channel(
            name, self.on_ca_connect, ctypes.py_object(self),
            0, ctypes.byref(chid))
        # Setting this allows a channel object to autoconvert into the chid
        # when passed to ca_ functions.
        self._as_parameter_ = chid.value

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
        '''Waits for the channel to become connected.  Raises a Timeout
        exception if the timeout expires first.'''
        ca_timeout(self.__connected, timeout, self.name)


class ChannelCache(object):
    '''A cache of all open channels.  If a channel is not present in the
    cache it is automatically opened.  The cache needs to be purged to
    ensure a clean shutdown.'''
    __slots__ = ['__channels']

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
        'as_string',        # Automatic type conversion of data to strings
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

    @cadef.event_handler
    def __on_event(args):
        '''This is called each time the subscribed value changes.  As this is
        called asynchronously, a signal must be queued for later dispatching
        to the monitoring user.'''
        self = args.usr

        if args.status == cadef.ECA_NORMAL:
            # Good data: extract value from the dbr.
            self.__signal(dbr.dbr_to_value(
                args.raw_dbr, args.type, args.count, self.channel.name,
                self.as_string))
        elif self.notify_disconnect:
            # Something is wrong: let the subscriber know, but only if
            # they've requested disconnect nofication.
            self.__signal(ca_nothing(self.channel.name, args.status))

    def __signal(self, value):
        if self.all_updates:
            # If all_updates is requested then every incoming update directly
            # generates a corresponding callback call.
            value.update_count = 1
            self.__callback_queue.Signal((self, self.callback, value))
        else:
            # If merged updates are requested then we hang onto the latest
            # value and only schedule a callback if there isn't one already
            # in the queue.
            self.__value = value
            if self.__update_count == 0:
                # First update since last reported.
                self.__callback_queue.Signal((
                    self, self.__merged_callback, None))
            self.__update_count += 1

    def _on_connect(self, connected):
        '''This is called each time the connection state of the underlying
        channel changes.  Note that this is also called asynchronously.'''
        if not connected and self.notify_disconnect:
            # Channel has become disconnected: tell the subscriber.
            self.__signal(ca_nothing(self.channel.name, cadef.ECA_DISCONN))

    def __del__(self):
        '''On object deletion ensure that the associated subscription is
        closed.'''
        self.close()

    def close(self):
        '''Closes the subscription and releases any associated resources.
        Note that no further callbacks will occur on a closed subscription,
        not even callbacks currently queued for execution.'''
        if self.__state == self.__OPEN:
            self.channel._remove_subscription(self)
            cadef.ca_clear_subscription(self)
            del self._as_parameter_
            del self.channel
            del self.__value
            del self.callback
        self.__state = self.__CLOSED

    def __init__(self, name, callback,
            events = DBE_VALUE,
            datatype = None, format = FORMAT_RAW, count = 0,
            all_updates = False, notify_disconnect = False):
        '''Subscription initialisation: callback and context are used to
        frame values written to the queue;  events selects which types of
        update are notified;  datatype, format, count and as_string define
        the format of returned data.'''

        self.name = name
        self.callback = callback
        self.as_string = datatype == DBR_CHAR_STR
        self.all_updates = all_updates
        self.notify_disconnect = notify_disconnect
        self.__update_count = 0

        # We connect to the channel so that we can be kept informed of
        # connection updates.
        self.channel = _channel_cache[name]
        self.channel._add_subscription(self)

        # Spawn the actual task of creating the subscription into the
        # background, as we may have to wait for the channel to become
        # connected.
        self.__state = self.__OPENING
        cothread.Spawn(self.__create_subscription,
            events, datatype, format, count)

    def __create_subscription(self, events, datatype, format, count):
        '''Creates the channel subscription with the specified parameters:
        event mask, datatype and format, array count.  Waits for the channel
        to become connected if datatype is not specified (None).'''

        if datatype is None:
            # If no datatype has been specified then try and pick up the
            # datatype associated with the connected channel.
            # First wait for the channel to connect
            self.channel.Wait()
            datatype = cadef.ca_field_type(self.channel)
        # Can now convert the datatype request into the subscription datatype.
        datatype = dbr.type_to_dbr(datatype, format)

        # Finally create the subscription with all the requested properties
        # and hang onto the returned event id as our implicit ctypes
        # parameter.
        if self.__state == self.__OPENING:
            event_id = ctypes.c_void_p()
            cadef.ca_create_subscription(
                datatype, count, self.channel, events,
                self.__on_event, ctypes.py_object(self),
                ctypes.byref(event_id))
            self._as_parameter_ = event_id.value
            self.__state = self.__OPEN


    # By default all subscription events are queued onto this queue which is
    # dispatched by the callback dispatcher in its own thread.
    __callback_queue = cothread.EventQueue()

    @classmethod
    def _callback_dispatcher(cls):
        '''The default event handler expects a callback and a value on
        the queue and simply fires the callback.  This runs as a continous
        background process to dispatch subscription events.'''
        while True:
            self, callback, value = cls.__callback_queue.Wait()
            # Only perform callbacks on open subscriptions.
            if self.__state == self.__OPEN:
                try:
                    callback(value)
                except:
                    # We try and be robust about exceptions in handlers, but
                    # to prevent a perpetual storm of exceptions, we close the
                    # subscription after reporting the problem.
                    print 'Subscription %s callback raised exception' % \
                        self.name
                    traceback.print_exc()
                    print 'Subscription %s closed' % self.name
                    self.close()

    def __merged_callback(self, _):
        '''Called on notification of update when merging multiple updates.
        The user's callback is fired with the latest value.'''
        value = self.__value
        self.__value = None
        value.update_count = self.__update_count
        self.__update_count = 0
        self.callback(value)


# Ensure the callback dispatcher is running.
cothread.Spawn(_Subscription._callback_dispatcher)


def camonitor(pvs, callback, **kargs):
    '''camonitor(pvs, callback,
        events = DBE_VALUE,
        datatype = None, format = FORMAT_RAW, count = 0,
        all_updates = False, notify_disconnect = False)

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
    '''
    if isinstance(pvs, str):
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
    pv, as_string, done = args.usr
    ctypes.pythonapi.Py_DecRef(args.usr)

    if args.status == cadef.ECA_NORMAL:
        done.Signal(dbr.dbr_to_value(
            args.raw_dbr, args.type, args.count, pv, as_string))
    else:
        done.SignalException(ca_nothing(pv, args.status))


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

    # If an element count has been specified, make sure it fits within the
    # channel, otherwise ask for everything by default.
    if count > 0:
        count = min(count, cadef.ca_element_count(channel))

    # If no datatype has been specified, use the channel's default
    if datatype is None:
        datatype = cadef.ca_field_type(channel)

    # Assemble the callback context.  Note that we need to explicitly
    # increment the reference count so that the context survives until the
    # callback routine gets to see it.
    done = cothread.Event()
    context = (pv, datatype == DBR_CHAR_STR, done)
    ctypes.pythonapi.Py_IncRef(context)

    # Perform the actual put as a non-blocking operation: we wait to be
    # informed of completion, or time out.
    cadef.ca_array_get_callback(
        dbr.type_to_dbr(datatype, format), count, channel,
        _caget_event_handler, ctypes.py_object(context))
    return ca_timeout(done, timeout, pv)


def caget_array(pvs, **kargs):
    # Spawn a separate caget task for each pv: this allows them to complete
    # in parallel which can speed things up considerably.
    #    The raise_on_wait flag means that any exceptions raised by any of
    # the spawned caget_one() calls will appear as exceptions to WaitForAll().
    return cothread.WaitForAll([
        cothread.Spawn(caget_one, pv, raise_on_wait = True, **kargs)
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
        retrieved from the server.

    throw
        Normally an exception will be raised if the channel cannot be
        connected to or if there is a data error.  If this is set to False
        then instead for each failing PV an empty value with .ok == False is
        returned.

    The format of values returned depends on the number of values requested
    for each PV.  If only one value is requested then the value is returned
    as a scalar, otherwise as a numpy array.'''
    if isinstance(pvs, str):
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
    pv, done = args.usr
    ctypes.pythonapi.Py_DecRef(args.usr)

    if args.status == cadef.ECA_NORMAL:
        done.Signal()
    else:
        done.SignalException(ca_nothing(pv, args.status))


@maybe_throw
def caput_one(pv, value, datatype=None, wait=False, timeout=5):
    '''Writes a value to a single pv, waiting for callback on completion if
    requested.'''

    # Connect to the channel and wait for connection to complete.
    timeout = cothread.AbsTimeout(timeout)
    channel = _channel_cache[pv]
    channel.Wait(timeout)

    # Note: the unused value returned below needs to be retained so that
    # dbr_array, a pointer to C memory, has the right lifetime: it has to
    # survive until ca_array_put[_callback] has been called.
    dbrtype, count, dbr_array, value = dbr.value_to_dbr(value, datatype)
    if wait:
        # Assemble the callback context and give it an extra reference count
        # to keep it alive until the callback handler sees it.
        done = cothread.Event()
        context = (pv, done)
        ctypes.pythonapi.Py_IncRef(context)

        # caput with callback requested: need to wait for response from
        # server before returning.
        cadef.ca_array_put_callback(
            dbrtype, count, channel, dbr_array,
            _caput_event_handler, ctypes.py_object(context))
        ca_timeout(done, timeout, pv)
    else:
        # Asynchronous caput, just do it now.
        cadef.ca_array_put(dbrtype, count, channel, dbr_array)

    # Return a success code for compatibility with throw=False code.
    return ca_nothing(pv)


def caput_array(pvs, values, repeat_value=False, **kargs):
    # Bring the arrays of pvs and values into alignment.
    if repeat_value or isinstance(values, str):
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
        cothread.Spawn(caput_one, pv, value, raise_on_wait = True, **kargs)
        for pv, value in zip(pvs, values)])


def caput(pvs, values, **kargs):
    '''caput(pvs, values,
        repeat_value = False, datatype = None, wait = False,
        timeout = 5, throw = True)

    Writes values to one or more PVs.  If multiple PVs are given together
    with multiple values then both lists or arrays should match in length,
    and values[i] is written to pvs[i].  Otherwise, if a single value is
    given or if repeat_value=True is specified, the same value is written
    to all PVs.

    The arguments control the behavour of caput as follows:

    repeat_value
        When writing an array value to an array of PVs ensures that the
        same array of values is written to each PV.

    timeout
        Timeout for the caput operation.  This can be a timeout interval
        in seconds, an absolute deadline (in time() format) as a single
        element tuple, or None to specify that no timeout will occur.  Note
        that a timeout of 0 will timeout immediately if any waiting is
        required.

    wait
        If wait=True is specified then channel access put with callback is
        invoked, and the caput operation will wait until the server
        acknowledges successful completion before returning.

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
    if isinstance(pvs, str):
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
        cothread.Spawn(connect_one, pv, raise_on_wait = True, **kargs)
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
    if isinstance(pvs, str):
        return connect_one(pvs, **kargs)
    else:
        return connect_array(pvs, **kargs)



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
    cadef.ca_context_destroy(cadef.ca_current_context())

cadef.ca_context_create(0)


@cothread.Spawn
def _PollChannelAccess():
    while True:
        cadef.ca_pend_event(1e-9)
        cothread.Sleep(1e-2)


# The value of the exception handler below is rather doubtful...
if False:
    @exception_handler
    def catools_exception(args):
        '''print ca exception message'''
        print >> sys.stderr, 'catools_exception:', \
            args.ctx, cadef.ca_message(args.stat)
    cadef.ca_add_exception_event(catools_exception, 0)
