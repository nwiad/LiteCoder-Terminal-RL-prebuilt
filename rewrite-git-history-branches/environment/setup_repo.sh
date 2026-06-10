#!/bin/bash
set -e

# Configure git
git config --global user.email "dev@example.com"
git config --global user.name "Developer"
git config --global init.defaultBranch main

# Create the repository
mkdir -p /app/repo
cd /app/repo
git init

# 1. Initial commit on main
echo "# Project" > README.md
git add README.md
git commit -m "initial commit"

# 2. Create commits directly on main (in order)

# Commit 1: Add auth.py
echo "# auth module" > auth.py
git add auth.py
git commit -m "added some auth stuff"

# Commit 2: Add ui.css
echo "/* ui styles */" > ui.css
git add ui.css
git commit -m "ui changes"

# Commit 3: Modify auth.py
printf "# auth module\ndef login(): pass" > auth.py
git add auth.py
git commit -m "more auth"

# Commit 4: Add api.py
echo "# api module" > api.py
git add api.py
git commit -m "api endpoint"

# Commit 5: Modify ui.css (this is the "fix button" commit)
printf "/* ui styles */\n.button { color: red; }" > ui.css
git add ui.css
git commit -m "fix button"

# Save the 5th commit hash for the experiment branch
FIFTH_COMMIT=$(git rev-parse HEAD)

# Commit 6: Modify api.py
printf "# api module\ndef get_users(): pass" > api.py
git add api.py
git commit -m "api stuff"

# Commit 7: Add db.py
echo "# database module" > db.py
git add db.py
git commit -m "database"

# Commit 8: Modify auth.py
printf "# auth module\ndef login(): pass\ndef logout(): pass" > auth.py
git add auth.py
git commit -m "logout thing"

# Commit 9: Modify db.py
printf "# database module\ndef connect(): pass" > db.py
git add db.py
git commit -m "db connection"

# Commit 10: Modify api.py
printf "# api module\ndef get_users(): pass\ndef create_user(): pass" > api.py
git add api.py
git commit -m "another api change"

# 3. Create experiment branch off the 5th commit
git checkout -b experiment "$FIFTH_COMMIT"

# Experiment commit 1
echo "# experiment" > experiment.py
git add experiment.py
git commit -m "trying something"

# Experiment commit 2
printf "# experiment\ndef test(): pass" > experiment.py
git add experiment.py
git commit -m "more experiments"

# Switch back to main
git checkout main

echo "Repository setup complete."
echo "Branches:"
git branch -a
echo "Main log:"
git log --oneline
