.. include:: <s5defs.txt>

.. role:: prettyprint
    :class: prettyprint

.. |emdash| unicode:: U+02014 .. EM DASH


==========================================
Training: Channel Access with ``cothread``
==========================================

:Author: Michael Abbott

Documentation:
    file:///dls_sw/prod/common/python/RHEL6-x86_64/cothread/2-15/docs/html/index.html

    https://cothread.readthedocs.io

Sources:
    file:///dls_sw/prod/common/python/RHEL6-x86_64/cothread/2-15
    https://github.com/dls-controls/cothread

Development version:
    file:///home/mga83/epics/cothread


Cothread
========

The ``cothread`` library provides EPICS "Channel Access" bindings for Python.
The library comprises two parts:

* ``cothread`` itself: "cooperative threads".

* ``cothread.catools`` provides channel access bindings.

Because EPICS involves communication with other machines events may happen at
any time.  The ``cothread`` library provides a mechanism for managing these
updates with the minimum of interference with the rest of the program.


Cothread catools bindings
=========================

The EPICS Channel Access Python interface consists of three functions:

``caget(pvs, ...)``
    Retrieves value from a single PV or a list of PVs.

``caput(pvs, values, ...)``
    Writes value or values to a single PV or list of PVs.

``camonitor(pvs, callback, ...)``
    Creates "subscription" with updates every time a PV changes: ``callback`` is
    called with a new value every time any listed PV updates.


Preliminaries
=============

Need to import ``cothread``, all of the examples will start with
the following code, 2.15 is the current release:

.. code:: python

    from pkg_resources import require
    require('cothread==2.15')

    import cothread
    from cothread.catools import *

Channel access waveform data is returned as ``numpy`` arrays, so it will be
convenient to include this in our list of imports:

.. code:: python

    import numpy


Example: Printing a PV
======================

Calling ``caget`` with a PV name returns the value of the PV.

.. code:: python

    print caget('SR-DI-DCCT-01:SIGNAL')

Calling ``caget`` with a list of PV names returns a list of PV values.

.. code:: python

    bpms = ['SR%02dC-DI-EBPM-%02d:SA:X' % (c+1, n+1)
        for c in range(24) for n in range(7)]
    sax = caget(bpms)
    print sax

Note that calling ``caget`` with a long list is potentially *much* faster than
calling ``caget`` on each element of the list in turn, as passing a list to
``caget`` allows all fetches to proceed concurrently.


Testing Speed of ``caget``
==========================

Compare:

.. code:: python

    import time
    start = time.time(); caget(bpms); print time.time() - start

with

.. code:: python

    start = time.time(); [caget(bpm) for bpm in bpms]; print time.time() - start

I tend to get a difference of a factor of around 50 between these two tests.


Exercise: Timing test
=====================

Exercise: put everything in a file and run this test standalone.  Try adding
more PVs and making the test controlled by a command line parameter.


Shape Polymorphism
==================

As we've already seen, the behaviour of the three channel access functions
varies depending on whether the first argument is a string or a list of strings,
for example:

.. code:: python

    print caget('SR-DI-DCCT-01:SIGNAL')
    print caget(['SR-DI-DCCT-01:SIGNAL', 'SR-DI-DCCT-01:LIFETIME'])

Similarly ``caput`` can write to multiple pvs, in which case a single value or a
list of values can be passed.

.. code:: python

    caput(['TEST:PV1', 'TEST:PV2'], 3)              # Writes 3 to both
    caput(['TEST:PV1', 'TEST:S'], [10, 'testing'])  # Writes different values

    # To write a repeated array to multiple TEST:PVs need to use repeat_value
    caput(['TEST:WF1', 'TEST:WF2'], [1, 2], repeat_value = True)

.. container:: incremental

    Note: this is the *only* case where ``repeat_value=True`` is needed.


Example: Monitoring a PV
========================

Updates to a PV result in a callback function being called.

.. code:: python

    def print_update(value):
        print value.name, value

    m = camonitor('SR-DI-DCCT-01:SIGNAL', print_update)
    cothread.Sleep(10)
    m.close()

