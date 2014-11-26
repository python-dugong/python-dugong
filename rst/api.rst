API Reference
=============

.. currentmodule:: dugong

Classes
-------

.. autoclass:: HTTPConnection
   :members:

.. autoclass:: HTTPResponse
   :members:

.. autoclass:: BodyFollowing
   :members:

.. autoclass:: CaseInsensitiveDict
   :members:

.. autoclass:: PollNeeded
   :members:

.. autoclass:: AioFuture

Functions
---------

.. autofunction:: is_temp_network_error


Exceptions
----------

Dugong functions may pass through any exceptions raised by the
:ref:`socket <socket-objects>` and `ssl.SSLSocket` methods. In
addition to that, the following dugong-specific exceptions may be
raised as well:

.. autoexception:: ConnectionClosed
   :members:

.. autoexception:: InvalidResponse
   :members:

.. autoexception:: UnsupportedResponse
   :members:

.. autoexception:: ExcessBodyData
   :members:

.. autoexception:: StateError
   :members:

.. autoexception:: ConnectionTimedOut
   :members:

.. autoexception:: HostnameNotResolvable
   :members:

.. autoexception:: DNSUnavailable
   :members:

Constants
---------

.. autodata:: MAX_LINE_SIZE

.. autodata:: MAX_HEADER_SIZE

.. autodata:: DNS_TEST_HOSTNAMES

Thread Safety
-------------

Dugong is not generally threadsafe. However, simultaneous use of the
same `HTTPConnection` instance by two threads is supported if once
thread is restricted to sending requests, and the other thread
restricted to reading responses.

Avoiding Deadlocks
------------------

The `HTTPConnection` class allows you to send an unlimited number of
requests to the server before reading any of the responses. However, at some
point the transmit and receive buffers on both the ends of the connection
will fill up, and no more requests can be send before at least some of the
responses are read, and attempts to send more data to the server will
block. If the thread that attempts to send data is is also responsible for
reading the responses, this will result in a deadlock.

There are several ways to avoid this:

- Do not send a new request before the last response has been read. This is
  the easiest solution, but it means that no HTTP pipelining can be used.

- Use different threads for sending requests and receiving responses.

- Use the coroutine based API (see :ref:`coroutine_pipelining` in the
  tutorial).

