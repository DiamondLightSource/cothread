#!/usr/bin/env python
"""
Example of using cosockets with urllib2
"""

from __future__ import print_function

import sys, os.path
py3= sys.version_info[0]>2

from optparse import OptionParser

import cothread
from cothread import cosocket
cosocket.socket_hook()

if py3:
    from urllib.parse import urlparse
    from urllib.request import urlopen, Request
else:
    from urlparse import urlparse
    from urllib2 import urlopen, Request

parser = OptionParser()
parser.add_option('-T', '--timeout', default='5', help='Abort after some time')

opts, args = parser.parse_args()

try:
    timo = float(opts.timeout)
except ValueError:
    parser.error('Invalid timeout')

nurls = [len(args)]

def download(url, nurls=nurls):
    try:
        rep = urlopen(url, None, timo)

        with open(os.path.basename(urlparse(rep.geturl()).path), 'wb') as F:
            D = rep.read()
            print('Recv', len(D))
            F.write(D)

        rep.close()

    finally:
        nurls[0] = nurls[0]-1
        if nurls[0]==0:
            cothread.Quit()
            print('Done')
        else:
            print(nurls[0], 'Remaining')

for url in args:
    cothread.Spawn(download, url)

cothread.WaitForQuit()
