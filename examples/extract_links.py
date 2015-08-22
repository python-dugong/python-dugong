#!/usr/bin/env python3
'''
Extract all links from a URL.
'''

import sys
import os.path
from io import TextIOWrapper
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin, urlunsplit
import re
import ssl

# We are running from the dugong source directory, append it to module path so
# that we can fallback on it if dugong hasn't been installed yet.
if __name__ == '__main__':
    basedir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
else:
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if (os.path.exists(os.path.join(basedir, 'setup.py')) and
    os.path.exists(os.path.join(basedir, 'dugong', '__init__.py'))):
    sys.path.append(basedir)

from dugong import HTTPConnection

# When running from HG repo, enable all warnings
if os.path.exists(os.path.join(basedir, '.hg')):
    import warnings
    warnings.simplefilter('error')

class LinkExtractor(HTMLParser):
    def __init__(self):
        if sys.version_info < (3,4):
            # Python 3.3 doesn't know about convert_charrefs
            super().__init__()
        else:
            super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return

        for (name, val) in attrs:
            if name == 'href':
                self.links.append(val)
            break

def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: %s <url>' % sys.argv[0])
    url = sys.argv[1]
    url_els = urlsplit(url)

    if url_els.scheme == 'https':
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ssl_context.options |= ssl.OP_NO_SSLv2
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.set_default_verify_paths()
    else:
        ssl_context = None

    with HTTPConnection(url_els.hostname, port=url_els.port,
                          ssl_context=ssl_context) as conn:
        path = urlunsplit(('', '') + url_els[2:4] + ('',)) or '/'
        conn.send_request('GET', path)
        resp = conn.read_response()
        if resp.status != 200:
            raise SystemExit('%d %s' % (resp.status, resp.reason))

        # Determine if we're reading text or binary data, and (in case of text),
        # what character set is being used.
        if 'Content-Type' not in resp.headers:
            type_ = 'application/octet-stream'
        else:
            type_ = resp.headers['Content-Type']

        hit = re.match(r'text/x?html(?:; charset=(.+))?$', type_)
        if not hit:
            raise SystemExit('Server did not send html but %s' % type_)

        if hit.group(1):
            charset = hit.group(1)
        else:
            charset = 'latin1'

        html_stream = TextIOWrapper(conn, encoding=charset)
        parser = LinkExtractor()

        while True:
            buf = html_stream.read(16*1024)
            if not buf:
                break
            parser.feed(buf)

    for link in parser.links:
        print(urljoin(url, link))

if __name__ == '__main__':
    main()
