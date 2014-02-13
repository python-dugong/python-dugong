==========================
 The Python Dugong Module
==========================

This module provides an API for communicating with HTTP 1.1 servers,
especially for implementing REST clients. It is an alternative to the
standard library's *http.client* (formerly *httplib*) module. In
contrast to *http.client*, the *dugong* module:

* allows you to send multiple requests right after each other without
  having to read the responses first.

* supports waiting for 100-continue before sending the request body.

* raises an exception instead of silently delivering partial data if the
  connection is closed before all data has been received.

* raises one specific exception (ConnectionClosed) if the connection
  has been closed (while http.client connection may raise any of
  BrokenPipeError, BadStatusLineError, ConnectionAbortedError,
  ConnectionResetError, or simply return '' on read)

* provides a single *HTTPConnection* class to communicate with the
  server (no separate *HTTPResponse* class).

Of course, these features come for a price:

* Only HTTP 1.1 connections are supported

* Extra care has to be taken when using non-idempotent http
  methods. This is because if a connection is terminated earlier than
  expected (e.g. because of the server sending an unsupported reply)
  but responses for multiple requests are pending, *dugong* cannot
  determine which requests have already been processed and which ones
  need to be resend.


Installation
============

As usual: download and extract the tarball, then run ::

  # python setup.py install [--user]

To run the self-tests, install `py.test`_ and run ::

  # py.test


Getting Help
============

The documentation can be `read online`__ and is also included in the
*doc/html* directory of the dugong tarball.

Please report any bugs on the `issue tracker`_. For discussion and
questions, please subscribe to the `dugong mailing list`_.


.. __: http://pythonhosted.org/dugong/
.. _dugong mailing list: https://groups.google.com/d/forum/python-dugong
.. _issue tracker: https://bitbucket.org/nikratio/python-dugong/issues
.. _py.test: http://www.pytest.org/
