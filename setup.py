#!/usr/bin/env python

from setuptools import setup, Extension

if 'version' not in globals():
    version = 'development'

setup(
    name = 'cothread',
    version = version,
    description = 'Cooperative threading based utilities',
    author = 'Michael Abbott',
    author_email = 'Michael.Abbott@diamond.ac.uk',
    entry_points = {
        'console_scripts': [
            'pvtree.py = cothread.tools.pvtree:main' ] },
    
    packages = ['cothread', 'cothread/tools'])
