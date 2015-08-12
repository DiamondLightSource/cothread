.. _catools:

Using the catools Library
=========================

.. module:: cothread.catools

.. seealso:: :ref:`cothread`.


Overview
--------

The :mod:`cothread.catools` library provides the following functions for access
to EPICS "process variables" over channel access:

:func:`caget(pvs, ...) <caget>`
    Returns a single snapshot of the current value of each PV.

:func:`caput(pvs, values, ...) <caput>`
    Writes values to one or more PVs.

:func:`camonitor(pvs, callback, ...) <camonitor>`
    Receive notification each time any of the listed PVs changes.

:func:`connect(pvs, ...) <connect>`
    Can be used to establish a connection to a list of PVs before calling the
    other routines.  This routine is optional.

To use these functions a certain amount of setup work is required.  The
following code illustrates a simple application which reads a value from one
PV, writes to another PV, and monitors a third until terminated with
control-C::

    # Library version specification required for dls libraries
    from pkg_resources import require
    require('cothread')

    import cothread
    from cothread.catools import *

    # Using caput: write 1234 into PV1.  Raises exception on failure
    caput('PV1', 1234)

    # Print out the value reported by PV2.
    print(caget('PV2'))

    # Monitor PV3, printing out each update as it is received.
    def callback(value):
        print('callback', value)
    camonitor('PV3', callback)

    # Now run the camonitor process until interrupted by Ctrl-C.
    cothread.WaitForQuit()


The following details are general to all cothread applications.

- At Diamond the routine :func:`pkg_resources.require` must be used to specify a
  particular version of the library to use, thus the following lines are
  required at the start of any catools application::

    from pkg_resources import require
    require('cothread==2.6')

  or if the most recent version is ok then the version number can be omitted as
  in the example.

- Any :const:`EPICS_CA_` environment variables should be set at this point,
  before importing :mod:`cothread.catools` (see :ref:`environment` below).

- Of course, the libraries must be imported.  The :mod:`cothread.catools`
  library is a sub-module of the :mod:`cothread` library, and can be imported
  separately.

- If :func:`camonitor` is being used then the program should suspend in an
  event loop of some sort.  The routine :func:`cothread.WaitForQuit` can be
  used, as otherwise the :func:`camonitor` activity has no opportunity to run
  before the program exits!



.. _environment:

Environment Variables
---------------------

A number of environment variables affect the operation of channel access.  These
can be set using the :attr:`os.environ` dictionary -- but note that these need
to be set *before* loading the :mod:`cothread.catools` module.  The following
are documented in the `EPICS channel access developers manual
<http://www.aps.anl.gov/epics/EpicsDocumentation/AppDevManuals/ChannelAccess/cadoc_4.htm>`_.


:const:`EPICS_CA_MAX_ARRAY_BYTES`
    Configures the maximum number of bytes that can be transferred in a single
    channel access message.

:const:`EPICS_CA_ADDR_LIST`
    A space separated list of channel access server addresses.

:const:`EPICS_CA_AUTO_ADDR_LIST`
    If set to :const:`NO` the automatic scanning of networks is disabled.

:const:`EPICS_CA_CONN_TMO`
    Connection timeout, 30 seconds by default.

:const:`EPICS_CA_BEACON_PERIOD`
    Beacon polling period, 15 seconds by default.

:const:`EPICS_CA_SERVER_PORT`, :const:`EPICS_CA_REPEATER_PORT`
    Set these to configure the ports used to connect to channel access.  By
    default ports 5064 and 5065 are used respectively.

Example code::

    import os
    os.environ['EPICS_CA_MAX_ARRAY_BYTES'] = '1000000'

    # Note: the first import of catools must come after the environ is set up.
    from cothread.catools import *


Function Reference
------------------

The :mod:`catools` API consists of the three functions :func:`caput`,
:func:`caget` and :func:`camonitor` together with an auxilliary
:func:`connect` function.  The functions :func:`caget` and :func:`camonitor`
return or deliver "augmented" values which are documented in more detail in
the section :ref:`Values`.


..  _Common:

Common Notes
~~~~~~~~~~~~

All four functions take an argument `pvs` which can specify the name of a
single PV or can be a list of PVs.  In all cases the returned result has the
same "shape" as the `pvs` argument, in other words, if `pvs` is a single
string then a single value (error code, value, or subscription) is returned,
and if `pvs` is a list then a list of exactly the same length is returned.

