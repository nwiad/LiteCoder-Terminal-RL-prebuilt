#!/bin/bash
set -e

# Create the repo directory
mkdir -p /app/repo
cd /app/repo

# Initialize git repo
git init
git config user.email "dev@example.com"
git config user.name "Dev User"

# Initial commit on main
cat > README.md << 'EOF'
# Project Repository

Welcome to the project. This repository contains the main application code.
EOF
git add README.md
git commit -m "Initial commit: add README.md"

# Create feature branch off main
git checkout -b feature/user-auth

# Feature commit 1: add auth.py
cat > auth.py << 'PYEOF'
"""User authentication module."""

def login(username, password):
    """Authenticate a user with username and password."""
    if not username or not password:
        raise ValueError("Username and password are required")
    # Placeholder authentication logic
    return {"user": username, "authenticated": True}

def logout(session_token):
    """Invalidate a user session."""
    if not session_token:
        raise ValueError("Session token is required")
    return {"status": "logged_out"}
PYEOF
git add auth.py
git commit -m "Add user authentication module"

# Feature commit 2: add config.yaml
cat > config.yaml << 'YAMLEOF'
auth:
  token_expiry: 3600
  max_attempts: 5
  lockout_duration: 900
  password_min_length: 8
  require_special_char: true
YAMLEOF
git add config.yaml
git commit -m "Add authentication configuration"

# Feature commit 3: add tests/test_auth.py
mkdir -p tests
cat > tests/test_auth.py << 'TESTEOF'
"""Tests for the authentication module."""

import unittest

class TestAuth(unittest.TestCase):
    def test_login_success(self):
        from auth import login
        result = login("testuser", "securepass")
        self.assertTrue(result["authenticated"])

    def test_login_missing_username(self):
        from auth import login
        with self.assertRaises(ValueError):
            login("", "password")

    def test_logout(self):
        from auth import logout
        result = logout("abc123token")
        self.assertEqual(result["status"], "logged_out")

if __name__ == "__main__":
    unittest.main()
TESTEOF
git add tests/test_auth.py
git commit -m "Add authentication tests"

# Switch back to main and delete the feature branch
git checkout main
git branch -D feature/user-auth

echo "Setup complete. Repository is at /app/repo with HEAD on main."
echo "The feature/user-auth branch has been deleted but commits remain in reflog."
