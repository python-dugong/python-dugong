#!/usr/bin/env python3

import sys
import os.path
import warnings

try:
    import setuptools
except ImportError:
    raise SystemExit('Setuptools/distribute package not found. Please install from '
                     'https://pypi.python.org/pypi/distribute')

if sys.version_info < (3,3):
    raise SystemExit('Python version is %d.%d.%d, but Dugong requires 3.3 or newer'
                     % sys.version_info[:3])

basedir = os.path.abspath(os.path.dirname(sys.argv[0]))
if os.path.exists(os.path.join(basedir, 'MANIFEST.in')):
    print('found MANIFEST.in, running in developer mode')
    warnings.resetwarnings()
    # We can't use `error`, because e.g. Sphinx triggers a
    # DeprecationWarning.
    warnings.simplefilter('default')

def main():
    try:
        from sphinx.application import Sphinx #pylint: disable-msg=W0612
    except ImportError:
        pass
    else:
        fix_docutils()

    with open(os.path.join(basedir, 'README.rst'), 'r') as fh:
        long_desc = fh.read()
    import dugong

    setuptools.setup(
          name='dugong',
          zip_safe=True,
          long_description=long_desc,
          version=dugong.__version__,
          description=('A HTTP 1.1 client module supporting asynchronous IO, pipelining '
                       'and `Expect: 100-continue`. Designed for RESTful protocols.'),
          author='Nikolaus Rath',
          author_email='Nikolaus@rath.org',
          license='PSF',
          keywords=['http'],
          package_dir={'': '.'},
          packages=setuptools.find_packages(),
          url='https://bitbucket.org/nikratio/python-dugong',
          classifiers=['Programming Language :: Python :: 3',
                       'Development Status :: 5 - Production/Stable',
                       'Intended Audience :: Developers',
                       'License :: OSI Approved :: Python Software Foundation License',
                       'Topic :: Internet :: WWW/HTTP',
                       'Topic :: Software Development :: Libraries :: Python Modules' ],
          provides=['dugong'],
          command_options={ 'sdist': { 'formats': ('setup.py', 'bztar') } ,
                            'build_sphinx': {'version': ('setup.py', dugong.__version__),
                                             'release': ('setup.py', dugong.__version__) }},
     )


def fix_docutils():
    '''Work around https://bitbucket.org/birkenfeld/sphinx/issue/1154/'''

    import docutils.parsers
    from docutils.parsers import rst
    old_getclass = docutils.parsers.get_parser_class

    # Check if bug is there
    try:
        old_getclass('rst')
    except AttributeError:
        pass
    else:
        return

    def get_parser_class(parser_name):
        """Return the Parser class from the `parser_name` module."""
        if parser_name in ('rst', 'restructuredtext'):
            return rst.Parser
        else:
            return old_getclass(parser_name)
    docutils.parsers.get_parser_class = get_parser_class

    assert docutils.parsers.get_parser_class('rst') is rst.Parser

if __name__ == '__main__':
    main()
