#!/usr/bin/env python

import glob
import os
import platform

try:
    # We prefer to use setuptools if possible, but it isn't always available
    from setuptools import setup, Extension

    setup_args = dict(
        entry_points = {
            'console_scripts': [
                'pvtree.py = cothread.tools.pvtree:main' ] },
        zip_safe = False)

except ImportError:
    from distutils.core import setup, Extension
    setup_args = {}


# these lines allow the version to be specified in Makefile.RELEASE
version = os.environ.get('MODULEVER', 'unknown')

# Extension module providing core coroutine functionality.  Very similar in
# spirit to greenlet.
_coroutine = Extension('cothread._coroutine',
    ['context/_coroutine.c', 'context/cocore.c', 'context/switch.c'],
    depends = glob.glob('context/switch-*.c') + glob.glob('context/*.h'))

setup(
    name = 'cothread',
    version = version,
    description = 'Cooperative threading based utilities',
    author = 'Michael Abbott',
    author_email = 'Michael.Abbott@diamond.ac.uk',
    url = 'http://controls.diamond.ac.uk/downloads/python/cothread/',
    license = 'GPL2',

    packages = ['cothread', 'cothread.tools'],
    ext_modules = [_coroutine],
    **setup_args)
