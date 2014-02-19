Known Issues
============

.. currentmodule:: dugong

* When sending requests with a ``Range`` header, Dugong may be unable
  to parse the server response. This happens if the server sends
  ``multipart/byteranges`` data without a ``Content-Length``
  header. This is allowed by RFC 2616, because the content length is
  implicit in the multipart body, but Dugong does not yet support
  parsing the body.
