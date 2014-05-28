#!/usr/bin/env python3
'''
test_dugong.py - Unit tests for dugong.py - run with py.test

Copyright (c) Nikolaus Rath <Nikolaus@rath.org>

This module may be distributed under the terms of the Python Software Foundation
License Version 2.  The complete license text may be retrieved from
http://hg.python.org/cpython/file/65f2c92ed079/LICENSE.
'''

if __name__ == '__main__':
    import pytest
    import sys

    # For profiling:
    #import cProfile
    #cProfile.run('pytest.main([%r] + sys.argv[1:])' % __file__,
    #             'cProfile.dat')
    #sys.exit()

    sys.exit(pytest.main([__file__] + sys.argv[1:]))

from dugong import HTTPConnection, BodyFollowing, CaseInsensitiveDict, _join
import dugong
from http.server import BaseHTTPRequestHandler, _quote_html
from io import TextIOWrapper
from base64 import b64encode
import http.client
import itertools
import pytest
import time
import ssl
import re
import os
import hashlib
import threading
import socketserver
from pytest import raises as assert_raises

# We want to test with a real certificate
SSL_TEST_HOST = 'www.google.com'

TEST_DIR = os.path.dirname(__file__)

class HTTPServer(socketserver.TCPServer):
    # Extended to add SSL support
    def get_request(self):
        (sock, addr) = super().get_request()
        if self.ssl_context:
            sock = self.ssl_context.wrap_socket(sock, server_side=True)
        return (sock, addr)


class HTTPServerThread(threading.Thread):
    def __init__(self, use_ssl=False):
        super().__init__()
        self.host = 'localhost'
        self.httpd = HTTPServer((self.host, 0), MockRequestHandler)
        self.port = self.httpd.socket.getsockname()[1]
        self.use_ssl = use_ssl

        if use_ssl:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            ssl_context.options |= ssl.OP_NO_SSLv2
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.load_cert_chain(os.path.join(TEST_DIR, 'server.crt'),
                                        os.path.join(TEST_DIR, 'server.key'))
            self.httpd.ssl_context = ssl_context
        else:
            self.httpd.ssl_context = None

    def run(self):
        self.httpd.serve_forever()

    def shutdown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

@pytest.fixture(scope='module', params=('plain', 'ssl'))
def http_server(request):
    httpd = HTTPServerThread(use_ssl=(request.param == 'ssl'))
    httpd.start()
    request.addfinalizer(httpd.shutdown)
    return httpd

@pytest.fixture()
def conn(request, http_server):
    if http_server.use_ssl:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ssl_context.options |= ssl.OP_NO_SSLv2
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.load_verify_locations(cafile=os.path.join(TEST_DIR, 'ca.crt'))
    else:
        ssl_context = None
    conn = HTTPConnection(http_server.host, port=http_server.port,
                          ssl_context=ssl_context)
    request.addfinalizer(conn.disconnect)
    return conn

def check_http_connection():
    '''Skip test if we can't connect to ssl test server'''

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ssl_context.options |= ssl.OP_NO_SSLv2
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.set_default_verify_paths()
    try:
        conn = http.client.HTTPSConnection(SSL_TEST_HOST, context=ssl_context)
        conn.request('GET', '/')
        resp = conn.getresponse()
        assert resp.status == 200
    except:
        pytest.skip('%s not reachable but required for testing' % SSL_TEST_HOST)
    finally:
        conn.close()

def test_connect_ssl():
    check_http_connection()

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ssl_context.options |= ssl.OP_NO_SSLv2
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.set_default_verify_paths()

    conn = HTTPConnection(SSL_TEST_HOST, ssl_context=ssl_context)
    conn.send_request('GET', '/')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/'
    conn.discard()
    conn.disconnect()

def test_invalid_ssl():
    check_http_connection()

    # Don't load certificates
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.options |= ssl.OP_NO_SSLv2
    context.verify_mode = ssl.CERT_REQUIRED

    conn = HTTPConnection(SSL_TEST_HOST, ssl_context=context)
    with pytest.raises(ssl.SSLError):
        conn.send_request('GET', '/')
    conn.disconnect()