In general there are advantages to calling :func:`caput`, :func:`caget` or
:func:`connect` on a list of PVs, as in this case the channel connection and
access delays will occur in parallel.

Several arguments are common through this API: `throw` determines how errors
are handled, `timeout` determines timeouts, and finally `datatype`, `format`
and `count` determine data formats and are documented in :ref:`Augmented`.

`timeout`
    The `timeout` argument specified how long :func:`caput` or :func:`caget`
    will wait for the entire operation to complete.  This timeout is in seconds,
    and can be one of several formats: a timeout interval in seconds, an
    absolute deadline (in :func:`time.time` format) as a single element tuple,
    or None to specify that no timeout will occur.  Note that a timeout of 0
    will timeout immediately if any waiting is required.

    If a timeout occurs then a :exc:`Timedout` exception will be raised unless
    ``throw=False`` has been set.

`throw`
    This parameter determines the behaviour of :func:`caget`, :func:`caput`, and
    :func:`connect` when an error occurs.  If ``throw=True`` (the default) is
    set then an exception is raised, otherwise if :const:`False` is specified an
    error code value is returned for each failing PV.


Functions
~~~~~~~~~

..  function:: caput(pvs, values, repeat_value=False, \
        datatype=None, wait=False, timeout=5, callback=None, throw=True)

    Writes values to one or more PVs.  If `pvs` is a single string then
    `values` is treated as a single value to be written to the named process
    variable, otherwise `pvs` must be iterable, and unless ``repeat_value=True``
    is set, `values` must also be an iterable of the same length in which case
    `values[i]` is written to `pvs[i]`.  Otherwise, if a single value is given
    or if ``repeat_value=True`` is specified, `values` is written to all PVs.

    The arguments control the behavour of caput as follows:

    `repeat_value`
        When writing a value to a list of PVs ensures that `values` is treated
        as a single value to be written to each PV.

    `datatype`
        See documentation for :ref:`Augmented` below.  Used to force
        transmitted data to the requested format, or select special alarm
        acknowledgement handling.  Note that only standard Python type
        conversion will be done, in particular conversion to and from strings
        is *not* automatic.

    `wait`
        If ``wait=True`` is specified then channel access put with callback is
        invoked, and the :func:`caput` operation will wait until the server
        acknowledges successful completion before returning.

    `callback`
        If a `callback` is specified then channel access put with callback is
        invoked and the given `callback` function will be called with the put
        response as a `ca_nothing` object passed as the only argument.  All
        :func:`caput` callbacks will will be called on a dedicated caput
        callback thread.

        Unless `wait` is specified the call to `caput` will complete as soon
        as the caput has been initiated.  If `wait` is specified, whether
        `caput` returns before or after `callback` is called is unpredictable.

    `timeout`, `throw`
        Documented in :ref:`Common` above.

    The return value from :func:`caput` is either a list or a single value,
    depending on the shape of `pvs`.  For each PV a :class:`ca_nothing` success
    code is returned on success, otherwise either an exception is raised or an
    appropriate error code is returned for each failing PV if ``throw=True`` is
    set.  The return code can be tested for boolean success, so for example it
    is possible to write::

        if not caput(pv, value, throw=False):
            # process caput error

    If all the PVs listed in `pvs` have already been connected, through a
    successful call to any :mod:`catools` method, then the library guarantees
    that the puts for each PV will occur strictly in sequence.  For any PVs
    which need a connection to be established the order of execution of puts
    is completely undefined.


..  function:: caget(pvs, timeout=5, datatype=None, format=FORMAT_RAW, \
        count=0, throw=True)

    Retrieves a value from one or more PVs.  If `pvs` is a single string then
    a single value is returned, otherwise a list of values is returned.  Each
    value returned is an :ref:`Augmented`, see below for details.

    If :attr:`!.ok` is :const:`False` then the :attr:`.errorcode` field is set
    to the appropriate :const:`ECA_` error code and ``str(value)`` will return
    an error message.

    The various arguments control the behaviour of :func:`caget` as follows:

    `datatype`, `format`, `count`
        See documentation for :ref:`Augmented` below.

    `timeout`, `throw`
        Documented in :ref:`Common` above.  If a value cannot be retrieved
        and ``throw=False`` is set then for each failing PV an empty value with
        ``.ok==False`` is returned.

    The format of values returned depends on the number of values requested
    for each PV.  If only one value is requested then the value is returned
    as a scalar, otherwise as a numpy array.