Updates arrive in the background until we close the monitor, but for normal
applications we leave the monitor open until the application exits.


``camonitor`` for Lists of PVs
==============================

If ``camonitor`` is passed a list of PVs it expects the update function to take
a second argument which is used as an index.

.. code:: python

    def print_update(value, index):
        print value.name, index, value

    mm = camonitor(bpms, print_update)
    cothread.Sleep(1)
    for m in mm:
        m.close()

.. container:: incremental

    If the index is not needed there is no particular benefit to calling
    ``camonitor`` on lists of PVs, unlike for ``caget`` and (it depends)
    ``caput``.


Exercise: ``camonitor`` and ``caput``
=====================================

Use ``camonitor`` and ``caput`` to monitor ``TEST:PV1`` and add 1 to it after a
couple of seconds.

Use ``cothread.Sleep(...)`` for sleeping.

.. Warning::

    Don't use ``time.sleep(...)`` when using cothread: this will prevent updates
    from taking place!

Use ``cothread.WaitForQuit()`` at the end of your script if there's nothing else
to do while cothread does its work.


A note on the last exercise
===========================

The obvious answer is to call ``cothread.Sleep`` in the camonitor callback
function, eg:

.. code:: python

    def do_update(value):
        cothread.Sleep(1)
        caput(value.name, value + 1)

    m = camonitor('TEST:PV1', do_update)
    cothread.Sleep(10)
    m.close()

Unfortunately doing this has the unfortunate side effect of blocking
all other camonitor updates during the ``Sleep``.

Only one camonitor callback function is processed at a time.  If you need to do
long lasting work in response to a PV update, push the processing somewhere else
with ``Spawn`` or ``Event``.


Augmented Values
================

Values returned by ``caget`` and delivered by ``camonitor`` are "augmented" by
extra information.  The following two fields are always present:

``.name``
    Contains the full name of the requested PV.

``.ok``
    Will be ``True`` for values fetched without trouble, ``False`` if value is
    not really a value!

For example:

.. code:: python

    v = caget('SR-DI-DCCT-01:SIGNAL')
    print v.name, v.ok, v


Augmented Values are Ordinary
=============================

Note that ``v`` (from above) is an ordinary number:

.. code:: python

    print isinstance(v, float)

However, it's not completely ordinary:

.. code:: python

    print type(v), type(1.0)

.. container:: incremental

    It will behave just like an ordinary float, but can be made completely
    ordinary with the ``+`` operator:

    ::

        print +v, type(+v)

    However you should not normally need to use this!


Getting Values with Timestamps
==============================

It is possible to get timestamp information with a retrieved or monitored PV,
but it needs to be requested:

.. code:: python

    v = caget('SR-DI-DCCT-01:SIGNAL', format = FORMAT_TIME)
    print v.name, v, v.datetime

The timestamp is also available in raw Unix format (seconds since 1970):

.. code:: python

    print v.timestamp


Example: Gathering Updates
==========================

We'll monitor a requested number of updates and gather them into a list.  For
this example the state is held in the local variables of the ``gather``
function: note the use of a nested function.

.. code:: python

    def gather(pv, count):
        values = []
        done = cothread.Event()
        def update(value):
            values.append(value)
            if len(values) >= count:
                done.Signal()
        m = camonitor(pv, update)
        done.Wait()
        m.close()
        return values

    print gather('SR21C-DI-DCCT-01:SIGNAL', 10)


Example: Circular Updates Buffer
================================

Let's try a different version with a circular buffer.  In this case we need a
class because the buffer will remain in existence for longer.

.. code:: python

    class Gather:
        def __init__(self, pv, count):
            self.count = count
            self.values = [0] * count
            self.inptr = 0
            camonitor(pv, self.update)
        def update(self, value):
            self.values[self.inptr] = value
            self.inptr = (self.inptr + 1) % self.count
        def get(self):
            return self.values[self.inptr:] + self.values[:self.inptr]

    buf = Gather('SR21C-DI-DCCT-01:SIGNAL', 10)
    cothread.Sleep(1)
    print buf.get()
    cothread.Sleep(5)
    print buf.get()

