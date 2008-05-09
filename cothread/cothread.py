'''Simple cooperative threading using coroutines.  The following functions
define the interface provided by this module.

    Spawn(function, arguments...)
        A new cooperative thread, or "task", is created as a call to 
        function(arguments).  Control is not transferred to the task until
        control is yielded.

    Sleep(delay)
    SleepUntil(time)
        The calling task is suspended until the given time.  Sleep(delay)
        suspends the task for at least delay seconds, SleepUntil(time)
        suspends until the specified time has passed (time is defined as the
        value returned by time.time()).
            Control is not returned to the calling task until all other
        active tasks have been processed.
        
    Yield()
        Yield() suspends control so that all other potentially busy tasks can
        run.  

Instances of the Event object can be used for communication between tasks.
The following Event object methods are relevant.

    Wait()
    Wait(timeout)
        Waits for the event object to be signalled or for the timeout to
        expire (if specified).  Returns True if a signal was received, False
        if a timeout ocurred.

    Signal()
        Signals the event object, releasing at least one waiting task.

Similarly the EventQueue can be used for communication.
'''

import sys
import time
import greenlet
import bisect
import traceback

import coselect


__all__ = [
    'Spawn',            # Spawn new task
    
    'Sleep',            # Suspend task for given delay
    'SleepUntil',       # Suspend task until specified time
    'Yield',            # Suspend task for immediate resumption
    
    'Event',            # Event for waiting and signalling
    'EventQueue',       # Queue of objects with event handling
    'WaitForAll',       # Wait for all events to become ready

    'AbsTimeout',       # Converts timeout into absolute deadline format
    'Timedout',         # Timeout exception raised by event waiting
    
    'Quit',             # Immediate process quit
    'WaitForQuit',      # Wait until Quit() is called

    'Timer',            # One-shot cancellable timer
]




class _TimerQueue(object):
    '''A timer queue: objects are held on the queue in timeout sequence
    '''
    __slots__ = ['__values', '__timeouts']

    # The queue is implemented using the bisect function to insert objects
    # into the queue without having to resort the list.  This is cheap and
    # cheerful to implement and runs fast enough, but makes cancellable
    # timers a bit more tedious.
    
    def __init__(self):
        # Keep the priorities separate from the values so that we don't have
        # to worry how values behave under comparison!
        self.__values = []
        self.__timeouts = []
        
    def put(self, value, timeout):
        '''Adds value to the queue with the specified timeout.'''
        index = bisect.bisect(self.__timeouts, timeout)
        self.__values.insert(index, value)
        self.__timeouts.insert(index, timeout)

    def timeout(self):
        '''Returns the timeout of the queue.  Only valid if queue is not
        empty.'''
        return self.__timeouts[0]

    def get_expired(self):
        '''Returns all of the objects in the queue with which have timed out
        relative to the given timeout.'''
        index = bisect.bisect_right(self.__timeouts, time.time())
        result = self.__values[:index]
        del self.__values[:index]
        del self.__timeouts[:index]
        return result

    def __len__(self):
        '''Returns the number of entries on the queue.'''
        return len(self.__timeouts)


# Important system invariants:
#   - A running task is not on any waiting queue.
#       This is enforced by:
#       1) when a task it suspended it is recorded on waiting queues by using
#          a shared _Wakeup() object;
#       2) the .wakeup() method is always used before resuming the task.