def test_get_pipeline(conn):

    # We assume that internal buffers are big enough to hold
    # a few requests

    paths = [ '/send_120_bytes' for _ in range(3) ]

    # Send requests
    for path in paths:
        crt = conn.co_send_request('GET', path)
        for io_req in crt:
            # If this fails, then internal buffers are too small
            assert io_req.poll(10)

    # Read responses
    for path in paths:
        resp = conn.read_response()
        assert resp.status == 200
        assert resp.path == path
        assert conn.readall() == DUMMY_DATA[:120]

def test_ssl_info(conn):
    conn.get_ssl_cipher()
    conn.get_ssl_peercert()

def test_blocking_send(conn):
    # Send requests until we block because all TCP buffers are full

    path = '/send_100_1200-byte_chunks'
    for count in itertools.count():
        crt = conn.co_send_request('GET', path, body=DUMMY_DATA[:8192])
        flag = False
        for io_req in crt:
            if not io_req.poll(1):
                flag = True
                break
        if flag:
            break
        if count > 1000000:
            pytest.fail("no blocking even after %d requests!?" % count)

    # Read responses
    for i in range(count):
        resp = conn.read_response()
        assert resp.status == 200
        conn.discard()

    # Now we should be able to complete the request
    assert io_req.poll(5)
    with pytest.raises(StopIteration):
        next(crt)

    resp = conn.read_response()
    assert resp.status == 200
    conn.discard()

def test_blocking_read(conn):
    delay = 10
    while True:
        conn.send_request('GET', '/send_10_120-byte_chunks_delay_%d_ms' % delay)
        resp = conn.read_response()
        assert resp.status == 200

        interrupted = 0
        parts = []
        while True:
            crt = conn.co_read(100)
            try:
                while True:
                    io_req = next(crt)
                    interrupted += 1
                    assert io_req.poll(5)
            except StopIteration as exc:
                buf = exc.value
                if not buf:
                    break
                parts.append(buf)
        assert not conn.response_pending()

        assert _join(parts) == DUMMY_DATA[:120]*10
        if interrupted >= 8:
            break
        elif delay > 5000:
            pytest.fail('no blocking read even with %f sec sleep' % delay)
        delay *= 2

def test_discard(conn):
    conn.send_request('GET', '/send_512_bytes')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/send_512_bytes'
    assert resp.length == 512
    conn.discard()
    assert not conn.response_pending()

def test_discard_chunked(conn):
    conn.send_request('GET', '/send_4_512-byte_chunks')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/send_4_512-byte_chunks'
    assert resp.length is None
    conn.discard()
    assert not conn.response_pending()

def test_read_text(conn):
    conn.send_request('GET', '/send_%d_bytes' % len(DUMMY_DATA))
    conn.read_response()
    fh = TextIOWrapper(conn)
    assert fh.read() == DUMMY_DATA.decode('utf8')
    assert not conn.response_pending()

def test_read_text2(conn):
    conn.send_request('GET', '/send_%d_bytes' % len(DUMMY_DATA))
    conn.read_response()
    fh = TextIOWrapper(conn)

    # This used to fail because TextIOWrapper can't deal with bytearrays
    fh.read(42)

def test_read_text3(conn):
    conn.send_request('GET', '/send_%d_bytes' % len(DUMMY_DATA))
    conn.read_response()
    fh = TextIOWrapper(conn)

    # This used to fail because TextIOWrapper tries to read from
    # the underlying fh even after getting ''
    while True:
        if not fh.read(77):
            break

    assert not conn.response_pending()

def test_read_identity(conn):
    conn.send_request('GET', '/send_512_bytes')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/send_512_bytes'
    assert resp.length == 512
    assert conn.readall() == DUMMY_DATA[:512]
    assert not conn.response_pending()

