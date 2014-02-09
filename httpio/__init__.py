'''
httpio.py - Python HTTP Client Module

Copyright (C) Nikolaus Rath <Nikolaus@rath.org>

This module may be distributed under the terms of the Python Software Foundation
License Version 2.

The CaseInsensitiveDict implementation is copyright 2013 Kenneth Reitz and
licensed under the Apache License, Version 2.0
(http://www.apache.org/licenses/LICENSE-2.0)
'''

import socket
import logging
import errno
import ssl
import hashlib
from base64 import b64encode
from collections import deque
from collections.abc import MutableMapping, Mapping
import email.parser
from http.client import (LineTooLong, HTTPS_PORT, HTTP_PORT, NO_CONTENT, NOT_MODIFIED)
from select import select

__version__ = '1.0'

log = logging.getLogger(__name__)

# Buffer size to use for reading from socket.
# Python <= 3.3's BufferedReader never reads more data than then
# buffer size on read1(), so we make sure this is reasonably large.
BUFSIZE = 128*1028

# maximal line length when calling readline().
_MAXLINE = 65536

CHUNKED_ENCODING = 'chunked_encoding'
IDENTITY_ENCODING = 'identity_encoding'

# Marker object for request body size when we're waiting
# for a 100-continue response from the server
WAITING_FOR_100c = object()

class HTTPResponse:
    '''
    This class encapsulates information about HTTP response.  Instances of this
    class are returned by the `HTTPConnection.read_response` method and have
    access to response status, reason, and headers.  Response body data
    has to be read directly from the `HTTPConnection` instance.
    '''

    def __init__(self, method, url, status, reason, headers,
                 length=None):
        
        #: HTTP Method of the request this was response is associated with
        self.method = method

        #: URL of the request this was response is associated with
        self.url = url

        #: HTTP status code returned by the server
        self.status = status

        #: HTTP reason phrase returned by the server
        self.reason = reason

        #: HTTP Response headers, a `email.message.Message` instance
        self.headers = headers

        #: Length of the response body or `None`, if not known
        self.length = length


class BodyFollowing:
    '''

    Sentinel class for the *body* parameter of the
    `~HTTPConnection.send_request` method. Passing an instance of this class
    declares that body data is going to be provided in separate calls to the
    `~HTTPConnection.write` method (or the `~HTTPConnection.co_sendfile`
    wrapper).

    If no length is specified in the constructor, the body data will be send
    using *chunked* encoding, which may or may not be supported by the remote
    server.
    '''

    __slots__ = 'length'
    
    def __init__(self, length=None):
        #: the length of the body data that is going to be send, or `None`
        #: to use chunked encoding.
        self.length = length

        
class _GeneralError(Exception):
    msg = 'General HTTP Error'

    def __init__(self, msg=None):
        if msg:
            self.msg = msg

    def __str__(self):
        return self.msg


class StateError(_GeneralError):
    '''
    Raised when attempting an operation that doesn't make
    sense in the current connection state.
    '''

    msg = 'Operation invalid in current connection state'


class ExcessBodyData(_GeneralError):
    '''
    Raised when trying to send more data to the server than
    announced.
    '''
    
    msg = 'Cannot send larger request body than announced'

class InvalidResponse(_GeneralError):
    '''
    Raised if the server produced an invalid response.
    '''

    msg = 'Server sent invalid response'


class UnsupportedResponse(_GeneralError):
    '''
    Raised if the server produced a response that we do not
    support (e.g. with undefined length).
    '''

    msg = 'Server sent unsupported response'


class ConnectionClosed(_GeneralError):
    '''
    Raised if the server unexpectedly closed the connection.
    '''

    msg = 'connection closed unexpectedly'


