TOP = .

# This includes Makefile.private which is written by the make system, before
# defining sensible defaults for all the symbols here.
include $(TOP)/Makefile.config

# Extra configuration dependencies.
DEPENDENCIES = \
    $(wildcard cothread/*.py cothread/*/*.py context/*.c context/*.h)


default: dist docs

dist: setup.py $(DEPENDENCIES) cothread/libca_path.py
	MODULEVER=$(MODULEVER) $(PYTHON) setup.py bdist_egg
	touch dist

# Clean the module
clean: clean_docs
	$(PYTHON) setup.py clean
	-rm -rf build dist *egg-info installed.files cothread/libca_path.py
	-find -name '*.pyc' -exec rm {} \;
	rm -f cothread/_coroutine.so

# Install the built egg
install: dist
	$(PYTHON) setup.py easy_install -m \
            --record=installed.files \
            --install-dir=$(INSTALL_DIR) \
            --script-dir=$(SCRIPT_DIR) dist/*.egg

docs: cothread/_coroutine.so
	sphinx-build -b html docs docs/html

clean_docs:
	rm -rf docs/html

.PHONY: default clean install docs clean_docs

cothread/libca_path.py:
	EVAL="$$($(PYTHON) cothread/load_ca.py)"  && \
        eval "$$EVAL"  && \
        echo "libca_path = '$$CATOOLS_LIBCA_PATH'" >$@

cothread/_coroutine.so: $(wildcard context/*.c context/*.h)
	$(PYTHON) setup.py build_ext -i
