'''Simple cooperative threading using greenlets.  The following functions
define the interface provided by this module.

    Spawn(function, arguments...)
        A new cooperative thread, or "task", is created as a call to 
        function(arguments).  Control is not transferred to the task until
        control is yielded.

    Sleep(delay)
    SleepUntil(time)
    Yield()
        The calling task is suspended until the given time.  Sleep(delay)
        suspends the task for at least delay seconds, SleepUntil(time)
        suspends until the specified time has passed (time is defined as the
        value returned by time.time()), and Yield() is the same as Sleep(0).
            Control is not returned to the calling task until all other
        active tasks have been processed.

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
import select

from utility import *



__all__ = [
    'Spawn',            # Spawn new task
    'Sleep',            # Suspend task for given delay
    'SleepUntil',       # Suspend task until specified time
    'Yield',            # Suspend task for immediate resumption
    'Event',            # Event for waiting and signalling
    'EventQueue',       # Queue of objects with event handling
    'Quit',             # Immediate process quit
    'WaitForAll',
    'WaitForQuit',
    'Quit',
    'AbsTimeout',
    'Timedout',
]




class _TimerQueue(object):
    '''A timer queue: objects are held on the queue in timeout sequence
    '''

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

    def cancel(self, value):
        '''Removes the given value from the queue, or is a no-op if the item
        isn't actually queued.'''
        try:
            index = self.__values.index(value)
        except ValueError:
            pass
        else:
            del self.__values[index]
            del self.__timeouts[index]
        
    def __len__(self):
        '''Returns the number of entries on the queue.'''
        return len(self.__timeouts)


