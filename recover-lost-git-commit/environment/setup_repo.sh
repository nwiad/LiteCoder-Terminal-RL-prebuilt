#!/bin/bash
set -e

# Configure Git
git config --global user.email "test@example.com"
git config --global user.name "Test User"
git config --global init.defaultBranch main

# Create bare remote repository
git init --bare /app/remote_repo.git

# Create temporary directory to set up the scenario
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Initialize a local repository
git init
git remote add origin /app/remote_repo.git

# Create initial commit
echo "# Project README" > README.md
echo "This is the initial project setup." >> README.md
git add README.md
git commit -m "Initial commit"

# Create a feature file (this will be the "lost" commit)
echo "def calculate_sum(a, b):" > feature.py
echo "    return a + b" >> feature.py
echo "" >> feature.py
echo "def calculate_product(a, b):" >> feature.py
echo "    return a * b" >> feature.py
git add feature.py
git commit -m "Add critical feature: calculation functions"

# Push both commits to remote
git push -u origin main

# Now simulate the accident: reset to previous commit and force push
git reset --hard HEAD~1
git push --force origin main

# Clean up temp directory
cd /app
rm -rf "$TEMP_DIR"

echo "Repository setup complete. Lost commit is in reflog but not on any branch."
