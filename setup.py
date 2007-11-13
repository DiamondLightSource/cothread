#!/usr/bin/env python

from distutils.core import setup, Extension


call_readline = Extension('cothread.call_readline',
    sources = ['src/call_readline.c'],
    libraries = ["readline", "ncurses"])

setup (
    name = 'CoThread',
    version = '1.0',
    description = 'Cooperative threading based utilities',
    author = 'Michael Abbott',
    author_email = 'Michael.Abbott@diamond.ac.uk',
    packages = ['cothread'],
    ext_modules = [call_readline])