..  function:: camonitor(pvs, callback, events=None, datatype=None, \
        format=FORMAT_RAW, count=0, all_updates=False, \
        notify_disconnect=False, connect_timeout=None)

    Creates a subscription to one or more PVs, returning a subscription
    object for each PV.  If a single PV is given then a single subscription
    object is returned, otherwise a list of subscriptions is returned.

    Subscriptions will remain active until the :meth:`.close` method is called
    on the returned subscription object.

    The precise way in which the callback routine is called on updates
    depends on whether `pvs` is a single name or a list of names.  If it is
    single name then it is called as::

        callback(value)

    for each update.  If `pvs` is a list of names then each update is
    reported as::

        callback(value, index)

    where `index` is the position in the original array of PVs of the PV
    generating this update.  The values passed to `callback` are
    :ref:`Augmented`.

    The parameters modify the behaviour as follows:

    `events`
        This identifies the type of update which will be notified.  A
        bit-wise or of any the following are possible:

        ============== ==============================================
        Flag           Description
        ============== ==============================================
        DBE_VALUE      Notify normal value changes
        DBE_LOG        Notify archive value changes
        DBE_ALARM      Notify alarm state changes
        DBE_PROPERTY   Notify property changes
                       (on 3.14.11 and later servers)
        ============== ==============================================

        If `events` is not specified then the default value depends on the value
        selected for `format` as follows:

        ==============  =============================================
        `format`        Default value for `events`
        ==============  =============================================
        FORMAT_RAW      DBE_VALUE
        FORMAT_TIME     DBE_VALUE | DBE_ALARM
        FORMAT_CTRL     DBE_VALUE | DBE_ALARM | DBE_PROPERTY
        ==============  =============================================

    `datatype`, `format`, `count`
        See documentation for :ref:`Augmented` below.

    `all_updates`
        If this is :const:`True` then every update received from channel
        access will be delivered to the callback, otherwise multiple updates
        received between callback queue dispatches will be merged into the
        most recent value.

        If updates are being merged then the value returned will be augmented
        with a field :attr:`.update_count` recording how many updates occurred
        on this value.

    `notify_disconnect`
        If this is :const:`True` then IOC disconnect events and channel access
        error reports will be reported by calling the callback with a
        :class:`ca_nothing` error with :attr:`!.ok` :const:`False`.  By default
        these notifications are suppressed so that only valid values will be
        passed to the callback routine.

    `connect_timeout`
        If a connection timeout is specified then the :func:`camonitor` will
        report a disconnection event after the specified interval if connection
        has not completed by this time.  Note that this notification will be
        made even if notify_disconnect is False, and that if the PV subsequently
        connects it will update as normal.


..  function:: connect(pvs, cainfo=False, wait=True, timeout=5, throw=True)

    Establishes a connection to one or more PVs, optionally returning detailed
    information about the connection.  A single PV or a list of PVs can be
    given.  This does not normally need to be called, as the :func:`ca...`
    routines will establish their own connections as required, but after a
    successful connection we can guarantee that ``caput(..., wait=False)`` will
    complete immediately without suspension and that ``caput(pvs, values)`` will
    execute in order if all PVs in `pvs` have been successfully connected.

    It is possible to test whether a channel has successfully connected without
    provoking suspension by calling ``connect(pv, wait=False, cainfo=True)``
    and testing the :attr:`.state` attribute of the result.

    The various arguments control the behaviour of :func:`connect` as follows:

    `wait`
        Normally the :func:`connect` routine will not return until the requested
        connection is established.  If ``wait=False`` is set then a connection
        request will be queued and :func:`connect` will unconditionally succeed.

    `cainfo`
        By default a simple :class:`ca_nothing` value is returned, but if
        ``cainfo=True`` is set then a :class:`ca_info` structure is returned.

        ..  class:: ca_info

            The following dynamic attributes record information about the
            channel access connection:

            ..  attribute:: .ok

                :const:`True` iff the channel was successfully connected.

            ..  attribute:: .name

                Name of PV.

            ..  attribute:: .state

                State of channel as an integer.  Look up
                ``.state_strings[.state]`` for textual description.  A value of
                2 indicates a currently connected PV.

            ..  attribute:: .host

                Host name and port of server providing this PV.

            ..  attribute:: .read

                :const:`True` iff read access to this PV is allowed.

            ..  attribute:: .write

                :const:`True` iff write access to this PV is allowed.

            ..  attribute:: .count

                Data count of this channel, length of the associated data array.

            ..  attribute:: .datatype

                Underlying channel datatype as :const:`DBR_` value.  Look up
                ``.datatype_strings[.datatype]`` for description.

            The following static attributes are provided to help with
            interpretation of the dynamic attributes:

            ..  attribute:: .state_strings

                Converts :attr:`.state` into a printable description of the
                connection state.

            ..  attribute:: .datatype_strings

                Textual descriptions of the possible channel data types, can be
                used to convert :attr:`.datatype` into a printable string.

        The :class:`str` representation of this structure can be printed to
        produce output similar to that produced by the ``cainfo`` command line
        tool.

    `timeout`, `throw`
        Documented in :ref:`Common` above.  If a value cannot be retrieved
        and ``throw=False`` is set then for each failing PV an empty value with
        ``.ok==False`` is returned.


