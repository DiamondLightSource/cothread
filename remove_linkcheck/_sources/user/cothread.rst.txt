.. _cothread:

Using the cothread Library
==========================

.. module:: cothread
    :noindex:


The :doc:`cothread<cothread>` Python library is designed for building tools using
cooperative threading.  This means that, with care, programs can effectively
run several tasks simultaneously.

The :mod:`cothread.catools` library is designed to support easy channel access
from Python, and makes essential use of the features of cooperative threads --
in particular, :func:`catools.camonitor` notifies updates in the background.

.. seealso:: :ref:`catools`.


Introduction to Cothreads
-------------------------

Cothreads (or "cooperative threads") are an approach to concurrent programming
where there is only one true thread of processing, but apparently concurrent
processes (or *cothreads*) can cooperatively share the processor.  Control is
passed from one cothread to another when the current cothread explicitly
suspends control, ultimately via a call to a :doc:`cothread<cothread>` library routine.
This means that between such suspending calls control will not be interrupted.
This has two advantages:

* No locking between threads is required.  This is a very helpful benefit of
  using cothreads, as getting locking between multiple threads right can be
  suprisingly difficult.

* The thread of processing is frequently more predictable: between two
  suspension points there is no possibility of unexpected background activity!

On the other hand, there is one disadvantage which needs to be kept in mind:

* If a cothread blocks (for example, by calling :func:`time.sleep` or reading
  from a blocking socket or remote file without first calling a select function)
  then *all* cothreads will be blocked.  The cothread library provides routines
  to help with this (see :func:`Sleep`, :func:`select` and :class:`socket`
  below).

To use the :doc:`cothread<cothread>` library the following overall structure should be
followed in the top level application::

    # Import the cothread library in each module that uses it.
    import cothread

    # Enable Qt processing, hang onto application instance if needed.
    qtapp = cothread.iqt()      # Not needed if not using Qt

    # Do the real work of the module, including spawning any background tasks.
    ...

    # Finally allow all background tasks to run to completion.
    cothread.WaitForQuit()      # Or some other blocking construct


1.  If Qt is to be used (for any graphical user interface) then the cothread
    library needs to be informed: this is done by calling :func:`iqt` before
    any work is done with Qt.  This call ensures that Qt processing will occur
    while the cothread scheduler is idle, and effectively turns Qt into
    another cothread.  The Qt application instance is created by this call and
    returned.

2.  Finally the main cothread (the thread of control used to start and run the
    program) must not exit until the program has finished.  If all the desired
    activity is in background tasks (spawned cothreads,
    :func:`catools.camonitor` processing or other background activity) then the
    simplest thing is to call :func:`WaitForQuit()` before exiting: this will
    wait until the :func:`Quit` function is called, or control-C is pressed
    somewhere, or the last Qt window is closed.


Cothread Suspension Points
~~~~~~~~~~~~~~~~~~~~~~~~~~

When using cothreads only certain function calls will cause control to be
yielded to another cothread, or in other words, will cause suspension of the
calling cothread -- here we call such a routine a "suspension point".

Understanding suspension points is important for effective use of cothreads:
between suspension points no other cothread will run, and the current cothread
has exclusive control of the process (except for any "real" threads that
might be running).  Once a suspension point is reached any other cothread can
run, in fact typically *all* other ready cothreads will run to their own
suspension points before control is returned to the suspending cothread.

The following are suspension points in the core :doc:`cothread<cothread>` library:

:func:`Sleep`, :func:`SleepUntil`
    The caller is always suspended, even if the expiry time has passed, so
    ``Sleep(0)`` has much the same effect as ``Yield()``.

:func:`Yield`
    This suspends the caller until all other active cothreads have run to
    their own suspension points.

``event``.\ ``Wait``
    On a :class:`Spawn`, :class:`Pulse`, :class:`Event` or :class:`EventQueue`
    object the ``Wait`` method will suspend the caller when the event object
    is not yet ready, independently of whether the timeout has already expired.
    To determine whether an event object is ready without risking suspension
    call ``bool()`` on the object.

    ..  note::

        This is an incompatible change from cothread version 2.0 and earlier.
        In earlier versions of cothread suspension does not occur on an expired
        timeout, but unfortunately this can easily lead to starvation of other
        cothreads.


