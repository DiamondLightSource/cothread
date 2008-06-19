PYTHON=python2.4
SCRIPT_DIR=/dls_sw/tools/bin
TEST_INSTALL_DIR=/dls_sw/work/common/python/test/packages
TEST_SCRIPT_DIR=/dls_sw/work/common/python/test/scripts

# builds a versioned python egg of the diamond namespace
# install with easy_install
# see http://peak.telecommunity.com/DevCenter/setuptools

all: dist make_docs

clean: remove clean_docs

dist: setup.py $(wildcard cothread/*.py src/*.c) 
	$(PYTHON) setup.py bdist_egg
	touch dist

remove:
	$(PYTHON) setup.py clean
	-rm -rf build dist *egg-info print_documentation.sh
	-find -name '*.pyc' -exec rm {} \;
	-find -name '*~' -exec rm {} \;

install: all
	$(PYTHON) setup.py dls_install -m --script-dir=$(SCRIPT_DIR) dist/*.egg

test: all
	$(PYTHON) setup.py dls_install -m --install-dir=$(TEST_INSTALL_DIR) \
            --script-dir=$(TEST_SCRIPT_DIR) dist/*.egg

make_docs:
	make -C docs

clean_docs:
	make -C docs clean
