Introduction
============

.. currentmodule:: dugong

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
  expected (e.g. because of the server sending an unsupported reply)
  but responses for multiple requests are pending, the client cannot
  determine which requests have been processed.

- Only HTTP 1.1 connections are supported

- Responses and requests *must* specify a Content-Length header when
  not using chunked encoding.

If a server response doesn't fulfill the last two requirements, an
`UnsupportedResponse` exception is raised. Typically, this means that
synchronization with the server will be lost, so the connection needs to be
reset by calling the `~HTTPConnection.close` method.

All request and response headers are represented as strings, but must be
encodable in latin1. Request and response body must be bytes.


