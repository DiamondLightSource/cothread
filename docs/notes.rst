..  _notes:

Cothread Architecture Notes
===========================

Some notes on key architectural issues in the :mod:`cothread` scheduler.


Coroutine Switching
-------------------

There are precisely 7 calls to :func:`switch` in the :mod:`cothread` library,
and it's crucial that they work together correctly.  These calls are (in order
of appearance in the code).

- During scheduler creation (in the :func:`.create` method of
  :class:`_Scheduler`) we create a separate scheduler task and switch to that.
  This should be called from the main parent task (ie, when it ends, the
  application terminates).

- As soon as the scheduler has been initialised, control is returned to the
  main task.  This is in :func:`.__scheduler`, which carries a top level loop
  for restarting the scheduler.

- If the main scheduler loop :func:`.__schedule_loop` raises an exception,
  control is switched to the main parent task with a special
  :const:`.__WAKEUP_INTERRUPT` return code.  The main task will at this point
  normally be waiting for a normal scheduler wake up.

- The :func:`.__tick` dispatcher switches to all ready tasks in turn passing a
  wakeup code, either :const:`.__WAKEUP_NORMAL` or :const:`.__WAKEUP_TIMEOUT`.

- If :func:`.poll_scheduler` has been called, and thus
  :func:`.__poll_callback` is set, the routine :func:`.__poll_suspend` will
  switch back to the suspended :func:`.poll_scheduler` call.  In this case
  special polling arguments are passed (this should be a list of (descriptor,
  flags) pairs, together with a timeout), and a list of active descriptors
  should be returned.

- :func:`.poll_scheduler` defines the other side of this switch: a list of
  ready descriptors is passed in a switch to the scheduler task, and the
  polling arguments described above are returned from the
  :func:`.poll_scheduler` call -- unless a :const:`.__WAKEUP_INTERRUPT` switch
  has occurred!

- The normal place where control is switched to the scheduler is in the middle
  of :func:`.wait_until`.  We have to pass an empty list (to be compatible
  with the :func:`.poll_scheduler` switch), and a wakeup reason should be
  returned.


Callback
--------

The new :func:`Callback` mechanism raises some issues.

1.  It is possible for the callback queue to grow without limit, and this is
    invisible to the poor users.  This can happen if too much time is spent in
    processing updates.

2.  The callback queue is processed without yielding.  If the callback queue is
    very long this can cause unresponsive behaviour.  Unfortunately inserting a
    yield on every callback is surprisingly costly.

3.  We lack any mechanism for observing what's going on inside the library.
