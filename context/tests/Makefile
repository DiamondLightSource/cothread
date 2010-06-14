TOP = ../..
include $(TOP)/Makefile.config
include ../Makefile.config

CFLAGS += -std=gnu99
CFLAGS += -pthread
CFLAGS += -Werror -Wall -Wextra
CFLAGS += -Wno-unused-parameter
CFLAGS += -Wno-missing-field-initializers
CFLAGS += -O2

CPPFLAGS += -I..

testco: testco.c coroutine.c ../cocore.c ../$(SWITCH_FRAME)

clean:
	rm -f testco

.PHONY: clean
