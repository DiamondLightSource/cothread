'''Pure Python ctypes interface to EPICS libca Channel Access library

Supports three methods:

    caget(pvs, ...)
        Returns a single snapshot of the current value of each PV.

    caput(pvs, values, ...)
        Writes values to one or more PVs.

    camonitor(pvs, callback, ...)
        Receive notification each time any of the listed PVs changes.

See the documentation for the individual functions for more details on using
them.'''

import sys
import atexit
import traceback

import cothread
from cadef import *
from dbr import *


__all__ = [
    # The core functions.
    'caput',            # Write PVs to channel access
    'caget',            # Read PVs from channel access
    'camonitor',        # Monitor PVs over channel access

    # Basic DBR request codes: any one of these can be used as part of a
    # datatype request.  
    'DBR_STRING',       # 40 character strings
    'DBR_SHORT',        # 16 bit signed       
    'DBR_FLOAT',        # 32 bit float        
    'DBR_ENUM',         # 16 bit unsigned     
    'DBR_CHAR',         # 8 bit unsigned      
    'DBR_LONG',         # 32 bit signed       
    'DBR_DOUBLE',       # 64 bit float        

    # Data type format requests
    'FORMAT_RAW',       # Request the underlying data only
    'FORMAT_TIME',      # Request alarm status and timestamp
    'FORMAT_CTRL',      # Request graphic and control fields

    # Event type notification codes for camonitor
    'DBE_VALUE',        # Notify normal value changes  
    'DBE_LOG',          # Notify archival value changes
    'DBE_ALARM',        # Notify alarm state changes   
]



