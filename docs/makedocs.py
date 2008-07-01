#!/usr/bin/env python2.4

import sys
import os
import pydoc
import shutil
import types

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))
import cothread
import cothread.catools

if os.access('pydoc', os.F_OK):
    shutil.rmtree('pydoc')
os.mkdir('pydoc')
os.chdir('pydoc')

def WriteModules(package):
    for name in dir(package):
        value = getattr(package, name)
        if type(value) is types.ModuleType:
            pydoc.writedoc(value)

pydoc.writedoc(cothread)
WriteModules(cothread)
