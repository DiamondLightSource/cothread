TOP = .

# This includes Makefile.private which is written by the make system, before
# defining sensible defaults for all the symbols here.
include $(TOP)/Makefile.config

default: dist make_docs

dist: setup.py $(wildcard cothread/*.py cothread/*/*.py) cothread/libca_path.py
	MODULEVER=$(MODULEVER) $(PYTHON) setup.py bdist_egg
	touch dist

# Clean the module
clean: clean_docs
	$(PYTHON) setup.py clean
	-rm -rf build dist *egg-info installed.files cothread/libca_path.py
	-find -name '*.pyc' -exec rm {} \;

# Install the built egg
install: dist
	$(PYTHON) setup.py easy_install -m \
		--record=installed.files \
		--install-dir=$(INSTALL_DIR) \
		--script-dir=$(SCRIPT_DIR) dist/*.egg

make_docs:
	$(MAKE) -C docs

clean_docs:
	$(MAKE) -C docs clean

.PHONY: clean clean_docs install make_docs clean_docs default

cothread/libca_path.py: $(EPICS_BASE)/lib/$(EPICS_HOST_ARCH)/libca.so
	echo "libca_path = '$<'" >$@
