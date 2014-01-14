100-Continue Support
====================

.. currentmodule:: httpio

When having to transfer large amounts of request bodies to the server, you
typically do not want to sent all the data over the network just to find out
that the server rejected the request because of e.g. insufficient
permissions. To avoid this situation, HTTP 1.1 specifies the "100-continue"
mechanism. When using 100-continue, the client transmits an additional
``Expect: 100-continue`` request header, and then waits for the server to
reply with status ``100 Continue`` before sending the request body data. If
the server instead responds with an error, the client can avoid pointless
transmission of the request body.

To use this mechanism with the httpio module, simply pass the
*expect100* parameter to `~HTTPConnection.send_request`, and call
`~HTTPConnection.read_response` twice: once before sending body data,
and a second time to read the final response::

    conn = HTTPConnection(hostname)
    conn.send_request('PUT', '/huge_file', body=os.path.getsize(filename),
                      expect100=True)

    (method, url, status, reason, header) = conn.read_response()
    if status != 100:
        raise RuntimeError('Server said: %s' % reason)

    with open(filename, 'rb') as fh:
        for _ in conn.co_sendfile(fh):
            pass

    (method, url, status, reason, header) = conn.read_response()
    assert status in (200, 204)

