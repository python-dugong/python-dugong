import sys
import os.path
import logging

if sys.version_info < (3,3):
    raise SystemExit('Python version is %d.%d.%d, but Dugong requires 3.3 or newer'
                     % sys.version_info[:3])

def pytest_addoption(parser):
    group = parser.getgroup("general")
    group._addoption("--installed", action="store_true", default=False,
                     help="Test the installed package.")
    
    group = parser.getgroup("terminal reporting")
    group._addoption("--logdebug", action="store_true", default=False,
                     help="Activate debugging output.")

def pytest_configure(config):

    # If we are running from the source directory, make sure that we load
    # modules from here
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if not config.getoption('installed'):
        if (os.path.exists(os.path.join(basedir, 'setup.py')) and
            os.path.exists(os.path.join(basedir, 'dugong', '__init__.py'))):
            sys.path.insert(0, basedir)

    # When running from HG repo, enable all warnings
    if os.path.exists(os.path.join(basedir, '.hg')):
        import warnings
        warnings.resetwarnings()
        warnings.simplefilter('error')

    logdebug = config.getoption('logdebug')
    if logdebug:
        root_logger = logging.getLogger()
        formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(threadName)s '
                                      '%(funcName)s: %(message)s',
                                      datefmt="%H:%M:%S")
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)