class _Scheduler(object):
    '''Coroutine activity scheduler.'''

    __slots__ = [
        '__ready_queue',    # Tasks waiting to run
        '__timer_queue',    # Tasks waiting for timers
        '__greenlet',       # Scheduler greenlet  
        '__poll_callback',  # Set while scheduler being polled from outside
        '__poll_queue',     # Polled files, event masks and tasks
    ]

    # Task wakeup reasons
    __WAKEUP_NORMAL = 0     # Normal wakeup
    __WAKEUP_TIMEOUT = 1    # Wakeup on timeout
    __WAKEUP_INTERRUPT = 2  # Special: transfer scheduler exception to main
    

    @classmethod
    def create(cls):
        '''Creates the scheduler in its own coroutine and starts it running.
        We switch to the scheduler long enough for it to complete
        initialisation.'''
        # We run the scheduler in its own greenlet to allow the main task to
        # participate in scheduling.  This produces its own complications but
        # makes for a more usable system.
        scheduler_task = greenlet.greenlet(cls.__scheduler)
        return scheduler_task.switch(greenlet.getcurrent())

    @classmethod
    def __scheduler(cls, caller):
        '''The top level scheduler loop.  Starts by creating the scheduler,
        and then manages dispatching from the top level.'''

        # First create the scheduler and pass it back to our caller.  The
        # next time we get control it's time to run the scheduling loop.
        self = cls()
        caller.switch(self)

        # If the schedule loop raises an exception then propogate the
        # exception up to the main thread before restarting the scheduler.
        # This has mostly the right effects: a standalone program will
        # terminate, and an interactive program will receive back control,
        # and the scheduler should carry on operating.
        while True:
            try:
                self.__schedule_loop()
            except:
                # Switch to the main task asking it to re-raise the
                # interrupt.  First we have to make sure it's not on the run
                # queue.
                for index, (task, reason) in enumerate(self.__ready_queue):
                    if task is caller:
                        del self.__ready_queue[index]
                        break
                # All task wakeup entry points will interpret this as a 
                # request to re-raise the exception.
                caller.switch(self.__WAKEUP_INTERRUPT)
        
    def __init__(self):
        # List of all tasks that are currently ready to be dispatched.
        self.__ready_queue = []
        # List of tasks waiting for a timeout
        self.__timer_queue = _TimerQueue()
        # Scheduler greenlet: this will be switched to whenever any other
        # task decides to sleep.
        self.__greenlet = greenlet.getcurrent()
        # Initially the schedule loop will run freely with its own select.
        self.__poll_callback = None
        # Dictionary of waitable descriptors for which polling needs to be
        # done.  Each entry consists of an event mask together with a list of
        # interested tasks.
        self.__poll_queue = {}
        

    def __tick(self):
        '''This must be called regularly to ensure that all waiting tasks are
        processed.  It processes all tasks that are ready to run and then runs
        all timers that have expired.'''
        # Wake up all the expired timers on entry.  These go to the end of
        # the ready queue.
        self.wakeup(self.__timer_queue.get_expired(), self.__WAKEUP_TIMEOUT)
        
        # Pick up the ready queue and process every task in it.  When each
        # task is resumed it is passed a flag indicating whether it has been
        # resumed because of an expired timer, or for some other reason
        # (typically either a voluntary suspend, or a successful wait for an
        # event).
        ready_queue = self.__ready_queue
        self.__ready_queue = []
        for task, reason in ready_queue:
            assert not task.dead
            task.switch(reason)

            
    def __schedule_loop(self):
        '''This runs a scheduler loop without returning.  If no poll interval
        is given then when there nothing to be done only timers will be
        run.'''
        while True:
            # Dispatch all waiting tasks
            self.__tick()
            
            # Now see how long we have to wait for the next tick
            if self.__ready_queue:
                # There are ready tasks: don't wait
                delay = 0
            elif self.__timer_queue:
                # There are timers waiting to fire: wait for the first one.
                delay = max(self.__timer_queue.timeout() - time.time(), 0)
            else:
                # Nothing to do: block until something external happens.
                delay = None

            # Finally suspend until something is ready.  The poll queue
            # contains a list of all the file descriptors we're interested
            # in.  First extract the (descriptor, events) pairs, do the
            # suspend, and finally wake up any interested tasks.
            poll_list = [
                (file, queue[0])
                for file, queue in self.__poll_queue.items()]
            self.__wakeup_poll(self.__poll_suspend(poll_list, delay))

                
    def __poll_suspend(self, *poll_args):
        '''Suspends the scheduler until the appropriate ready condition is
        reached.  Returns lists of ready file descriptors and events.'''
        if self.__poll_callback is None:
            # If we're not being polled from outside, run our own poll.
            return coselect.poll_block(*poll_args)
        else:
            # If the scheduler loop was invoked from outside then return
            # control back to the caller: it will provide the select
            # operation we need.
            return self.__poll_callback.switch(*poll_args)


    def poll_scheduler(self, ready_list):
        '''This is called when the scheduler needs to be controlled from
        outside.  It will perform a full round of scheduling before returing
        control to the caller.
            Two values are returned, a list of descriptors and events plus
        a timeout, being precisely the values required for a call to
        poll_block().  A sensible default outer scheduler loop would be

            ready_list = []
            while True:
                ready_list = poll_block(*poll_scheduler(ready_list))
        '''
        assert self.__poll_callback is None, 'Nested pollers will not work'
        
        # Switching to the scheduler will return control to us when the next
        # round is complete.
        #    Note that the first time this is called we may get an incomplete
        # schedule, as we may be resuming inside the dispatch loop: in effect
        # the first call to this routine interrupts the original scheduler.
        self.__poll_callback = greenlet.getcurrent()
        result = self.__greenlet.switch(ready_list)
        self.__poll_callback = None
        
        if result == self.__WAKEUP_INTERRUPT:
            # This case arises if we are main and the scheduler just died.
            raise
        else:
            return result
        

    def spawn(self, function):
        '''Spawns a new task: function is spawned as a new background task
        as a child of the scheduler task.'''
        task = greenlet.greenlet(function, self.__greenlet)
        self.__ready_queue.append((task, self.__WAKEUP_NORMAL))


    def do_yield(self):
        '''Hands control to the next task with work to do, will return as
        soon as there is time.'''
        task = greenlet.getcurrent()
        self.__ready_queue.append((task, self.__WAKEUP_NORMAL))
        # See wait_until() below for explanations on why this isn't trivial.
        if self.__greenlet.switch([]) == self.__WAKEUP_INTERRUPT:
            raise


    def wait_until(self, until, suspend_queue = None, wakeup = None):
        '''The calling task is suspended.  If a deadline is given then the
        task will definitely be woken up when the deadline is reached if not
        before.  If a suspend_queue is given then the task is added to it
        (and it is the caller's responsibility to ensure the task is woken
        up, with a call to wakeup()).
            Returns True iff the wakeup is from a timeout.'''
        # If the timeout has already expired then do nothing at all.
        if until is not None and time.time() >= until:
            return True
            
        # If no wakeup has been specified, create one.  This is a key
        # component for ensuring consistent behaviour of the system: the
        # wakeup object ensures each task is only woken up exactly once.
        if wakeup is None:
            wakeup = _Wakeup()
            
        # If a timeout or a suspension queue has been specified, add
        # ourselves as appropriate.  Failing either of these it's up to the
        # caller to arrange a wakeup.
        if suspend_queue is not None:
            suspend_queue.append(wakeup)
        if until is not None:
            self.__timer_queue.put(wakeup, until)

        # Suspend until we're woken.
        # Normally this call will return control to __tick(), but there are
        # two other cases to consider.  On the very first suspend control is
        # returned to the top of __scheduler(), and more interestingly, on
        # suspending immediately after calling poll_scheduler() control is
        # returned to __select().  This last case expects a list of ready
        # descriptors to be returned, so we have to be compatible with this!
        result = self.__greenlet.switch([])
        if result == self.__WAKEUP_INTERRUPT:
            # We get here if main is suspended and the scheduler decides to
            # die.  Make sure our wakeup is cancelled, and then re-raise the
            # offending exception.
            wakeup.wakeup()
            raise
        else:
            return result == self.__WAKEUP_TIMEOUT
            
    def wakeup(self, wakeups, reason = __WAKEUP_NORMAL):
        '''Wakes up all the given tasks.  Returns the number of tasks
        actually woken.'''
        wakeup_count = 0
        for wakeup in wakeups:
            task = wakeup.wakeup()
            if task is not None:
                self.__ready_queue.append((task, reason))
                wakeup_count += 1
        return wakeup_count

                
    def poll_until(self, poller, until):
        '''Cooperative poll: the calling task is suspended until one of
        the specified waitable objects becomes ready or the timeout expires.
        '''
        # Add our poller to the appropriate poll event queues so that we'll
        # get woken.
        for file, events in poller.event_list():
            # Each entry on the poll queue is a pair: a mask of events being
            # waited for, and a list of pollers to be notified.
            queue = self.__poll_queue.setdefault(file, [0, []])
            queue[0] |= events
            queue[1].append(poller)
        self.wait_until(until, wakeup = poller.wakeup)

    def __wakeup_poll(self, poll_result):
        '''Called with the result of a system poll: a list of file descriptors
        and wakeup reasons.  Each waiting task is informed.'''
        # Work through all the notified files: with each file is a received
        # event mask which we'll pass through to the interested task.
        for file, events in poll_result:
            new_events = 0
            new_pollers = []
            for poller in self.__poll_queue[file][1]:
                events = poller.notify_wakeup(file, events)
                if events:
                    # If a task says that it's still waiting for an event on
                    # this file (evidently the events mask we gave it wasn't
                    # interesting enough) it's going need to go back on the
                    # queue.
                    #     We could allow the task to wake up and do this
                    # processing then instead, but it comes out a little
                    # neater here.
                    new_pollers.append(poller)
                    new_events |= events
            if new_pollers:
                # Oh dear, somebody's still interested.
                self.__poll_queue[file] = [new_events, new_pollers]
            else:
                del self.__poll_queue[file]