..  function:: cainfo(pvs, timeout=5, throw=True)

    This is an alias for :func:`connect` with `cainfo` and `wait` set to
    ``True``.  Returns a :class:`ca_info` structure containing information about
    the connected PV or a list of structures, as appropriate.


..  _Values:

Working with Values
-------------------

There are two types of values returned by :mod:`cothread.catools` functions:
"augmented values" and "error codes".  The :func:`caput` function only returns
an error code value (which may indicate success), while :func:`caget` and
:func:`camonitor` will normally return (or deliver) augmented values, but will
return (or deliver) an error code on failure.

The following fields are common to both types of value.  This means that is is
always safe to test ``value.ok`` for a value returned by :func:`caget` or
:func:`caput` or delivered by :func:`camonitor`.

..  attribute:: .ok

    Set to :const:`True` if the data is good, :const:`False` if there was an
    error.  For augmented values :attr:`!.ok` is always set to :const:`True`.

..  attribute:: .name

    Name of the pv.

If :attr:`!.ok` is :const:`True` then two further attributes are set (see
:ref:`Augmented` for further details):

..  attribute:: .datatype

    Underlying EPICS data type.

..  attribute:: .element_count

    Underlying EPICS length.  This is typically determined by record support at
    database loading type, for instance for :const:`waveform` records this is
    the value in the :const:`.NELM` field.

    Note that this determines the maximum length of the associated data array,
    but the returned data may be shorter, for instance the :const:`.NORD` field
    of a :const:`waveform` record can determine a shorter length.


Values and their Types
~~~~~~~~~~~~~~~~~~~~~~

The type of values returned by :func:`caget` or delivered by :func:`camonitor`
callbacks is determined by the requested datatype in the original :func:`caget`
or :func:`camonitor` call together with the underlying length of the requested
EPICS field.

If the underlying length (:attr:`!.element_count`) of the EPICS value is 1 then
the value will be returned as a Python scalar, and will be one of the three
basic scalar types (string, integer or floating point number), but wrapped as an
augmented type.

If on the other hand :attr:`!.element_count` is not 1 then the value is treated
as an array and is always returned as a numpy array, again wrapped as an
augmented type.  Note that this means that even if ``caget(pv, count=1)`` is
used to fetch a value with one element, if the underlying PV is an array then
the result returned will be an array.

..  note::

    This is an incompatible change in behaviour from previous versions of
    cothread.  Previously whether to return a value as an array or a scalar was
    determined purely by the length of the retrieved data, now it is determined
    by the underlying length of the EPICS source, ie by its
    :attr:`!.element_count` value.

The table below enumerates the possibilities:

    ==================  =============== ========================================
    Cothread type       Derived from    For these values
    ==================  =============== ========================================
    :class:`ca_str`     :class:`str`    String value
    :class:`ca_int`     :class:`int`    Integral value
    :class:`ca_float`   :class:`float`  Floating point value
    :class:`ca_array`   :class:`ndarry` Any array value
    ==================  =============== ========================================

..  class:: ca_str
..  class:: ca_int
..  class:: ca_float

    Scalar types derived from basic Python types.

..  class:: ca_array

    Array type derived from :class:`numpy.ndarray`.  The associated
    :attr:`dtype` will be as close a fit to the underlying data as possible.


..  _Augmented:

Augmented Values
~~~~~~~~~~~~~~~~

Augmented values are normally Python or :mod:`numpy` values with extra fields:
the :attr:`!.ok` and :attr:`!.name` fields are already mentioned above, and
further extra fields will be present depending on format requested for the data.
As pointed out above, :attr:`!.ok` is always :const:`True` for valid data.

Four different types of augmented value are returned: strings, integers,
floating point numbers or arrays, depending on the length of the data
requested -- an array is only used when the data length is >1.

