#!/usr/bin/env python3

import os

import require
from cothread import *
from cothread.coselect import *


def reader(r):
    while True:
        ll = poll_list(((r, POLLIN),))
        if ll:
#            if ll[r] & POLLIN:
            if ll[0][1] & POLLIN:
                l = os.read(r, 1024)
                print('reader read', repr(l))
            else:
                print('no pollin?', ll)
                break
        else:
            print('eh?', ll)
            break


def reader2(r):
    while True:
        if select([r], [], []):
            print('reader2 read', repr(os.read(r, 1024)))


r, w = os.pipe()
Spawn(reader, r)
os.write(w, 'testing')

select([0], [], [], 1)
