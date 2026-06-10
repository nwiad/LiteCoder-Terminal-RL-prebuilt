#!/bin/bash
# Setup script: creates a messy workspace with 9 files in 3 groups

mkdir -p /app/project/docs
mkdir -p /app/project/src
mkdir -p /app/project/tests
mkdir -p /app/project/.github/workflows

# Documentation group
cat > /app/project/README.md << 'EOF'
# My Project

A sample Python application for demonstration purposes.

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
python src/app.py
```
EOF

cat > /app/project/CONTRIBUTING.md << 'EOF'
# Contributing

Thank you for your interest in contributing!

## How to Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Code Style

Please follow PEP 8 guidelines for Python code.
EOF

cat > /app/project/docs/usage.md << 'EOF'
# Usage Guide

## Getting Started

Import the main module:

```python
from src.app import main
```

## API Reference

- `main()` — Entry point of the application
- `add(a, b)` — Returns the sum of two numbers
- `greet(name)` — Returns a greeting string
EOF

# Feature group
cat > /app/project/src/app.py << 'EOF'
"""Main application module."""


def add(a, b):
    """Return the sum of two numbers."""
    return a + b


def greet(name):
    """Return a greeting string."""
    return f"Hello, {name}!"


def main():
    """Entry point."""
    result = add(2, 3)
    print(f"2 + 3 = {result}")
    print(greet("World"))


if __name__ == "__main__":
    main()
EOF

cat > /app/project/src/utils.py << 'EOF'
"""Utility functions."""

import os
import sys


def get_project_root():
    """Return the project root directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_debug():
    """Check if debug mode is enabled."""
    return os.environ.get("DEBUG", "false").lower() == "true"


def log(message):
    """Print a log message to stderr."""
    print(f"[LOG] {message}", file=sys.stderr)
EOF

cat > /app/project/tests/test_app.py << 'EOF'
"""Tests for the main application module."""

import unittest
from src.app import add, greet


class TestApp(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 1), 0)

    def test_greet(self):
        self.assertEqual(greet("Alice"), "Hello, Alice!")
        self.assertEqual(greet("World"), "Hello, World!")


if __name__ == "__main__":
    unittest.main()
EOF

# Build group
cat > /app/project/Makefile << 'EOF'
.PHONY: all test clean run

all: test

test:
	python -m pytest tests/

run:
	python src/app.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
EOF

cat > /app/project/Dockerfile << 'EOF'
FROM python:3.13-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt || true

CMD ["python", "src/app.py"]
EOF

cat > /app/project/.github/workflows/ci.yml << 'EOF'
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install dependencies
        run: pip install pytest
      - name: Run tests
        run: python -m pytest tests/
EOF

echo "Setup complete. Files created in /app/project/"