In almost all circumstances an augmented value will behave exactly like a
normal value, but there are a few rare cases where differences in behaviour are
observed (these are mostly bugs).  If this occurs the augumentation can be
stripped from an augmented value `value` by writing ``+value`` -- this returns
the underlying value.

The type of augmented values is determined both by parameters passed to
:func:`caget` and :func:`camonitor` and by the underlying datatype.  Both of
these functions share parameters `datatype`, `format` and `count` which can be
used to control the type of the data returned:

`datatype`
    For :func:`caget` and :func:`camonitor` this controls the format of the
    data that will be requested, while for :func:`caput` the data will be
    coerced into the requested format.  `datatype` can be any of the
    following:

    1.  :const:`None` (the default).  In this case the "native" datatype
        provided by the channel will be returned.

    2.  A :const:`DBR_` value, one of the following:

        ..  data:: DBR_STRING

            Strings are up to 39 characters long -- this is a constraint set
            by EPICS.  For longer strings the data type :const:`DBR_CHAR_STR`
            can be used if the IOC is able to deliver strings as arrays of char.

        ..  data:: DBR_CHAR
                   DBR_SHORT
                   DBR_LONG

            These are all signed integer types, with 8, 16 and 32 bit values
            respectively.  The parameter `as_string` can be set to convert
            arrays of :const:`DBR_CHAR` to strings.

        ..  data:: DBR_FLOAT
                   DBR_DOUBLE

            Floating point values with 32 and 64 bit values, respectively.

        ..  data:: DBR_ENUM

            A 16 bit unsigned integer value representing an index into an
            array of strings.  The associated strings can be retrieved by
            using ``format=FORMAT_CTRL`` and inspecting the :attr:`.enums`
            field.


    3.  A python type compatible with any of the above values, such as
        :class:`int`, :class:`float` or :class:`str`.  These correspond to
        :const:`DBR_LONG`, :const:`DBR_DOUBLE` and :const:`DBR_STRING`
        respectively.

    4.  Any :class:`numpy.dtype` compatible with any of the above values.

    5.  One of the special values :const:`DBR_CHAR_STR` or
        :const:`DBR_CHAR_BYTES`.  This is used to request a char array which is
        then converted to a Python string or :class:`bytes` string on receipt.
        It is not sensible to specify `count` with this option.  The option
        :const:`DBR_CHAR_BYTES` is meaningless and not supported for
        :func:`caput`.

        Note that if the PV name ends in ``$`` and `datatype` is not specified
        then :const:`DBR_CHAR_STR` will be used.

    6.  The special value :const:`DBR_ENUM_STR`, only for :func:`caget` and
        :func:`camonitor`.  In this case the "native" channel datatype is used
        unless the channel is an enumeration, in which case the corresponding
        string is returned.

    7.  For :func:`caget` and :func:`camonitor` two further special values are
        supported.  In both of these cases `format` is ignored:

        ..  data:: DBR_STSACK_STRING

            Returns the current value as a string together with extra fields
            :attr:`.status`, :attr:`.severity`, :attr:`.ackt`, :attr:`.acks`.

        ..  data:: DBR_CLASS_NAME

            Returns the name of the "enclosing interface", typically the
            record type, and typically the same as the EPICS ``.RTYP`` field.

        For :func:`caput` also two further values are supported:

        ..  data:: DBR_PUT_ACKT
                   DBR_PUT_ACKS

            These are used for global alarm acknowledgement, where
            :const:`_ACKT` configures whether alarms need to be acknowleged
            and :const:`_ACKS` acknowledges alarms of a particular severity.