The ``cothread.coselect`` module adds the following suspension points:

:func:`select`, :class:`poll`, :func:`poll_list`
    These are all always suspension points.

In the :mod:`cothread.catools` module the following routines can cause
suspension (note that :func:`catools.camonitor` is the only routine guaranteed
not to suspend):

:func:`catools.caget`
    This is always a suspension point.

:func:`catools.caput`
    This routine may cause the caller to suspend.  To avoid suspension, put to
    only one PV, use ``wait=False`` (the default), and ensure that the channel
    is already connected -- this will be the case if it has already been
    successfully used in any :mod:`~cothread.catools` method.  To ensure suspension use
    ``wait=True``.

The ``cothread.cosocket`` module makes most socket operations into suspension
points when the corresponding socket operation is not yet ready.


Order of Execution
~~~~~~~~~~~~~~~~~~

It is possible to be fairly precise about the order in which certain processes
will occur.

* Cothreads started by :class:`Spawn` will initially be processed in the order
  in which they were created with no other cothreads intervening.

* Cothreads waiting on an event will be woken strictly in the sequence in
  which waiting takes place, just so long as no timeout occurs.  Cothreads
  woken by timeouts generally execute after other processing is complete.

This ordering of processing together with the fact that cothreads are only
suspended when control needs to be lost means that certain guarantees about
ordering of processing can be made, in particular see :func:`catools.caput`.


Callbacks and Timers
~~~~~~~~~~~~~~~~~~~~

Callbacks and timers are also provided through the cothread library, and it is
important to understand how they interact with other routines.

Timers
    Timers are created by the :class:`Timer` function documented below.  The
    callback that is invoked as part of the timer is a fresh cothread, spawned
    when the timer is created.  This means that the timer callback function can
    run for as long as desired without interfering with other timer callbacks
    (so long as it suspends regularly, of course!)

    Note however that a timer will not retrigger itself until its current
    callback routine completes.


Callbacks from :func:`catools.camonitor`
    The callback routines called in response to :func:`catools.camonitor` are
    all invoked on a single cothread.  This means that extended processing
    within a single callback will prevent any other callbacks from being
    processed.  To avoid this either spawn a new cothread to perform further
    process, or communicate with an existing separate cothread.


Other callbacks
    Other callbacks will depend on the library generating them, but it is safest
    to treat them as "blocking" in the sense described above.


Timeouts and Deadlines
~~~~~~~~~~~~~~~~~~~~~~

All of the waiting methods in the :doc:`cothread<cothread>` library take a `timeout`
argument.  This can be in one of three forms:

``None``
    A timeout of ``None`` means that the timeout will never complete, so
    for example a call to ``Sleep(None)`` will never return, and so is not
    useful, but this option is useful in other cases when no timeout is wanted.

Timeout interval in seconds
    A numerical argument is interpreted as a timeout interval in seconds from
    the time of call.  Note that although a timeout of 0 will immediately
    timeout, cothread suspension will still occur.

``(`` deadline in seconds ``,)``
    A tuple containing one numerical value is interpreted as a timeout deadline
    in seconds in the ``time.time()`` epoch.  If the deadline has already passed
    the call will timeout, but cothread suspension will occur first.

The following helper functions are available for working with timeouts:

..  function:: AbsTimeout(timeout)

    Takes a timeout and returns a timeout, ensuring that `timeout` is in
    deadline format (or ``None``).  If repeated wait functions are to be
    called with the same desired timeout this should be used to ensure the
    timeout is a deadline.

..  function:: Deadline(deadline)

    Converts a deadline in ``time.time()`` epoch seconds into a :doc:`cothread<cothread>`
    timeout format.

..  function:: GetDeadline(timeout)

    Returns the associated deadline in seconds, or returns ``None`` if
    `timeout` is ``None``.


Cothread API
------------

The following functions define the basic cothread interface provided by this
module.