This buffer can now safely be left running and will at any time return the last
``count`` values received.


Example: Gathering Arrays
=========================

Working with ``numpy`` arrays can be much more efficient than working with
Python lists of values:

.. code:: python

    x = numpy.array(caget(bpms))
    print x.mean(), x.std()
    print x - x.mean()

However, when it matters, timestamp information and other extended attributes
are lost when gathering values into arrays, so if the timestamps are needed a
little more care is required:

.. code:: python

    rawx = caget(bpms, format = FORMAT_TIME)
    x = numpy.array(rawx)
    tx = numpy.array([v.timestamp for v in rawx])
    print tx.max() - tx.min()   # Check spread of timestamps


Example: Default Error Handling
===============================

For ``caget`` we only really need to worry about fetching PVs that don't exist,
for ``camonitor`` we may also need to pay attention to PVs becoming
disconnected.  The default behaviour of ``cothread`` produces sensible results,
but this can be overridden.


This behaviour of raising an exception when ``caget`` and ``caput`` fails is the
best default behaviour, because in routine naive use if a PV is unavailable then
this is an unrecoverable error.  However, this isn't always what we want.


Adjusting the Timeout
=====================

.. code:: python

    caget('bogus')

This raises an exception after five seconds.  The timeout can be adjusted with
an explicit argument:

.. code:: python

    caget('bogus', timeout = 1)

Alternatively, when fetching very large numbers of PVs through the gateway it
can happen that the default five second timeout isn't long enough.


Catching Errors from ``caget``
==============================

We can ask ``caget`` to return an error value instead of raising an exception:

.. code:: python

    v1, v2 = caget(['bogus', 'SR-DI-DCCT-01:SIGNAL'], throw = False)
    print v1.ok, v2.ok

Note that if a pv is not ``ok`` we can't test for things like timestamps:

.. code:: python

    v = caget('bogus', format = FORMAT_TIME, throw = False)
    print v.name, v.ok
    print v.datetime

This raises an exception when trying to interrogate the ``datetime`` field on a
PV that never arrived!


Catching Errors from ``caput``
==============================

The same applies to ``caput``.  We'll try writing to a PV we can write to, one
we can't, and one that doesn't exist:

.. code:: python

    pvs = ['TEST:PV1', 'bogus', 'SR-DI-DCCT-01:SIGNAL']
    results = caput(pvs, 1, timeout = 1, throw = False)
    for result in results:
        print result.name, result.ok
        print result

Note that a complete description of the error is in the failing results: in this
case each result is a catchable exception object with a descriptive error
message as its string representation.


Cothread and Qt
===============

The cothread library relies on cooperative transfer of control between
cothreads, and similarly Qt has its own mechanism of events and notifications.
For cothread and Qt to work together, these two libraries need to be introduced
to each other.

Fortunately this is easy.  Run:

.. code:: python

    cothread.iqt()

It's safest to run this before importing any Qt dependent libraries.

This function will create and return the Qt application object if you need it.


Plotting: Preamble
==================

A certain amount of boilerplate preamble is required to get interactive plotting
working with ``dls-python``.  We'll show the complete set:

.. code:: python

    from pkg_resources import require
    require('cothread==2.15')
    require('matplotlib')

    import cothread
    from cothread.catools import *

    import numpy

    cothread.iqt()

    import pylab
    pylab.ion()


Plotting: An Example
====================

Now we can fetch and plot a waveform:

.. code:: python

    wfx = caget('SR-DI-EBPM-01:SA:X')
    ll = pylab.plot(wfx)

Now let's make it update continuously:

.. code:: python

    def update_ll(wfx):
        ll[0].set_ydata(wfx)
        pylab.draw()

    m = camonitor('SR-DI-EBPM-01:SA:X', update_ll)

Exercise: Plot both X and Y on the same graph.  Hint: ``SR-DI-EBPM-01:BPMID``
contains a good x-axis.


