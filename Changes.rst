.. currentmodule:: httpio

Unreleased Changes
==================

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


Release 1.0 (2013-07-13)
========================

* Initial release.
  
