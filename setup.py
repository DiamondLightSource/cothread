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
extra_compile_args = [
    '-Werror',
    '-Wall',
    '-Wextra',
    '-Wno-unused-parameter',
    '-Wno-missing-field-initializers',
    '-Wundef',
    '-Wcast-align',
    '-Wwrite-strings',
    '-Wmissing-prototypes',
    '-Wmissing-declarations',
    '-Wstrict-prototypes']
_coroutine = Extension('cothread._coroutine',
    ['context/_coroutine.c', 'context/cocore.c', 'context/switch.c'],
    extra_compile_args = extra_compile_args,
    depends = glob.glob('context/switch-*.c') + glob.glob('context/*.h'))
ext_modules = [_coroutine]

if platform.system() == 'Windows':
    _winlib = Extension(
        'cothread._winlib', ['context/_winlib.c'],
        extra_compile_args = extra_compile_args)
    ext_modules.append(_winlib)

setup(
    name = 'cothread',
    version = version,
    description = 'Cooperative threading based utilities',
    author = 'Michael Abbott',
    author_email = 'Michael.Abbott@diamond.ac.uk',
    url = 'http://controls.diamond.ac.uk/downloads/python/cothread/',
    license = 'GPL2',

    packages = ['cothread', 'cothread.tools'],
    ext_modules = ext_modules,
    **setup_args)