def test_exhaust_buffer(conn):
    if conn.ssl_context:
        pytest.skip('test does not have ssl support yet')

    conn._rbuf = dugong._Buffer(600)
    conn.send_request('GET', '/send_512_bytes')
    conn.read_response()

    # Test the case where the readbuffer is truncated and
    # returned, instead of copied
    conn._rbuf.compact()
    for io_req in conn._co_fill_buffer(1):
        io_req.poll()
    assert conn._rbuf.b == 0
    assert conn._rbuf.e > 0
    buf = conn.read(600)
    assert len(conn._rbuf.d) == 600
    assert buf == DUMMY_DATA[:len(buf)]
    assert conn.readall() == DUMMY_DATA[len(buf):512]

def test_full_buffer(conn):
    if conn.ssl_context:
        pytest.skip('test does not have ssl support yet')

    conn._rbuf = dugong._Buffer(100)
    conn.send_request('GET', '/send_512_bytes')
    conn.read_response()

    buf = conn.read(101)
    pos = len(buf)
    assert buf == DUMMY_DATA[:pos]

    # Make buffer empty, but without capacity for more
    assert conn._rbuf.e == 0
    conn._rbuf.e = len(conn._rbuf.d)
    conn._rbuf.b = conn._rbuf.e

    assert conn.readall() == DUMMY_DATA[pos:512]

def test_readinto_identity(conn):
    conn.send_request('GET', '/send_512_bytes')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/send_512_bytes'
    assert resp.length == 512
    parts = []
    while True:
        buf = bytearray(600)
        len_ = conn.readinto(buf)
        if not len_:
            break
        parts.append(buf[:len_])
    assert _join(parts) == DUMMY_DATA[:512]
    assert not conn.response_pending()

def test_read_chunked(conn):
    conn.send_request('GET', '/send_3_300-byte_chunks')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.length is None
    assert conn.readall() == DUMMY_DATA[:300]*3
    assert not conn.response_pending()

def test_read_chunked2(conn):
    conn.send_request('GET', '/send_10_5-byte_chunks')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.length is None
    assert conn.readall() == DUMMY_DATA[:5]*10
    assert not conn.response_pending()

def test_readinto_chunked(conn):
    conn.send_request('GET', '/send_3_300-byte_chunks')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.length is None
    assert resp.path == '/send_3_300-byte_chunks'
    parts = []
    while True:
        buf = bytearray(600)
        len_ = conn.readinto(buf)
        if not len_:
            break
        parts.append(buf[:len_])
    assert _join(parts) == DUMMY_DATA[:300] * 3
    assert not conn.response_pending()

def test_double_read(conn):
    conn.send_request('GET', '/send_10_bytes')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.length == 10
    assert resp.path == '/send_10_bytes'
    with pytest.raises(dugong.StateError):
        resp = conn.read_response()

def test_read_raw(conn):
    conn.send_request('GET', '/send_unsupported')
    resp = conn.read_response()
    assert resp.status == 200
    with pytest.raises(dugong.UnsupportedResponse):
        conn.readall()
    assert conn.read_raw(512) == b'body data'
    assert conn.read_raw(512) == b''

def test_abort_read(conn):
    conn.send_request('GET', '/send_3_300-byte_chunks')
    resp = conn.read_response()
    assert resp.status == 200
    conn.read(200)
    conn.disconnect()
    assert_raises(dugong.ConnectionClosed, conn.read, 200)

def test_abort_co_read(conn):
    conn.send_request('GET', '/send_3_300-byte_chunks')
    resp = conn.read_response()
    assert resp.status == 200
    cofun = conn.co_read(450)
    next(cofun)
    conn.disconnect()
    assert_raises(dugong.ConnectionClosed, next, cofun)

def test_abort_write(conn):
    conn.send_request('PUT', '/allgood', body=BodyFollowing(42))
    conn.write(b'fooo')
    conn.disconnect()
    assert_raises(dugong.ConnectionClosed, conn.write, b'baar')

