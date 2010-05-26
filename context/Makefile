CFLAGS += -std=gnu99
CFLAGS += -pthread
CFLAGS += -O2 -Werror -Wall -Wextra
CFLAGS += -Wno-unused-parameter
CFLAGS += -Wno-missing-field-initializers

_coroutine.so: coroutine.c
	$(CC) $(CPPFLAGS) -fPIC --shared -o $@ $<

testco: testco.c coroutine.c

clean:
	rm -f testco _coroutine.so

.PHONY: clean