..  class:: Spawn(function, arguments, raise_on_wait=False, \
        stack_size=0, ...)

    A new cooperative thread, or *cothread*, is created as a call to
    ``function(arguments)`` where ``arguments`` can be any list of values and
    keyword arguments (except for the ``raise_on_wait`` and ``stack_size``
    arguments).  This routine is not a suspension point.

    This is the fundamental building block of the cothreading library.  It is
    quite cheap to spawn fresh cothreads, and so this constructor can be used
    freely.

    :param raise_on_wait:
        By default any exception raised by running ``function(arguments)`` is
        caught and reported by a traceback to ``stderr``.  If this flag is
        set then instead the exception is retained and returned when
        :meth:`Wait` is called.

    :param stack_size:
        If a non-zero ``stack_size`` is specified the new cothread is allocated
        its own stack, otherwise it will share the main process stack.  The
        tradeoffs involved in whether to allocate a stack are subtle.  By
        default it is safest to leave this parameter unset.

    It is possible to wait for the completion of a spawned cothread by calling
    its :meth:`Wait` method:

    ..  method:: Wait(timeout=None)

        This blocks until the spawned cothread completes, either by returning
        from its function call, or by raising an exception.  Note that only one
        waiter will be woken.  If the cothread was created with ``raise_on_wait``
        set to ``True`` then any exception raised by the cothread will be
        re-raised when :meth:`Wait` is called.


..  function::
        Sleep(timeout)
        SleepUntil(time)

    The calling task is suspended until the given time.  :func:`Sleep` suspends
    the task for at least delay seconds, :func:`SleepUntil` suspends until the
    specified time has passed (`time` is defined as the value returned by
    ``time.time()``).

..  function:: Yield(timeout=0)

    :func:`Yield` suspends control so that all other potentially busy tasks
    can run.  Control is not returned to the calling task until all other
    active tasks have been processed, or the timeout has expired.


Communication between cothreads is provided by :class:`Pulse`, :class:`Event`,
and :class:`EventQueue` objects.  A :class:`Pulse` holds no values, an
:class:`Event` can hold at most one value (or signal), while an
:class:`EventQueue` can hold a list of unbounded length.


..  class:: Event(auto_reset=True)

    Event objects are initially created unsignalled.  The ``auto_reset`` flag
    determines whether the signalled state of the event object is persistent,
    and determines how many cothreads are woken when :meth:`~Event.Signal` is
    called on an event.  The :class:`bool` state of an event object is ``True``
    iff it is signalled.

    The following methods define the behaviour of this object.

    ..  method:: Wait(timeout=None)

        The calling cothread will be suspended until a signal is written to the
        :class:`Event` by a call to :meth:`Signal()`, at which point the value
        passed to :meth:`Signal()` is returned.  If a timeout occurs (a timeout
        of ``None`` specifies no timeout) this is signalled by raising the
        exception :exc:`Timedout`.

        If ``auto_reset`` was specified as ``True`` then the signal is
        consumed, and subsequent calls to :meth:`Wait` will block until further
        :meth:`Signal` calls occur.

    ..  method:: Signal(value=None)

        The event object is marked as signalled and the value passed is recorded
        to be returned by a call to :meth:`Wait`.  If one or more cothreads are
        waiting for a signal then at least one will be woken with the new value
        (if ``auto_reset`` is ``True`` then only one will be woken, otherwise
        all will be).

        Note that this routine does *not* suspend the caller, even if another
        cothread is woken: it will not process until later.

    ..  method:: SignalException(exception)

        This is similar in effect to :meth:`Signal`, but the effect on
        cothreads calling :meth:`Wait` is that they will receive the given
        exception.

    ..  method:: Reset()

        Resets the signal and erases its value.  Also erases any exception
        written to the event.


