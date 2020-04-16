#!/bin/bash

set -e
PYTHON="python3.8"

source venv/bin/activate
$PYTHON fetch.py "$@"
