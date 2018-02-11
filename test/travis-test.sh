#!/bin/bash

set -e

python -m pytest test/

python setup.py build_sphinx