def test_write_toomuch(conn):
    conn.send_request('PUT', '/allgood', body=BodyFollowing(42))
    with pytest.raises(dugong.ExcessBodyData):
        conn.write(DUMMY_DATA[:43])

def test_write_toolittle(conn):
    conn.send_request('PUT', '/allgood', body=BodyFollowing(42))
    conn.write(DUMMY_DATA[:24])
    with pytest.raises(dugong.StateError):
        conn.send_request('GET', '/send_5_bytes')

def test_write_toolittle2(conn):
    conn.send_request('PUT', '/allgood', body=BodyFollowing(42))
    conn.write(DUMMY_DATA[:24])
    with pytest.raises(dugong.StateError):
        conn.read_response()

def test_write_toolittle3(conn):
    conn.send_request('GET', '/send_10_bytes')
    conn.send_request('PUT', '/allgood', body=BodyFollowing(42))
    conn.write(DUMMY_DATA[:24])
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/send_10_bytes'
    assert len(conn.readall()) == 10
    with pytest.raises(dugong.StateError):
        conn.read_response()

def test_put(conn):
    data = DUMMY_DATA
    conn.send_request('PUT', '/allgood', body=data)
    resp = conn.read_response()
    conn.discard()
    assert resp.status == 204
    assert resp.length == 0
    assert resp.reason == 'MD5 matched'

    headers = CaseInsensitiveDict()
    headers['Content-MD5'] = 'nUzaJEag3tOdobQVU/39GA=='
    conn.send_request('PUT', '/allgood', body=data, headers=headers)
    resp = conn.read_response()
    conn.discard()
    assert resp.status == 400
    assert resp.reason.startswith('MD5 mismatch')

def test_put_separate(conn):
    data = DUMMY_DATA
    conn.send_request('PUT', '/allgood', body=BodyFollowing(len(data)))
    conn.write(data)
    resp = conn.read_response()
    conn.discard()
    assert resp.status == 204
    assert resp.length == 0
    assert resp.reason == 'Ok, but no MD5'

    headers = CaseInsensitiveDict()
    headers['Content-MD5'] = b64encode(hashlib.md5(data).digest()).decode('ascii')
    conn.send_request('PUT', '/allgood', body=BodyFollowing(len(data)),
                      headers=headers)
    conn.write(data)
    resp = conn.read_response()
    conn.discard()
    assert resp.status == 204
    assert resp.length == 0
    assert resp.reason == 'MD5 matched'

    headers['Content-MD5'] = 'nUzaJEag3tOdobQVU/39GA=='
    conn.send_request('PUT', '/allgood', body=BodyFollowing(len(data)),
                      headers=headers)
    conn.write(data)
    resp = conn.read_response()
    conn.discard()
    assert resp.status == 400
    assert resp.reason.startswith('MD5 mismatch')

def test_100cont(conn):
    conn.send_request('PUT', '/fail_with_403', body=BodyFollowing(256),
                      expect100=True)
    resp = conn.read_response()
    assert resp.status == 403
    conn.discard()

    conn.send_request('PUT', '/all_good', body=BodyFollowing(256), expect100=True)
    resp = conn.read_response()
    assert resp.status == 100
    assert resp.length == 0
    conn.write(DUMMY_DATA[:256])
    resp = conn.read_response()
    assert resp.status == 204
    assert resp.length == 0

def test_100cont_2(conn):
    conn.send_request('PUT', '/fail_with_403', body=BodyFollowing(256),
                      expect100=True)

    with pytest.raises(dugong.StateError):
        conn.send_request('PUT', '/fail_with_403', body=BodyFollowing(256), expect100=True)

    conn.read_response()
    conn.readall()

def test_100cont_3(conn):
    conn.send_request('PUT', '/fail_with_403', body=BodyFollowing(256), expect100=True)

    with pytest.raises(dugong.StateError):
        conn.write(b'barf!')

    conn.read_response()
    conn.readall()

