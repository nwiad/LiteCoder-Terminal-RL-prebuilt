#!/bin/bash
set -e

# Create the repository directory
mkdir -p /app/repo
cd /app/repo
git init

# Configure git user for commits
git config user.name "Alice Martin"
git config user.email "alice@example.com"

# === Commits on main branch ===

# Commit 1: Initial project setup
mkdir -p src
cat > src/app.py << 'PYEOF'
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
PYEOF
cat > README.md << 'MDEOF'
# MyProject
A sample project for release management.
MDEOF
git add .
GIT_AUTHOR_DATE="2024-01-10T09:00:00+00:00" GIT_COMMITTER_DATE="2024-01-10T09:00:00+00:00" \
  git commit -m "Initial project setup"

# Commit 2: Add configuration file
cat > config.yaml << 'CFGEOF'
app:
  name: myproject
  version: "1.0.0"
  debug: false
CFGEOF
git add config.yaml
GIT_AUTHOR_DATE="2024-01-15T11:30:00+00:00" GIT_COMMITTER_DATE="2024-01-15T11:30:00+00:00" \
  git commit -m "Add application configuration file"

# Commit 3: Add utility module
cat > src/utils.py << 'PYEOF'
def format_name(first, last):
    return f"{first} {last}"

def validate_email(email):
    return "@" in email and "." in email
PYEOF
git add src/utils.py
GIT_AUTHOR_DATE="2024-02-01T14:00:00+00:00" GIT_COMMITTER_DATE="2024-02-01T14:00:00+00:00" \
  git commit -m "Add utility module with helpers"

# === Create release-1.x branch from current main ===
git checkout -b release-1.x

# Commit 4: First release-branch-only commit (logging utility)
cat > src/logger.py << 'PYEOF'
import logging

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger
PYEOF
git add src/logger.py
GIT_AUTHOR_DATE="2024-02-10T08:00:00+00:00" GIT_COMMITTER_DATE="2024-02-10T08:00:00+00:00" \
  git commit -m "Add logging utility"

# === Now add commits ONLY on release-1.x (not merged to main) ===

# Release-only commit 1 by Bob
git config user.name "Bob Chen"
git config user.email "bob@example.com"
cat > src/hotfix_auth.py << 'PYEOF'
def validate_token(token):
    if not token or len(token) < 32:
        return False
    return True
PYEOF
git add src/hotfix_auth.py
GIT_AUTHOR_DATE="2024-03-05T16:45:00+00:00" GIT_COMMITTER_DATE="2024-03-05T16:45:00+00:00" \
  git commit -m "fix: patch critical authentication bypass"

# Release-only commit 2 by Carol
git config user.name "Carol Rivera"
git config user.email "carol@example.com"
cat > src/session.py << 'PYEOF'
import time

SESSION_TIMEOUT = 3600

def is_session_valid(start_time):
    return (time.time() - start_time) < SESSION_TIMEOUT
PYEOF
git add src/session.py
GIT_AUTHOR_DATE="2024-03-20T10:15:00+00:00" GIT_COMMITTER_DATE="2024-03-20T10:15:00+00:00" \
  git commit -m "feat: add session timeout handling"

# Release-only commit 3 by Bob again
git config user.name "Bob Chen"
git config user.email "bob@example.com"
cat > src/rate_limit.py << 'PYEOF'
from collections import defaultdict
import time

request_counts = defaultdict(list)

def check_rate_limit(client_id, max_requests=100, window=60):
    now = time.time()
    request_counts[client_id] = [t for t in request_counts[client_id] if now - t < window]
    if len(request_counts[client_id]) >= max_requests:
        return False
    request_counts[client_id].append(now)
    return True
PYEOF
git add src/rate_limit.py
GIT_AUTHOR_DATE="2024-04-02T13:30:00+00:00" GIT_COMMITTER_DATE="2024-04-02T13:30:00+00:00" \
  git commit -m "feat: implement API rate limiting"

# Release-only commit 4 by Alice
git config user.name "Alice Martin"
git config user.email "alice@example.com"
sed -i 's/version: "1.0.0"/version: "1.0.1"/' config.yaml
git add config.yaml
GIT_AUTHOR_DATE="2024-04-10T09:00:00+00:00" GIT_COMMITTER_DATE="2024-04-10T09:00:00+00:00" \
  git commit -m "chore: bump version to 1.0.1 for hotfix release"

# === Switch back to main and diverge ===
git checkout main

# Main-only commit by Alice
git config user.name "Alice Martin"
git config user.email "alice@example.com"
cat > src/feature_new.py << 'PYEOF'
def new_dashboard():
    return {"status": "ok", "widgets": []}
PYEOF
git add src/feature_new.py
GIT_AUTHOR_DATE="2024-03-25T12:00:00+00:00" GIT_COMMITTER_DATE="2024-03-25T12:00:00+00:00" \
  git commit -m "feat: add new dashboard endpoint"

echo "Repository setup complete."
echo "Branches:"
git branch -a
echo ""
echo "Commits on release-1.x but NOT on main:"
git log --oneline main..release-1.x