class _Scheduler(object):
    '''Coroutine activity scheduler.'''

    __WAKEUP_NORMAL = 0
    __WAKEUP_TIMEOUT = 1
    __WAKEUP_INTERRUPT = 2

    @classmethod
    def create(cls, poll_interval):
        '''Creates the scheduler in its own coroutine and starts it running.
        We switch to the scheduler long enough for it to complete
        initialisation.'''
        scheduler_task = greenlet.greenlet(cls.__scheduler)
        return scheduler_task.switch(greenlet.getcurrent(), poll_interval)

    @classmethod
    def __scheduler(cls, caller, poll_interval):
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
                self.__schedule_loop(poll_interval)
            except:
                # Now transfer control to the main task in a controlled way.
                # Cancel any occurrences of the main task on any queues to
                # avoid strange multiple reentry issues.
                if caller in self.__ready_queue:
                    del self.__ready_queue[self.__ready_queue.index(caller)]
                self.__timer_queue.cancel(caller)
                self.__allow_suspend = True
                caller.switch(self.__WAKEUP_INTERRUPT)

        
    def __init__(self):
        # List of all tasks that are currently ready to be dispatched.
        self.__ready_queue = []
        # List of tasks waiting for a timeout
        self.__timer_queue = _TimerQueue()
        # Scheduler greenlet: this will be switched to whenever any other
        # task decides to sleep.
        self.__greenlet = greenlet.getcurrent()
        # Don't allow hook routines to suspend: this is rather like an
        # interrupt context, and can cause mayhem.  We start up with this
        # true so that the main thread creating us can suspend to here.
        #    Note that every instance of .switch() is called in a context
        # where this flag is known to be True.
        self.__allow_suspend = True
        # Initially the schedule loop will run freely with its own select.
        self.__poll_callback = None
        

    def __schedule_loop(self, poll_interval=None):
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
                # There are timers waiting to fire: wait for the first one,
                # but don't forget to poll if the wait is too long.
                delay = max(self.__timer_queue.timeout() - time.time(), 0)
                if poll_interval and delay > poll_interval:
                    delay = poll_interval
            else:
                # Nothing to do: just poll
                delay = poll_interval

            # Finally suspend until something is ready.
            iwtd, owtd, ewtd = self.__select([], [], [], delay)

                
    def __select(self, iwtd, owtd, ewtd, timeout):
        '''Suspends the scheduler until the appropriate ready condition is
        reached.  Returns lists of ready sockets.'''
        if self.__poll_callback is None:
            # If we're not being polled from outside, run our own select.
            return select.select(iwtd, owtd, ewtd, timeout)
        else:
            # If the scheduler loop was invoked from outside then return
            # control back to the caller.  
            callback = self.__poll_callback
            self.__poll_callback = None
            self.__allow_suspend = True
            return callback.switch(iwtd, owtd, ewtd, timeout)


    def poll_scheduler(self, iwtd, owtd, ewtd):
        '''This is called when the scheduler needs to be controlled from
        outside.  It will perform a full round of scheduling before returing
        control to the caller.
            Four values are returned, being precisely the values required for
        a call to select().  A sensible default outer scheduler loop would be

            iwtd, owtd, ewtd = [], [], []
            while True:
                iwtd, owtd, ewtd = select(*poll_scheduler(iwtd, owtd, ewtd))
        '''
        # Set up the poll callback hook so we get control back
        assert self.__poll_callback is None
        assert self.__allow_suspend
        # Switching to the scheduler will return control to us when the next
        # round is complete.
        #    Note that the first time this is called we may get an incomplete
        # schedule, as we may be resuming inside the dispatch loop: in effect
        # the first call to this routine interrupts the original scheduler.
        self.__poll_callback = greenlet.getcurrent()
        return self.__greenlet.switch(iwtd, owtd, ewtd)
        

    def __tick(self):
        '''This must be called regularly to ensure that all waiting tasks are
        processed.  It processes all tasks that are ready to run and then runs
        all timers that have expired.'''
        assert greenlet.getcurrent() is self.__greenlet

        # Pick up the expired timers on entry.  We do this now (rather than
        # at the end of task processing) to help with fairness.
        expired_timers = self.__timer_queue.get_expired()
        
        # Pick up the ready queue and process every task in it.  When each
        # task is resumed it is passed a flag indicating whether it has been
        # resumed because of an expired timer, or for some other reason
        # (typically either a voluntary suspend, or a successful wait for an
        # event).
        ready_queue = self.__ready_queue
        self.__ready_queue = []
        self.__allow_suspend = True
        
        for task in ready_queue:
            assert not task.dead
            task.switch(self.__WAKEUP_NORMAL)
            
        # Also expire all the timers
        for task in expired_timers:
            assert not task.dead
            task.switch(self.__WAKEUP_TIMEOUT)
            
        self.__allow_suspend = False

            
    def spawn(self, function):
        '''Spawns a new task: function(*argv,**argk) is spawned as a new
        background task.  The new task will not be scheduled on this tick.
        '''
        task = greenlet.greenlet(function, self.__greenlet)
        self.__ready_queue.append(task)


    def wait_until(self, until, suspend_queue = None):
        '''The calling task is suspended.  If a deadline is given then the
        task will definitely be woken up when the dealine is reached if not
        before.  If a suspend_queue is given then the task is added to it
        (and it is the caller's responsibility to ensure the task is woken
        up, with a call to wakeup()).
        '''
        task = greenlet.getcurrent()
        
        assert self.__allow_suspend, 'Hook routines are not allowed to suspend'
        assert task is not self.__greenlet, 'Scheduler cannot suspend'
        assert self.__greenlet, 'Scheduler seems to have vanished!'
        assert until is not None or suspend_queue is not None

        # Either a timeout or a suspension queue (or maybe both) should have
        # been specified.  
        if suspend_queue is not None:
            suspend_queue.append(task)
        if until:
            self.__timer_queue.put(task, until)

        # At this point we've no idea which sockets are ready...  Switch back
        # to the scheduler with what we've got.
        result = self.__greenlet.switch([], [], [])

        # There are three possible wakeup reasons: normal wakeup
        if result != self.__WAKEUP_NORMAL and suspend_queue is not None:
            # If the task didn't resume normally then remove it from the
            # suspend queue.  If it did then presumably the task that woken
            # us has already done this.
            del suspend_queue[suspend_queue.index(task)]
        if result == self.__WAKEUP_INTERRUPT:
            # Re-raise the interrupt that the scheduler caught for us.
            raise
        else:
            return result == self.__WAKEUP_TIMEOUT

            
    def wakeup(self, wakeups):
        '''Wakes up all the given tasks and removes any which are on the
        timer queue.'''
        self.__ready_queue.extend(wakeups)
        for task in wakeups:
            # It's a little irritating: we have to cancel timers even if
            # there aren't any!
            #    Note that we have to cancel the timers here rather than on
            # wakeup, as otherwise the newly woken task might see the timer
            # wakeup first, which would be quite unfortunate...
            self.__timer_queue.cancel(task)


