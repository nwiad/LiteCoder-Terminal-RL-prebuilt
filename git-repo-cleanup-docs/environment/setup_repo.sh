#!/bin/bash
# This script creates a messy Git repository with large binary files,
# code files, and inconsistent commit history for cleanup tasks.

set -e

REPO_DIR="/app/repo"
mkdir -p "$REPO_DIR"
cd "$REPO_DIR"

git init
git config user.email "dev@example.com"
git config user.name "Developer"

# === Commit 1: Initial project files ===
cat > main.py << 'PYEOF'
#!/usr/bin/env python3
"""Main application entry point."""

def greet(name):
    return f"Hello, {name}!"

def add(a, b):
    return a + b

if __name__ == "__main__":
    print(greet("World"))
    print(f"2 + 3 = {add(2, 3)}")
PYEOF

cat > utils.py << 'PYEOF'
"""Utility functions for the project."""

import os
import sys

def read_config(path):
    with open(path, 'r') as f:
        return f.read()

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def log_message(msg):
    print(f"[LOG] {msg}", file=sys.stderr)
PYEOF

cat > config.json << 'JSONEOF'
{
  "app_name": "MyProject",
  "version": "0.1.0",
  "debug": true,
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "mydb"
  }
}
JSONEOF

git add -A
git commit -m "Initial commit: add main app and utilities"

# === Commit 2: Add a large binary file (2MB) ===
dd if=/dev/urandom of=data_archive.bin bs=1024 count=2048 2>/dev/null
git add data_archive.bin
git commit -m "Add data archive binary"

# === Commit 3: Add more code and another large file ===
cat > server.py << 'PYEOF'
"""Simple HTTP server module."""

from http.server import HTTPServer, SimpleHTTPRequestHandler

def run_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"Server running on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
PYEOF

# Large compiled binary (~1.5MB)
dd if=/dev/urandom of=app_binary.exe bs=1024 count=1536 2>/dev/null

git add -A
git commit -m "Add server module and compiled binary"

# === Commit 4: Add media file and test data ===
mkdir -p assets
# Large image file (~3MB)
dd if=/dev/urandom of=assets/background.png bs=1024 count=3072 2>/dev/null

cat > tests.py << 'PYEOF'
"""Basic test suite."""

from main import greet, add

def test_greet():
    assert greet("Alice") == "Hello, Alice!"

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0

if __name__ == "__main__":
    test_greet()
    test_add()
    print("All tests passed!")
PYEOF

git add -A
git commit -m "Add assets and test suite"

# === Commit 5: Add log file and another large binary ===
cat > debug.log << 'LOGEOF'
2024-01-15 10:00:01 INFO  Application started
2024-01-15 10:00:02 DEBUG Loading configuration
2024-01-15 10:00:03 WARN  Cache miss for key: user_session
2024-01-15 10:00:05 ERROR Connection timeout to database
2024-01-15 10:01:00 INFO  Retry successful
LOGEOF

# Large shared library (~1.2MB)
dd if=/dev/urandom of=libhelper.so bs=1024 count=1228 2>/dev/null

git add -A
git commit -m "Add debug log and shared library"

# === Commit 6: Update code files ===
cat >> main.py << 'PYEOF'

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
PYEOF

cat >> utils.py << 'PYEOF'

def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
PYEOF

git add -A
git commit -m "Add math functions and size formatter"

# === Commit 7: Add another large file in subdirectory ===
mkdir -p build
dd if=/dev/urandom of=build/release.tar.gz bs=1024 count=1800 2>/dev/null

git add -A
git commit -m "Add build artifact"

echo "=== Repository setup complete ==="
echo "Commits: $(git rev-list --count HEAD)"
echo "Repo size: $(du -sk .git | cut -f1) KB"
echo "Large files (>1MB):"
find . -path ./.git -prune -o -type f -size +1M -print
