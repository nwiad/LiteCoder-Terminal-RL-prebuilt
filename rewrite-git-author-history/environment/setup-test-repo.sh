#!/bin/bash
set -e

# Configure git
git config --global user.name "Setup Script"
git config --global user.email "setup@example.com"

# Create test repository
mkdir -p /app/test-repo
cd /app/test-repo
git init

# Commit 1 - Author: Alice
export GIT_AUTHOR_NAME="Alice Johnson"
export GIT_AUTHOR_EMAIL="alice@example.com"
export GIT_COMMITTER_NAME="Alice Johnson"
export GIT_COMMITTER_EMAIL="alice@example.com"
export GIT_AUTHOR_DATE="2024-01-15T10:00:00Z"
export GIT_COMMITTER_DATE="2024-01-15T10:00:00Z"

echo "Initial content" > README.md
echo "# Project" > docs.txt
git add README.md docs.txt
git commit -m "Initial commit with project structure"

# Commit 2 - Author: Bob
export GIT_AUTHOR_NAME="Bob Smith"
export GIT_AUTHOR_EMAIL="bob@example.com"
export GIT_COMMITTER_NAME="Bob Smith"
export GIT_COMMITTER_EMAIL="bob@example.com"
export GIT_AUTHOR_DATE="2024-01-16T14:30:00Z"
export GIT_COMMITTER_DATE="2024-01-16T14:30:00Z"

echo "Updated content with more details" > README.md
echo "function main() { return 0; }" > code.js
git add README.md code.js
git commit -m "Add main functionality and update README"

# Commit 3 - Author: Alice
export GIT_AUTHOR_NAME="Alice Johnson"
export GIT_AUTHOR_EMAIL="alice@example.com"
export GIT_COMMITTER_NAME="Alice Johnson"
export GIT_COMMITTER_EMAIL="alice@example.com"
export GIT_AUTHOR_DATE="2024-01-17T09:15:00Z"
export GIT_COMMITTER_DATE="2024-01-17T09:15:00Z"

echo "# Project Documentation" > docs.txt
echo "This is the documentation." >> docs.txt
git add docs.txt
git commit -m "Update documentation"

# Commit 4 - Author: Bob
export GIT_AUTHOR_NAME="Bob Smith"
export GIT_AUTHOR_EMAIL="bob@example.com"
export GIT_COMMITTER_NAME="Bob Smith"
export GIT_COMMITTER_EMAIL="bob@example.com"
export GIT_AUTHOR_DATE="2024-01-18T16:45:00Z"
export GIT_COMMITTER_DATE="2024-01-18T16:45:00Z"

echo "function main() { console.log('Hello'); return 0; }" > code.js
git add code.js
git commit -m "Add logging to main function"

echo "Test repository created successfully at /app/test-repo"