class _Wakeup(object):
    '''A _Wakeup object is used when a task is to be suspended on one or more
    queues.  On wakeup the original task is returned, but only once: this is
    used to ensure that entries on other queues are effectively cancelled.'''
    __slots__ = ['__task']
    def __init__(self):
        self.__task = greenlet.getcurrent()
    def wakeup(self):
        task = self.__task
        self.__task = None
        return task
    def woken(self):
        return self.__task is None



class Timedout(Exception):
    '''Waiting for event timed out.'''


def AbsTimeout(timeout):
    '''A timeout is represented in one of three forms:

    None            A timeout that never expires
    interval        A relative timeout interval
    (deadline,)     An absolute deadline

    This routine checks that the given input is in one of these three forms
    and returns a timeout in absolute deadline format.'''
    if timeout is None:
        return None
    elif isinstance(timeout, tuple):
        return timeout
    else:
        return (timeout + time.time(),)

def Deadline(timeout):
    '''Converts a timeout into a deadline.'''
    if timeout is None:
        return None
    else:
        return AbsTimeout(timeout)[0]
    

class EventBase(object):
    '''The base class for implementing events and signals.'''
    __slots__ = ['__waiters']

    def __init__(self):
        # List of tasks currently waiting to be woken up.
        self.__waiters = []

    def _WaitUntil(self, timeout=None):
        '''Suspends the calling task until _Wakeup() is called.  Raises an
        exception if a timeout occurs first.'''
        # The scheduler tells us whether we were resumed on a timeout or on a
        # normal schedule event.
        if _scheduler.wait_until(Deadline(timeout), self.__waiters):
            raise Timedout('Timed out waiting for event')

    def _Wakeup(self, wake_all = True):
        '''Wakes one or all waiting tasks.'''
        if self.__waiters:
            if wake_all:
                # Wake up everybody who was waiting.
                _scheduler.wakeup(self.__waiters)
                self.__waiters = []
            else:
                # Wake up the task at the head of the queue: everybody else
                # will have to wait their turn.  There is a certain delicacy
                # to this: we have to keep going until somebody actually
                # wakes!
                for n, wakeup in enumerate(self.__waiters):
                    if _scheduler.wakeup([wakeup]):
                        break
                del self.__waiters[:n+1]

        

