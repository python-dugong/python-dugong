Coroutine Support
=================

.. currentmodule:: dugong

The last point warrants slightly more explanation. When called with
``via_cofun=True``, the `~HTTPConnection.send_request` method does not
send the request itself, but prepares and returns a cofunction (in
form of a Python generator) that performs the actual transmission.  A
cofunction is entered and resumed by passing it to the built-in `next`
function. Execution of the cofunction is completed (and all data has
been sent) when the `next` call raises `StopIteration`. This means
that a cofunction can be conviently used as iterator in a for loop:
whenever the cofunction suspends, the loop body will be executed, and
then the coroutine resumed.

The confunction based API is suitable to avoid deadlocks, because the
cofunctions returned by this class will suspend sending request data as soon
as (even partial) response data has been received from the server. To avoid
congestion of the transmit buffers (and eventual deadlock), the caller is
expected to read the available response data (using one of the ``read*``
methods) before resuming the cofunction.

In code, this looks as follows::

    documents = [ '/file_{}.html'.format(x) for x in range(10) ]
    conn = HTTPConnection('www.server.com')

    def read_response():
        nonlocal out_fh
        if conn.get_current_response(): 
            # Active response, so we are reading body
            out_fh.write(conn.read(8192))
        else:
            # No active response
            (method, url, status, reason, header) = conn.read_response()
            assert status == 200
            out_fh = open(url[1:], 'w')

    # Try to send all the requests...
    for doc in documents:
        cofun = conn.send_request('GET', doc, via_cofun=True)
        for _ in cofun: # value of _ is irrelevant and undefined
            # ..but interrupt if partial response data is available
            read_response()

    # All requests send, now read rest of responses
    while conn.response_pending():
        read_response()


If request body data needs to be transmitted as well, a bit more work
is needed. In principle, the `~HTTPConnection.write` method could
return a cofunction as well. However, this typically does not make
sense as `~HTTPConnection.write` itself is already called repeatedly
until all data has been written. Instead, `~HTTPConnection.write`
therefore accepts a *partial=True* argument, which causes it to write
only as much data as currently fits into the transmit buffer (the
actual number of bytes written is returned). As long as a prior
`select` indicates that the connection is ready for writing, calls to
`~HTTPConnection.write` (with ``partial=True``) are then guaranteed
not to block.

For example, a number of large files could be uploaded using pipelining with
the following code::

    from select import select
    from http.client import NO_CONTENT

    files = [ 'file_{}.tgz'.format(x) for x range(10) ]
    conn = HTTPConnection('www.server.com')

    def read_response():
        resp = conn.read_response()
        assert resp.status == NO_CONTENT
        assert conn.read(42) == b''

    for name in files:
        cofun = conn.send_request('PUT', '/' + name, via_cofun=True,
                                  body=BodyFollowing(os.path.getsize(name)))
        for _ in cofun:
            read_response()

        with open(name, 'rb') as fh:
            buf = b''
            while True:
                (writeable, readable, _) = select((conn.socket_fileno(),),
                                                  (conn.socket_fileno(),), ())
                if readable:
                    read_response()

                if not writeable:
                    continue

                if not buf:
                    buf = fh.read(8192)
                    if not buf:
                        break

                len_ = conn.write(buf, partial=True)
                buf = buf[len_:]

    # All requests sent, now read rest of responses
    while conn.response_pending():
        read_response()


Since sending a file-like object as the request body is a rather
common use case, there actually is a convenience
`~HTTPConnection.co_sendfile` method that provides a cofunction for
this special case. Using `~HTTPConnection.co_sendfile`, the outer loop
in the above code can be written as::

    for name in files:
        cofun = conn.send_request('PUT', '/' + name, via_cofun=True,
                                  body=BodyFollowing(os.path.getsize(name)))
        for _ in cofun:
            read_response()

        with open(name, 'rb') as fh:
            cofun = conn.co_sendfile(fh)
            for _ in cofun:
                read_response()


The use of coroutines and `select` allows pipelining with low latency
and high throughput. However, it should be noted that even when using
the techniques described above `HTTPConnection` instances do not
provide a fully non-blocking API. Both the `~HTTPConnection.read` and
`~HTTPConnection.read_response` methods may still block if
insufficient data is available in the receive buffer. This is because
`~HTTPConnection.read_response` always reads the entire response
header, and `~HTTPConnection.read` always retrieves chunk headers
completely. It is expected that this will not significantly impact
throughput, as response headers are typically short enough to be
transmitted in a single TCP packet, and the likelihood of a chunk
header being split among two packets is very small.

It is also important that `select` should only be used with
`HTTPConnection` instances to avoid congestion when pipelining
multiple requests, i.e. to interrupt transmitting request data when
response data is available. In particular, a `select` call MUST NOT
must not be used to wait for incoming data. This can lead to a
deadlock, since server responses are buffered internally by the
`HTTPConnection` instance and may thus be available for retrieval even
if `select` reports that no data is available for reading from the
socket.
