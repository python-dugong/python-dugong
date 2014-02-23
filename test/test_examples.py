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

basename = os.path.join(os.path.dirname(__file__), '..')

def test_httpcat():
    cmdline = [sys.executable,
              os.path.join(basename, 'examples', 'httpcat.py'),
              'http://docs.oracle.com/javaee/7/firstcup/doc/creating-example.htm' ]
    
    with open('/dev/null', 'wb') as devnull:
        subprocess.check_call(cmdline, stdout=devnull)

def test_extract_links():
    cmdline = [sys.executable,
              os.path.join(basename, 'examples', 'extract_links.py'),
              'http://docs.oracle.com/javaee/7/firstcup/doc/creating-example.htm' ]
    
    with open('/dev/null', 'wb') as devnull:
        subprocess.check_call(cmdline, stdout=devnull)
        
def test_pipeline1():
    cmdline = [sys.executable,
              os.path.join(basename, 'examples', 'pipeline1.py') ]

    for x in ('preface.htm', 'intro.htm', 'java-ee.htm',
              'creating-example.htm', 'next-steps.htm',
              'creating-example001.htm'):
        cmdline.append('http://docs.oracle.com/javaee/7/firstcup/doc/' + x)
    
    with open('/dev/null', 'wb') as devnull:
        subprocess.check_call(cmdline, stdout=devnull)
        
