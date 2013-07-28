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
          description='a HTTP client supporting pipelining and Expect: 100-continue', 
          author='Nikolaus Rath',
          author_email='Nikolaus@rath.org',
          license='PSF',
          keywords=['http'],
          package_dir={'': '.'},
          packages=setuptools.find_packages(),
          provides=['httpio'],
          command_options={ 'sdist': { 'formats': ('setup.py', 'bztar') } },
         )

    
if __name__ == '__main__':
    main()