`format`
    This controls how much auxilliary information will be returned with
    the retrieved data, and can be one of the following:

    ..  data:: FORMAT_RAW

        The data is returned unaugmented except for the :attr:`!.name` and
        :attr:`!.ok` fields.  This is the default value.

    ..  data:: FORMAT_TIME

        The data is augmented by timestamp fields :attr:`.timestamp` and
        :attr:`.raw_stamp` together with alarm :attr:`.status` and
        :attr:`.severity` fields.  The value in :attr:`.timestamp` is in
        :func:`time.time` format (seconds in Unix UTC epoch) rounded to the
        nearest microsecond.

    ..  data:: FORMAT_CTRL

        The data is augmented by channel access "control" fields.  The set of
        fields returned depends on the underlying datatype as follows:

        :const:`DBR_SHORT`, :const:`DBR_CHAR`, :const:`DBR_LONG`
            The alarm :attr:`.status` and :attr:`.severity` fields together with
            :attr:`.units` and limit fields: :attr:`.upper_disp_limit`,
            :attr:`.lower_disp_limit`, :attr:`.upper_alarm_limit`,
            :attr:`.lower_alarm_limit`, :attr:`.upper_warning_limit`,
            :attr:`.lower_warning_limit`, :attr:`.upper_ctrl_limit`,
            :attr:`.lower_ctrl_limit`.  The meaning of these fields is
            determined by EPICS channel access.

        :const:`DBR_FLOAT`, :const:`DBR_DOUBLE`
            As above together with a :attr:`.precision` field.

        :const:`DBR_ENUM`
            Alarm :attr:`.status` and :attr:`.severity` fields together with
            :attr:`.enums`, a list of possible enumeration strings.  The
            underlying value for an enumeration will be an index into
            :attr:`.enums`.

        :const:`DBR_STRING`
            :const:`_CTRL` format is not supported for this field type, and
            :const:`FORMAT_TIME` data is returned instead.


`count`
    The precise behaviour of this parameter is EPICS server and client version
    specific, but for recent versions of EPICS there are three options:

    0 (default)
        For recent versions of EPICS this is interpreted as a request for the
        true data dependent length of the data, for example, the number of
        points in a waveform record determined by the ``.NORD`` field).  For
        older versions of EPICS the full waveform is returned.

        ..  note::

            This feature means that a very visible change in behaviour is seen
            when upgrading from EPICS 3.14.11 to 3.14.12.  Before this update
            requests from waveform records ignore ``.NORD``, subsequently it is
            possible for truncated data to be returned in response to a default
            request.

    -1 (or any negative value)
        This will always request the entire waveform, up to
        :attr:`.element_count` values.

    any other value
        Returns the specified number of elements, up to :attr:`.element_count`.


Fields in Augmented Values
~~~~~~~~~~~~~~~~~~~~~~~~~~

Summary of all available fields in augmented values.

The following fields are present in all augmented values.

..  attribute:: .name

    Name of record, always present.

..  attribute:: .ok

    Set to :const:`True`, always present.

The following fields are present if :attr:`!.ok` is :const:`True`:

..  attribute:: .datatype

    This is the underlying EPICS data type of the value, and is one of the
    following values:

    ==============  ==  ========================================================
    DBR_STRING      0   String (up to 40 characters)
    DBR_SHORT       1   16-bit signed integer
    DBR_FLOAT       2   32-bit floating point number
    DBR_ENUM        3   Enumeration, should be value between 0 and 15, but the
                        underlying data is a 16-bit integer
    DBR_CHAR        4   8-bit signed integer
    DBR_LONG        5   32-bit signed integer
    DBR_DOUBLE      6   64-bit floating point number
    ==============  ==  ========================================================

..  attribute:: .element_count

    Number of elements in the underlying EPICS value.  If this is not 1 then the
    value is treated as an array, otherwise up to this many elements may be
    present in the value.


The following fields are present in all values if :const:`FORMAT_TIME` is
specified.

..  attribute:: .raw_stamp

    Record timestamp in raw format as provided by EPICS (but in the local Unix
    epoch, not the EPICS epoch).  Is a tuple of the form ``(secs, nsec)`` with
    integer seconds and nanosecond values, provided in case full ns timestamp
    precision is required.

..  attribute:: .timestamp

    Timestamp in seconds in format compatible with ``time.time()`` rounded to
    the nearest microsecond: for nanosecond precision use :attr:`.raw_stamp`
    instead.

..  attribute:: .datetime

    This is a dynamic property which returns :attr:`timestamp` as a
    :class:`datetime` value by computing ::

        datetime.datetime.fromtimestamp(value.timestamp)

    from the :attr:`timestamp` attribute.  This calculation takes local time
    into account.

    ..  note::

        This is an incompatible change from cothread version 2.3 and earlier.
        In earlier versions this field did not exist but could be assigned to,
        in this release :attr:`datetime` is a read-only property which cannot
        be assigned to.


The following fields are present in all values if :const:`FORMAT_TIME` or
:const:`FORMAT_CTRL` is specified.

..  attribute:: .severity

    EPICS alarm severity, normally one of the values listed below.

    =  ==================================
    0  No alarm
    1  Alarm condition, minor severity
    2  Alarm condition, major severity.
    3  Invalid value.
    =  ==================================

..  attribute:: .status

    Reason code associated with alarm severity, always present with
    :attr:`.severity` code.


