#!/bin/bash
set -e

# Create and initialize the repo
mkdir -p /app/repo
cd /app/repo
git init
git config user.email "test@example.com"
git config user.name "Test User"

# Commit 1: Initial commit - create critical_data.txt and readme.txt
cat > critical_data.txt << 'EOF'
version=1.0
status=active
data=important_record_001
EOF

cat > readme.txt << 'EOF'
Project README
EOF

git add critical_data.txt readme.txt
git commit -m "Initial commit"

# Commit 2: Update readme
cat > readme.txt << 'EOF'
Project README
Updated with more info.
EOF

git add readme.txt
git commit -m "Update readme"

# Commit 3: Remove critical data (simulates accidental deletion)
git rm critical_data.txt
git commit -m "Remove critical data"

# Commit 4: Add notes
cat > notes.txt << 'EOF'
Some development notes.
EOF

git add notes.txt
git commit -m "Add notes"
