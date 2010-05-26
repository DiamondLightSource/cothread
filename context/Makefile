CFLAGS += -std=gnu99
CFLAGS += -pthread
CFLAGS += -Werror -Wall -Wextra
CFLAGS += -Wno-unused-parameter
CFLAGS += -Wno-missing-field-initializers
# CFLAGS += -O2
CFLAGS += -g

# CPPFLAGS += -DUSE_UCONTEXT

PYTHON_DIR = /home/tools/python2.4/include/python2.4

_coroutine.so: _coroutine.c coroutine.c
	$(CC) $(CPPFLAGS) -I$(PYTHON_DIR) $(CFLAGS) -fPIC --shared -o $@ $^

coroutine.so: coroutine.c
	$(CC) $(CPPFLAGS) -fPIC --shared -o $@ $<

# testco: testco.c coroutine.c switch-ucontext.c
testco: testco.c coroutine.c switch-x86.s

clean:
	rm -f testco _coroutine.so

.PHONY: clean
