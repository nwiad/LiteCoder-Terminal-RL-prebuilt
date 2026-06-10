#!/bin/bash
set -e

# Create bare remote repo
git init --bare /app/remote.git

# Create working repo
mkdir -p /app/repo
cd /app/repo
git init
git remote add origin /app/remote.git

git config user.email "dev@example.com"
git config user.name "Developer"

# ============================================================
# MAIN BRANCH: baseline JSON parser project
# ============================================================

mkdir -p tests

cat > README.md << 'READMEEOF'
# JSON Parser

A simple JSON parser written in Python.

## Usage

```python
from parser import parse
result = parse('{"key": "value"}')
```

## Running Tests

```bash
python -m pytest tests/
```
READMEEOF

cat > parser.py << 'PYEOF'
"""Simple JSON parser module."""

import json


def parse(text):
    """Parse a JSON string and return the resulting object."""
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    return json.loads(text)


def parse_file(filepath):
    """Parse a JSON file and return the resulting object."""
    with open(filepath, 'r') as f:
        return json.load(f)


def validate(text):
    """Check if a string is valid JSON."""
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False
PYEOF

cat > tests/__init__.py << 'PYEOF'
PYEOF

cat > tests/test_parser.py << 'PYEOF'
"""Tests for the JSON parser module."""

import pytest
from parser import parse, parse_file, validate


def test_parse_object():
    result = parse('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_array():
    result = parse('[1, 2, 3]')
    assert result == [1, 2, 3]


def test_parse_invalid():
    with pytest.raises(Exception):
        parse('not json')


def test_validate_valid():
    assert validate('{"a": 1}') is True


def test_validate_invalid():
    assert validate('not json') is False
PYEOF

git add -A
git commit -m "Initial project setup"

# Push main to remote
git push -u origin main

# ============================================================
# FEATURE/PARSER BRANCH: 9 commits
# ============================================================

git checkout -b feature/parser

# --- Commit 1: "Add skeleton for new tokenizer module" ---
cat > tokenizer.py << 'PYEOF'
"""Tokenizer module for JSON parsing."""


class Token:
    """Represents a single token."""
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


class Tokenizer:
    """Skeleton tokenizer class."""
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def tokenize(self):
        """Tokenize the input text. Not yet implemented."""
        raise NotImplementedError("Tokenizer not yet implemented")
PYEOF

git add tokenizer.py
git commit -m "Add skeleton for new tokenizer module"

# --- Commit 2: "Refactor: extract helper functions from parser.py" ---
cat > helpers.py << 'PYEOF'
"""Helper functions extracted from parser module."""


def strip_whitespace(text):
    """Remove leading and trailing whitespace from text."""
    return text.strip()


def is_numeric(text):
    """Check if text represents a numeric value."""
    try:
        float(text)
        return True
    except (ValueError, TypeError):
        return False
PYEOF

# Update parser.py to use helpers
cat > parser.py << 'PYEOF'
"""Simple JSON parser module."""

import json
from helpers import strip_whitespace, is_numeric


def parse(text):
    """Parse a JSON string and return the resulting object."""
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    text = strip_whitespace(text)
    return json.loads(text)


def parse_file(filepath):
    """Parse a JSON file and return the resulting object."""
    with open(filepath, 'r') as f:
        return json.load(f)


def validate(text):
    """Check if a string is valid JSON."""
    try:
        text = strip_whitespace(text)
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False
PYEOF

git add helpers.py parser.py
git commit -m "Refactor: extract helper functions from parser.py"

# --- Commit 3: "Implement tokenizer and integrate into parser" ---
# Part A: implement the tokenizer
cat > tokenizer.py << 'PYEOF'
"""Tokenizer module for JSON parsing."""


class Token:
    """Represents a single token."""
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


class Tokenizer:
    """Tokenizer for JSON strings."""
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.tokens = []

    def tokenize(self):
        """Tokenize the input text into a list of tokens."""
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch in ' \t\n\r':
                self.pos += 1
            elif ch == '{':
                self.tokens.append(Token('LBRACE', ch))
                self.pos += 1
            elif ch == '}':
                self.tokens.append(Token('RBRACE', ch))
                self.pos += 1
            elif ch == '[':
                self.tokens.append(Token('LBRACKET', ch))
                self.pos += 1
            elif ch == ']':
                self.tokens.append(Token('RBRACKET', ch))
                self.pos += 1
            elif ch == ':':
                self.tokens.append(Token('COLON', ch))
                self.pos += 1
            elif ch == ',':
                self.tokens.append(Token('COMMA', ch))
                self.pos += 1
            elif ch == '"':
                self._read_string()
            elif ch in '-0123456789':
                self._read_number()
            elif self.text[self.pos:self.pos+4] == 'true':
                self.tokens.append(Token('BOOL', True))
                self.pos += 4
            elif self.text[self.pos:self.pos+5] == 'false':
                self.tokens.append(Token('BOOL', False))
                self.pos += 5
            elif self.text[self.pos:self.pos+4] == 'null':
                self.tokens.append(Token('NULL', None))
                self.pos += 4
            else:
                raise ValueError(f"Unexpected character: {ch}")
        return self.tokens

    def _read_string(self):
        self.pos += 1  # skip opening quote
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] != '"':
            if self.text[self.pos] == '\\':
                self.pos += 1
            self.pos += 1
        value = self.text[start:self.pos]
        self.pos += 1  # skip closing quote
        self.tokens.append(Token('STRING', value))

    def _read_number(self):
        start = self.pos
        if self.text[self.pos] == '-':
            self.pos += 1
        while self.pos < len(self.text) and self.text[self.pos] in '0123456789.eE+-':
            self.pos += 1
        value = self.text[start:self.pos]
        self.tokens.append(Token('NUMBER', float(value) if '.' in value else int(value)))