# There is only the one scheduler, which we create right away.  A dedicated
# scheduler task is created: this allows the main task to suspend, but does
# mean that the scheduler is not the parent of all the tasks it's managing.
_scheduler = _Scheduler.create(1e-2)


class QuitScheduler(Exception):
    '''Exception raised on quit request.  This should propagate through the
    scheduler to abort all activity.'''


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
    else:
        try:
            _, = timeout
            return timeout
        except TypeError:
            return (timeout + time.time(),)

def Deadline(timeout):
    '''Converts a timeout into a deadline.'''
    if timeout is None:
        return None
    else:
        return AbsTimeout(timeout)[0]
    

class EventBase(object):
    '''The base class for implementing events and signals.'''

    def __init__(self):
        # List of tasks currently waiting to be woken up.
        self.__waiters = []

    def _WaitUntil(self, timeout=None):
        '''Suspends the calling task until _Wakeup() is called.'''
        # The scheduler tells us whether we were resumed on a timeout or on a
        # normal schedule event.
        if _scheduler.wait_until(Deadline(timeout), self.__waiters):
            raise Timedout('Timed out waiting for event')

    def _Wakeup(self, wake_all = True):
        '''Wakes one or all waiting tasks.'''
        if self.__waiters:
            if wake_all:
                # Wake up everybody who was waiting.
                wakeup = self.__waiters
                self.__waiters = []
            else:
                # Wake up the task at the head of the queue: everybody else
                # will have to wait their turn.
                wakeup = self.__waiters[:1]
                del self.__waiters[:1]
            _scheduler.wakeup(wakeup)

        

class Spawn(EventBase):
    '''This class is used to wrap cooperative threads: every task (except
    for main) managed by the scheduler should be an instance of this class.'''

    finished = property(fget = lambda self: self.__finished)
    
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
        self.__raise_on_wait = keyword_argument(kargs, 'raise_on_wait')
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
                print 'Spawed task raised uncaught exception in', \
                    self.__function.__name__
                traceback.print_exc()
                self.__result = (True, None)
        self._Wakeup()

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
        if not self.__value:
            self._WaitUntil(timeout)

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
    '''A queue of objects.'''

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
        if not self.__queue:
            self._WaitUntil(timeout)
        if self.__queue:
            return self.__queue.pop(0)
        else:
            assert self.__closed, 'Why is the queue empty?'
            raise StopIteration
            

    def Signal(self, value):
        '''Adds the given value to the tail of the queue.'''
        assert not self.__closed, 'Can\'t write to a closed queue'
        self.__queue.append(value)
        self._Wakeup(False)

    def close(self):
        '''An event queue can be closed.  This will cause waiting to raise
        the StopIteration exception, and will prevent any further signals to
        the queue.'''
        self.__closed = True
        self._Wakeup(True)

    def __iter__(self):
        '''An event queue can itself be treated as an iterator: this allows
        event dispatching using a for loop, and provides some support for
        combining queues.'''
        return self

    def next(self):
        return self.Wait()



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



# Other highly desireably entites:
#
#   An asynchronous event queue: can be written from another thread
#
#   Cancellable timers
#
#   The ability to wait for an event to occur one of a set of objects
#
#   The ability to wait for a coroutine to complete

