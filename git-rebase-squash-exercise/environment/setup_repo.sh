#!/bin/bash
set -e

mkdir -p /app/repo
cd /app/repo

git init
git config user.email "user@example.com"
git config user.name "Test User"

# Initial commit on main
cat > README.md << 'EOF'
# My Project
EOF
git add README.md
git commit -m "Initial commit"

# Create feature-branch from main
git checkout -b feature-branch

# Commit 1: Create feature.py
cat > feature.py << 'PYEOF'
def hello():
    return "hello"
PYEOF
git add feature.py
git commit -m "commit 1"

# Commit 2: Modify feature.py - add world()
cat >> feature.py << 'PYEOF'

def world():
    return "world"
PYEOF
git add feature.py
git commit -m "commit 2"

# Commit 3: Create tests.py
cat > tests.py << 'PYEOF'
def test_hello():
    assert hello() == "hello"
PYEOF
git add tests.py
git commit -m "commit 3"

# Commit 4: Modify feature.py - add greet()
cat >> feature.py << 'PYEOF'

def greet(name):
    return f"hello {name}"
PYEOF
git add feature.py
git commit -m "commit 4"

# Commit 5: Modify tests.py - add test_greet()
cat >> tests.py << 'PYEOF'

def test_greet():
    assert greet("alice") == "hello alice"
PYEOF
git add tests.py
git commit -m "commit 5"

# Commit 6: Modify feature.py - add farewell()
cat >> feature.py << 'PYEOF'

def farewell():
    return "goodbye"
PYEOF
git add feature.py
git commit -m "commit 6"

# Commit 7: Modify tests.py - add test_farewell()
cat >> tests.py << 'PYEOF'

def test_farewell():
    assert farewell() == "goodbye"
PYEOF
git add tests.py
git commit -m "commit 7"

# Commit 8: Create config.txt
cat > config.txt << 'EOF'
version=1.0
EOF
git add config.txt
git commit -m "commit 8"

echo "Repository setup complete. feature-branch has 8 commits ahead of main."
git log --oneline