PYEOF

# Part B: integrate tokenizer into parser
cat > parser.py << 'PYEOF'
"""Simple JSON parser module."""

import json
from helpers import strip_whitespace, is_numeric
from tokenizer import Tokenizer


def parse(text):
    """Parse a JSON string and return the resulting object."""
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    text = strip_whitespace(text)
    tokenizer = Tokenizer(text)
    tokens = tokenizer.tokenize()
    return json.loads(text)


def parse_file(filepath):
    """Parse a JSON file and return the resulting object."""
    with open(filepath, 'r') as f:
        content = f.read()
    return parse(content)


def validate(text):
    """Check if a string is valid JSON."""
    try:
        text = strip_whitespace(text)
        tokenizer = Tokenizer(text)
        tokenizer.tokenize()
        return True
    except (json.JSONDecodeError, TypeError, ValueError):
        return False
PYEOF

git add tokenizer.py parser.py
git commit -m "Implement tokenizer and integrate into parser"

# --- Commit 4: "Fix typo in test_parser.py" ---
# Add a small fix (e.g., fix a comment typo)
sed -i 's/"""Tests for the JSON parser module."""/"""Tests for the JSON parser module."""\n# Fixed: corrected test descriptions/' tests/test_parser.py
git add tests/test_parser.py
git commit -m "Fix typo in test_parser.py"

# --- Commit 5: "Core parser rewrite using new tokenizer" ---
cat > parser.py << 'PYEOF'
"""Simple JSON parser module - rewritten to use tokenizer."""

import json
from helpers import strip_whitespace, is_numeric
from tokenizer import Tokenizer, Token


def parse(text):
    """Parse a JSON string using the tokenizer pipeline."""
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    text = strip_whitespace(text)
    tokenizer = Tokenizer(text)
    tokens = tokenizer.tokenize()
    # Use tokenizer for validation, then parse
    return _build_value(tokens, 0)[0]


def _build_value(tokens, pos):
    """Recursively build a Python value from tokens."""
    if pos >= len(tokens):
        raise ValueError("Unexpected end of input")
    token = tokens[pos]
    if token.type == 'LBRACE':
        return _build_object(tokens, pos)
    elif token.type == 'LBRACKET':
        return _build_array(tokens, pos)
    elif token.type == 'STRING':
        return token.value, pos + 1
    elif token.type == 'NUMBER':
        return token.value, pos + 1
    elif token.type == 'BOOL':
        return token.value, pos + 1
    elif token.type == 'NULL':
        return None, pos + 1
    else:
        raise ValueError(f"Unexpected token: {token}")


def _build_object(tokens, pos):
    """Build a dict from tokens starting at LBRACE."""
    obj = {}
    pos += 1  # skip LBRACE
    while tokens[pos].type != 'RBRACE':
        key = tokens[pos].value
        pos += 1  # skip key
        pos += 1  # skip COLON
        value, pos = _build_value(tokens, pos)
        obj[key] = value
        if tokens[pos].type == 'COMMA':
            pos += 1
    return obj, pos + 1


