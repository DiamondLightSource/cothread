|code_ci| |docs_ci| |coverage| |pypi_version| |license|

cothread
========

The ``cothread`` Python library is designed for building tools using cooperative
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

    pip install git+git://github.com/DiamondLightSource/cothread

Documentation
=============

Full documentation is available at https://DiamondLightSource.github.io/cothread

.. |code_ci| image:: https://github.com/DiamondLightSource/cothread/actions/workflows/code.yml/badge.svg?branch=master
    :target: https://github.com/DiamondLightSource/cothread/actions/workflows/code.yml
    :alt: Code CI

.. |docs_ci| image:: https://github.com/DiamondLightSource/cothread/actions/workflows/docs.yml/badge.svg?branch=master
    :target: https://github.com/DiamondLightSource/cothread/actions/workflows/docs.yml
    :alt: Docs CI

.. |coverage| image:: https://codecov.io/gh/DiamondLightSource/cothread/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/DiamondLightSource/cothread
    :alt: Test Coverage

.. |pypi_version| image:: https://img.shields.io/pypi/v/cothread.svg
    :target: https://pypi.org/project/cothread
    :alt: Latest PyPI version

.. |license| image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: Apache License

..
    Anything below this line is used when viewing README.rst and will be replaced
    when included in index.rst
