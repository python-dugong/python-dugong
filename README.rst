httpio
======

This module provides an alternative to the standard library's
`http.client` module. In contrast to `http.client`, `httpio`:

 - allows you to send multiple requests right after each other without
   having to read the responses first.

 - supports waiting for 100-continue before sending the request body.

 - raises an exception instead of silently delivering partial data if the
   connection is closed before all data has been received.

 - raises one specific exception (ConnectionClosed) if the connection has
   been closed (while http.client connection may raise any of
   BrokenPipeError, BadStatusLineError, ConnectionAbortedError,
   ConnectionResetError, or simply return '' on read)

 - provides a single `HTTPConnection` class to communicate with the
   server (no separate `HTTPResponse` class).

Of course, these features come for a price:

 - Only HTTP 1.1 connections are supported

 - Extra care has to be taken when using non-idempotent http
   methods. This is because if a connection is terminated earlier than
   expected (e.g. because of the server sending an unsupported reply)
   but responses for multiple requests are pending, `httpio` cannot
   determine which requests have already been processed and which ones
   need to be resend.

       
For detailed usage instructions, consult the docstring of the
`httpio.HTTPConnection` class.
