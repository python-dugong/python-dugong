#!/bin/bash

set -e

python -m pytest test/
python -m pytest --count=2 test/

python setup.py build_sphinx
