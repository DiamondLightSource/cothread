# Makefile for building cothread documentation

# Ensure asciidoc is on the path.
PATH := $(PATH):/dls_sw/tools/local/bin

ASCIIDOC_FILES = $(wildcard *.txt)

HTML_FILES = $(patsubst %.txt, %.html, $(ASCIIDOC_FILES))

default: $(HTML_FILES) pydoc

clean:
	rm -f *.html *.xml
	rm -rf pydoc

%.html: %.txt
	asciidoc -o $@ $<

pydoc: $(wildcard ../cothread/*.py) 
	./makedocs.py
