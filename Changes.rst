.. currentmodule:: dugong

Release 3.7.1 (2017-06-05)
==========================

* Now compatible with Python 3.6.


Release 3.7 (2016-06-20)
========================

* Dugong now supports server responses that specify just ``Connection:
  close`` instead of providing the response length or using chunked
  encoding.

* Dugong now honors the `~ssl.SSLContext.check_hostname` attribute of
  `~ssl.SSLContext` objects.

Release 3.6 (2016-04-23)
========================

* Dugong now uses semantic versioning. This means that
  backwards-incompatible versions (i.e., versions that change the
  existing API in some way) will be reflected in an increase of the
  major version number, i.e. the next backwards-incompatible version
  will have version 4.0.

* Various minor bugfixes.

Release 3.5 (2015-01-31)
========================

* The `is_temp_network_error` function now knows about more kinds of
  temporary errors, in particular also about those that do not have a
  corresponding Python exception (e.g. no route to host).

Release 3.4 (2014-11-29)
========================

* The :file:`examples/extract_links.py` script is now Python 3.3
  compatible again.

* Dugong now has proper proxy support for plain HTTP
  connections. Thanks to Vincent Bernat for the patch.

* Dugong now raises `DNSUnavailable` or `HostnameNotResolvable`
  exceptions instead of the more generic `socket.gaierror` and
  `socket.herror` exceptions where possible.

Release 3.3 (2014-08-06)
========================

* It was possible for some methods to raise `BrokenPipeError`, or
  `ConnectionResetError` instead of `ConnectionClosed` (especially
  under FreeBSD). This has now been fixed.

* It was possible for methods that need to read data from the server
  to raise `AssertionError` in some circumstances. This has been
  fixed.

Release 3.2 (2014-07-27)
========================

* A `HTTPConnection` instance can now be used as a context manager.

* If a connection is closed unexpectedly while request body data is
  being written to the server (i.e., during a call to
  `HTTPConnection.write` or `HTTPConnection.co_write`), dugong now
  pretends that the body has been sent to the server completely (while
  still raising `ConnectionClosed`).

  This makes it possible to catch the exception and nevertheless call
  `~HTTPConnection.read_response` (or
  `~HTTPConnection.co_read_response`) to try to read an error response
  that the server may have sent during the upload (if no response has
  been received, `ConnectionClosed` will be raised again).

* `is_temp_network_error` now actively tries to distinguish between
  permanent and temporary name resolution problems by attempting to
  resolve a number of test hostnames.

* `HTTPConnection` has a new `~HTTPConnection.timeout`
  attribute. Regular `HTTPConnection` methods (i.e., no coroutines)
  will now raise `ConnectionTimedOut` if no data could be send or
  received for *timeout* seconds.

Release 3.1 (2014-06-28)
========================

* Fixed a problem with some testcases failing with a BrokenPipeError.

* Fixed a bug that, in some cases, resulted in additional ``\0`` bytes
  being appended at the end of the response body, or in an incorrect
  `InvalidResponse` exception being raised.

* When trying to continue reading or writing body data after calling
  `HTTPConnection.disconnect`, dugong now raises `ConnectionClosed`
  instead of `AttributeError`.

Release 3.0, (2014-04-20)
=========================

* Major version bump because of backwards incompatible changes.

* Added `HTTPConnection.read_raw` method.

* The `PollNeeded` class now uses the `!select.POLLIN` and
  `!select.POLLOUT` constants instead of `!select.EPOLLIN` and
  `!select.EPOLLOUT` to signal what kind of I/O needs to be
  performed. This makes dugong compatible with systems lacking epoll
  (e.g. FreeBSD).

* The unit tests now check if the host is reachable before trying to
  run the example scripts. This avoids bogus test errors if
  there is no internet connection or if the remote host is down.
  (issue #7).


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