The following fields are present in numeric values if :const:`FORMAT_CTRL` is
specified.  Values of type :const:`DBR_ENUM` or :const:`DBR_STRING` are not
numeric.

..  attribute:: .units

    Units for display.

..  attribute::
        .upper_disp_limit
        .lower_disp_limit

    Suggested display limits for numerical values.

..  attribute::
        .upper_alarm_limit
        .lower_alarm_limit
        .upper_warning_limit
        .lower_warning_limit
        .upper_ctrl_limit
        .lower_ctrl_limit

    Various EPICS numeric limits.

..  attribute:: .precision

    For floating point values only, the specified display precision
    (or 0 if not specified).  Present if value is a floating point type.

The following field is only present in :const:`DBR_ENUM` values.

..  attribute:: .enums

    For enumeration values only, an array of enumeration strings
    indexable by enumeration value.


..  _ca_nothing:

Error Code Values
~~~~~~~~~~~~~~~~~

Error code values are used to indicate a success return from :func:`caput` (in
which case :attr:`!.ok` is :const:`True`), to indicated disconnection using
:func:`camonitor`, and to indicate any other failure, either as a return value
or raised as an exception.

..  class:: ca_nothing

    All error code values have type :class:`ca_nothing` and provide the
    following fields:

    ..  attribute:: .ok

        Set to :const:`True` if the data is good, :const:`False` if there was an
        error.  Testing an error code value for boolean will return the value of
        :attr:`!.ok`, so for example it is possible to write::

            if not caput(pv, value, throw=False):
                process caput error

    ..  attribute:: .name

        Name of the PV which generated this error..

    ..  attribute:: .errorcode

        Channel access error code.  The following values are worth noting:

        ..  data:: ECA_SUCCESS

            Success error code.  In this case :attr:`!.ok` is :const:`True`.
            Returned by successful :func:`caput` and :func:`connect` calls.

        ..  data:: ECA_DISCONN

            Channel disconnected.  This is used by :func:`camonitor` to report
            channel disconnect events.

        ..  data:: ECA_TIMEOUT

            Channel timed out.  Reported if user specified timeout ocurred
            before completion and if ``throw=False`` specified.


PV and PV_array Classes
-----------------------

.. module:: cothread.pv

Two classes are provided for wrapping :func:`camonitor`.  The :class:`PV` class
wraps access to a single PV and always contains the latest value.  On the other
hand, :class:`PV_array` gathers a uniform array of PVs into a single array.
These two classes can be imported from :mod:`cothread.pv`.

Note that both classes will automatically unsubscribe from their PVs when
deleted.

..  note::

    Note that both of these classes are still somewhat experimental and may
    change in future releases.


..  class:: PV(pv, on_update=None, initial_value=None, caput_wait=False, \
    [initial_timeout], **kargs)

    Creates a wrapper to monitor *pv*.  If an *on_update* function is passed it
    will be called with the class instance as argument after each update to the
    instance.  The *kargs* are passed through to the called :func:`camonitor`.
    The flag *caput_wait* can be set to change the default behaviour of
    :meth:`caput`.

    The behaviour of the first call to :meth:`get` is affected by two arguments,
    *initial_value* and *initial_timeout*, at most one of which can be
    specified.  If *initial_timeout* is specified then the first call to
    :meth:`get` will block until this timeout expires or a valid PV value is
    available.  Otherwise *initial_value* can be set to specify a value to
    return until the PV has updated.

    ..  note::

        This is an incompatible change from cothread versions 2.11 and 2.12.  In
        these versions the *initial_timeout* argument is named *timeout*,
        defaults to 5, and cannot be unset.

    Note that blocking on a PV object for the initial update cannot be safely
    done from within a camonitor callback, as in this case the blocking
    operation is waiting for a camonitor callback to occur, and only one
    camonitor callback is processed at a time.

    ..  method:: close()

        Closes the associated :func:`camonitor`.  No further updates will occur.
        Note that it is sufficient to drop all references to the class, it will
        then automatically call :meth:`close`.

    ..  method:: sync([timeout])

        This call will block until the :class:`PV` object has seen at least one
        update.  If *initial_timeout* was specified in the constructor then its
        associated deadline can be used as a default timeout, otherwise a
        *timeout* must be specified.

    ..  method:: get()

        Returns the current value associated with the PV.  This will be the most
        recently delivered PV value as notified through a :func:`camonitor`
        callback.

        On the first call to :meth:`get` if no value has yet been delivered (no
        callback has yet occurred) this call will block until the timeout passed
        to the constructor has expired or a value has arrived, and if the
        timeout expires then an exception is raised.

    ..  method:: get_next(timeout=None, reset=False)

        Returns a fresh value associated with the PV, blocks and waits if
        necessary.  Values are consumed by calling this method or :meth:`reset`,
        values are generated by :func:`camonitor` callbacks, so to ensure the
        value is fresher than the point of call *reset* can be set to discard
        any pending value.  A *timeout* can be specified to limit how long to
        wait for a new value, and a timeout exception may be raised.

    ..  method:: reset()

        Discards any pending value for :meth:`get_next`, ensures
        :meth:`get_next` will block until a fresh value arrives.

    ..  method:: caget(** kargs)

        Directly calls :func:`caget` on the underlying PV with the given
        arguments.

    ..  method:: caput(value, ** kargs)

        Directly calls :func:`caput` on the underlying PV with the given
        arguments.  If *caput_wait* was set in the original :class:`PV`
        constructor then by default :func:`caput` is called with ``wait=True``,
        otherwise :func:`caput` is non blocking.

    ..  attribute:: name

        This is the PV name, and should be the same as ``.value.name``.

    ..  attribute:: value

        This attribute is a property wrapping :meth:`get` and :meth:`caput`, so
        given ``pv = PV(pvname)`` then ``pv.value`` returns the most recent
        value for ``pv`` and ``pv.value = new_value`` will call ``caput(pvname,
        new_value)``.


