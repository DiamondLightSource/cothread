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


../cothread/_coroutine.so: _coroutine.c $(SWITCH_FRAME)
	$(CC) $(CPPFLAGS) $(CFLAGS) -fPIC --shared -o $@ $^

clean:
	rm -f ../cothread/_coroutine.so Makefile.config

Makefile.config: Makefile.config.in
	$(CC) -E -xc $< >$@

.PHONY: clean
