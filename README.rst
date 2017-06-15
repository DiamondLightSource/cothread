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