class Spawn(EventBase):
    '''This class is used to wrap cooperative threads: every task (except
    for main) managed by the scheduler should be an instance of this class.'''
    __slots__ = [
        '__function', '__args', '__kargs',
        '__result',
        '__raise_on_wait',
    ]

    finished = property(fget = lambda self: bool(self.__result))
    
    def __init__(self, function, *args, **kargs):
        '''The given function and arguments will be called as a new task.
        All of the arguments will be be passed through to function, except for
        the special keyword raise_on_wait which defaults to False.
            If raise_on_wait is set then any exception raised during the
        execution of this task will be postponed until Wait() is called.  This
        allows such exceptions to be caught without disturbing the normal
        operation of the system.
            Otherwise exceptions are allowed to propogate.  This means that
        they will pass through the scheduler causing it to stop operation:
        there is little point in catching such exceptions.'''
        EventBase.__init__(self)
        self.__function = function
        self.__args = args
        self.__kargs = kargs
        self.__result = ()
        self.__raise_on_wait = kargs.pop('raise_on_wait', False)
        # Hand control over to the run method in the scheduler.
        _scheduler.spawn(self.__run)

    def __run(self, _):
        try:
            # Try for normal successful result.
            self.__result = (True,
                self.__function(*self.__args, **self.__kargs))
        except:
            # Oops: the task terminated with an exception.  
            if self.__raise_on_wait:
                # The creator of the task is willing to catch this exception,
                # so hang onto it now until Wait() is called.
                self.__result = (False, sys.exc_info())
            else:
                # No good.  We can't allow this exception to propagate, as
                # doing so will kill the scheduler.  Instead report the
                # traceback right here.
                print 'Spawned task', self.__function.__name__, \
                    'raised uncaught exception'
                traceback.print_exc()
                self.__result = (True, None)
        self._Wakeup()
        # See wait_until() for an explanation of this return value.
        return []

    def Wait(self, timeout = None):
        '''Waits until the task has completed.  May raise an exception if the
        task terminated with an exception and raise_on_wait was selected.
        Can only be called once, as the result is deleted after call.'''
        if not self.__result:
            self._WaitUntil(timeout)
        ok, result = self.__result
        # Delete the result before returning to avoid cycles: in particular,
        # if the result is an exception the associated traceback needs to be
        # dropped now.
        del self.__result
        if ok:
            return result
        else:
            # Re-raise the exception that actually killed the task here where
            # it can be received by whoever waits on the task.
            # There's a real reference count looping problem here -- can't
            # make the task go away when it's finished with...
            raise result[0], result[1], result[2]


    