def test_tunnel(http_server):
    if http_server.use_ssl:
        pytest.skip('test does not have ssl support yet')

    conn = HTTPConnection('remote_server', proxy=(http_server.host, http_server.port))

    conn.send_request('GET', '/send_10_bytes')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/send_10_bytes'
    assert conn.readall() == DUMMY_DATA[:10]
    conn.disconnect()

def test_read_toomuch(conn):
    conn.send_request('GET', '/send_10_bytes')
    conn.send_request('GET', '/send_8_bytes')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/send_10_bytes'
    assert conn.readall() == DUMMY_DATA[:10]
    assert conn.read(8) == b''

def test_read_toolittle(conn):
    conn.send_request('GET', '/send_10_bytes')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/send_10_bytes'
    buf = conn.read(8)
    assert buf == DUMMY_DATA[:len(buf)]
    with pytest.raises(dugong.StateError):
        resp = conn.read_response()

def test_empty_response(conn):
    conn.send_request('HEAD', '/send_512_bytes')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/send_512_bytes'
    assert resp.length == 0

    # Check that we can go to the next response without
    # reading anything
    assert not conn.response_pending()
    conn.send_request('GET', '/send_512_bytes')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/send_512_bytes'
    assert resp.length == 512
    assert conn.readall() == DUMMY_DATA[:512]
    assert not conn.response_pending()

def test_head(conn):
    conn.send_request('HEAD', '/send_10_bytes')
    resp = conn.read_response()
    assert resp.status == 200
    assert len(conn.readall()) == 0

    conn.send_request('HEAD', '/fail_with_317')
    resp = conn.read_response()
    assert resp.status == 317
    assert len(conn.readall()) == 0

@pytest.fixture(params=(63,64,65,100,99,103,500,511,512,513))
def buffer_size(request):
    return request.param

def test_smallbuffer(conn, buffer_size):
    conn._rbuf = dugong._Buffer(buffer_size)
    conn.send_request('GET', '/send_512_bytes')
    resp = conn.read_response()
    assert resp.status == 200
    assert resp.path == '/send_512_bytes'
    assert resp.length == 512
    assert conn.readall() == DUMMY_DATA[:512]
    assert not conn.response_pending()

def test_mutable_read(conn):
    # Read data and modify it, to make sure that this doesn't
    # affect the buffer

    conn._rbuf = dugong._Buffer(129)
    conn.send_request('GET', '/send_512_bytes')
    conn.read_response()

    # Assert that buffer is full, but does not start at beginning
    assert conn._rbuf.b > 0

    # Need to avoid conn.read(), because it converts to bytes
    buf = dugong.eval_coroutine(conn.co_read(150))
    pos = len(buf)
    assert buf == DUMMY_DATA[:pos]
    memoryview(buf)[:10] = b'\0' * 10

    # Assert that buffer is empty
    assert conn._rbuf.b == 0
    assert conn._rbuf.e == 0
    buf = dugong.eval_coroutine(conn.co_read(150))
    assert buf == DUMMY_DATA[pos:pos+len(buf)]
    memoryview(buf)[:10] = b'\0' * 10
    pos += len(buf)

    assert conn.readall() == DUMMY_DATA[pos:512]
    assert not conn.response_pending()


DUMMY_DATA = ','.join(str(x) for x in range(10000)).encode()

