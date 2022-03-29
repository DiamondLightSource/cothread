|build_status| |coverage| |pypi-version| |readthedocs|

cothread
========

The `cothread` Python library is designed for building tools using cooperative
threading.  This means that, with care, programs can effectively run several
tasks simultaneously.

The `cothread.catools` library is designed to support easy channel access from
Python, and makes essential use of the features of cooperative threads -- in
particular, `catools.camonitor()` notifies updates in the background.

See the documentation for more details.


Installation
------------
To install the latest release, type::

    pip install cothread

To install the latest code directly from source, type::

    pip install git+git://github.com/dls-controls/cothread

Documentation
=============

Full documentation is available at http://cothread.readthedocs.org

Upload to PyPI
==============

Run the following commands to create a virtual environment, build cothread, 
do a test upload to test.pypi.org, and finally upload it to PyPi.

Ask a member of dls-controls for the username and password to use::

    pipenv install numpy twine build
    SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct) pipenv run python -m build --sdist
    pipenv run twine upload -r testpypi dist/*
    pipenv run twine upload dist/*

We set SOURCE_DATE_EPOCH from git commit for reproducible builds - see https://reproducible-builds.org/

License
=======
GPL2 License (see COPYING)

.. |pypi-version| image:: https://img.shields.io/pypi/v/cothread.svg
    :target: https://pypi.python.org/pypi/cothread/
    :alt: Latest PyPI version

.. |readthedocs| image:: https://readthedocs.org/projects/cothread/badge/?version=latest
    :target: https://readthedocs.org/projects/cothread/?badge=latest
    :alt: Documentation Status

.. |build_status| image:: https://travis-ci.org/dls-controls/cothread.svg?style=flat
    :target: https://travis-ci.org/dls-controls/cothread
    :alt: Build Status

.. |coverage| image:: https://coveralls.io/repos/dls-controls/cothread/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/dls-controls/cothread?branch=master
    :alt: Test coverage
