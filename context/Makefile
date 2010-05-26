CFLAGS += -std=gnu99
CFLAGS += -pthread
CFLAGS += -Werror -Wall -Wextra
CFLAGS += -Wno-unused-parameter
CFLAGS += -Wno-missing-field-initializers
CFLAGS += -O2
# CFLAGS += -g

PYTHON_DIR = /home/tools/python2.4/include/python2.4

include Makefile.config


../cothread/_coroutine.so: _coroutine.c $(SWITCH_FRAME)
	$(CC) $(CPPFLAGS) -I$(PYTHON_DIR) $(CFLAGS) -fPIC --shared -o $@ $^

clean:
	rm -f ../cothread/_coroutine.so Makefile.config

Makefile.config: Makefile.config.in
	$(CC) -E -xc $< >$@

.PHONY: clean
