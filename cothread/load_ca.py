# This file is part of the Diamond cothread library.
#
# Copyright (C) 2007 James Rowland, 2007-2012 Michael Abbott,
# Diamond Light Source Ltd.
#
# The Diamond cothread library is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License,
# or (at your option) any later version.
#
# The Diamond cothread library is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
# Contact:
#      Dr. Michael Abbott,
#      Diamond Light Source Ltd,
#      Diamond House,
#      Chilton,
#      Didcot,
#      Oxfordshire,
#      OX11 0DE
#      michael.abbott@diamond.ac.uk

# As discovering the location of libca (or whatever it's called in this
# particular system) is somewhat involved the work is gathered into this file.
# This file can also be run as a standalone script to discover the path to
# libca.

from __future__ import print_function

import ctypes
import platform
import os


# Figure out the libraries that need to be loaded and the loading method.
load_library = ctypes.cdll.LoadLibrary
system = platform.system()
if system == 'Windows':
    load_library = ctypes.windll.LoadLibrary
    lib_files = ['Com.dll', 'ca.dll']
elif system == 'Darwin':
    lib_files = ['libca.dylib']
else:
    lib_files = ['libca.so']


def _get_arch():
    import os
    try:
        return os.environ['EPICS_HOST_ARCH']
    except KeyError:
        import platform
        return "%s-%s" % (platform.system().lower(), platform.machine())

epics_host_arch = _get_arch()


def _libca_path(load_libca_path):
    # We look for libca in a variety of different places, searched in order:
    #
    # 1. Firstly if CATOOLS_LIBCA_PATH is set in the environment we take that as
    #    gospel.  This allows the remaining search to be overridden.
    # 2. If epicscorelibs is installed, allow it to provide libca.
    # 3. If the libca_path module is present we accept the value it defines.
    # 4. Finally check for EPICS_BASE and compute appropriate architecture.

    # First allow a forced override
    libca_path = os.environ.get('CATOOLS_LIBCA_PATH')
    if libca_path:
        return libca_path

    # If epicscorelibs is installed, use the bundled libca.
    try:
        from epicscorelibs.path import get_lib
        return get_lib('ca')
    except ImportError:
        pass

    # Next import from configuration file if present, unless this has been
    # disabled.
    if load_libca_path:
        try:
            # If libca_path has been defined go with that
            from .libca_path import libca_path
            return libca_path
        except ImportError:
            pass

    # If no libca_path, how about local copies of the files?
    libca_path = os.path.abspath(os.path.dirname(__file__))
    if os.path.isfile(os.path.join(libca_path, lib_files[-1])):
        # Yes, there seems to be something locally installed.
        return libca_path

    # No local install, no local configuration, no override.  Try for standard
    # environment variable configuration instead.
    epics_base = os.environ['EPICS_BASE']
    return os.path.join(epics_base, 'lib', epics_host_arch)


if __name__ == '__main__':
    # If run standalone we are a helper script.  Write out the relevant
    # definitions for the use of our caller.
    libca_path = _libca_path(False)
    print('CATOOLS_LIBCA_PATH=\'%s\'' % libca_path)
    print('LIB_FILES=\'%s\'' % ' '.join(lib_files))

else:
    # Load the library (or libraries).
    try:
        # First try loading the libraries directly without searching anywhere.
        # In this case we'll pick up from the path or anything already loaded
        # into the interpreter.
        for lib in lib_files:
            libca = load_library(lib)
    except OSError:
        # Ask _libca_path() where to find things.
        libca_path = _libca_path(True)
        if os.path.isfile(libca_path):
            libca = load_library(libca_path)
        else:
            for lib in lib_files:
                libca = load_library(os.path.join(libca_path, lib))
