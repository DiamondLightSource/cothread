CFLAGS += -std=gnu99
CFLAGS += -Werror -Wall -Wextra
CFLAGS += -Wno-unused-parameter
CFLAGS += -Wno-missing-field-initializers
CFLAGS += -O2

CPPFLAGS += -I..

testco: testco.c coroutine.c ../cocore.c ../switch.c

clean:
	rm -f testco

.PHONY: clean
