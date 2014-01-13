#!/usr/bin/env python3

try:
    import setuptools
except ImportError:
    raise SystemExit('Setuptools/distribute package not found. Please install from '
                     'https://pypi.python.org/pypi/distribute')
    
def main():

    setuptools.setup(
          name='httpio',
          zip_safe=True,
          version=1.0,
          description='A http.client replacement supporting pipelining and Expect: 100-continue', 
          author='Nikolaus Rath',
          author_email='Nikolaus@rath.org',
          license='PSF',
          keywords=['http'],
          package_dir={'': '.'},
          packages=setuptools.find_packages(),
          url='https://bitbucket.org/nikratio/python-httpio',
          classifiers=['Programming Language :: Python :: 3',
                       'Development Status :: 5 - Production/Stable',
                       'Intended Audience :: Developers',
                       'License :: OSI Approved :: Python Software Foundation License',
                       'Topic :: Internet :: WWW/HTTP',
                       'Topic :: Software Development :: Libraries :: Python Modules' ],
          provides=['httpio'],
          command_options={ 'sdist': { 'formats': ('setup.py', 'bztar') } },
         )

    
if __name__ == '__main__':
    main()
