#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import threading

import cothread

class TestCoThread(unittest.TestCase):
    def test_spawn_wait(self):
        state = [0]

        @cothread.Spawn
        def task():
            state[0] = 1
            return 42

        # not started yet
        self.assertEqual(state, [0])

        V = task.Wait(0.1)

        self.assertEqual(V, 42)

    def test_spawn_yield(self):
        state = [0]

        @cothread.Spawn
        def task():
            state[0] = 1
            return 42

        # not started yet
        self.assertEqual(state, [0])

        cothread.Yield()

        self.assertEqual(state, [1])

        V = task.Wait(0) # pool because task should already be complete

        self.assertEqual(V, 42)

    def test_event(self):
        state = [0]
        E = cothread.Event()

        @cothread.Spawn
        def task():
            state[0] = 1
            E.Signal(43)

        V = E.Wait(0.1)

        self.assertEqual(V, 43)

class TestCoOtherThread(unittest.TestCase):
    # test interactions with a blocking worker thread

    def test_callback(self):
        cb = cothread.GetCallback()

        # we are the main thread
        self.assertTrue(cb is cothread.Callback)
        self.assertTrue(cb is cothread.GetCallback(threading.current_thread()))

        state = [0]
        E = cothread.Event()

        def action(S,evt):
            S.append(2)
            evt.Signal()

        def task():
            state[0] = 1
            cb(action, state, E)

        T = threading.Thread(target=task)
        T.start()

        E.Wait(0.1)

        T.join(0.1)

        self.assertEqual(state, [1,2])

    def test_queue(self):
        Q1 = cothread.ThreadedEventQueue()
        Q2 = cothread.ThreadedEventQueue()
        _abort = object()

        def mathtask():
            while True:
                inp = Q1.Wait(0.1)
                if inp is _abort:
                    Q2.Signal(_abort)
                    return
                R = reduce(lambda a,b:a+b, inp[1:], inp[0])
                Q2.Signal(R)

        T = threading.Thread(target=mathtask)
        T.start()

        Q1.Signal([1,2,3])
        V = Q2.Wait(0.1)
        self.assertEqual(V, 6)

        Q1.Signal([7,3])
        V = Q2.Wait(0.1)
        self.assertEqual(V, 10)

        Q1.Signal(_abort)
        V = Q2.Wait(0.1)
        self.assertTrue(V is _abort)

        T.join(0.1)

class TestCoMultiThread(unittest.TestCase):
    # test independent cothreads running in different OS threads
    def test_queue(self):
        Q1 = cothread.ThreadedEventQueue()

        state = []

        def task():
            E = cothread.Event(auto_reset=False)
            Q1.Signal((cothread.GetCallback(), E))
            @cothread.Spawn
            def innertask():
                state.append(('inner',
                              threading.current_thread()))
            V = E.Wait(0.1)
            Q1.Signal(V+1)

        T = threading.Thread(target=task)
        T.start()

        workercb, evt = Q1.Wait(0.1)
        self.assertTrue(workercb is not cothread.Callback)
        self.assertTrue(workercb is cothread.GetCallback(T))
        workercb(evt.Signal, 41)

        V = Q1.Wait(0.1)
        self.assertTrue(V, 42)
        self.assertEqual(state, [('inner', T)])

        T.join(0.1)

if __name__=='__main__':
    unittest.main()