..  class:: RLock()

    The :class:`RLock` is a reentrant lock that can be used to protect access
    or modification of variables by two cothreads at the same time. It is
    reentrant because once it is acquired by a cothread, that same cothread
    may acquire it again without blocking. This same cothread must release it
    once for each time it has acquired it.

    It can be used as a context manager to acquire that lock and guarantee that
    release will be called even if an exception is raised. For example::

        lock = RLock()
        x, y = 0, 0

        with lock:
            x = 1
            some_function_that_yields_control()
            y = 1

    Now as long as any other function that uses x and y also protects access
    with this same lock, x and y will always be in a consistent state. It also
    means that some_function_that_yields_control() can also acquire the lock
    without causing a deadlock.

    The following methods are supported:

    ..  method:: acquire(timeout=None)

        Acquire the lock if necessary and increment the recursion level.

        If this cothread already owns the lock, increment the recursion level
        by one, and return immediately. Otherwise, if another cothread owns the
        lock, block until the lock is unlocked. Once the lock is unlocked (not
        owned by any cothread), then grab ownership, set the recursion level to
        one, and return. If more than one thread is blocked waiting until the
        lock is unlocked, only one at a time will be able to grab ownership of
        the lock.

    ..  method:: release()

        Release a lock, decrementing the recursion level

        If after the decrement it is zero, reset the lock to unlocked (not owned
        by any cothread), and if any other cothreads are blocked waiting for the
        lock to become unlocked, allow exactly one of them to proceed. If after
        the decrement the recursion level is still nonzero, the lock remains
        locked and owned by the calling cothread.

        Only call this method when the calling cothread owns the lock. An
        AssertionError is raised if this method is called when the lock is
        unlocked or the cothread doesn't own the lock.


..  class:: Pulse()

    Pulse objects have no state and all cothreads waiting on a Pulse object will
    block until :meth:`Signal()` is called, at which point waiting cothreads
    will be woken.

    The following methods are available.

    ..  method:: Wait(timeout=None)

        The calling cothread will suspend until :meth:`Signal()` is called or
        until a timeout occurs, in which case a :exc:`Timedout` exception is
        returned.

    ..  method:: Signal(wake_all=True)

        Wakes one or all cothreads waiting on the object.  By default all
        waiting cothreads are woken, but ``Signal(False)`` can be used to
        wake just one waiting cothread.

    A Pulse object behaves similarly to an :class:`Event` object, but the wakeup
    is unconditional and a Pulse object has no state.  This object can used as a
    notifier for updating complex conditions.


..  class:: EventQueue(max_length=None)

    The :class:`EventQueue` is designed to support the communication of a
    stream of values between two cothreads.  Calling :func:`len` on an event
    queue returns the number of entries currently in its queue.  An event
    queue can also be consumed as an iterator, see code example below.

    Optionally a maximum queue length can be specified.  In this case attempts
    to signal a queue with ``max_length`` pending elements will fail.

    The following methods are supported:

    ..  method:: Wait(timeout=None)

        Returns the next object from the queue, blocking if necessary.  If a
        timeout occurs then :exc:`Timedout` is raised.  If the queue has been
        closed then :exc:`StopIteration` is raised.

        If the queue is non empty when :meth:`Wait` is called control will not
        be suspended.

    ..  method:: Signal(value)

        Adds the given value to the queue, waking up a waiting cothread if one
        is waiting.  This routine does not suspend the caller.  ``True`` is
        returned on success.

        If the queue is full, i.e. if ``max_length`` was specified on creation and
        the current queue length is equal to this limit, then no action is taken
        and ``False`` is returned.

    ..  method:: Reset()

        Discards all values in the queue.

    ..  method:: close()

        Marks the queue as closed, after which no more signals can be raised.
        Calling :meth:`Wait()` on a closed queue will cause
        :py:exc:`StopIteration` to be raised.

    Example code using iteration over an :class:`EventQueue`::

        def consumer(e):
            for x in e:
                print('consumed', x)

        eq = EventQueue()
        Spawn(consumer, eq)

        for i in range(10):
            eq.Signal(i)
            Sleep(1)


..  class:: ThreadedEventQueue()

    The :class:`ThreadedEventQueue` behaves like an :class:`EventQueue`, but
    is designed to be used to communicate between a Python thread outside of
    the cothread library and a cothread.  Communication can occur in either
    direction: an outside thread can call :meth:`~Event.Signal` on a threaded event
    queue while a cothread calls :meth:`~Event.Wait`, or vice versa.  Note however that
    for communicating from Python threads to cothread it is more efficient to
    use :func:`Callback`.

    If a thread calls :meth:`~Event.Wait` it will block until a cothread (or another
    thread) calls :meth:`~Event.Signal`.  If this is undesirable then the field
    ``.wait_descriptor`` can be waited on using the standard :func:`select`
    or :func:`poll` functions.  Note that this file handle must *only* be used
    for waiting, and must not be read from!


