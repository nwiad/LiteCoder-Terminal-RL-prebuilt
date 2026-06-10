#!/usr/bin/env bash
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────
BARE_REPO="/tmp/broken-repo.git"
WORK_DIR="/tmp/_setup_workdir"

# Clean slate
rm -rf "$BARE_REPO" "$WORK_DIR"

# ── Build a temporary working repo ────────────────────────────
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"
git init
git config user.email "dev@example.com"
git config user.name "Developer"

# Commit 1 – initial file
cat > tracker.py <<'PYEOF'
class BugTracker:
    def __init__(self):
        self.issues = []

    def add_issue(self, title):
        self.issues.append({"title": title, "status": "open"})

    def list_open(self):
        return [i for i in self.issues if i["status"] == "open"]
PYEOF
git add tracker.py
git commit -m "Initial commit: add BugTracker class"

# Commit 2 – add a README
cat > README.md <<'EOF'
# Bug Tracker
A simple issue tracker utility.
EOF
git add README.md
git commit -m "Add project README"

# Commit 3 – the commit we will "lose" (contains Refs #1883)
cat > tracker.py <<'PYEOF'
class BugTracker:
    def __init__(self):
        self.issues = []

    def add_issue(self, title, priority="normal"):
        self.issues.append({"title": title, "status": "open", "priority": priority})

    def close_issue(self, title):
        for issue in self.issues:
            if issue["title"] == title:
                issue["status"] = "closed"
                return True
        return False

    def list_open(self):
        return [i for i in self.issues if i["status"] == "open"]
PYEOF
git add tracker.py
git commit -m "Add close_issue method and priority field - Refs #1883"

# Save the SHA we are about to hide
LOST_SHA=$(git rev-parse HEAD)

# Commit 4 – another change on top
cat > tracker.py <<'PYEOF'
class BugTracker:
    def __init__(self):
        self.issues = []

    def add_issue(self, title):
        self.issues.append({"title": title, "status": "open"})

    def list_open(self):
        return [i for i in self.issues if i["status"] == "open"]

    def count(self):
        return len(self.issues)
PYEOF
git add tracker.py
git commit -m "Add count helper method"

# Commit 5 – one more
cat > CONTRIBUTING.md <<'EOF'
# Contributing
Please open an issue before submitting a PR.
EOF
git add CONTRIBUTING.md
git commit -m "Add contributing guidelines"

# ── Simulate the disaster: hard-reset drops the lost commit ───
# Reset main back to commit 2, then cherry-pick commits 4 & 5
# so the lost commit (3) is no longer in any branch ancestry.
COMMIT2=$(git log --reverse --format='%H' | sed -n '2p')
COMMIT4=$(git log --reverse --format='%H' | sed -n '4p')
COMMIT5=$(git log --reverse --format='%H' | sed -n '5p')

git reset --hard "$COMMIT2"
git cherry-pick "$COMMIT4"
git cherry-pick "$COMMIT5"

# ── Export to a bare repo ─────────────────────────────────────
git clone --bare "$WORK_DIR" "$BARE_REPO"

# Also transplant the reflog so the lost commit is discoverable
mkdir -p "$BARE_REPO/logs/refs/heads"
cp -a .git/logs/HEAD "$BARE_REPO/logs/HEAD" 2>/dev/null || true
cp -a .git/logs/refs/heads/master "$BARE_REPO/logs/refs/heads/master" 2>/dev/null || true

# Copy the lost object explicitly (it may have been pruned from the bare clone)
OBJ_DIR="${LOST_SHA:0:2}"
OBJ_FILE="${LOST_SHA:2}"
mkdir -p "$BARE_REPO/objects/$OBJ_DIR"
cp -a ".git/objects/$OBJ_DIR/$OBJ_FILE" "$BARE_REPO/objects/$OBJ_DIR/$OBJ_FILE" 2>/dev/null || true

# Also copy tree and blob objects referenced by the lost commit
# so that `git show` works on it after clone
git cat-file -p "$LOST_SHA" | grep '^tree ' | awk '{print $2}' | while read TREE_SHA; do
    TD="${TREE_SHA:0:2}"
    TF="${TREE_SHA:2}"
    mkdir -p "$BARE_REPO/objects/$TD"
    cp -a ".git/objects/$TD/$TF" "$BARE_REPO/objects/$TD/$TF" 2>/dev/null || true

    # Copy blobs referenced by the tree
    git cat-file -p "$TREE_SHA" | awk '{print $3}' | while read BLOB_SHA; do
        BD="${BLOB_SHA:0:2}"
        BF="${BLOB_SHA:2}"
        mkdir -p "$BARE_REPO/objects/$BD"
        cp -a ".git/objects/$BD/$BF" "$BARE_REPO/objects/$BD/$BF" 2>/dev/null || true
    done
done

# Copy parent commit's tree and blobs too (needed for diff)
PARENT_SHA=$(git cat-file -p "$LOST_SHA" | grep '^parent ' | head -1 | awk '{print $2}')
if [ -n "$PARENT_SHA" ]; then
    PD="${PARENT_SHA:0:2}"
    PF="${PARENT_SHA:2}"
    mkdir -p "$BARE_REPO/objects/$PD"
    cp -a ".git/objects/$PD/$PF" "$BARE_REPO/objects/$PD/$PF" 2>/dev/null || true

    PARENT_TREE=$(git cat-file -p "$PARENT_SHA" | grep '^tree ' | awk '{print $2}')
    if [ -n "$PARENT_TREE" ]; then
        PTD="${PARENT_TREE:0:2}"
        PTF="${PARENT_TREE:2}"
        mkdir -p "$BARE_REPO/objects/$PTD"
        cp -a ".git/objects/$PTD/$PTF" "$BARE_REPO/objects/$PTD/$PTF" 2>/dev/null || true

        git cat-file -p "$PARENT_TREE" | awk '{print $3}' | while read BLOB_SHA; do
            BD="${BLOB_SHA:0:2}"
            BF="${BLOB_SHA:2}"
            mkdir -p "$BARE_REPO/objects/$BD"
            cp -a ".git/objects/$BD/$BF" "$BARE_REPO/objects/$BD/$BF" 2>/dev/null || true
        done
    fi
fi

# ── Clean up ──────────────────────────────────────────────────
rm -rf "$WORK_DIR"

echo "Setup complete. Bare repo at $BARE_REPO"
echo "Lost commit SHA: $LOST_SHA"