class HTTPConnection:
    '''
    This class encapsulates a HTTP connection.
    '''

    def __init__(self, hostname, port=None, ssl_context=None, proxy=None):

        if port is None:
            if ssl_context is None:
                self.port = HTTP_PORT
            else:
                self.port = HTTPS_PORT
        else:
            self.port = port

        self.ssl_context = ssl_context
        self.hostname = hostname
        self._sock_fh = None
        self._sock = None
            
        #: a tuple ``(hostname, port)`` of the proxy server to use or `None`.
        #: Note that currently only CONNECT-style proxying is supported.
        self.proxy = proxy
        
        #: a deque of ``(method, url, body_len)`` tuples corresponding to
        #: requests whose response has not yet been read completely. Requests
        #: with Expect: 100-continue will be added twice to this queue, once
        #: after the request header has been sent, and once after the request
        #: body data has been sent. *body_len* is `None`, or the size of the
        #: **request** body that still has to be sent when using 100-continue.
        self._pending_requests = deque()
        
        #: This attribute is `None` when a request has been sent completely.  If
        #: request headers have been sent, but request body data is still
        #: pending, it is set to a ``(method, url, body_len)`` tuple. *body_len*
        #: is the number of bytes that that still need to send, or
        #: WAITING_FOR_100c if we are waiting for a 100 response from the server.
        self._out_remaining = None
        
        #: Number of remaining bytes of the current response body (or current
        #: chunk), or None if the response header has not yet been read.
        self._in_remaining = None
        
        #: Transfer encoding of the active response (if any).
        self._encoding = None

        #: True if there is an active coroutine (there can be only one, since
        #: otherwise outgoing data from the different coroutines could get
        #: interleaved)
        self._coroutine_active = False


    def _send(self, buf, partial=False):
        '''Send data over socket

        If partial is True, may send only part of the data.
        Return number of bytes sent.
        '''

        while True:
            try:
                if partial:
                    len_ = self._sock.send(buf)
                else:
                    self._sock.sendall(buf)
                    len_ = len(buf)
                break
            except BrokenPipeError:
                raise ConnectionClosed('found closed when trying to write') from None
            except OSError as exc:
                if exc.errno == errno.EINVAL:
                    # Blackhole routing, according to ip(7)
                    raise ConnectionClosed('ip route goes into black hole') from None
                else:
                    raise
            except InterruptedError:
                # According to send(2), this means that no data has been sent
                # at all before the interruption, so we just try again.
                pass

        return len_

    
    def _tunnel(self):
        '''Set up CONNECT tunnel to final server'''
        
        self._send(("CONNECT %s:%d HTTP/1.0\r\n\r\n"
                    % (self.hostname, self.port)).encode('latin1'))

        self._sock_fh = self._sock.makefile(mode='rb', buffering=BUFSIZE)
        (status, reason) = self._read_status()
        self._read_header()

        if status != 200:
            self.close()
            raise OSError("Tunnel connection failed: %d %s" % (status, reason))
        
        self._sock_fh.detach()
        
    def connect(self):
        """Connect to the host and port specified in __init__

        This method generally does not need to be called manually.
        """

        if self.proxy:
            self._sock = socket.create_connection(self.proxy)
            self._tunnel()
        else:
            self._sock = socket.create_connection((self.hostname, self.port))

        if self.ssl_context:
            server_hostname = self.hostname if ssl.HAS_SNI else None
            self._sock = self.ssl_context.wrap_socket(self._sock, server_hostname=server_hostname)

            try:
                ssl.match_hostname(self._sock.getpeercert(), self.hostname)
            except:
                self.close()
                raise

        # Python <= 3.3's BufferedReader never reads more data than then
        # buffer size on read1(), so we make sure this is reasonably large.
        self._sock_fh = self._sock.makefile(mode='rb', buffering=BUFSIZE)
        self._out_remaining = None
        self._in_remaining = None
        self._pending_requests = deque()
  

    def close(self):
        '''Close HTTP connection'''

        if self._sock_fh:
            self._sock_fh.close()
            self._sock_fh = None

        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                # When called to reset after connection problems, socket
                # may have shut down already.
                pass
            self._sock.close()
            self._sock = None


    def write(self, buf, partial=False):
        '''Write request body data

        `ExcessBodyData` will be raised when attempting to send more data than
        required to complete the request body of the active request.

        If *partial* is True, this method may write less than *buf*. The actual
        number of bytes written is returned.
        '''

        if not self._out_remaining:
            raise StateError('No active request with pending body data')

        (method, url, remaining) = self._out_remaining
        if remaining is WAITING_FOR_100c:
            raise StateError("can't write when waiting for 100-continue")
            
        if len(buf) > remaining:
            raise ExcessBodyData('trying to write %d bytes, but only %d bytes pending'
                                    % (len(buf), remaining))

        log.debug('trying to write %d bytes', len(buf))
        len_ = self._send(buf, partial)
        log.debug('wrote %d bytes', len_)
        if len_ == remaining:
            log.debug('body sent fully')
            self._out_remaining = None
            self._pending_requests.append((method, url, None))
        else:
            self._out_remaining = (method, url, remaining - len_)
        return len_

        
    def co_sendfile(self, fh):
        '''Return coroutine to send request body data from *fh*

        *fh* needs to have *readinto* method. The method will read and transfer
        only as much data as necessary to complete the request body of the
        active request.
        
        This method does not send any data but returns a coroutine in form of a
        generator.  The data must then be sent by repeatedly calling `next` on
        the generator until `StopIteration` is raised. A `next` call will return
        normally only if not all data has been send *and* response data is
        available in the receive buffer.
        '''

        if not hasattr(fh, 'readinto'):
            raise TypeError('*fh* needs to have a *readinto* method')

        if not self._out_remaining:
            raise StateError('No active request with pending body data')

        sock_tup = (self._sock,)

        if self._coroutine_active:
            raise RuntimeError('Cannot have multiple coroutines sending simultaneously')

        buf = bytearray(min(BUFSIZE, self._out_remaining[2]))
        # We work on a memoryview instead of the bytearray, because
        # slicing a bytearray creates a new object.
        buf = memoryview(buf)
        sbuf = buf[:0]
        self._coroutine_active = True
        try:
            while True:
                log.debug('running select')
                (readable, writeable, _) = select(sock_tup, sock_tup, ())
                
                if readable:
                    log.debug('socket is readable, yielding')
                    yield

                if not writeable:
                    continue

                if len(sbuf) == 0:
                    log.debug('reading data from fh...')
                    len_ = fh.readinto(buf[:min(BUFSIZE, self._out_remaining[2])])
                    if not len_:
                        break
                    sbuf = buf[:len_]

                log.debug('sending data...')
                len_ = self.write(sbuf, partial=True)
                sbuf = sbuf[len_:]
                if not self._out_remaining:
                    break

        finally:
            self._coroutine_active = False


    def send_request(self, method, url, headers=None, body=None,
                     via_cofun=False, expect100=False):
        '''Send a new HTTP request to the server

        The message body may be passed in the *body* argument or be sent
        separately using the `.write` method (or the `.co_sendfile` wrapper). In
        the former case, *body* must be a :term:`bytes-like object`. In the
        latter case, *body* must be an a `BodyFollowing` instance specifying the
        length of the data that will be sent. If no length is specified, the
        data will be send using the *chunked* encoding (which may or may not be
        supported by the remote server).

        *headers* should be a mapping containing the HTTP headers to be send
        with the request. Multiple header lines with the same key are not
        supported. It is recommended to pass a `CaseInsensitiveDict` instance,
        other mappings will be converted to `CaseInsensitiveDict` automatically.
        
        If *via_cofun* is True, this method does not actually send any data
        but returns a coroutine in form of a generator.  The request data must
        then be sent by repeatedly calling `next` on the generator until
        `StopIteration` is raised. A `next` call will return normally only if
        not all data has been send *and* response data is available in the
        receive buffer.
        '''

        if expect100 and not isinstance(body, BodyFollowing):
            raise ValueError('expect100 only allowed for separate body')
        
        if self._sock is None:
            log.debug('connection seems closed, reconnecting.')
            self.connect()

        if self._out_remaining:
            raise StateError('body data has not been sent completely yet')

        if headers is None:
            headers = CaseInsensitiveDict()
        elif not isinstance(headers, CaseInsensitiveDict):
            headers = CaseInsensitiveDict(headers)

        pending_body_size = None
        if body is None:
            headers['Content-Length'] = '0'
        elif isinstance(body, BodyFollowing):
            if body.length is None:
                raise ValueError('Chunked encoding not yet supported.')
            log.debug('preparing to send %d bytes of body data', body.length)
            if expect100:
                headers['Expect'] = '100-continue'
                # Do not set _out_remaining, we must only send data once we've
                # read the response. Instead, save body size in
                # _pending_requests so that it can be restored by
                # read_response().
                pending_body_size = body.length
                self._out_remaining = (method, url, WAITING_FOR_100c)
            else:
                self._out_remaining = (method, url, body.length)
            headers['Content-Length'] = str(body.length)
            body = None
        elif isinstance(body, (bytes, bytearray, memoryview)):
            headers['Content-Length'] = str(len(body))
            if 'Content-MD5' not in headers:
                headers['Content-MD5'] = b64encode(hashlib.md5(body).digest()).decode('ascii')
        else:
            raise TypeError('*body* must be None, bytes-like or BodyFollowing')

        # Generate host header
        host = self.hostname
        if host.find(':') >= 0:
            host = '[{}]'.format(host)
        default_port = HTTPS_PORT if self.ssl_context else HTTP_PORT
        if self.port == default_port:
            headers['Host'] = host
        else:
            headers['Host'] = '{}:{}'.format(host, self.port)

        # Assemble request
        headers['Accept-Encoding'] = 'identity'
        headers['Connection'] = 'keep-alive'
        request = [ '{} {} HTTP/1.1'.format(method, url).encode('latin1') ]
        for key, val in headers.items():
            request.append('{}: {}'.format(key, val).encode('latin1'))
        request.append(b'')

        if body is not None:
            request.append(body)
        else:
            request.append(b'')

        buf = b'\r\n'.join(request)

        if via_cofun:
            def success():
                log.debug('request for %s %s transmitted completely', method, url)
                if not self._out_remaining or expect100:
                    self._pending_requests.append((method, url, pending_body_size))
            return self._co_send_data(buf, completion_hook=success)
        else:
            log.debug('sending %s request for %s', method, url)
            self._send(buf)
            if not self._out_remaining or expect100:
                self._pending_requests.append((method, url, pending_body_size))


    def _co_send_data(self, buf, completion_hook=None):
        '''Return generator for sending *buf*

        This method is ignorant of the current connection state and
        for internal use only.

        *completion_hook* is called once all data has been sent.
        '''

        sock_tup = (self._sock,)

        if self._coroutine_active:
            raise RuntimeError('Cannot have multiple coroutines sending simultaneously')

        self._coroutine_active = True
        try:
            while True:
                log.debug('running select')
                (readable, writeable, _) = select(sock_tup, sock_tup, ())

                if readable:
                    log.debug('socket is readable, yielding')
                    yield

                if not writeable:
                    continue

                log.debug('sending data...')
                sent = self._send(buf, partial=True)
                if sent == len(buf):
                    break
                buf = buf[sent:]

            if completion_hook is not None:
                completion_hook()
        finally:
            self._coroutine_active = False


    def fileno(self):
        '''Return file no of underlying socket

        This allows HTTPConnection instances to be used in a `select`
        call. Due to internal buffering, data may be available for
        *reading* (but not writing) even if `select` indicates that
        the socket is not currently readable.
        '''

        return self._sock.fileno()

    
    def response_pending(self):
        '''Return True if there are still outstanding responses

        This includes responses that have been partially read.
        '''

        return len(self._pending_requests) > 0

    
    def read_response(self):
        '''Read response status line and headers

        Return a `HTTPResponse` object containing information about
        response status, reason, and headers. The response body data
        may be retrieved with the `.read` or `.readall` methods.

        Even for a response with empty body, the `read` method must be called
        once before the next response can be processed.
        '''
        
        if len(self._pending_requests) == 0:
            raise StateError('No pending requests')

        if self._in_remaining is not None:
            raise StateError('Previous response not read completely')

        (method, url, body_size) = self._pending_requests[0]

        # Need to loop to handle any 1xx responses
        while True:
            (status, reason) = self._read_status()
            log.debug('got %03d %s', status, reason)
            header = self._read_header()

            if status < 100 or status > 199:
                break

            # We are waiting for 100-continue
            if body_size is not None and status == 100:
                break
            
        # Handle (expected) 100-continue
        if status == 100:
            assert self._out_remaining == (method, url, WAITING_FOR_100c)

            # We're ready to sent request body now
            self._out_remaining = self._pending_requests.popleft()
            self._in_remaining = None

            # Return early, because we don't have to prepare
            # for reading the response body at this time
            return HTTPResponse(method, url, status, reason, header, length=0)

        # Handle non-100 status when waiting for 100-continue
        elif body_size is not None:
            assert self._out_remaining == (method, url, WAITING_FOR_100c)
            # RFC 2616 actually states that the server MAY continue to read
            # the request body after it has sent a final status code
            # (http://tools.ietf.org/html/rfc2616#section-8.2.3). However,
            # that totally defeats the purpose of 100-continue, so we hope
            # that the server behaves sanely and does not attempt to read
            # the body of a request it has already handled. (As a side note,
            # this ambuigity in the RFC also totally breaks HTTP pipelining,
            # as we can never be sure if the server is going to expect the
            # request or some request body data).
            self._out_remaining = None


        #
        # Prepare to read body
        #
        body_length = None
        
        tc = header['Transfer-Encoding']
        if tc:
            tc = tc.lower()
        if tc and tc == 'chunked':
            log.debug('Chunked encoding detected')
            self._encoding = CHUNKED_ENCODING
            self._in_remaining = 0
        elif tc and tc != 'identity':
            # Server must not sent anything other than identity or chunked,
            # so we raise InvalidResponse rather than UnsupportedResponse
            raise InvalidResponse('Cannot handle %s encoding' % tc)
        else:
            log.debug('identity encoding detected')
            self._encoding = IDENTITY_ENCODING

        # does the body have a fixed length? (of zero)
        if (status == NO_CONTENT or status == NOT_MODIFIED or
            100 <= status < 200 or method == 'HEAD'):
            log.debug('no content by RFC')
            body_length = 0
            self._in_remaining = 0
            # for these cases, there isn't even a zero chunk we could read
            self._encoding = IDENTITY_ENCODING

        # Chunked doesn't require content-length
        elif self._encoding is CHUNKED_ENCODING:
            pass

        # Otherwise we require a content-length. We defer raising
        # the exception to read(), so that we can still return
        # the headers and status.
        elif 'Content-Length' not in header:
            log.debug('no content length and no chunkend encoding, will raise on read')
            self._encoding = UnsupportedResponse('No content-length and no chunked encoding')
            self._in_remaining = 0
            
        else:
            self._in_remaining = int(header['Content-Length'])
            body_length = self._in_remaining

        log.debug('setting up for %d byte body chunk', self._in_remaining)

        return HTTPResponse(method, url, status, reason, header, body_length)

    def _read_status(self):
        '''Read response line'''
        
        log.debug('reading response status line')

        # read status
        line = self._sock_fh.readline(_MAXLINE + 1)
        if len(line) > _MAXLINE:
            raise LineTooLong("status line too long")

        if not line:
            # Presumably, the server closed the connection before
            # sending a valid response.
            raise ConnectionClosed()

        line = line.decode('latin1')
        try:
            version, status, reason = line.split(None, 2)
        except ValueError:
            try:
                version, status = line.split(None, 1)
                reason = ""
            except ValueError:
                # empty version will cause next test to fail.
                version = ""

        if not version.startswith("HTTP/1"):
            raise UnsupportedResponse('%s not supported' % version)

        # The status code is a three-digit number
        try:
            status = int(status)
            if status < 100 or status > 999:
                raise InvalidResponse('%d is not a valid status' % status)
        except ValueError:
            raise InvalidResponse('%s is not a valid status' % status) from None

        return (status, reason.strip())

    
    def _read_header(self):
        '''Read response header'''
        
        log.debug('reading response header')

        # In the long term we should just use email.parser.BytesParser with the
        # email.policy.HTTPPolicy. However, as of Python 3.3 the existence of
        # the later is only provisional, and the documentation isn't quite clear
        # about what encoding will be used when using the BytesParser.
        headers = []
        while True:
            line = self._sock_fh.readline(_MAXLINE + 1)
            if len(line) > _MAXLINE:
                raise LineTooLong("header line too long")
            log.debug('got %r', line)
            headers.append(line)
            if line in (b'\r\n', b'\n', b''):
                break
        hstring = b''.join(headers).decode('iso-8859-1')
        msg = email.parser.Parser().parsestr(hstring)

        return msg


    def readall(self):
        '''Read complete response body'''

        parts = []
        while True:
            buf = self.read(BUFSIZE)
            if not buf:
                break
            parts.append(buf)

        return b''.join(parts)

    def discard(self):
        '''Read and discard current response body'''

        while True:
            buf = self.read(BUFSIZE)
            if not buf:
                break
    
    def read(self, len_):
        '''Read *len_* bytes of response body data
        
        This method may return less than *len_* bytes, but will return b'' only
        if the response body has been read completely. Further attempts to read
        more data after b'' has been returned will result in `StateError` being
        raised.
        '''
        
        if self._in_remaining is None:
            raise StateError('No active response with body')

        if not isinstance(len_, (int)):
            raise TypeError('*len_* must be int')

        if len_ == 0:
            return b''
        
        if self._encoding is IDENTITY_ENCODING:
            return self._read_id(len_)
        elif self._encoding is CHUNKED_ENCODING:
            return self._read_chunked(len_)
        elif isinstance(self._encoding, Exception):
            raise self._encoding
        else:
            raise RuntimeError('ooops, this should not be possible')

        
    def _read_id(self, len_):
        '''Read *len_* bytes from response body assuming identity encoding'''

        if self._in_remaining == 0:
            self._in_remaining = None
            self._pending_requests.popleft()
            return b''

        if len_ > self._in_remaining:
            len_ = self._in_remaining
        log.debug('trying to read %d bytes', len_)
        buf = self._sock_fh.read1(len_)
        self._in_remaining -= len(buf)

        if not buf:
            raise ConnectionClosed('connection closed with %d bytes outstanding'
                                   % self._in_remaining)
        return buf


    def _read_chunked(self, len_):
        '''Read *len_* bytes from response body assuming chunked encoding'''
        
        if self._in_remaining == 0:
            log.debug('starting next chunk')
            self._in_remaining = self._read_next_chunk_size()
            if self._in_remaining == 0:
                self._read_and_discard_trailer()
                self._in_remaining = None
                self._pending_requests.popleft()
                return b''

        buf = self._read_id(len_)
        
        if self._in_remaining == 0:
            log.debug('chunk completed')
            # toss the CRLF at the end of the chunk
            if len(self._sock_fh.read(2)) != 2:
                raise ConnectionClosed('connection closed with 2 bytes outstanding')

        return buf


    def _read_next_chunk_size(self):
        log.debug('reading next chunk size')

        # Read the next chunk size from the file
        line = self._sock_fh.readline(_MAXLINE + 1)
        if not line:
            raise ConnectionClosed('connection closed before final chunk')
        if len(line) > _MAXLINE:
            raise LineTooLong("chunk size")
        i = line.find(b";")
        if i >= 0:
            line = line[:i] # strip chunk-extensions
        try:
            return int(line, 16)
        except ValueError:
            raise InvalidResponse('Cannot read chunk size %r' % line) from None


    def _read_and_discard_trailer(self):
        log.debug('discarding chunk trailer')

        # read and discard trailer up to the CRLF terminator
        while True:
            line = self._sock_fh.readline(_MAXLINE + 1)
            if len(line) > _MAXLINE:
                raise LineTooLong("trailer line")
            if not line or line in (b'\r\n', b'\n', b''):
                break