..  class:: Timer(timeout, callback, retrigger=False, reuse=False, stack_size=0)

    This triggers a call to `callback`, with no arguments, when `timeout`
    expires.  If ``retrigger`` is ``True`` then after `callback` completes
    the timer will be reenabled and the cycle will repeat, in which case
    `timeout` must be a relative timeout, otherwise only one call will occur.
    If ``retrigger`` is ``False`` then once the timer has fired it cannot be
    reused unless ``reuse`` is set to ``True``, see :meth:`reset` below.

    The following two methods can be used to control the timer object:

    ..  method:: cancel()

        The timer can be cancelled at any time by calling the :meth:`cancel()`
        method.  The timer will not fire after this call and will no longer be
        reusable.  To avoid memory leaks :meth:`cancel()` should be called on
        timers with either ``retrigger`` or ``reuse`` set once they are no longer
        needed.

    ..  method:: reset(timeout, retrigger=None)

        This method allows a reusable timer to be controlled.  This applies to
        any timer created with either ``retrigger`` or ``reuse`` set, but this
        method cannot be called after :meth:`cancel()` has been called.

        A `timeout` of ``None`` can be specified to suspend the timer,
        otherwise a new timeout must always be specified when calling
        :meth:`reset()`.  Any pending timeout will be cancelled when
        :meth:`reset()` is called.

        A new value for the ``retrigger`` flag can also be specified.


..  function:: WaitForAll(event_list, timeout=None)

    This routine waits for all events in ``event_list`` to become ready: this is
    done by simply iterating through all the events in turn, waiting for them
    to complete.  If `timeout` expires then an exception is raised.

    Note that if :func:`WaitForAll` is interrupted early by an exception or
    timeout all pending resources for the remaining events in ``event_list`` will
    still be consumed.

..  function::
        Quit()
        WaitForQuit(catch_interrupt=True)

    The routine :func:`WaitForQuit` blocks until one of the following occurrs:
    :func:`Quit` is called, :any:`signal.SIGINT` is received (by pressing control-C),
    or the last Qt window is closed.  By default (if ``catch_interrupt=True`` is
    set) keyboard interrupts are handled by a signal handler which simply calls
    :func:`Quit`.  This means that the only way to interrupt a loop without a
    suspension point is to use another signal such as ``SIGQUIT`` (control-\\).

    This is designed to be used as the final blocking call at the end of the
    main program so that other event loops can run.

    ..  note::

        This use of ``catch_interrupt`` to set a signal handler is an incompatible
        change from cothread 2.0 and earlier.

..  function:: Callback(action, *args)

    This function can be called from any Python thread to arrange for
    ``action(*args)`` to be called in the cothread's own thread.

    Note that all callbacks are called in sequence and so any individual
    ``action()`` should return as soon as possible to avoid blocking subsequent
    callbacks -- if more work needs to be done, call ``Spawn()``.

..  function:: CallbackResult(action, *args, **kargs, \
        callback_queue=Callback, callback_timeout=None, callback_spawn=True)

    This is similar to :func:`Callback`: this can be called from any Python
    thread, and ``action(*args, **kargs)`` will be called in cothread's own
    thread.  The difference is that the this function will block until
    `action` returns, and the result will be returned as the result from
    :func:`CallbackResult`.  For example, the following can be used to perform
    channel access from an arbitrary thread::

        value = CallbackResult(caget, pv)

    The following arguments are processed by :func:`CallbackResult`, all others
    are passed through to `action`:

    ``callback_queue``
        By default the standard :func:`Callback` queue is used for dispatch to
        the cothread core, but a separate callback method can be specified here.

    ``callback_timeout``
        By default the thread will block indefinitely until `action` completes,
        or a specific timeout can be specified here.

    ``callback_spawn``
        By default a new cothread will be spawned for each callback; this can
        help to avoid interlock problems as mentioned above under
        :func:`Callback`, but adds overhead.


