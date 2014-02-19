==========
 Tutorial
==========

.. currentmodule:: dugong


Basic Use
=========

A HTTP request can be send and read in four lines::

  conn = HTTPConnection('www.python.org')
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

    conn = HTTPConnection('www.google.com', ssl_context=ssl_context)
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
  conn = HTTPConnection('somehost.com')
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
  conn = HTTPConnection('somehost.com')
  conn.send_request('POST', '/form.php', body=request_body)
  conn.read_response()
  
or (if you want to send bigger amounts) you can provide it in multiple
chunks::
  
  conn = HTTPConnection('somehost.com')
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

  conn = HTTPConnection('somehost.com')
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
  while True:
      try:
          conn = HTTPConnection('www.python.org')
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
          
  
Pipelining
==========

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

  conn = HTTPConnection('somehost.com')

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


Non-blocking, Coroutine based API
=================================

Dugong fully supports non-blocking operation using coroutines (as a
matter of fact, most of the methods introduced so far are implemented
as thin, blocking wrappers around the correponding
coroutines). Coroutines in Python are generators, and are obtained by
calling generator functions. A coroutine can be resumed by passing it
to the built-in `next` function, and the coroutine can pass the
control flow back to the caller by :ref:`yielding <yieldexpr>`
values. When the coroutine eventually terminates, the last call to
`next` will raise `StopIteration` exception, whose *value* attribute
holds the return value of the coroutine.

The above paragraph is completely general and applies to any Python
coroutine. What you need to know in order to really make use of a
coroutine is when it will yield, what values it will yield, and what
value it will eventually return. For coroutines returned by Dugong,
the following rules apply:

* A coroutine yields whenever an IO operation would block.

* The yielded value is always a `PollNeeded` instance that contains
  information about the IO request that would block.

* The final return value is the "regular" result. 
  
All `HTTPConnection` methods that start with ``co_`` return
coroutines. For example, the proper way to read a response body
without blocking is (to keep the example simple, the first three
method calls still use the simple, blocking API, and only the
`~HTTPConnection.readall` call uses a coroutine)::

  conn = HTTPConnection('somehost.com')
  conn.send_request('GET', 'slow_stuff.html')
  resp = conn.read_response()
  assert resp.status == 200

  crt = conn.co_readall() # crt = coroutine
  try:
      while True:
          io_req = next(crt)
          # No data ready for reading, need to wait for data 
          # to arrive from server
  except StopIteration as exc:
      body = exc.value
  
As it is, this code fragment would simply do a busy-loop until the
data has arrived from the server. In practice, this is not desired,
and one probably wants to do some work while waiting for the data to
arrive. But how do we know when there is data available? The necessary
information is contained in the `~PollNeeded.fd` and
`~PollNeeded.mask` attributes of the `io_req <PollNeeded>` object:
they contain the file descriptor and type of I/O operation that we are
waiting for. This information can then be used in e.g. a
`~select.select` call. If we simply want to wait until the data is
there, this could be done as follows::

  from select import select, EPOLLIN
  
  # ...
  
  crt = conn.co_readall()
  try:
      while True:
          io_req = next(crt)
          
          # We know we're waiting for data to arrive
          assert io_req.mask == EPOLLIN
          
          # Wait for data to be be ready for reading on the given fd
          select((io_req.fd,), (), ())
  except StopIteration as exc:
      body = exc.value
   
In general, the `~PollNeeded.mask` attribute is an :ref:`epoll
<epoll-objects>` compatible event mask. In the above situation,
however, we don't explicity test the mask since we know that the
coroutine must be waiting for data to arrive.

.. _coroutine_pipelining:
   
Pipelining with Coroutines
--------------------------

Of course, the above example still doesn't provide any additional
functionality over a simple `~HTTPConnection.readall` call -- we have
replaced a single method call with a rather complicated loop. The
advantage of coroutines comes from the fact that inside the loop you
can now do other work -- for example, you can simultaenously send
requests and read responses, which allows you to pipeline requests
without using multiple threads, and without danger of deadlocking. For
example, suppose you want to check a large number of URLs (stored in
the *path_list* variable) for missing documents. This could be
implemented as follows::

    send_request_crt = None
    read_response_crt = None
    missing_documents = []
    conn = HTTPConnection('somehost.com')
    while path_list: # while there are requests to send

        if not send_request_crt:
            # We are not sending any requests at the moment, so start a new
            # send_request coroutine
            path = path_list.pop()
            send_request_crt = conn.co_send_request('HEAD', path)

        if not read_response_crt:
            # We are not reading any responses at the moment, so start a new
            # read_response coroutine.
            read_response_crt = conn.co_read_response()

        try:
            # Send request until we can't send any more data without blocking
            io_req_1 = next(send_request_crt)
        except StopIteration:
            # Request has been sent completely
            send_request_crt = None
            continue

        try:
            # Read response until we have to wait for more data from the server
            io_req_2 = next(read_response_crt)
        except StopIteration as exc:
            # Response has been read completely
            read_response_crt = None
            resp = exc.value
            if resp.status != 200:
                missing_documents.append(resp.path)
            # Since we sent a HEAD request, this is guaranteed to return b''
            # without blocking
            assert conn.read(10) == b''
            continue

        # We can't do any more work, wait until we're able to read or send
        # data again.
        assert io_req_1.mask == EPOLLOUT
        assert io_req_2.mask == EPOLLIN
        select((io_req_2.fd,), (io_req_1.fd,), ())

    # All requests have been sent, now we just need to collect the
    # remaining responses.
    while conn.response_pending():
        try:
            io_req_2 = next(read_response_crt)
        except StopIteration as exc:
            resp = exc.value
            if resp.status != 200:
                missing_documents.append(resp.path)
            read_response_crt = conn.co_read_response()
        else:
            io_req_2.poll()

Note that in the last line we have used a convience method of
`PollNeeded` instances: `~PollNeeded.poll` calls `~select.select` with
the right parameters and blocks until the given IO request can be
satisfied.

The above code may look a bit intimidating, but it can be considerably
simplified if we use the :ref:`yield from <yieldexpr>` expression. In
fact, using ``yield from`` we can trivially extend the example to also
save all the document bodies to disk::
  
    conn = HTTPConnection('somehost.com')
    missing_documents = []

    # This function returns a coroutine that sends all requests
    def send_requests():
        for path in path_list:
            yield from conn.co_send_request('GET', path)

    # This functions returns a coroutine that reads all responses
    def read_responses():
        for (i, path) in enumerate(path_list):
            resp = yield from conn.co_read_response()
            if resp.status != 200:
                missing_documents.append(resp.path)
            with open('doc_%i.dat' % i, 'wb') as fh:
                buf = yield from conn.readall()
                fh.write(buf)

    send_request_crt = send_requests()
    read_response_crt = read_responses()
    while True:
        # Send requests until we block
        if send_request_crt:
            try:
                io_req_1 = next(send_request_crt)
            except StopIteration:
                # All requests sent
                send_request_crt = None

        # Read responses until we block
        try:
            io_req_2 = next(read_response_crt)
        except StopIteration as exc:
            # All responses read
            break

        # Wait for fds to become ready for I/O
        assert io_req_1.mask == EPOLLOUT
        assert io_req_2.mask == EPOLLIN
        select((io_req_2.fd,), (io_req_1.fd,), ())


        
