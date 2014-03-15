.. currentmodule:: dugong

Release 2.2 (2014-03-14)
========================

* Unittests requiring the `asyncio` module are now skipped if this
  module is not available.
  
  
Release 2.1 (2014-03-11)
========================

* Fixed a problem where data was not sent to the server if the syscall
  was interrupted by a signal.

* It is no longer necessary to read from response body at least once
  even if has zero length.

* `PollNeeded.poll` now uses `select.poll` instead of
  `select.select`. This avoids a "filedescriptor out of range"
  exception that may be raised by `select.select` when the
  filedescriptor exceeds some system-specific value.


Release 2.0 (2014-02-23)
========================

* Renamed module from *httpio* to *dugong*.

* The coroutine based API was completely overhauled.
  
* Introduced `BodyFollowing` class for use with *body* parameter of
  `~HTTPConnection.send_request` method.

* `~HTTPConnection.send_request` now returns a `HTTPResponse` instance
  instead of a tuple.

* The :meth:`!HTTPConnection.get_current_response` method has been removed.

* The :meth:`!HTTPConnection.fileno` method has been removed.

* Added `CaseInsensitiveDict` class.

* `~HTTPConnection.send_request` now converts the *header* parameter
  to a `CaseInsensitiveDict`.

* `~HTTPConnection.send_request` now automatically generates a
  ``Content-MD5`` header when the body is passed in as a bytes-like
  object.

* `HTTPConnection.read` now accepts `None` for the *len_* parameter.

* `HTTPConnection` instances now support a bare-bones `io.IOBase`
  interface so that they can be combined with `io.TextIOWrapper` to
  read text response bodies.

* The :meth:`!HTTPConnection.close` method was renamed to
  `HTTPConnection.disconnect` to prevent confusion related to the
  ``closed`` attribute (which may be `True` if the connection is
  established, but there is no active response body).

* Repeatedly trying to read more response data after the response body
  has been read completely no longer results in `StateError`  being
  raised, but simply returns ``b''``.
  
Release 1.0 (2013-07-13)
========================

* Initial release.
  
