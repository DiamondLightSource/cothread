#!/usr/bin/env python

#from distutils.core import setup, Extension
from setuptools import setup, Extension

if 'version' not in globals():
    version = 'development'

call_readline = Extension('cothread.call_readline',
    sources = ['src/call_readline.c'],
    libraries = ['readline', 'ncurses'])

setup(
    name = 'cothread',
    version = version,
    description = 'Cooperative threading based utilities',
    author = 'Michael Abbott',
    author_email = 'Michael.Abbott@diamond.ac.uk',
    
    packages = ['cothread'],
    ext_modules = [call_readline],
    setup_requires = ['dls.environment==1.0'])
