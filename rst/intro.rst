Introduction
============

.. currentmodule:: httpio

This class encapsulates a HTTP connection.

In contrast to the standard library's http.client module, this class

- allows you to send multiple requests right after each other without
  having to read the responses first.

- supports waiting for 100-continue before sending the request body.

- raises an exception instead of silently delivering partial data if the
  connection is closed before all data has been received.

- raises one specific exception (ConnectionClosed) if the connection has
  been closed (while http.client connection may raise any of
  BrokenPipeError, BadStatusLineError, ConnectionAbortedError,
  ConnectionResetError, or simply return '' on read)

These features come for a price:

 - It is recommended to use this class only for idempotent HTTP
   methods. This is because if a connection is terminated earlier than
   expected (e.g. because of the server sending an unsupported reply) but
   responses for multiple requests are pending, the client cannot determine
   which requests have been processed.

 - Only HTTP 1.1 connections are supported

 - Responses and requests *must* specify a Content-Length header when
   not using chunked encoding.

If a server response doesn't fulfill the last two requirements, an
`UnsupportedResponse` exception is raised. Typically, this means that
synchronization with the server will be lost, so the connection needs to be
reset by calling the `~HTTPConnection.close` method.

All request and response headers are represented as strings, but must be
encodable in latin1. Request and response body must be bytes.


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

