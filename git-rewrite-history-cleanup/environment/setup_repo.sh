#!/bin/bash
set -e

REPO_DIR="/app/project-repo"

# Clean up if exists
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
cd "$REPO_DIR"

git init
git checkout -b main

# Configure git user
git config user.email "dev@example.com"
git config user.name "Developer"

# Commit 1: Initial project structure
mkdir -p src tests assets
echo "# Project Repo" > README.md
echo "print('hello')" > src/main.py
git add -A
git commit -m "Initial project structure"

# Commit 2: Add large binary file (assets_large.bin >100KB)
dd if=/dev/urandom of=assets/assets_large.bin bs=1024 count=150 2>/dev/null
git add -A
git commit -m "Add large asset file"

# Commit 3: fix: typo in readme
echo "# Project Repo - Updated" > README.md
git add -A
git commit -m "fix: typo in readme"

# Commit 4: fix: update readme formatting
echo -e "# Project Repo - Updated\n\nA sample project." > README.md
git add -A
git commit -m "fix: update readme formatting"

# Commit 5: Add logging module
echo "import logging" > src/logger.py
echo "app started" > app.log
git add -A
git commit -m "Add logging module"

# Commit 6: fix: logger configuration
echo -e "import logging\nlogging.basicConfig(level=logging.INFO)" > src/logger.py
git add -A
git commit -m "fix: logger configuration"

# Commit 7: Add build artifacts and temp files
echo "build output" > build.tmp
echo "cache data" > cache.tmp
git add -A
git commit -m "Add build configuration"

# Commit 8: Add feature module
echo "def feature(): return 'feature_a'" > src/feature.py
git add -A
git commit -m "Add feature module"

# Commit 9: fix: improve feature return value
echo "def feature(): return 'feature_a_improved'" > src/feature.py
git add -A
git commit -m "fix: improve feature return value"

# Commit 10: Add test suite
echo "def test_main(): assert True" > tests/test_main.py
git add -A
git commit -m "Add test suite"

# Commit 11: fix: correct test assertion
echo -e "def test_main(): assert True\ndef test_feature(): assert True" > tests/test_main.py
git add -A
git commit -m "fix: correct test assertion"

# Commit 12: Add second large binary (data_dump.bin >100KB)
dd if=/dev/urandom of=data_dump.bin bs=1024 count=200 2>/dev/null
git add -A
git commit -m "Add data dump for analysis"

# Commit 13: Add debug log
echo "debug info line 1" > debug.log
git add -A
git commit -m "Add debug configuration"

# Now create a side branch and merge to produce a merge commit
# Commit 14: (on side branch) Add utils module
git checkout -b feature-utils
echo "def util(): return 'util'" > src/utils.py
git add -A
git commit -m "Add utils module"

# Commit 15: fix: test file header
echo "# Test utils" > tests/test_utils.py
git add -A
git commit -m "fix: test file header"

# Switch back to main
git checkout main

# Commit 16: Add config on main (parallel work)
echo "config_key=value" > src/config.ini
git add -A
git commit -m "Add project configuration"

# Commit 17: Merge feature-utils into main (creates merge commit)
git merge feature-utils --no-ff -m "Merge branch 'feature-utils'"

# Commit 18: fix: logging output path
echo -e "import logging\nlogging.basicConfig(level=logging.INFO, filename='out.log')" > src/logger.py
git add -A
git commit -m "fix: logging output path"

echo "Setup complete. Repository created at $REPO_DIR"
echo "Total commits on main: $(git rev-list --count main)"
