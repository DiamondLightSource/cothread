import time
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from cothread import *

def task(done, n):
    done.Wait()

done = Event(auto_reset = False)

N = int(sys.argv[1])
stack_size = int(sys.argv[2])

def test():
    now = time.time()
    tasks = [Spawn(task, done, n, stack_size=stack_size) for n in range(N)]
    done.Signal()
    WaitForAll(tasks)
    end = time.time()

    print('Spawning', N, 'tasks in', end-now, 'seconds')

test()
test()
test()
test()
