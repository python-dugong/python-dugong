#!/usr/bin/env python3
'''
test_dugong.py - Unit tests for Dugong - run with py.test

Copyright (c) Nikolaus Rath <Nikolaus@rath.org>

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
from urllib.request import build_opener, ProxyHandler, URLError
try:
    import asyncio
except ImportError:
    asyncio = None
    
basename = os.path.join(os.path.dirname(__file__), '..')

def check_url(url):
    '''Skip test if *url* cannot be reached'''

    # Examples ignore proxy settings, so should urllib
    proxy_handler = ProxyHandler({})
    opener = build_opener(proxy_handler)
    
    try:
        resp = opener.open(url, None, 15)
    except URLError:
        pytest.skip('%s not reachable but required for testing' % url)

    if resp.status != 200:
        pytest.skip('%s not reachable but required for testing' % url)

    resp.close()

def test_httpcat():
    url =  'http://docs.oracle.com/javaee/7/firstcup/doc/creating-example.htm'
    check_url(url)
    cmdline = [sys.executable,
               os.path.join(basename, 'examples', 'httpcat.py'), url ]
    
    with open('/dev/null', 'wb') as devnull:
        subprocess.check_call(cmdline, stdout=devnull)

def test_extract_links():
    url =  'http://docs.oracle.com/javaee/7/firstcup/doc/creating-example.htm'
    check_url(url)
    cmdline = [sys.executable,
              os.path.join(basename, 'examples', 'extract_links.py'), url ]
    
    with open('/dev/null', 'wb') as devnull:
        subprocess.check_call(cmdline, stdout=devnull)

@pytest.mark.skipif(asyncio is None,
                    reason='asyncio module not available')
def test_pipeline1():
    cmdline = [sys.executable,
              os.path.join(basename, 'examples', 'pipeline1.py') ]

    for x in ('preface.htm', 'intro.htm', 'java-ee.htm',
              'creating-example.htm', 'next-steps.htm',
              'creating-example001.htm'):
        url = 'http://docs.oracle.com/javaee/7/firstcup/doc/' + x
        check_url(url)
        cmdline.append(url)
    
    with open('/dev/null', 'wb') as devnull:
        subprocess.check_call(cmdline, stdout=devnull)
        
