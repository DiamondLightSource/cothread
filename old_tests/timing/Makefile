EPICS_BASE ?= /dls_sw/epics/R3.14.11/base

CPPFLAGS += -I$(EPICS_BASE)/include
CPPFLAGS += -I$(EPICS_BASE)/include/os/Linux

CFLAGS += -std=gnu99
CFLAGS += -O3

CFLAGS += -Werror
CFLAGS += -Wall -Wextra
CFLAGS += -Wno-unused-parameter
CFLAGS += -Wno-missing-field-initializers
CFLAGS += -Wundef
CFLAGS += -Wshadow
CFLAGS += -Wcast-align
CFLAGS += -Wwrite-strings
CFLAGS += -Wredundant-decls
CFLAGS += -Wmissing-prototypes
CFLAGS += -Wmissing-declarations
# CFLAGS += -Wstrict-prototypes

LDLIBS += -lca
LDFLAGS += -L$(EPICS_BASE)/lib/linux-x86
LDFLAGS += -Wl,-rpath,$(EPICS_BASE)/lib/linux-x86

timing: timing.c

getpv: getpv.c

test: timing
	./timing

clean:
	rm -f timing

.PHONY: clean test
