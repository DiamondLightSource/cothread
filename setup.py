from distutils.core import setup, Extension


call_readline = Extension('cothread.call_readline',
    sources = ['call_readline.c'],
    libraries = ["readline", "ncurses"])

setup (
    name = 'CoThread',
    version = '1.0',
    description = 'Cooperative threading based utilities',
    author = 'Michael Abbott',
    author_email = 'Michael.Abbott@diamond.ac.uk',
    packages = ['cothread'],
    package_dir = {'cothread': '.'},
    ext_modules = [call_readline])
