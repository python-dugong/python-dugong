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

Release 1.0 (2013-07-13)
========================

* Initial release.
  
