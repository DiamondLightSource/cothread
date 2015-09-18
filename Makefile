TOP = .

# This includes Makefile.private which is written by the make system, before
# defining sensible defaults for all the symbols here.
include $(TOP)/Makefile.config

# Extra configuration dependencies.
DEPENDENCIES = \
    $(wildcard cothread/*.py cothread/*/*.py context/*.c context/*.h)


default: dist docs

local: cothread/_coroutine.so

dist: setup.py $(DEPENDENCIES) cothread/libca_path.py
	MODULEVER=$(MODULEVER) $(PYTHON) setup.py bdist_egg
	touch dist

# Clean the module
clean: clean_docs
	$(PYTHON) setup.py clean
	-rm -rf build dist *egg-info installed.files cothread/libca_path.py
	-find -name '*.pyc' -exec rm {} \;
	rm -f cothread/*.so

# Install the built egg
install: dist
	$(PYTHON) setup.py easy_install -m \
            --record=installed.files \
            --install-dir=$(INSTALL_DIR) \
            --script-dir=$(SCRIPT_DIR) dist/*.egg

# publish
publish: default
	$(PYTHON) setup.py register -r pypi sdist upload -r pypi

# publish to test pypi
testpublish: default
	$(PYTHON) setup.py register -r pypitest sdist upload -r pypitest

docs: cothread/_coroutine.so
	sphinx-build -b html docs docs/html

test:
	$(PYTHON) setup.py test

clean_docs:
	rm -rf docs/html

.PHONY: default clean install docs clean_docs local

cothread/libca_path.py:
	EVAL="$$($(PYTHON) cothread/load_ca.py)"  && \
        eval "$$EVAL"  && \
        echo "libca_path = '$$CATOOLS_LIBCA_PATH'" >$@

cothread/_coroutine.so: $(wildcard context/*.c context/*.h)
	$(PYTHON) setup.py build_ext -i

build_ext: cothread/_coroutine.so
.PHONY: build_ext
