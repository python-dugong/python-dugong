API Reference
=============

.. currentmodule:: httpio

Functions
---------

.. autofunction:: is_temp_network_error

Classes
-------

.. autoclass:: HTTPConnection
   :members:

Exceptions
----------

.. autoexception:: ConnectionClosed
   :members:

.. autoexception:: InvalidResponse
   :members:
      
.. autoexception:: StateError
   :members:
      
.. autoexception:: UnsupportedResponse
   :members:
      
.. autoexception:: ExcessBodyData
   :members:

   
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

- Use different threads for sending requests and receiving responses. This
  may or may not be easy to do in your application.

- Use the *via_cofun* parameter of `~HTTPConnection.send_request` to
  send requests, and a combination of `~HTTPConnection.write` with
  *partial=True* and `select` to send request body data.

