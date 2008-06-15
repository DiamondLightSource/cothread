# Makefile for building cothread documentation

# Ensure asciidoc is on the path.
PATH := /home/share/embedded/local/bin:$(PATH)

ASCIIDOC_FILES = $(wildcard *.txt)

HTML_FILES = $(patsubst %.txt, %.html, $(ASCIIDOC_FILES))

default: $(HTML_FILES) pydoc

clean:
	rm -f *.html *.xml
	rm -rf pydoc

%.html: %.txt
	asciidoc -o $@ $<

pydoc: ../build/lib.linux-i686-2.4
	./makedocs.py
