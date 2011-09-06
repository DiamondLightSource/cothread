# This file is part of the Diamond cothread library.
#
# Copyright (C) 2007 James Rowland, 2007-2010 Michael Abbott,
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


def _libca_path(load_libca_path):
    # We look for libca in a variety of different places, searched in order:
    #
    # 1. Firstly if CATOOLS_LIBCA_PATH is set in the environment we take that as
    #    gospel.  This allows the remaining search to be overridden.
    # 2  If the libca_path module is present we accept the value it defines.
    # 3. Check for local copies of the libca file(s).
    # 4. Finally check for EPICS_BASE and optionally EPICS_HOST_ARCH, which we
    #    normally guess if not specified.

    # First allow a forced override
    libca_path = os.environ.get('CATOOLS_LIBCA_PATH')
    if libca_path:
        return libca_path

    # Next import from configuration file if present, unless this has been
    # disabled.
    if load_libca_path:
        try:
            # If libca_path has been defined go with that
            from libca_path import libca_path
            return libca_path
        except ImportError:
            pass

    # If no libca_path, how about local copies of the files?
    libca_path = os.path.dirname(__file__)
    if os.access(os.path.join(libca_path, lib_files[-1]), os.R_OK):
        # Yes, there seems to be something locally installed.
        return libca_path

    # No local install, no local configuration, no override.  Try for standard
    # environment variable configuration instead.
    epics_base = os.environ['EPICS_BASE']
    epics_host_arch = os.environ.get('EPICS_HOST_ARCH')
    if not epics_host_arch:
        # Mapping from host architecture to EPICS host architecture name can be
        # done with a little careful guesswork.  As EPICS architecture names are
        # a little arbitrary this isn't guaranteed to work.
        system_map = {
            ('Linux',   '32bit', 'i386'):   'linux-x86',
            ('Linux',   '32bit', 'i686'):   'linux-x86',
            ('Linux',   '64bit', 'x86_64'): 'linux-x86_64',
            ('Darwin',  '64bit', 'i386'):   'darwin-x86',
            ('Windows', '32bit', 'x86'):    'win32-x86',
            ('Windows', '64bit', '????'):   'windows-x64',  # Not quite yet!
        }
        bits = platform.architecture()[0]
        machine = platform.machine()
        epics_host_arch = system_map[(system, bits, machine)]
    return os.path.join(epics_base, 'lib', epics_host_arch)


if __name__ == '__main__':
    # If run standalone we are a helper script.  Write out the relevant
    # definitions for the use of our caller.
    libca_path = _libca_path(False)
    print 'CATOOLS_LIBCA_PATH=\'%s\'' % libca_path
    print 'LIB_FILES=\'%s\'' % ' '.join(lib_files)

else:
    # Finally load the library (or libraries, if there are dependencies to
    # resolve).
    libca_path = _libca_path(True)
    for lib in lib_files:
        libca = load_library(os.path.join(libca_path, lib))
