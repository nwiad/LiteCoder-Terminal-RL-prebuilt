#!/bin/bash
# Script to initialize git repository with commit history
# This will be run during Docker build to create the test scenario

set -e

cd /app

# Initialize git repository
git init
git config user.email "test@example.com"
git config user.name "Test User"

# Commit 1: Initial version (working)
cat > app.py << 'EOF'
#!/usr/bin/env python3
"""Simple calculator application for testing git bisect."""

def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

def divide(a, b):
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

if __name__ == "__main__":
    print("Calculator Application")
    print(f"5 + 3 = {add(5, 3)}")
    print(f"10 - 4 = {subtract(10, 4)}")
    print(f"6 * 7 = {multiply(6, 7)}")
    print(f"20 / 5 = {divide(20, 5)}")
EOF
git add app.py
git commit -m "Initial calculator implementation"

# Commits 2-5: Add features (all working)
for i in {2..5}; do
    echo "# Version $i" >> app.py
    git add app.py
    git commit -m "Update version to $i"
done

# Commit 6: Introduce the bug in divide function
cat > app.py << 'EOF'
#!/usr/bin/env python3
"""Simple calculator application for testing git bisect."""

def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

def divide(a, b):
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a // b  # BUG: Changed to integer division

if __name__ == "__main__":
    print("Calculator Application")
    print(f"5 + 3 = {add(5, 3)}")
    print(f"10 - 4 = {subtract(10, 4)}")
    print(f"6 * 7 = {multiply(6, 7)}")
    print(f"20 / 5 = {divide(20, 5)}")
# Version 2
# Version 3
# Version 4
# Version 5
EOF
git add app.py
git commit -m "Refactor divide function for performance"

# Commits 7-12: More changes (bug persists)
for i in {7..12}; do
    echo "# Version $i" >> app.py
    git add app.py
    git commit -m "Update version to $i"
done

echo "Git repository initialized with 12 commits"
echo "Bug introduced in commit 6"
