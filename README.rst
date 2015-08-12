.. image:: https://pypip.in/v/cothread/badge.png
    :target: https://pypi.python.org/pypi/cothread/
    :alt: Latest PyPI version

.. image:: https://pypip.in/d/cothread/badge.png
    :target: https://pypi.python.org/pypi/cothread/
    :alt: Number of PyPI downloads

.. image:: https://readthedocs.org/projects/cothread/badge/?version=latest
    :target: https://readthedocs.org/projects/cothread/
    :alt: Documentation Status

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

    pip install git+git://github.com/Araneidae/cothread

Documentation
=============

Full documentation is available at http://cothread.readthedocs.org

License
=======
GPL2 License (see LICENSE)
