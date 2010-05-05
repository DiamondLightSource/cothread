# Makefile for building cothread documentation
TOP = ..
ASCIIDOC = asciidoc
include $(TOP)/Makefile.config


ASCIIDOC_FILES = $(wildcard *.txt)

HTML_FILES = $(patsubst %.txt, %.html, $(ASCIIDOC_FILES))

default: $(HTML_FILES) pydoc

clean:
	rm -f *.html *.xml
	rm -rf pydoc

%.html: %.txt
	$(ASCIIDOC) -o $@ $<

pydoc: $(wildcard ../cothread/*.py)
	$(PYTHON) makedocs.py