..  function:: iqt(poll_interval=0.05, run_exec=True, argv=None)

    If Qt is to be used then this routine must be called during initialisation
    to enable the Qt event loop and create the initial Qt application instance.
    The Qt application instance is returned.

    The normal Qt event hook does not work correctly with modal dialogs (because
    they run their own message loops) -- typically a modal window will block the
    the scheduling of other cothreads.

    If :doc:`cothread<cothread>` is used in a context where there is no control over the
    Qt event loop then ``run_exec`` can be set to ``False`` to ensure that
    :doc:`cothread<cothread>` doesn't try to run the event loop.


.. exception:: Timedout

    Exception indicating an event has timed out.


Coselect and Cosocket Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To enable cothreaded access to sockets and other external event generating
sources the ``cothread.coselect`` library provides coperative implementations
of :func:`select`, :func:`poll` and :class:`socket` from the Python library
:mod:`select` and :mod:`socket` modules.  The following methods and classes are
provided:

..  function:: select(iwtd, owtd, ewtd, timeout=None)

    Cooperative :func:`select` function, interface compatible with the Python
    library :func:`select.select` function (though the exceptions raised are
    slightly different).


..  function:: poll()

    Cooperative ``poll`` object, interface compatible with the Python
    library :func:`select.poll` object.


..  function:: poll_list(event_list, timeout=None)

    Simpler function for waiting for one or more events to occur.  This
    function is used to implement the more compatible :func:`select` and
    :class:`poll` interfaces.

    The ``event_list`` parameter is a list of pairs, each consisting of a
    waitable descriptor and an event mask (generated by oring together
    ``POLL...`` constants).  This routine will cooperatively block until
    any descriptor signals a selected event (or any event from
    ``POLLHUP``, ``POLLERR``, ``POLLNVAL``) or until the
    timeout (in seconds) occurs.

..
    The return value is a dictionary mapping ready descriptors to their
    corresponding mask of ready events.

    This isn't true yet, but it's a good idea.  Unfortunately it's an
    incompatible API change.  //////


..  class:: socket(...)

    This is a cooperative non-blocking wrapper of the standard :class:`socket`
    class.  This can be imported directly from :doc:`cothread<cothread>` and used with
    constants and most methods from the standard :mod:`socket` module, or
    alternatively ``socket_hook()`` can be called before importing the
    :mod:`socket` module.

..  function:: socketpair(...)

    This function wraps :func:`socket.socketpair` to return a pair of
    cooperative stream :class:`socket` instances which are already connected.

..  function:: create_connection(address, ...)

    This function wraps :func:`socket.create_connection` to return a cothread
    compatible socket.

..  function:: select_hook()

    This function will replace the :func:`select.select` and
    :func:`select.poll` methods in the :mod:`select` module with the
    non-blocking cothread compatible functions defined here.  Do not use this if
    other threads need to use functions from the :mod:`select` module.


..  function:: socket_hook()

    This function will replace :class:`socket.socket` and
    :func:`socket.socketpair` in the :mod:`socket` module with
    :class:`cothread.socket` and :func:`socketpair`.  This will convert most
    Python socket library functions into cooperative socket functions and allows
    all of the helper functions in the :class:`socket` module to be used.

    Note that this function will affect all threads, so if the application
    contains a non-cothread thread using sockets this function must not be used.


Coserver Functions
~~~~~~~~~~~~~~~~~~

.. module:: cothread.coserver

:mod:`cothread.coserver` provides coorperative versions of the server classes
from :mod:`socketserver` and :mod:`http.server` modules.

..  class:: TCPServer(...)

    Wrapped version of :class:`socketserver.TCPServer`.

..  class:: UDPServer(...)

    Wrapped version of :class:`socketserver.UDPServer`.

..  class:: HTTPPServer(...)

    Wrapped version of :class:`http.server.HTTPServer`.

..  class:: CoThreadingMixIn()

    A cooperative equivalent to :class:`socketserver.ThreadingMixIn` which
    spawns a new cothread to handle each request.

..  class:: CoThreadingTCPServer(...)

..  class:: CoThreadingUDPServer(...)

..  class:: CoThreadingHTTPServer(...)

    Convenience classes which apply :class:`CoThreadingMixIn`.

..  class:: BaseServer(...)

    Wrapped version of :class:`socketserver.BaseServer` provided for
    completeness.  User code will typically not use this class directly.