..  class:: PV_array(pvs, dtype=float, count=1, on_update=None, \
    caput_wait=False, **kargs)

    Uses *pvs* to create an aggregate array containing the value of all
    specified PVs aggregated into a single :mod:`numpy` array.  The type of all
    the elements is specified by *dtype* and the number of points contributed by
    each PV is given by *count*.  If *count* is 1 the generated array is one
    dimensional of shape ``(len(pvs),)``, otherwise the shape is
    ``(len(pvs),count)``.  The flag *caput_wait* can be set to change the
    default behaviour of :meth:`caput`.


    At the same time arrays of length ``len(pvs)`` are created for the
    connection status, timestamp and severity of each PV.

    If specified the *on_update* method will be called for each update to each
    field of the managed array.  The arguments passed are the updated
    :class:`PV_array` instance and the index of the update.

    ..  method:: close()

        Closes all monitors.  Note that this is called automatically when the
        last reference to the created :class:`PV_array` instance is dropped.

    ..  method:: get()

        Returns copy of current value.  This will be a :mod:`numpy` array with
        shape and dtype determined by the arguments to the constructor.  This is
        the same as the value returned by the :attr:`value` attribute.

    ..  method:: caget(** kargs)

        Directly calls :func:`caget` on the list of PVs and returns an array of
        results; this should be the same shape and parameters as returned by
        :meth:`get`.

    ..  method:: caput(value, ** args)

        Directly calls :func:`caput` on the stored list of PVs.  If *caput_wait*
        was set in the original :class:`PV` constructor then by default
        :func:`caput` is called with ``wait=True``, otherwise :func:`caput` is
        non blocking.


    ..  method:: sync(timeout=5, throw=False)

        This method attempts to ensure that all of the PVs associated with this
        array have received at least one update by blocking.

    ..  attribute:: value

        Returns copy of current value, same as :meth:`get` when read, calls
        :meth:`caput` when written to.

    ..  attribute:: names

        Stores the names of the monitored PVs.

    ..  attribute:: timestamp

        Timestamp of the most recent update for each monitored PV in standard
        :func:`time.time` format.

    ..  attribute:: severity

        Array of EPICS severity codes for the most recent update for each PV.

    ..  attribute:: status

        Array of EPICS status codes for the most recent update for each PV.

    ..  attribute:: ok

        Connection status for each monitored PV.  If any element of :attr:`!.ok`
        is :const:`False` then the PV is disconnected and the corresponding
        :attr:`!.value`, :attr:`!.timestamp`, :attr:`!.severity` and
        :attr:`!.status` elements contain old and stale values.

    ..  attribute:: all_ok

        Returns aggregate status of :attr:`!.ok`, :const:`True` iff all PVs
        currently connected.

    Note that the attributes :attr:`value`, :attr:`ok`, :attr:`timestamp`,
    :attr:`severity`, and :attr:`status` all return fresh copies of the
    underlying data.  This means that the values returned are not affected by
    subsequent updates to the :class:`PV_array` object.
