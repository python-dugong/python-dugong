#!/usr/bin/env python3
'''
Retrieve a list of URLs and print them to stdout.
'''

import sys
import os.path
from io import TextIOWrapper
import re

# We are running from the dugong source directory, make sure that we use modules
# from this directory
if __name__ == '__main__':
    basedir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
else:
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if (os.path.exists(os.path.join(basedir, 'setup.py')) and
    os.path.exists(os.path.join(basedir, 'dugong', '__init__.py'))):
    sys.path.insert(0, basedir)

# When running from HG repo, enable all warnings
if os.path.exists(os.path.join(basedir, '.hg')):
    import warnings
    warnings.simplefilter('default')

from dugong import HTTPConnection, BUFFER_SIZE

for url in sys.argv[1:]:
    hit = re.match(r'http://([^/]+)(/.+)$', url)
    assert hit
    (host, path) = hit.groups()

    conn = HTTPConnection(host)
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

    hit = re.match(r'(.+?)(?:; charset=(.+))?$', type_)
    if not hit:
        raise SystemExit('Unable to parse content-type: %s' % type_)
    if hit.group(2):
        charset = hit.group(2)
    elif hit.group(1).startswith('text/'):
        charset = 'latin1'
    else:
        charset = None # binary data

    if charset:
        instream = TextIOWrapper(conn, encoding=charset)
        outstream = sys.stdout
    else:
        instream = conn
        # Since we're writing bytes rather than text, we need to bypass
        # any encoding.
        outstream = sys.stdout.raw

    while True:
        buf = instream.read(BUFFER_SIZE)
        if not buf:
            break
        outstream.write(buf)


