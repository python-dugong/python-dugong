==========================
 The Python Dugong Module
==========================

.. default-role:: code

.. start-intro

The Python Dugong module provides an API for communicating with HTTP
1.1 servers. It is an alternative to the standard library's
`http.client` (formerly *httplib*) module. In contrast to
`http.client`, Dugong:

- allows you to send multiple requests right after each other without
  having to read the responses first.

- supports waiting for 100-continue before sending the request body.

- raises an exception instead of silently delivering partial data if the
  connection is closed before all data has been received.

- raises one specific exception (`ConnectionClosed`) if the connection
  has been closed (while `http.client` connection may raise any of
  `BrokenPipeError`, `~http.client.BadStatusLine`,
  `ConnectionAbortedError`, `ConnectionResetError`,
  `~http.client.IncompleteRead` or simply return ``''`` on read)

- supports non-blocking, asynchronous operation and is compatible with
  the asyncio_ module.

- is not compatible with old HTTP 0.9 or 1.0 servers.

All request and response headers are represented as `str`, but must be
encodable in latin1. Request and response body must be `bytes-like
objects`_ or binary streams.

Dugong requires Python 3.3 or newer.

.. _`bytes-like objects`: http://docs.python.org/3/glossary.html#term-bytes-like-object

Installation
============

As usual: download the tarball from PyPi_, extract it, and run ::

  # python3 setup.py install [--user]

To run the self-tests, install `py.test`_ and run ::

  # py.test-3 test/


.. _PyPi: https://pypi.python.org/pypi/dugong/#downloads

Getting Help
============

The documentation can be `read online`__ and is also included in the
*doc/html* directory of the dugong tarball.

Please report any bugs on the `issue tracker`_. For discussion and
questions, please subscribe to the `dugong mailing list`_.

Development Status
==================

The Dugong API is not yet stable and may change from one release to
the other.

.. __: http://pythonhosted.org/dugong/
.. _dugong mailing list: https://groups.google.com/d/forum/python-dugong
.. _issue tracker: https://bitbucket.org/nikratio/python-dugong/issues
.. _py.test: http://www.pytest.org/
.. _asyncio: http://docs.python.org/3.4/library/asyncio.html