class AsyncEventQueue(EventBase):
    def __init__(self):
        pass

class Timer(EventBase):
    def __init__(self, timeout, callback, retrigger = False):
        '''Triggers a callback to be made after the specified timeout.  If
        retriggering is selected then the ti
            Timers are called from the dedicated timer thread, which means
        that blocking in one timer will cause all other timers to block. 
        '''
        pass
            

# Publish the global functions of the master scheduler.

PollScheduler = _scheduler.poll_scheduler


def SleepUntil(deadline):
    '''Sleep until the specified deadline.'''
    _scheduler.wait_until(deadline)

def Sleep(timeout):
    '''Sleep until the specified timeout has expired.'''
    _scheduler.wait_until(time.time() + timeout)

def Yield():
    '''Yield control to another task.  Equivalent to a zero sleep.'''
    # Implement this as a timeout which expires instantly.
    _scheduler.wait_until(0)


_QuitEvent = Event(auto_reset = False)

def Quit():
    '''Signals the quit event.  Once signalled it stays signalled.'''
    _QuitEvent.Signal()
    
def WaitForQuit(catch_interrupt = True):
    '''Waits for the quit event to be signalled.'''
    if catch_interrupt:
        try:
            _QuitEvent.Wait()
        except KeyboardInterrupt:
            # As a courtesy we quietly catch and discard the keyboard
            # interrupt.  Unfortunately we don't have full control over where
            # this is going to be caught, but if we get it we can exit
            # quietly.
            pass
    else:
        _QuitEvent.Wait()




# def install_threads():
#     global qapp
#     import qt, sys
#     from dls.ca2.catools import ca_pend_event
#     ca_green_setup()
#     if qt.qApp.startingUp():
#         qapp = qt.QApplication(sys.argv)
#     class Timer(qt.QObject):
#         def timerEvent(self, event):
#             ca_pend_event(1e-9)
#             tick()
#     t = Timer(qt.qApp)
#     t.startTimer(1)
# 
# def exec_loop(worker = None):
#     """optionally start worker in new green thread
#     and run qt event loop with ms scheduler wakeup timer"""
#     import qt
#     install_threads()
#     result = runme(worker)
#     qt.qApp.exec_loop()
#     return result[0]
# 
# def runme(worker):
#     # factored out of start and start gui
#     result = [None]
#     def run_and_quit():
#         "run main function and then quit event loop"
#         result[0] = worker()
#         quit()
#     if worker is not None:
#         spawn(run_and_quit)
#     return result
# 
# def mainloop():
#     from dls.ca2.catools import ca_pend_event
#     while not done[0]:
#         t0 = time.time()
#         # service channel access
#         ca_pend_event(1e-9)
#         # run scheduled threads
#         tick()
#         # calculate time remaining until next tick
#         t1 = time.time()
#         td = 1e-3 - (t1 - t0)
#         if td < 1e-9:
#             td = 1e-9
#         # wait
#         time.sleep(td)
# 
# def start(worker = None):
#     "optionally start worker in new green thread and run event loop"
#     result = runme(worker)
#     mainloop()
#     return result[0]
# 
# def quit():
#     "quit event loop"
#     done[0] = True
#     if qapp:
#         qapp.quit()
# 
# __all__ = ["getcurrent", "Yield", "spawn", "co_sleep", "tick", "queue", "start", "exec_loop", "quit", "install_threads", "asleep", "mainloop"]
# 
# if __name__ == "__main__":
#     from pkg_resources import require
#     require("dls.ca2")
#     from dls.ca2.catools import caget
#     # timer test
#     def test():
#         while True:
#             t0 = time.time()
#             print caget("SR21C-DI-DCCT-01:SIGNAL").value
#             asleep(0.2)
#             print time.time() - t0
#     # start sets up channel access, spawns function, and runs event loop
#     start(test)
#     
