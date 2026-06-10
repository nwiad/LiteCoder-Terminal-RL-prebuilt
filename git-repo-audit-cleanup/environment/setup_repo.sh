#!/bin/bash
set -e

REPO_DIR="/app/test_repo"
mkdir -p "$REPO_DIR"
cd "$REPO_DIR"
git init

# ============================================================
# Commit 1: Initial project structure (Author: Dev Team)
# ============================================================
git config user.name "Dev Team"
git config user.email "devteam@example.com"

mkdir -p src
cat > src/main.py << 'PYEOF'
#!/usr/bin/env python3
"""Main application entry point."""

def main():
    print("Application started")

if __name__ == "__main__":
    main()
PYEOF

cat > README.md << 'EOF'
# Test Project
A sample project for testing purposes.
EOF

git add .
git commit -m "Initial project structure"

# ============================================================
# Commit 2: Add config with sensitive data (Author: John Smith)
# ============================================================
git config user.name "John Smith"
git config user.email "john.smith@company.org"

cat > config.json << 'EOF'
{
  "database": {
    "host": "db.internal.example.com",
    "port": 5432,
    "username": "admin",
    "password": "SuperS3cretP@ssw0rd!"
  },
  "api_key": "AKIAIOSFODNN7EXAMPLE",
  "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
EOF

git add .
git commit -m "Add application configuration"

# ============================================================
# Commit 3: Add .env file with secrets (Author: Jane Doe)
# ============================================================
git config user.name "Jane Doe"
git config user.email "jane.doe@company.org"

cat > .env << 'EOF'
DB_HOST=db.internal.example.com
DB_PORT=5432
DB_USER=admin
DB_PASSWORD=SuperS3cretP@ssw0rd!
API_KEY=AKIAIOSFODNN7EXAMPLE
AWS_ACCESS_KEY_ID=AKIAI44QH8DHBEXAMPLE
AWS_SECRET_ACCESS_KEY=je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY
JWT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U
EOF

git add .
git commit -m "Add environment configuration"

# ============================================================
# Commit 4: Add deploy script with credentials (Author: Dev Admin)
# ============================================================
git config user.name "Dev Admin"
git config user.email "admin@devops.example.com"

cat > deploy.sh << 'DEPLOYEOF'
#!/bin/bash
# Deployment script
SERVER="deploy.example.com"
DEPLOY_TOKEN="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef12"
DB_PASSWORD="SuperS3cretP@ssw0rd!"

echo "Deploying to $SERVER..."
curl -H "Authorization: token $DEPLOY_TOKEN" https://api.example.com/deploy
DEPLOYEOF
chmod +x deploy.sh

git add .
git commit -m "Add deployment script"

# ============================================================
# Commit 5: Add large binary asset (Author: John Smith)
# ============================================================
git config user.name "John Smith"
git config user.email "jsmith@personal.dev"

# Create a 2MB file
dd if=/dev/urandom of=large_asset.bin bs=1024 count=2048 2>/dev/null

git add .
git commit -m "Add large binary asset"

# ============================================================
# Commit 6: Add source module (Author: Jane Doe)
# ============================================================
git config user.name "Jane Doe"
git config user.email "jane.doe@company.org"

cat > src/utils.py << 'PYEOF'
"""Utility functions."""

def format_output(data):
    return str(data)

def validate_input(value):
    return value is not None
PYEOF

git add .
git commit -m "Add utility module"

# ============================================================
# Commit 7: Add large backup archive (Author: Dev Admin)
# ============================================================
git config user.name "Dev Admin"
git config user.email "admin@devops.example.com"

# Create a 1.5MB file
dd if=/dev/urandom of=backup.tar.gz bs=1024 count=1536 2>/dev/null

git add .
git commit -m "Add backup archive"

# ============================================================
# Commit 8: Update main with new features (Author: Dev Team)
# ============================================================
git config user.name "Dev Team"
git config user.email "devteam@example.com"

cat > src/main.py << 'PYEOF'
#!/usr/bin/env python3
"""Main application entry point."""
from utils import format_output, validate_input

def process(data):
    if validate_input(data):
        return format_output(data)
    return None

def main():
    print("Application started")
    result = process("hello")
    print(result)

if __name__ == "__main__":
    main()
PYEOF

git add .
git commit -m "Update main with processing features"

# ============================================================
# Commit 9: Add tests (Author: Jane Doe)
# ============================================================
git config user.name "Jane Doe"
git config user.email "jane.doe@company.org"

mkdir -p tests
cat > tests/test_main.py << 'PYEOF'
"""Tests for main module."""

def test_process():
    from src.main import process
    assert process("hello") == "hello"
    assert process(None) is None
PYEOF

git add .
git commit -m "Add unit tests"

# ============================================================
# Commit 10: Update README (Author: John Smith with personal email)
# ============================================================
git config user.name "John Smith"
git config user.email "jsmith@personal.dev"

cat > README.md << 'EOF'
# Test Project

A sample project for testing purposes.

## Setup
1. Clone the repository
2. Run `python src/main.py`

## Testing
Run `python -m pytest tests/`
EOF

git add .
git commit -m "Update README with setup instructions"

echo "Test repository created successfully with 10 commits."