def _build_array(tokens, pos):
    """Build a list from tokens starting at LBRACKET."""
    arr = []
    pos += 1  # skip LBRACKET
    while tokens[pos].type != 'RBRACKET':
        value, pos = _build_value(tokens, pos)
        arr.append(value)
        if tokens[pos].type == 'COMMA':
            pos += 1
    return arr, pos + 1


def parse_file(filepath):
    """Parse a JSON file using the tokenizer pipeline."""
    with open(filepath, 'r') as f:
        content = f.read()
    return parse(content)


def validate(text):
    """Check if a string is valid JSON using tokenizer."""
    try:
        text = strip_whitespace(text)
        tokenizer = Tokenizer(text)
        tokens = tokenizer.tokenize()
        _build_value(tokens, 0)
        return True
    except (ValueError, TypeError):
        return False
PYEOF

git add parser.py
git commit -m "Core parser rewrite using new tokenizer"

# --- Commit 6: "fixup! Refactor: extract helper functions from parser.py" ---
# Add another helper that was missed in the original refactor
cat >> helpers.py << 'PYEOF'


def normalize_whitespace(text):
    """Normalize internal whitespace in text."""
    import re
    return re.sub(r'\s+', ' ', text).strip()


def safe_convert(value, target_type):
    """Safely convert a value to target type."""
    try:
        return target_type(value)
    except (ValueError, TypeError):
        return None
PYEOF

git add helpers.py
git commit -m "fixup! Refactor: extract helper functions from parser.py"

# --- Commit 7: "Add performance benchmark script" ---
cat > benchmark.py << 'PYEOF'
"""Performance benchmark for the JSON parser."""

import time
import json
from parser import parse


def generate_test_data(size=100):
    """Generate test JSON data of given size."""
    data = {f"key_{i}": f"value_{i}" for i in range(size)}
    return json.dumps(data)


def run_benchmark(iterations=1000):
    """Run parsing benchmark."""
    test_data = generate_test_data()
    start = time.time()
    for _ in range(iterations):
        parse(test_data)
    elapsed = time.time() - start
    print(f"Parsed {iterations} iterations in {elapsed:.4f}s")
    print(f"Average: {elapsed/iterations*1000:.4f}ms per parse")
    return elapsed


if __name__ == "__main__":
    run_benchmark()
PYEOF

git add benchmark.py
git commit -m "Add performance benchmark script"

# --- Commit 8: "Fix typo in README" ---
sed -i 's/A simple JSON parser written in Python./A simple yet powerful JSON parser written in Python./' README.md
git add README.md
git commit -m "Fix typo in README"

# --- Commit 9: "Add unit tests and update documentation" ---
cat > tests/test_tokenizer.py << 'PYEOF'
"""Tests for the tokenizer module."""

from tokenizer import Tokenizer, Token


def test_tokenize_object():
    t = Tokenizer('{"key": "value"}')
    tokens = t.tokenize()
    assert tokens[0].type == 'LBRACE'
    assert tokens[-1].type == 'RBRACE'


def test_tokenize_array():
    t = Tokenizer('[1, 2, 3]')
    tokens = t.tokenize()
    assert tokens[0].type == 'LBRACKET'
    assert tokens[-1].type == 'RBRACKET'


def test_tokenize_string():
    t = Tokenizer('"hello"')
    tokens = t.tokenize()
    assert len(tokens) == 1
    assert tokens[0].type == 'STRING'
    assert tokens[0].value == 'hello'


def test_tokenize_number():
    t = Tokenizer('42')
    tokens = t.tokenize()
    assert len(tokens) == 1
    assert tokens[0].type == 'NUMBER'
    assert tokens[0].value == 42


def test_tokenize_bool():
    t = Tokenizer('true')
    tokens = t.tokenize()
    assert tokens[0].type == 'BOOL'
    assert tokens[0].value is True
PYEOF

# Update README with documentation
cat > README.md << 'READMEEOF'
# JSON Parser

A simple yet powerful JSON parser written in Python.

## Features

- Custom tokenizer for JSON strings
- Recursive descent parser
- File parsing support
- JSON validation
- Performance benchmarking

## Usage

```python
from parser import parse
result = parse('{"key": "value"}')
```

## Modules

- `parser.py` - Main parser module
- `tokenizer.py` - JSON tokenizer
- `helpers.py` - Utility functions
- `benchmark.py` - Performance benchmarks

## Running Tests

```bash
python -m pytest tests/
```
READMEEOF

git add tests/test_tokenizer.py README.md
git commit -m "Add unit tests and update documentation"

# Push feature branch to remote
git push -u origin feature/parser

echo "Setup complete. Repository at /app/repo with branches: main, feature/parser"
