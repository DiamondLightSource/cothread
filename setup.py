#!/usr/bin/env python

import glob
import os
import platform
import re

from setuptools import setup, Extension

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
    ext_modules = ext_modules,
)
