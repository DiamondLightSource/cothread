# This file is part of the Diamond cothread library.
#
# Copyright (C) 2010 Michael Abbott, Diamond Light Source Ltd.
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

'''Wrapper for greenlet coroutine implementation, to be imported when _coroutine
extension is not available.'''


# It is very odd: there are two different versions of the greenlet library
# available with slightly different interfaces.
try:
    import greenlet
    create_greenlet = greenlet.greenlet
except ImportError:
    from py.magic import greenlet
    create_greenlet = greenlet

DEFAULT_STACK_SIZE = None

get_current = greenlet.getcurrent

def create(parent, action, stack_size):
    return create_greenlet(action, parent)

def switch(coroutine, arg):
    return coroutine.switch(arg)

def enable_check_stack(enable):
    pass
