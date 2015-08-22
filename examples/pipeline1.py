#!/usr/bin/env python3

import sys
import os.path
from urllib.parse import urlsplit, urlunsplit

# We are running from the dugong source directory, append it to module path so
# that we can fallback on it if dugong hasn't been installed yet.
if __name__ == '__main__':
    basedir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
else:
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if (os.path.exists(os.path.join(basedir, 'setup.py')) and
    os.path.exists(os.path.join(basedir, 'dugong', '__init__.py'))):
    sys.path.append(basedir)

# When running from HG repo, enable all warnings
if os.path.exists(os.path.join(basedir, '.hg')):
    import warnings
    warnings.simplefilter('error')

# Assemble path list
hostname = None
path_list = []
for url in sys.argv[1:]:
    o = urlsplit(url)
    if hostname is None:
        hostname = o.hostname
        port = o.port
    elif (hostname, port) != (o.hostname, o.port):
        raise SystemExit('Can only pipeline to one host')
    if o.scheme != 'http':
        raise SystemExit('Can only do http')
    path_list.append(urlunsplit(('', '') + o[2:4] + ('',)))


# Code from here on is included in documentation
# start-example
import asyncio
import atexit
from dugong import HTTPConnection, AioFuture

# Get a MainLoop instance from the asyncio module to switch
# between coroutines (and clean up at program exit)
loop = asyncio.get_event_loop()
atexit.register(loop.close)

with HTTPConnection(hostname, port) as conn:
    # This generator function returns a coroutine that sends
    # all the requests.
    def send_requests():
        for path in path_list:
            yield from conn.co_send_request('GET', path)

    # This generator function returns a coroutine that reads
    # all the responses
    def read_responses():
        bodies = []
        for path in path_list:
            resp = yield from conn.co_read_response()
            assert resp.status == 200
            buf = yield from conn.co_readall()
            bodies.append(buf)
        return bodies

    # Create the coroutines
    send_crt = send_requests()
    recv_crt = read_responses()

    # Register the coroutines with the event loop
    send_future = AioFuture(send_crt, loop=loop)
    recv_future = AioFuture(recv_crt, loop=loop)

    # Run the event loop until the receive coroutine is done (which
    # implies that all the requests must have been sent as well):
    loop.run_until_complete(recv_future)

    # Get the result returned by the coroutine
    bodies = recv_future.result()

# end-example
