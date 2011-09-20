CFLAGS += -std=gnu99
CFLAGS += -Werror -Wall -Wextra
CFLAGS += -Wno-unused-parameter
CFLAGS += -Wno-missing-field-initializers
# CFLAGS += -O2
CFLAGS += -g

CPPFLAGS += -I..

testco: testco.c ../cocore.c ../switch.c

clean:
	rm -f testco

.PHONY: clean