class MockRequestHandler(BaseHTTPRequestHandler):

    server_version = "MockHTTP"
    protocol_version = 'HTTP/1.1'

    #def log_message(self, format, *args):
    #    pass

    def handle_expect_100(self):
        if self.handle_errors():
            return
        else:
            self.send_response_only(100)
            self.end_headers()
            return True

    def handle(self):
        # Ignore exceptions resulting from the client closing
        # the connection.
        try:
            return super().handle()
        except ValueError as exc:
            if exc.args ==  ('I/O operation on closed file.',):
                pass
            else:
                raise
        except BrokenPipeError:
            pass

    def do_GET(self):
        if self.handle_errors():
            return

        len_ = int(self.headers['Content-Length'])
        if len_:
            self.rfile.read(len_)

        hit = re.match(r'^/send_unsupported', self.path)
        if hit:
            self.send_response(200)
            self.send_header("Content-Type", 'application/octet-stream')
            self.end_headers()
            self.wfile.write(b'body data')
            self.wfile.close()
            return

        hit = re.match(r'^/send_([0-9]+)_bytes', self.path)
        if hit:
            len_ = int(hit.group(1))
            self.send_response(200)
            self.send_header("Content-Type", 'application/octet-stream')
            self.send_header("Content-Length", str(len_))
            self.end_headers()
            self.wfile.write(DUMMY_DATA[:len_])
            return

        hit = re.match(r'^/send_([0-9]+)_([0-9]+)-byte_chunks(?:_delay_([0-9]+)_ms)?',
                       self.path)
        if hit:
            count = int(hit.group(1))
            len_ = int(hit.group(2))
            delay = hit.group(3)
            delay = int(delay)*1e-3 if delay else 0
            self.send_response(200)
            self.send_header("Content-Type", 'application/octet-stream')
            self.send_header("Transfer-Encoding", 'chunked')
            self.end_headers()
            data = DUMMY_DATA[:len_]
            for i in range(count):
                if i % 3 == 0 and delay:
                    time.sleep(delay)
                self.wfile.write(('%x\r\n' % len_).encode('us-ascii'))
                if i % 3 == 1 and delay:
                    self.wfile.write(data[:len_//2])
                    time.sleep(delay)
                    self.wfile.write(data[len_//2:])
                else:
                    self.wfile.write(data)
                if i % 3 == 2 and delay:
                    time.sleep(delay)
                self.wfile.write(b'\r\n')
                self.wfile.flush()
            self.wfile.write(b'0\r\n\r\n')
            return

        self.send_error(500)

    def handle_errors(self):
        hit = re.match(r'^/fail_with_([0-9]+)', self.path)
        if hit:
            self.send_error(int(hit.group(1)))
            return True

        if self.command == 'PUT':
            encoding = self.headers['Content-Encoding']
            if encoding and encoding != 'identity':
                self.send_error(415)
                return True

        return False

    def do_PUT(self):
        if self.handle_errors():
            return

        len_ = int(self.headers['Content-Length'])
        data = self.rfile.read(len_)
        if 'Content-MD5' in self.headers:
            md5 = b64encode(hashlib.md5(data).digest()).decode('ascii')
            if md5 != self.headers['Content-MD5']:
                self.send_error(400, 'MD5 mismatch: %s vs %s'
                                   % (md5, self.headers['Content-MD5']))
                return

            self.send_response(204, 'MD5 matched')
        else:
            self.send_response(204, 'Ok, but no MD5')

        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_CONNECT(self):
        # Just pretend we're the remote server too
        self.send_response(200)
        self.end_headers()
        self.close_connection = 0

    def do_HEAD(self):
        if self.handle_errors():
            return

        hit = re.match(r'^/send_([0-9]+)_bytes', self.path)
        if hit:
            len_ = int(hit.group(1))
            self.send_response(200)
            self.send_header("Content-Type", 'application/octet-stream')
            self.send_header("Content-Length", str(len_))
            self.end_headers()
            return

        # No idea
        self.send_error(500)

    def send_error(self, code, message=None):
        # Overwritten to not close connection on errors and provide
        # content-length
        try:
            shortmsg, longmsg = self.responses[code]
        except KeyError:
            shortmsg, longmsg = '???', '???'
        if message is None:
            message = shortmsg
        explain = longmsg
        self.log_error("code %d, message %s", code, message)
        # using _quote_html to prevent Cross Site Scripting attacks (see bug #1100201)
        content = (self.error_message_format % {'code': code, 'message': _quote_html(message),
                                               'explain': explain}).encode('utf-8', 'replace')
        self.send_response(code, message)
        self.send_header("Content-Type", self.error_content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if self.command != 'HEAD' and code >= 200 and code not in (204, 304):
            self.wfile.write(content)
