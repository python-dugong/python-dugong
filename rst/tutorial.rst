==========
 Tutorial
==========

.. currentmodule:: dugong


Basic Use
=========

A HTTP request can be send and read in four lines::

  with HTTPConnection('www.python.org') as conn:
      conn.send_request('GET', '/index.html')
      resp = conn.read_response()
      body = conn.readall()

`~HTTPConnection.send_request` is a `HTTPResponse` object that gives
access to the response header::

  print('Server said:')
  print('%03d %s' % (resp.status, resp.reason))
  for (key, value) in resp.headers.items():
      print('%s: %s' % (key, value))

`HTTPConnection.readall` returns a a :term:`bytes-like object`. To
convert to text, you could do something like ::

    hit = re.match(r'^(.+?)(?:; charset=(.+))?$', resp.headers['Content-Type'])
    if not hit:
        raise SystemExit("Can't determine response charset")
    elif hit.group(2): # found explicity charset
        charset = hit.group(2)
    elif hit.group(1).startswith('text/'):
        charset = 'latin1' # default for text/ types by RFC 2616
    else:
        raise SystemExit('Server sent binary data')
    text_body = body.decode(charset)


SSL Connections
===============

If you would like to establish a secure connection, you need to pass
the appropriate `~ssl.SSLContext` object to `HTTPConnection`. For example::

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ssl_context.options |= ssl.OP_NO_SSLv2
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.set_default_verify_paths()

    with HTTPConnection('www.google.com', ssl_context=ssl_context) as conn:
        conn.send_request('GET', '/index.html')
        resp = conn.read_response()
        body = conn.readall()

If you need information about the peer certificate, use the
`~HTTPConnection.get_ssl_peercert` method.

Streaming API
=============

When retrieving larger objects, it's generally better not to read the
response body all at once but in smaller chunks::

  BUFSIZE = 32*1024 # Read in 32 kB chunks

  # ...

  conn.send_request('GET', '/big_movie.mp4')
  resp = conn.read_response()
  assert resp.status == 200

  with open('big_movie.mp4', 'wb') as fh:
      while True:
          buf = conn.read(BUFSIZE)
          if not buf:
             break
          fh.write(buf)

Alternatively, the `~HTTPConnection.readinto` method may give better
performance in some situations::

  buf = bytearray(BUFSIZE)
  with open('big_movie.mp4', 'wb') as fh:
      while True:
          len_ = conn.readinto(buf)
          if not len_:
             break
          fh.write(buf[:len_])


Uploading Data
==============

If you want to send data to the server, you can provide the data
directly to `~HTTPConnection.send_request`, ::

  # A simple SQL injection attack for your favorite PHP script
  request_body = "'; DELETE FROM passwords;".encode('us-ascii')
  with HTTPConnection('somehost.com') as conn:
      conn.send_request('POST', '/form.php', body=request_body)
      conn.read_response()

or (if you want to send bigger amounts) you can provide it in multiple
chunks::

  # ...
  with open('newest_release.mp4', r'b') as fh:
      size = os.fstat(fh.fileno()).st_size
      conn.send_request('PUT', '/public/newest_release.mp4',
                        body=BodyFollowing(size))

      while True:
          buf = fh.read(BUFSIZE)
          if not buf:
              break
          conn.write(buf)

  resp = conn.read_response()
  assert resp.status in (200, 204)

Here we used the special `BodyFollowing` class to indicate that the
request body data will be provided in separate calls.

100-Continue Support
====================

When having to transfer large amounts of request bodies to the server,
you typically do not want to sent all the data over the network just
to find out that the server rejected the request because of
e.g. insufficient permissions. To avoid this situation, HTTP 1.1
specifies the *100-continue* mechanism. When using 100-continue, the
client transmits an additional ``Expect: 100-continue`` request
header, and then waits for the server to reply with status ``100
Continue`` before sending the request body data. If the server instead
responds with an error, the client can avoid pointless transmission of
the request body.

