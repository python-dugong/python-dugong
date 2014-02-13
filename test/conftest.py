import sys
import os.path

def pytest_addoption(parser):
    group = parser.getgroup("general")
    group._addoption("--installed", action="store_true", default=False,
                     help="Test the installed package.")
    
def pytest_configure(config):

    # If we are running from the source directory, make sure that we load
    # modules from here
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if not config.getoption('installed'):
        if (os.path.exists(os.path.join(basedir, 'setup.py')) and
            os.path.exists(os.path.join(basedir, 'dugong', '__init__.py'))):
            sys.path.insert(0, basedir)