class Event(EventBase):
    '''Any number of tasks can wait for an event to occur.  A single value
    can also be associated with the event.'''
    __slots__ = [
        '__value',
        '__auto_reset',
    ]

    value = property(fget = lambda self: self.__value)
    
    def __init__(self, auto_reset = True):
        '''An event object is either signalled or reset.  Any task can wait
        for the object to become signalled, and it will be suspended until
        this occurs.  

        The intial value can be specified, as can the behaviour on succesfully
        signalling a process: if auto_reset=True is specified then only one
        task at a time sees any individual signal on this object.'''
        EventBase.__init__(self)
        self.__value = ()
        self.__auto_reset = auto_reset
        
    def __nonzero__(self):
        '''Tests whether the event is signalled.'''
        return bool(self.__value)
        
    def Wait(self, timeout = None):
        '''The caller will block until the event becomes true, or until the
        timeout occurs if a timeout is specified.  A Timeout exception is
        raised if a timeout occurs.'''
        # If one task resets the event while another is waiting the wait may
        # fail, so we have to loop here.
        deadline = AbsTimeout(timeout)
        while not self.__value:
            self._WaitUntil(deadline)

        ok, result = self.__value
        if self.__auto_reset:
            # If this is an auto reset event then we reset it on exit;
            # this means that we're the only thread that sees it being
            # signalled.  
            self.__value = ()

        # Finally return the result as a value or raise an exception.
        if ok:
            return result
        else:
            raise result
            
    def Signal(self, value = None):
        '''Signals the event.  Any waiting tasks are scheduled to be woken.'''
        self.__value = (True, value)
        self._Wakeup(not self.__auto_reset)

    def SignalException(self, exception):
        '''Signals the event with an exception: the next call to wait will
        receive an exception instead of a normal return value.'''
        self.__value = (False, exception)
        self._Wakeup(not self.__auto_reset)

    def Reset(self):
        '''Resets the event (and erases the value).'''
        self.__value = ()


