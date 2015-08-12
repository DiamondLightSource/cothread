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

'''Cooperative threading utilities.  This package contains the following
modules:

    cothread
        Support for cooperative threading tasks with a full event handling
        system.

    catools
        Channel access support tools for client access to EPICS records.
'''

from . import cothread
from . import input_hook

from .cothread import *
from .input_hook import *
from .coselect import *
from .cosocket import *
from .version import __version__

# Publish all public symbols from cothread and input_hook as default exports.
# The coselect functions aren't exported by default but are available.
__all__ = cothread.__all__ + input_hook.__all__