To use this mechanism, pass the *expect100* parameter to
`~HTTPConnection.send_request`, and call
`~HTTPConnection.read_response` twice: once before sending body data,
and a second time to read the final response::

  # ...
  with open('newest_release.mp4', r'b') as fh:
      size = os.fstat(fh.fileno()).st_size
      conn.send_request('PUT', '/public/newest_release.mp4',
                        body=BodyFollowing(size), expect100=True)

      resp = conn.read_response()
      if resp.status != 100:
          raise RuntimeError('Server said: %s' % resp.reason)

      while True:
          buf = fh.read(BUFSIZE)
          if not buf:
              break
          conn.write(buf)

  resp = conn.read_response()
  assert resp.status in (200, 204)


Retrying on Error
=================

Sometimes the connection to the remote server may get interrupted for
a variety of reasons, resulting in a variety of exceptions. For
convience, you may use the `is_temp_network_error` method to determine if a
given exception indicates a temporary problem (i.e., if it makes sense
to retry)::

  delay = 1
  conn = HTTPConnection('www.python.org')
  while True:
      try:
          conn.send_request('GET', '/index.html')
          conn.read_response()
          body = conn.readall()
      except Exception as exc:
          if is_temp_network_error(exc):
              print('Got %s, retrying..' % exc)
              time.sleep(delay)
              delay *= 2
          else:
              raise
      else:
          break
      finally:
          conn.disconnect()


Timing out
==========

It can take quite a long time before the operation system recognises
that a TCP/IP connection has been interrupted. If you'd rather be
informed right away when there has been no data exchange for some
period of time, dugong allows you to specify a custom timeout::

  conn = HTTPConnection('www.python.org')
  conn.timeout = 10
  try:
      conn.send_request('GET', '/index.html')
      conn.read_response()
      body = conn.readall()
  except ConnectionTimedOut:
      print('Unable to send or receive any data for more than',
            conn.timeout, 'seconds, aborting.')
      sys.exit(1)


.. _pipelining:

Pipelining with Threads
=======================

Pipelining means sending multiple requests in succession, without
waiting for the responses. First, let's consider how do **not** do it::

  # DO NOT DO THIS!
  conn = HTTPConnection('somehost.com')
  for path in path_list:
      conn.send_request('GET', path)

  bodies = []
  for path in path_list:
      resp = conn.read_response()
      assert resp.status == 200
      bodies.append(conn.readall())

This will probably even work as long as you don't have too many
elements in *path_list*. However, it is very bad practice, because at
some point the server will stop reading requests until some responses
have been read (because all the TCP buffers are full). At this point,
your application will deadlock.

One better way do it is to use threads. Dugong is not generally
threadsafe, but using one thread to send requests and one thread to
read responses is supported::

  with HTTPConnection('somehost.com') as conn:

      def send_requests():
          for path in path_list:
              conn.send_request('GET', path)
      thread = threading.thread(target=send_requests)
      thread.run()

      bodies = []
      for path in path_list:
          resp = conn.read_response()
          assert resp.status == 200
          bodies.append(conn.readall())

      thread.join()

Another way is to use coroutines. This is explained in the next
section.


.. _coroutine_pipelining:

Pipelining with Coroutines
==========================

Instead of using two threads to send requests and responses, you can
also use two coroutines. A coroutine is essentially a function that
can be suspended and resumed at specific points. Dugong coroutines
suspend themself when they would have to wait for an I/O operation to
complete. This makes them perfect for pipelining: we'll define one
coroutine that sends requests, and a second one to read responses, and
then execute them "interleaved": whenever we can't send another
request, we try to read a response, and if we can't read a response,
we try to send another request.

The following example demonstrates how to do this to efficiently
retrieve a large number of documents (stored in *url_list*):

.. literalinclude:: ../examples/pipeline1.py
   :start-after: start-example
   :end-before: end-example

Here we have used the :ref:`yield from expression <yieldexpr>` to
integrate the coroutines returned by
`~HTTPConnection.co_send_request`, `~HTTPConnection.co_read_response`,
and `~HTTPConnection.co_readall` into two custom coroutines
*send_requests* and *read_responses*. To schedule the coroutines, we
use `AioFuture` to obtain `asyncio Futures <asyncio.Future>` for them,
and then rely on the :mod:`asyncio` module to do the heavy lifting and
switch execution between them at the right times.

For more details about this, take a look at :ref:`coroutines`, or the
`asyncio documentation <asyncio>`.

