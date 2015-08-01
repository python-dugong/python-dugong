#!/usr/bin/env python3
'''
test_dugong.py - Unit tests for Dugong - run with py.test

Copyright © 2014 Nikolaus Rath <Nikolaus.org>

This module may be distributed under the terms of the Python Software Foundation
License Version 2.  The complete license text may be retrieved from
http://hg.python.org/cpython/file/65f2c92ed079/LICENSE.
'''

if __name__ == '__main__':
    import pytest
    import sys
    sys.exit(pytest.main([__file__] + sys.argv[1:]))

import subprocess
import os
import sys
import pytest
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

try:
    import asyncio
except ImportError:
    asyncio = None

basename = os.path.join(os.path.dirname(__file__), '..')

class HTTPRequestHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

class HTTPServerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.host = 'localhost'
        self.httpd = TCPServer((self.host, 0), HTTPRequestHandler)
        self.port = self.httpd.socket.getsockname()[1]
        self.url = 'http://%s:%d' % (self.host, self.port)

    def run(self):
        self.httpd.serve_forever()

    def shutdown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

@pytest.fixture(scope='module')
def mock_server(request):
    os.chdir(basename)
    httpd = HTTPServerThread()
    httpd.start()
    request.addfinalizer(httpd.shutdown)
    return httpd

def test_httpcat(mock_server):
    cmdline = [sys.executable, 'examples/httpcat.py',
               mock_server.url + '/setup.py' ]
    with open('/dev/null', 'wb') as devnull:
        subprocess.check_call(cmdline, stdout=devnull)

def test_extract_links(mock_server):
    cmdline = [sys.executable, 'examples/extract_links.py',
               mock_server.url + '/test/' ]
    with open('/dev/null', 'wb') as devnull:
        subprocess.check_call(cmdline, stdout=devnull)

@pytest.mark.skipif(asyncio is None,
                    reason='asyncio module not available')
def test_pipeline1(mock_server):
    cmdline = [sys.executable, 'examples/pipeline1.py' ]
    for name in os.listdir('test'):
        if os.path.isdir('test/'+name):
            name += '/' # avoid redirect
        cmdline.append('%s/test/%s' % (mock_server.url, name))

    with open('/dev/null', 'wb') as devnull:
        subprocess.check_call(cmdline, stdout=devnull)
