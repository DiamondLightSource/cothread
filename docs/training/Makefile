RST2S5 = rst2s5.py

# Need to explicitly point Python to our Pygments install
TOOLS = /dls_sw/prod/tools/RHEL6-x86_64
LIB_PATH = prefix/lib/python2.7/site-packages
export PYTHONPATH = $(TOOLS)/Pygments/1-4/$(LIB_PATH)/Pygments-1.4-py2.7.egg

%.html: %.rst
	$(RST2S5) $< $@

default: cothread.html

cothread.html: $(wildcard styles/*)

clean:
	rm -r cothread.html

.PHONY: default clean
