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

TOP = ..
include $(TOP)/Makefile.config

CFLAGS += -std=gnu99
CFLAGS += -pthread
CFLAGS += -Werror -Wall -Wextra
CFLAGS += -Wno-unused-parameter
CFLAGS += -Wno-missing-field-initializers
CFLAGS += -O2
# CFLAGS += -g

# Pick up the appropriate flags for building a Python extension
CPPFLAGS += $(shell $(PYTHON_CONFIG) --includes)

# Compute the appropriate frame switching code to use: this is computed by
# Makefile.config.in from the currently configured compiler.
include Makefile.config


../cothread/_coroutine.so: _coroutine.c cocore.c $(SWITCH_FRAME)
	$(CC) $(CPPFLAGS) $(CFLAGS) -fPIC --shared -o $@ $^

clean:
	rm -f ../cothread/_coroutine.so Makefile.config

Makefile.config: Makefile.config.in
	$(CC) -E -xc $< >$@

.PHONY: clean
