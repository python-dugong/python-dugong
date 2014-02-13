Known Issues
============

.. currentmodule:: dugong

* `HTTPConnection` instances can not be used as IO streams with the
  :mod:`io` classes. This is because they attempt to read and write
  directly to the socket file descriptor returned by
  `HTTPConnection.fileno` (which is required for compatibility with
  `select`). A workaround is to use the corresponding Python functions
  in the :mod:`!_pyio` module.