class ca_nothing(Exception):
    '''This value is returned as a success indicator from caput, as a failure
    indicator from caget, and may be raised as an exception to report a data
    error on caget or caput with wait.'''
    
    def __init__(self, name, errorcode = ECA_NORMAL):
        '''Initialise with PV name and associated errorcode.'''
        self.ok = errorcode == ECA_NORMAL
        self.name = name
        self.errorcode = errorcode

    def __str__(self):
        return ca_message(self.errorcode)


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
            except CAException, error:
                return ca_nothing(pv, error.status)
            except Disconnected, error:
                return ca_nothing(pv, ECA_DISCONN)
            except cothread.Timedout:
                return ca_nothing(pv, ECA_TIMEOUT)

    # Make sure the wrapped function looks like its original self.
    throw_wrapper.__name__ = function.__name__
    throw_wrapper.__doc__ = function.__doc__

    return throw_wrapper



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
    
    @connection_handler
    def on_ca_connect(args):
        '''This routine is called every time the connection status of the
        channel changes.  This is called directly from channel access, which
        means that user callbacks should not be called directly.'''
        
        self = ca_puser(args.chid)
        op = args.op
        assert op in [CA_OP_CONN_UP, CA_OP_CONN_DOWN]
        connected = op == CA_OP_CONN_UP

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
        ca_create_channel(
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
            ca_clear_channel(self)

    def _purge(self):
        '''Forcible purge of channel.  As well as closing the channels,
        ensures that all subscriptions attached to the channel are also
        closed.'''
        for subscription in list(self.__subscriptions):
            subscription.close()
        ca_clear_channel(self)
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
        self.__connected.Wait(timeout)


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
        'channel',          # The associated channel object
        '__state',          # Whether the subscription is active
        '_as_parameter_',   # Associated channel access subscription handle
        'all_updates',      # True iff all updates delivered without merging
        '__value',          # Most recent update if merging updates
        '__update_count',   # Number of updates seen since last notification
    ]
    
    # _Subscription state values:
    __OPENING = 0       # Subscription not complete yet
    __OPEN    = 1       # Normally active
    __CLOSED  = 2       # Closed but not yet deleted
    
    @event_handler
    def __on_event(args):
        '''This is called each time the subscribed value changes.  As this is
        called asynchronously, a signal must be queued for later dispatching
        to the monitoring user.'''
        self = args.usr

        if args.status == ECA_NORMAL:
            # Good data: extract value from the dbr.
            self.__signal(dbr_to_value(
                args.raw_dbr, args.type, args.count, self.channel.name))
        else:
            # Something is wrong: let the subscriber know
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
        if not connected:
            # Channel has become disconnected: tell the subscriber.
            self.__signal(ca_nothing(self.channel.name, ECA_DISCONN))

    def __del__(self):
        '''On object deletion ensure that the associated subscription is
        closed.'''
        self.close()
        
    def close(self):
        '''Closes the subscription and releases any associated resources.'''
        if self.__state == self.__OPEN:
            self.channel._remove_subscription(self)
            ca_clear_subscription(self)
            del self._as_parameter_
            del self.channel
            del self.__value
            del self.callback
        self.__state = self.__CLOSED

    def __init__(self, name, callback, 
            events = DBE_VALUE,
            datatype = None, format = FORMAT_RAW, count = 0,
            all_updates = False):
        '''Subscription initialisation: callback and context are used to
        frame values written to the queue;  events selects which types of
        update are notified;  datatype, format and count define the format
        of returned data.'''

        self.name = name
        self.callback = callback
        self.all_updates = all_updates
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
            datatype = ca_field_type(self.channel)
        # Can now convert the datatype request into the subscription datatype.
        datatype = type_to_dbr(datatype, format)

        # Finally create the subscription with all the requested properties
        # and hang onto the returned event id as our implicit ctypes
        # parameter.
        if self.__state == self.__OPENING:
            event_id = ctypes.c_void_p()
            ca_create_subscription(
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
            try:
                callback(value)
            except:
                # We try and be robust about exceptions in handlers, but to
                # prevent a perpetual storm of exceptions, we close the
                # subscription after reporting the problem.
                print 'Subscription %s callback raised exception' % self.name
                traceback.print_exc()
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
        all_updates = False)

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
        occurred on this value.'''
    if isinstance(pvs, str):
        return _Subscription(pvs, callback, **kargs)
    else:
        return [
            _Subscription(pv, lambda v, n=n: callback(v, n), **kargs)
            for n, pv in enumerate(pvs)]


# ----------------------------------------------------------------------------
#   caget


@event_handler
def _caget_event_handler(args):
    '''This will be called when a caget request completes, either with a
    brand new data value or with failure.  The result is communicated back
    to the original caller.'''

    # We are called exactly once, so can consume the context right now.  Note
    # that we have to do some manual reference counting on the user context,
    # as this is a python object that is invisible to the C api.
    pv, done = args.usr
    ctypes.pythonapi.Py_DecRef(args.usr)
    
    if args.status == ECA_NORMAL:
        done.Signal(dbr_to_value(args.raw_dbr, args.type, args.count, pv))
    else:
        done.SignalException(ca_nothing(pv, args.status))


@maybe_throw
def caget_one(pv, timeout=None, datatype=None, format=FORMAT_RAW, count=0):
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

    # If no element count has been specified, ask for the entire set provided
    # by the channel.
    if count == 0:
        count = ca_element_count(channel)
    else:
        count = min(count, ca_element_count(channel))

    # If no datatype has been specified, use the channel's default
    if datatype is None:
        datatype = ca_field_type(channel)

    # Assemble the callback context.  Note that we need to explicitly
    # increment the reference count so that the context survives until the
    # callback routine gets to see it.
    done = cothread.Event()
    context = (pv, done)
    ctypes.pythonapi.Py_IncRef(context)
    
    # Perform the actual put as a non-blocking operation: we wait to be
    # informed of completion, or time out.
    ca_array_get_callback(
        type_to_dbr(datatype, format), count, channel,
        _caget_event_handler, ctypes.py_object(context))
    return done.Wait(timeout)


def caget_array(pvs, **kargs):
    # Spawn a separate caget task for each pv: this allows them to complete
    # in parallel which can speed things up considerably.
    return cothread.WaitForAll(
        [ cothread.Spawn(caget_one, pv, raise_on_wait = True, **kargs)
          for pv in pvs ])


def caget(pvs, **kargs):
    '''caget(pvs,
        timeout = None, datatype = None,
        format = FORMAT_RAW, count = 0, throw = True)

    Retrieves the value from one or more PVs.  If a single pv is given then
    a single value is returned, otherwise a list of values is returned.

    Every value returned has the following fields:

        .ok     Set to True if the data is good, False if there was an error
                (and throw=False has been selected).

        .name   Name of the pv.

    If ok is False then the .errorcode field is set to the appropriate ECA_
    error code and str(value) will return an appropriate error message.
    
    The various arguments control the behaviour of caget as follows:

    timeout
        Timeout for the caget operation.  This can be either a timeout
        interval in seconds, or a absolute deadline (in time() format) as a
        single element tuple.

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

