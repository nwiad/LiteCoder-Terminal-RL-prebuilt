#!/bin/bash
set -e

REPO_DIR="/app/corrupt_repo"

# Clean up if exists
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
cd "$REPO_DIR"

# Initialize repo
git init
git checkout -b main

# Commit 1: Add README.md and config.txt
cat > README.md << 'EOF'
# My Project
This is a sample project for testing.
EOF

cat > config.txt << 'EOF'
debug=false
log_level=info
port=8080
EOF

mkdir -p src
cat > src/app.py << 'EOF'
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
EOF

git add README.md config.txt src/app.py
git commit -m "Initial commit: add README, config, and app"

# Save first commit hash for feature branch
FIRST_COMMIT=$(git rev-parse HEAD)

# Commit 2: Update app.py
cat > src/app.py << 'EOF'
import sys

def main():
    print("Hello, World!")
    return 0

def helper():
    return "helper function"

if __name__ == "__main__":
    sys.exit(main())
EOF

git add src/app.py
git commit -m "Update app.py with helper function and sys.exit"

# Save second commit hash for tag
SECOND_COMMIT=$(git rev-parse HEAD)

# Create lightweight tag v1.0 pointing to second commit
git tag v1.0 "$SECOND_COMMIT"

# Commit 3: Update README and config
cat > README.md << 'EOF'
# My Project
This is a sample project for testing.

## Features
- Main application
- Configuration support
- Helper utilities
EOF

cat > config.txt << 'EOF'
debug=false
log_level=info
port=8080
max_connections=100
timeout=30
EOF

git add README.md config.txt
git commit -m "Update README with features and expand config"

# Create feature branch from first commit
git checkout -b feature "$FIRST_COMMIT"

# Add a commit on feature branch
cat > src/feature.py << 'EOF'
def new_feature():
    return "This is a new feature"
EOF

git add src/feature.py
git commit -m "Add new feature module"

# Save feature commit hash
FEATURE_COMMIT=$(git rev-parse HEAD)

# Go back to main
git checkout main

# ============================================
# Now corrupt the repository
# ============================================

# 1. Truncate/delete a loose object file
# Find a loose object and truncate it
LOOSE_OBJ=$(find .git/objects -type f ! -path "*/info/*" ! -path "*/pack/*" | head -1)
if [ -n "$LOOSE_OBJ" ]; then
    echo "CORRUPT" > "$LOOSE_OBJ"
fi

# 2. Overwrite .git/refs/heads/feature with invalid data
echo "0000000000000000000000000000000000000000" > .git/refs/heads/feature

# 3. Remove the v1.0 tag file
rm -f .git/refs/tags/v1.0

# Save commit hashes for potential recovery reference
# Store them outside the repo so the recovery script doesn't trivially find them
echo "$FIRST_COMMIT" > /app/.commit_hashes_first
echo "$SECOND_COMMIT" > /app/.commit_hashes_second
echo "$FEATURE_COMMIT" > /app/.commit_hashes_feature

echo "Repository created and corrupted at $REPO_DIR"
echo "First commit: $FIRST_COMMIT"
echo "Second commit (v1.0): $SECOND_COMMIT"
echo "Feature commit: $FEATURE_COMMIT"
echo "Corrupted loose object: $LOOSE_OBJ"