class EventQueue(EventBase):
    '''A queue of objects.  A queue can also be treated as an interator.'''
    __slots__ = [
        '__queue',
        '__closed',
    ]

    class Empty(Exception):
        '''Event queue is empty.'''
        
    def __init__(self):
        EventBase.__init__(self)
        self.__queue = []
        self.__closed = False

    def __len__(self):
        '''Returns the number of objects waiting on the queue.'''
        return len(self.__queue)

    def Wait(self, timeout = None):
        '''Returns the next object from the queue, or raises a Timeout
        exception if the timeout expires first.'''
        deadline = AbsTimeout(timeout)
        while not self.__queue and not self.__closed:
            self._WaitUntil(deadline)
        if self.__queue:
            return self.__queue.pop(0)
        else:
            raise StopIteration

    def Signal(self, value):
        '''Adds the given value to the tail of the queue.'''
        assert not self.__closed, 'Can\'t write to a closed queue'
        self.__queue.append(value)
        self._Wakeup(False)

    def close(self):
        '''An event queue can be closed.  This will cause waiting to raise
        the StopIteration exception (once existing entries have been read),
        and will prevent any further signals to the queue.'''
        self.__closed = True
        self._Wakeup(True)

    def __iter__(self):
        '''An event queue can itself be treated as an iterator: this allows
        event dispatching using a for loop, and provides some support for
        combining queues.'''
        return self

    def next(self):
        return self.Wait()



class Timer:
    '''A cancellable one-shot timer.'''
    
    def __init__(self, timeout, callback):
        '''The callback will be called after the specified timeout.'''
        self.__deadline = AbsTimeout(timeout)
        self.__callback = callback
        self.__cancel = Event(auto_reset = False)
        Spawn(self.__timer)

    def __timer(self):
        try:
            self.__cancel.Wait(self.__deadline)
        except Timedout:
            # There can be a race between cancelling and timing out: ensure
            # that if we were cancelled before being fired we do nothing.
            if not self.__cancel:
                self.__callback()

    def cancel(self):
        self.__cancel.Signal()
            
            

def WaitForAll(event_list, timeout = None, iterator = False):
    '''Waits for all events in the event list to become ready or for the
    timeout to expire.'''
    # Make sure that the timeout is actually a deadline, then it's easy to do
    # all the waits in sequence.
    timeout = AbsTimeout(timeout)
    result = (event.Wait(timeout) for event in event_list)
    if not iterator:
        # If an interator hasn't been requested then flatten the iterator
        # now.  This ensures that the default behaviour really is to wait for
        # everything to complete.
        result = list(result)
    return result



# Other possibly desirable entites:
#
#   An asynchronous event queue: can be written from another thread
#       This shouldn't be too hard to implement using the existing
#       select/poll mechanism for notificaiton.
#
#   The ability to wait for an event to occur one of a set of objects
#       This would probably require quite deep hooking into the queueing
#       mechanism, and seems of limited value (the natural alternative is to
#       create a task per event).
#
#   The ability to kill a task
#       This is probably doable with the .throw greenlet method (or even with
#       a special wakeup value), but may require some care.



_QuitEvent = Event(auto_reset = False)

def Quit():
    '''Signals the quit event.  Once signalled it stays signalled.'''
    _QuitEvent.Signal()
    
def WaitForQuit(catch_interrupt = True):
    '''Waits for the quit event to be signalled.'''
    try:
        _QuitEvent.Wait()
    except KeyboardInterrupt:
        if catch_interrupt:
            # As a courtesy we quietly catch and discard the keyboard
            # interrupt.  Unfortunately we don't have full control over where
            # this is going to be caught, but if we get it we can exit
            # quietly.
            pass
        else:
            raise


# There is only the one scheduler, which we create right away.  A dedicated
# scheduler task is created: this allows the main task to suspend, but does
# mean that the scheduler is not the parent of all the tasks it's managing.
_scheduler = _Scheduler.create()


def SleepUntil(deadline):
    '''Sleep until the specified deadline.  Note that if the deadline has
    already passed then no yield of control will ooccur.'''
    _scheduler.wait_until(deadline)

def Sleep(timeout):
    '''Sleep until the specified timeout has expired.'''
    _scheduler.wait_until(time.time() + timeout)

    
# Publish the global functions of the scheduler.
PollScheduler = _scheduler.poll_scheduler
Yield = _scheduler.do_yield
