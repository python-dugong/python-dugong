.. currentmodule:: dugong

Unreleased Changes
==================

* Renamed module from *httpio* to *dugong*.  
  
* Introduced `BodyFollowing` class for use with *body* parameter of
  `~HTTPConnection.send_request` method.

* `~HTTPConnection.send_request` now returns a `HTTPResponse` instance
  instead of a tuple.

* The `!HTTPConnection.get_current_response` method has been removed.

* Added `CaseInsensitiveDict` class.

* `~HTTPConnection.send_request` now converts the *header* parameter
  to a `CaseInsensitiveDict`.

* `~HTTPConnection.send_request` now automatically generates a
  ``Content-MD5`` header when the body is passed in as a bytes-like
  object.

* Fixed `~HTTPConnection.co_sendfile` to send the actual data instead
  of just \0 bytes.

* `HTTPConnection.read` now accepts `None` for the *len_* parameter.

* `HTTPConnection` instances now support a bare-bones `io.IOBase`
  interface so that they can be combined with `io.TextIOWrapper` to
  read text response bodies.

* Renamed :meth:`!HTTPConnection.fileno` to
  `HTTPConnection.socket_fileno`, so that standard IO layers (like
  `io.TextIOWrapper`) don't try to read from the underlying socket.

  
Release 1.0 (2013-07-13)
========================

* Initial release.
  
