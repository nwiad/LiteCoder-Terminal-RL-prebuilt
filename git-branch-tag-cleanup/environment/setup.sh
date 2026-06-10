#!/bin/bash
set -e

# Initialize bare remote repo
git init --bare /app/remote-repo.git

# Initialize working repo
mkdir -p /app/repo
cd /app/repo
git init
git config user.email "dev@example.com"
git config user.name "Developer"

# Create main branch with 5 commits
echo "# Project README" > README.md
echo "Initial project description." >> README.md
git add README.md
git commit -m "Initial commit"

echo "## Installation" >> README.md
echo "Run make install" >> README.md
git add README.md
git commit -m "Add installation instructions"

echo "config=default" > config.txt
git add config.txt
git commit -m "Add config file"

echo "## Usage" >> README.md
echo "Run make run" >> README.md
git add README.md
git commit -m "Add usage section"

echo "## Contributing" >> README.md
echo "Please submit pull requests to main." >> README.md
git add README.md
git commit -m "Add contributing guidelines"

# Add remote
git remote add origin /app/remote-repo.git

# Create develop branch from commit 3 (HEAD~2) and diverge
git checkout -b develop HEAD~2

# Overwrite README.md with conflicting content on develop
cat > README.md << 'DEVEOF'
# Project README
Initial project description.
## Installation
Run make install
## Development
Set up your dev environment with make dev.
## Testing
Run make test to execute the test suite.
DEVEOF
git add README.md
git commit -m "Add development and testing sections"

echo "dev-tools=enabled" >> config.txt
git add config.txt
git commit -m "Enable dev tools in config"

# Switch back to main
git checkout main
