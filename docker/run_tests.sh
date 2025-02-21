#!/bin/bash

# Exit on error
set -e

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install test requirements
pip install -r tests/requirements-test.txt

# Run tests
pytest tests/

# Deactivate virtual environment
deactivate 