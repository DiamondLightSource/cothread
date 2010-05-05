PREFIX = /dls_sw/prod/tools/RHEL5
PYTHON = $(PREFIX)/bin/python2.6
INSTALL_DIR = $(PREFIX)/lib/python2.6/site-packages
SCRIPT_DIR = $(PREFIX)/bin
MODULEVER = 0.0

# Override defaults above with release info
-include Makefile.private

# builds a versioned python egg of the diamond namespace
# install with easy_install
# see http://peak.telecommunity.com/DevCenter/setuptools

all: dist make_docs

clean: remove clean_docs
	rm -f cothread/libca_path.py

dist: setup.py $(wildcard cothread/*.py cothread/*/*.py) cothread/libca_path.py
	$(PYTHON) setup.py bdist_egg
	touch dist

remove:
	$(PYTHON) setup.py clean
	-rm -rf build dist *egg-info print_documentation.sh
	-find -name '*.pyc' -exec rm {} \;

install: all
	$(PYTHON) setup.py easy_install -m \
            --script-dir=$(SCRIPT_DIR) dist/*.egg

test: all
	$(PYTHON) setup.py easy_install -m \
            --install-dir=$(TEST_INSTALL_DIR) \
            --script-dir=$(TEST_SCRIPT_DIR) dist/*.egg

make_docs:
	make -C docs

clean_docs:
	make -C docs clean

cothread/libca_path.py: $(EPICS_BASE)/lib/$(EPICS_HOST_ARCH)/libca.so
	echo "libca_path = '$<'" >$@