def is_temp_network_error(exc):
    '''Return true if *exc* represents a potentially temporary network problem'''

    if isinstance(exc, (socket.timeout, ConnectionError, TimeoutError, InterruptedError,
                        ConnectionClosed, ssl.SSLZeroReturnError, ssl.SSLEOFError,
                        ssl.SSLSyscallError)):
        return True

    # Formally this is a permanent error. However, it may also indicate
    # that there is currently no network connection to the DNS server
    elif (isinstance(exc, (socket.gaierror, socket.herror))
          and exc.errno in (socket.EAI_AGAIN, socket.EAI_NONAME)):
        return True

    return False


class CaseInsensitiveDict(MutableMapping):
    """A case-insensitive `dict`-like object.

    Implements all methods and operations of
    :class:`collections.abc.MutableMapping` as well as `.copy`.

    All keys are expected to be strings. The structure remembers the case of the
    last key to be set, and :meth:`!iter`, :meth:`!keys` and :meth:`!items` will
    contain case-sensitive keys. However, querying and contains testing is case
    insensitive::

        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['aCCEPT'] == 'application/json' # True
        list(cid) == ['Accept'] # True

    For example, ``headers['content-encoding']`` will return the value of a
    ``'Content-Encoding'`` response header, regardless of how the header name
    was originally stored.

    If the constructor, :meth:`!update`, or equality comparison operations are
    given multiple keys that have equal lower-case representions, the behavior
    is undefined.
    """
    
    def __init__(self, data=None, **kwargs):
        self._store = dict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def lower_items(self):
        """Like :meth:`!items`, but with all lowercase keys."""
        return (
            (lowerkey, keyval[1])
            for (lowerkey, keyval)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
         return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, dict(self.items()))
