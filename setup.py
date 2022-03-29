#!/usr/bin/env python

import glob
import os
import platform
import re

try:
    # We prefer to use setuptools if possible, but it isn't always available
    from setuptools import setup, Extension

    setup_args = dict(
        entry_points = {
            'console_scripts': [
                'pvtree.py = cothread.tools.pvtree:main' ] },
        install_requires = ['numpy'],
        zip_safe = False)

except ImportError:
    from distutils.core import setup, Extension
    setup_args = {}

def get_version():
    '''Extracts the version number from the version.py file.
    '''
    VERSION_FILE = 'cothread/version.py'
    mo = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]',
        open(VERSION_FILE).read(), re.M)
    if mo:
        version = mo.group(1)
        bs_version = os.environ.get('MODULEVER', '0.0')
        assert bs_version == '0.0' or bs_version == version, \
            'Version %s specified by the build system doesn\'t match %s in ' \
            'version.py' % (bs_version, version)
        return version
    else:
        raise RuntimeError(
            'Unable to find version string in %s.' % VERSION_FILE)


# Extension module providing core coroutine functionality.  Very similar in
# spirit to greenlet.
extra_compile_args = [
#    '-Werror',
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
    version = get_version(),
    description = 'Cooperative threading based utilities',
    long_description = open('README.rst').read(),
    author = 'Michael Abbott',
    author_email = 'Michael.Abbott@diamond.ac.uk',
    url = 'https://github.com/dls-controls/cothread',
    license = 'GPL2',
    packages = ['cothread', 'cothread.tools'],
    ext_modules = ext_modules,
    test_suite="tests",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: '
            'GNU General Public License v2 or later (GPLv2+)',
    ],
    **setup_args)
