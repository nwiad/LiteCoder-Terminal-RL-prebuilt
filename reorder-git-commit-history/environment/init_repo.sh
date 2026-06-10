#!/bin/bash
set -e

# Initialize Git repository
cd /app
mkdir -p repo
cd repo
git init
git config user.email "test@example.com"
git config user.name "Test User"

# Create initial file
echo "# Project" > README.md
git add README.md
git commit -m "Initial commit"

# Feature 1: Add user authentication
echo "def authenticate(user, password):" > auth.py
echo "    return True" >> auth.py
git add auth.py
git commit -m "Add user authentication feature"

# Bug fix 1: Fix typo in README
sed -i 's/Project/Project Documentation/' README.md
git add README.md
git commit -m "Fix typo in README"

# Feature 2: Implement logging system
echo "import logging" > logger.py
echo "logger = logging.getLogger(__name__)" >> logger.py
git add logger.py
git commit -m "Implement logging system"

# Bug fix 2: Patch authentication vulnerability
echo "def authenticate(user, password):" > auth.py
echo "    if not user or not password:" >> auth.py
echo "        return False" >> auth.py
echo "    return True" >> auth.py
git add auth.py
git commit -m "Patch security bug in authentication"

# Feature 3: Add database connection
echo "import sqlite3" > database.py
echo "def connect():" >> database.py
echo "    return sqlite3.connect('app.db')" >> database.py
git add database.py
git commit -m "Add database connection feature"

# Bug fix 3: Correct logger import
echo "import logging" > logger.py
echo "import sys" >> logger.py
echo "logger = logging.getLogger(__name__)" >> logger.py
git add logger.py
git commit -m "Fix missing import in logger"

# Feature 4: New API endpoint
echo "from flask import Flask" > api.py
echo "app = Flask(__name__)" >> api.py
echo "@app.route('/api/users')" >> api.py
echo "def get_users():" >> api.py
echo "    return {'users': []}" >> api.py
git add api.py
git commit -m "Add new API endpoint for users"

# Bug fix 4: Repair database connection leak
echo "import sqlite3" > database.py
echo "def connect():" >> database.py
echo "    conn = sqlite3.connect('app.db')" >> database.py
echo "    conn.row_factory = sqlite3.Row" >> database.py
echo "    return conn" >> database.py
git add database.py
git commit -m "Repair connection leak in database module"

echo "Git repository initialized with interleaved commits at /app/repo"