@event_handler
def _caput_event_handler(args):
    '''Event handler for caput with callback completion.  Returns status
    code to caller.'''

    # This is called exactly once when a caput request completes.  Extract
    # our context information and discard the context immediately.
    pv, done = args.usr
    ctypes.pythonapi.Py_DecRef(args.usr)
    
    if args.status == ECA_NORMAL:
        done.Signal()
    else:
        done.SignalException(ca_nothing(pv, args.status))
    

@maybe_throw
def caput_one(pv, value, timeout=None, wait=False):
    '''Writes a value to a single pv, waiting for callback on completion if
    requested.'''
    
    # Connect to the channel and wait for connection to complete.
    timeout = cothread.AbsTimeout(timeout)
    channel = _channel_cache[pv]
    channel.Wait(timeout)

    # Assemble the data in the appropriate format.
    datatype, count, dbr_array = value_to_dbr(value)
    if wait:
        # Assemble the callback context and give it an extra reference count
        # to keep it alive until the callback handler sees it.
        done = cothread.Event()
        context = (pv, done)
        ctypes.pythonapi.Py_IncRef(context)
        
        # caput with callback requested: need to wait for response from
        # server before returning.
        ca_array_put_callback(
            datatype, count, channel, dbr_array.ctypes.data,
            _caput_event_handler, ctypes.py_object(context))
        done.Wait(timeout)
    else:
        # Asynchronous caput, just do it now.
        ca_array_put(datatype, count, channel, dbr_array.ctypes.data)
        
    # Return a success code for compatibility with throw=False code.
    return ca_nothing(pv)

    
def caput_array(pvs, values, repeat_value=False, **kargs):
    if repeat_value or isinstance(values, str) or not iterable(values):
        # A convenience hack to repeat a single value.
        values = [values] * len(pvs)
    assert len(pvs) == len(values), 'PV and value lists must match in length'
    return cothread.WaitForAll([
        cothread.Spawn(caput_one, pv, value, raise_on_wait = True, **kargs)
        for pv, value in zip(pvs, values)])

    
def caput(pvs, values, **kargs):
    '''caput(pvs, values,
        repeat_value = False, timeout = None, wait = False, throw = True)

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
        Timeout for the caput operation.  This can be either a timeout
        interval in seconds, or an absolute deadline (in time() format) as a
        single element tuple.

    wait
        If wait=True is specified then channel access put with callback is
        invoked, and the caput operation will wait until the server
        acknowledges successful completion before returning.

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
    ca_context_destroy(ca_current_context())

ca_context_create(0)


@cothread.Spawn
def _PollChannelAccess():
    while True:
        ca_pend_event(1e-9)
        cothread.Sleep(1e-2)


# The value of the exception handler below is rather doubtful...
if False:
    @exception_handler
    def catools_exception(args):
        '''print ca exception message'''
        print >> sys.stderr, 'catools_exception:', \
            args.ctx, ca_message(args.stat)
    ca_add_exception_event(catools_exception, 0)
