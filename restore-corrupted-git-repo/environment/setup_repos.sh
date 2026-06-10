#!/bin/bash
set -e

# Configure git identity
git config --global user.email "developer@example.com"
git config --global user.name "Developer"
git config --global init.defaultBranch main

cd /app

# ============================================================
# Step 1: Create the "remote backup" bare repository
# ============================================================
mkdir remote-source && cd remote-source
git init

# Commit 1 on main
echo "# Project Alpha" > README.md
git add README.md
git commit -m "Initial commit: add README"

# Commit 2 on main
cat > config.json <<'CONF'
{
  "app_name": "Project Alpha",
  "version": "1.0.0",
  "debug": false
}
CONF
git add config.json
git commit -m "Add project configuration"

# Commit 3 on main
mkdir -p src
cat > src/main.py <<'PY'
def main():
    print("Hello from Project Alpha")

if __name__ == "__main__":
    main()
PY
git add src/main.py
git commit -m "Add main application entry point"

# Create feature/auth branch off main
git checkout -b feature/auth

cat > src/auth.py <<'PY'
def authenticate(username, password):
    """Authenticate a user."""
    if not username or not password:
        return False
    return True
PY
git add src/auth.py
git commit -m "Add authentication module"

echo 'AUTH_SECRET="changeme"' > .env.example
git add .env.example
git commit -m "Add example environment file for auth"

# Go back to main
git checkout main

# Create the bare backup from this repo
cd /app
git clone --bare remote-source remote-backup.git
rm -rf remote-source

# ============================================================
# Step 2: Clone from backup to create the local repo
# ============================================================
git clone remote-backup.git corrupted-repo
cd corrupted-repo

# Fetch all remote branches
git fetch origin

# ============================================================
# Step 3: Add 2 unpushed commits on main (never pushed)
# ============================================================
cat > src/utils.py <<'PY'
def format_output(data):
    """Format data for display."""
    return str(data).strip()
PY
git add src/utils.py
git commit -m "Add utility functions module"

cat >> README.md <<'MD'

## Getting Started

1. Install dependencies
2. Run `python src/main.py`
MD
git add README.md
git commit -m "Update README with getting started guide"

# Save the SHAs of unpushed commits (last 2 on main)
UNPUSHED_SHA1=$(git log --format=%H -1 HEAD~1)
UNPUSHED_SHA2=$(git log --format=%H -1 HEAD)

# ============================================================
# Step 4: Create hotfix/urgent-fix branch (never pushed)
# ============================================================
git checkout -b hotfix/urgent-fix

cat > src/hotfix.py <<'PY'
def apply_urgent_fix():
    """Apply critical security patch."""
    print("Urgent fix applied")
PY
git add src/hotfix.py
git commit -m "Apply urgent security hotfix"

HOTFIX_SHA=$(git log --format=%H -1 HEAD)

# Go back to main
git checkout main

# ============================================================
# Step 5: Corrupt the repository by deleting some object files
# We must be careful to:
#   - Keep the reflog intact
#   - Keep pack files intact (remote objects are safe)
#   - Delete only some loose objects from the unpushed commits
# ============================================================

# Find loose object files for the unpushed commits' trees/blobs
# We'll delete a few tree/blob objects but NOT the commit objects themselves
# so the reflog can still reference them

# Get tree objects from unpushed commits
TREE1=$(git cat-file -p "$UNPUSHED_SHA1" | grep "^tree" | awk '{print $2}')
TREE2=$(git cat-file -p "$UNPUSHED_SHA2" | grep "^tree" | awk '{print $2}')
HOTFIX_TREE=$(git cat-file -p "$HOTFIX_SHA" | grep "^tree" | awk '{print $2}')

# Get a blob from the utils.py file added in unpushed commit 1
BLOB1=$(git ls-tree "$TREE1" -- src/utils.py | awk '{print $3}')

# Delete specific loose objects to simulate corruption
# Delete tree objects (these will cause fsck errors)
delete_loose_object() {
    local sha="$1"
    local prefix="${sha:0:2}"
    local suffix="${sha:2}"
    local path=".git/objects/$prefix/$suffix"
    if [ -f "$path" ]; then
        rm "$path"
        echo "Deleted object: $sha"
    fi
}

# Delete some tree and blob objects to create corruption
delete_loose_object "$TREE1"
delete_loose_object "$BLOB1"
delete_loose_object "$HOTFIX_TREE"

echo ""
echo "=== Setup Complete ==="
echo "Remote backup: /app/remote-backup.git"
echo "Corrupted repo: /app/corrupted-repo"
echo "Unpushed commit 1: $UNPUSHED_SHA1"
echo "Unpushed commit 2: $UNPUSHED_SHA2"
echo "Hotfix commit: $HOTFIX_SHA"
echo ""
echo "Verify corruption:"
cd /app/corrupted-repo
git fsck 2>&1 || true
echo ""
echo "Reflog still has references:"
git reflog --all 2>&1 | head -20
