#!/bin/bash
# This script creates the bare origin.git repository at /app/origin.git
# with a main branch containing multiple commits, exactly one of which
# has the word "stable" in its commit message.

set -e

mkdir -p /app
cd /tmp

# Create a temporary working repo
rm -rf /tmp/build-repo
mkdir /tmp/build-repo
cd /tmp/build-repo
git init
git checkout -b main

git config user.email "dev@example.com"
git config user.name "Developer"

# Commit 1: Initial project setup
echo "# Project Alpha" > README.md
echo "version=0.1.0" > config.txt
git add .
git commit -m "Initial project setup"

# Commit 2: Add core module
mkdir -p src
echo 'def hello():
    return "Hello, World!"' > src/core.py
git add .
git commit -m "Add core module with hello function"

# Commit 3: The stable release commit (contains "stable" keyword)
echo "version=1.0.0" > config.txt
echo 'def hello():
    return "Hello, World!"

def greet(name):
    return f"Hello, {name}!"' > src/core.py
echo "## v1.0.0 - Stable Release" >> README.md
git add .
git commit -m "Release v1.0.0 - stable production build"

# Commit 4: Experimental feature A
mkdir -p src/experimental
echo 'def feature_a():
    return "experimental feature A"' > src/experimental/feature_a.py
git add .
git commit -m "Add experimental feature A (untested)"

# Commit 5: Experimental feature B
echo 'def feature_b():
    return "experimental feature B"' > src/experimental/feature_b.py
git add .
git commit -m "Add experimental feature B (work in progress)"

# Commit 6: Broken config change
echo "version=2.0.0-alpha" > config.txt
echo "debug=true" >> config.txt
echo "unsafe_mode=enabled" >> config.txt
git add .
git commit -m "Update config for alpha testing (breaks production)"

# Now create the bare repository from this
git clone --bare /tmp/build-repo /app/origin.git

# Clean up
rm -rf /tmp/build-repo

echo "Setup complete. origin.git created at /app/origin.git"
