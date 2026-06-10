#!/bin/bash
set -e

# Initialize git repo at /app
mkdir -p /app
cd /app
git init
git config user.email "dev@example.com"
git config user.name "Developer"

# Commit 1: Initial commit with README
cat > README.md << 'EOF'
# Project App

A sample web application with API routes, models, and utilities.

## Setup
pip install -r requirements.txt

## Usage
python app.py
EOF
git add README.md
git commit -m "Initial commit: add README"

# Commit 2: Add src/config.py
mkdir -p src
cat > src/config.py << 'PYEOF'
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
PORT = int(os.getenv("PORT", "8000"))

class Config:
    DATABASE_URL = DATABASE_URL
    SECRET_KEY = SECRET_KEY
    DEBUG = DEBUG
    PORT = PORT
PYEOF
git add src/config.py
git commit -m "Add application configuration module"

# Commit 3: Add src/utils.py
cat > src/utils.py << 'PYEOF'
import hashlib
import json
from datetime import datetime

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def format_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_json_file(filepath: str) -> dict:
    with open(filepath, "r") as f:
        return json.load(f)
PYEOF
git add src/utils.py
git commit -m "Add utility functions for hashing and parsing"

# Commit 4: Add app.py
cat > app.py << 'PYEOF'
from src.config import Config

def create_app():
    print(f"Starting app on port {Config.PORT}")
    print(f"Debug mode: {Config.DEBUG}")
    return {"status": "running", "port": Config.PORT}

if __name__ == "__main__":
    app = create_app()
    print(f"App started: {app}")
PYEOF
git add app.py
git commit -m "Add main application entry point"

# Commit 5: Add models/database.py
mkdir -p models
cat > models/__init__.py << 'PYEOF'
PYEOF
cat > models/database.py << 'PYEOF'
import sqlite3
from src.config import Config

class Database:
    def __init__(self):
        self.connection = None

    def connect(self):
        self.connection = sqlite3.connect(Config.DATABASE_URL)
        return self.connection

    def execute(self, query, params=None):
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()

    def close(self):
        if self.connection:
            self.connection.close()
PYEOF
git add models/
git commit -m "Add database model layer"

# Commit 6: Add api/routes.py and requirements.txt
mkdir -p api
cat > api/__init__.py << 'PYEOF'
PYEOF
cat > api/routes.py << 'PYEOF'
from models.database import Database

def get_users():
    db = Database()
    db.connect()
    users = db.execute("SELECT * FROM users")
    db.close()
    return users

def get_health():
    return {"status": "healthy", "version": "1.0.0"}

ROUTES = {
    "/users": get_users,
    "/health": get_health,
}
PYEOF
cat > requirements.txt << 'PYEOF'
sqlite3-api>=1.0
pytest>=7.0
black>=23.0
PYEOF
git add api/ requirements.txt
git commit -m "Add API routes and project dependencies"

# Commit 7: Add tests
mkdir -p tests
cat > tests/__init__.py << 'PYEOF'
PYEOF
cat > tests/test_utils.py << 'PYEOF'
import unittest
from src.utils import hash_password, format_timestamp
from datetime import datetime

class TestUtils(unittest.TestCase):
    def test_hash_password(self):
        result = hash_password("secret")
        self.assertEqual(len(result), 64)

    def test_format_timestamp(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_timestamp(dt)
        self.assertEqual(result, "2024-01-15 10:30:00")

if __name__ == "__main__":
    unittest.main()
PYEOF
git add tests/
git commit -m "Add unit tests for utility functions"

# Now verify we have 8 commits (1 initial + 7 feature)
echo "=== Commits before reset ==="
git log --oneline

# Simulate the force-push disaster: reset back to the very first commit
FIRST_COMMIT=$(git rev-list --max-parents=0 HEAD)
git reset --hard "$FIRST_COMMIT"

echo ""
echo "=== Commits after reset (only initial commit remains) ==="
git log --oneline

echo ""
echo "=== Reflog shows lost commits ==="
git reflog

echo ""
echo "Setup complete. Repository is ready for recovery task."