Advanced Topics
===============


Advanced Topic: Cothreads
=========================

We've already seen cothreads: ``camonitor`` callbacks occur "in the background",
really they occur on a dedicated cothread.

Cothreads are *cooperative* "threads", which means a cothread will run until it
deliberately relinquishes control.  This has advantages and disadvantages:

Advantage
    No locking is required, a cothread will not run when it's not expected.

Disadvantage
    A cothread that won't relinquish control will block all other cothreads.

Note that Python can't make use of multiple cores.


Creating a Cothread
===================

Creating a cothread is very easy: just define the function to run in the
cothread and call ``cothread.Spawn``:

.. code:: python

    running = True
    def background(name, sleep=1):
        while running:
            print 'Hello from', name
            cothread.Sleep(sleep)

    cothread.Spawn(background, 'test1')
    cothread.Spawn(background, 'test2', sleep = 2)

    cothread.Sleep(10)
    running = False

    cothread.Sleep(3)


Communicating with Cothreads
============================

Communicate using event objects and queues:

``cothread.Event()``
    Creates an event object which is either ready or not ready.  When it's ready
    it has a value.

``cothread.EventQueue()``
    Almost exactly like an event object, but multiple values can be waiting.

Both objects support two methods:

event\ ``.Signal(value)``
    Makes event object ready with given value.

event\ ``.Wait(timeout=None)``
    Suspends cothread until object is ready, consumes and returns value.


Example: Using ``Event``
========================

.. code:: python

    class PV:
        def __init__(self, pv):
            self.event = cothread.Event()
            camonitor(pv, self.__on_update, format = FORMAT_TIME)
        def __on_update(self, value):
            self.event.Signal(value)
        def get(self, timeout=None):
            return self.event.Wait(timeout)

    import time
    pv = PV('SR21C-DI-DCCT-01:SIGNAL')
    for n in range(5):
        v = pv.get()
        print v.timestamp, time.time()
        cothread.Sleep(1)

Note that we always get the latest value, even though the PV updates at 5Hz.

Cothread already implements a fuller featured version of this class available as
``cothread.pv.PV``, and another variant ``cothread.pv.PV_array``.


Cothread Suspension Points
==========================

The following functions are cothread suspension points (where control can be
yielded to another cothread):

* ``Sleep()``, ``SleepUntil()``, ``Yield()``
* event\ ``.Wait()``
* ``caget()``
* ``caput()`` most of the time (see documentation to avoid suspension).

The following cothread modules provide extra cothread aware suspension points,
see documentation for details:

* ``cothread.coselect``: provides ``select()`` and ``poll`` functionality.
* ``cothread.cosocket``: provides cothread aware socket API.


Cothreads and Real Threads
==========================

Python threads are created with the ``threading.Thread`` class.  A Python thread
cannot safely call cothread methods ... except for ``cothread.Callback()``,
which arranges for its argument to be called in a cothread:

.. code:: python

    def callback_code(n):
        print 'cothread tick', n

    import time
    def thread_code(count):
        for n in range(count):
            print 'thread tick', n
            cothread.Callback(callback_code, n)
            time.sleep(0.5)

    import thread
    thread.start_new_thread(thread_code, (5,))
    cothread.Sleep(5)


Slightly more Realistic Version
===============================

.. code:: python

    def consumer(event):
        while True:
            n = event.Wait()
            print 'consumed', n

    import time
    def producer(event, count):
        for n in range(count):
            print 'thread tick', n
    #        event.Signal(n)
            cothread.Callback(lambda n: event.Signal(n), n)
            time.sleep(0.5)

    import thread
    event = cothread.Event()
    cothread.Spawn(consumer, event)
    thread.start_new_thread(producer, (event, 5))
    cothread.Sleep(5)

Try replacing the ``Callback`` call with a direct ``Signal`` call and see what
happens.

Bonus question: what's wrong with this?

.. code:: python

    cothread.Callback(lambda: event.Signal(n))
