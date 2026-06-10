#!/bin/bash
set -e

REPO_DIR="/app/repo"
mkdir -p "$REPO_DIR"
cd "$REPO_DIR"
git init
git config user.name "Setup Script"
git config user.email "setup@example.com"

# ============================================================
# Root Alpha: 4 commits, service-alpha/ directory
# ============================================================
git checkout --orphan root-alpha

# Commit 1
mkdir -p service-alpha
cat > service-alpha/main.py << 'PYEOF'
def hello():
    print("Hello from Alpha")

if __name__ == "__main__":
    hello()
PYEOF
git add service-alpha/main.py
GIT_AUTHOR_NAME="Alice Alpha" GIT_AUTHOR_EMAIL="alice@alpha.dev" \
GIT_AUTHOR_DATE="2023-01-10T09:00:00+00:00" \
GIT_COMMITTER_NAME="Alice Alpha" GIT_COMMITTER_EMAIL="alice@alpha.dev" \
GIT_COMMITTER_DATE="2023-01-10T09:00:00+00:00" \
git commit -m "alpha: initial project setup"

# Commit 2
cat > service-alpha/config.yaml << 'YAMLEOF'
service:
  name: alpha
  port: 8001
  debug: true
YAMLEOF
git add service-alpha/config.yaml
GIT_AUTHOR_NAME="Alice Alpha" GIT_AUTHOR_EMAIL="alice@alpha.dev" \
GIT_AUTHOR_DATE="2023-02-15T14:30:00+00:00" \
GIT_COMMITTER_NAME="Alice Alpha" GIT_COMMITTER_EMAIL="alice@alpha.dev" \
GIT_COMMITTER_DATE="2023-02-15T14:30:00+00:00" \
git commit -m "alpha: add configuration file"

# Commit 3
cat > service-alpha/utils.py << 'PYEOF'
import os

def get_env(key, default=None):
    return os.environ.get(key, default)

def format_response(data):
    return {"status": "ok", "data": data}
PYEOF
git add service-alpha/utils.py
GIT_AUTHOR_NAME="Alan Alpha" GIT_AUTHOR_EMAIL="alan@alpha.dev" \
GIT_AUTHOR_DATE="2023-04-20T11:00:00+00:00" \
GIT_COMMITTER_NAME="Alan Alpha" GIT_COMMITTER_EMAIL="alan@alpha.dev" \
GIT_COMMITTER_DATE="2023-04-20T11:00:00+00:00" \
git commit -m "alpha: add utility functions"

# Commit 4
cat > service-alpha/README.md << 'MDEOF'
# Service Alpha
A microservice for handling alpha operations.
## Setup
Run `python main.py` to start.
MDEOF
git add service-alpha/README.md
GIT_AUTHOR_NAME="Alice Alpha" GIT_AUTHOR_EMAIL="alice@alpha.dev" \
GIT_AUTHOR_DATE="2023-06-01T16:45:00+00:00" \
GIT_COMMITTER_NAME="Alice Alpha" GIT_COMMITTER_EMAIL="alice@alpha.dev" \
GIT_COMMITTER_DATE="2023-06-01T16:45:00+00:00" \
git commit -m "alpha: add README documentation"

# ============================================================
# Root Beta: 3 commits, service-beta/ directory
# ============================================================
git checkout --orphan root-beta

# Commit 1
mkdir -p service-beta
cat > service-beta/app.js << 'JSEOF'
const express = require('express');
const app = express();
app.get('/', (req, res) => res.send('Beta Service'));
module.exports = app;
JSEOF
git add service-beta/app.js
GIT_AUTHOR_NAME="Bob Beta" GIT_AUTHOR_EMAIL="bob@beta.io" \
GIT_AUTHOR_DATE="2023-01-25T10:15:00+00:00" \
GIT_COMMITTER_NAME="Bob Beta" GIT_COMMITTER_EMAIL="bob@beta.io" \
GIT_COMMITTER_DATE="2023-01-25T10:15:00+00:00" \
git commit -m "beta: initialize express application"

# Commit 2
cat > service-beta/package.json << 'JSONEOF'
{
  "name": "service-beta",
  "version": "1.0.0",
  "main": "app.js",
  "dependencies": {
    "express": "^4.18.0"
  }
}
JSONEOF
git add service-beta/package.json
GIT_AUTHOR_NAME="Bob Beta" GIT_AUTHOR_EMAIL="bob@beta.io" \
GIT_AUTHOR_DATE="2023-03-10T08:00:00+00:00" \
GIT_COMMITTER_NAME="Bob Beta" GIT_COMMITTER_EMAIL="bob@beta.io" \
GIT_COMMITTER_DATE="2023-03-10T08:00:00+00:00" \
git commit -m "beta: add package.json with dependencies"

# Commit 3
cat > service-beta/test.js << 'JSEOF'
const assert = require('assert');
const app = require('./app');
console.log('Tests passed');
JSEOF
git add service-beta/test.js
GIT_AUTHOR_NAME="Brenda Beta" GIT_AUTHOR_EMAIL="brenda@beta.io" \
GIT_AUTHOR_DATE="2023-05-05T13:20:00+00:00" \
GIT_COMMITTER_NAME="Brenda Beta" GIT_COMMITTER_EMAIL="brenda@beta.io" \
GIT_COMMITTER_DATE="2023-05-05T13:20:00+00:00" \
git commit -m "beta: add basic test suite"

# ============================================================
# Root Gamma: 3 commits, service-gamma/ directory
# ============================================================
git checkout --orphan root-gamma

# Commit 1
mkdir -p service-gamma
cat > service-gamma/main.go << 'GOEOF'
package main

import "fmt"

func main() {
    fmt.Println("Gamma service started")
}
GOEOF
git add service-gamma/main.go
GIT_AUTHOR_NAME="Grace Gamma" GIT_AUTHOR_EMAIL="grace@gamma.org" \
GIT_AUTHOR_DATE="2023-02-01T12:00:00+00:00" \
GIT_COMMITTER_NAME="Grace Gamma" GIT_COMMITTER_EMAIL="grace@gamma.org" \
GIT_COMMITTER_DATE="2023-02-01T12:00:00+00:00" \
git commit -m "gamma: initial Go service"

# Commit 2
cat > service-gamma/go.mod << 'MODEOF'
module service-gamma

go 1.21
MODEOF
git add service-gamma/go.mod
GIT_AUTHOR_NAME="Grace Gamma" GIT_AUTHOR_EMAIL="grace@gamma.org" \
GIT_AUTHOR_DATE="2023-03-22T15:30:00+00:00" \
GIT_COMMITTER_NAME="Grace Gamma" GIT_COMMITTER_EMAIL="grace@gamma.org" \
GIT_COMMITTER_DATE="2023-03-22T15:30:00+00:00" \
git commit -m "gamma: add go.mod for module support"

# Commit 3
cat > service-gamma/handler.go << 'GOEOF'
package main

import "net/http"

func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("healthy"))
}
GOEOF
git add service-gamma/handler.go
GIT_AUTHOR_NAME="Gary Gamma" GIT_AUTHOR_EMAIL="gary@gamma.org" \
GIT_AUTHOR_DATE="2023-05-18T09:45:00+00:00" \
GIT_COMMITTER_NAME="Gary Gamma" GIT_COMMITTER_EMAIL="gary@gamma.org" \
GIT_COMMITTER_DATE="2023-05-18T09:45:00+00:00" \
git commit -m "gamma: add health check handler"

# ============================================================
# Set main branch to point to root-alpha
# ============================================================
git checkout root-alpha
git branch -M main
# Recreate root-alpha pointing to same commit
git branch root-alpha

echo "Repository setup complete."
echo "Branches:"
git branch -a
echo ""
echo "Root commits:"
for branch in root-alpha root-beta root-gamma; do
    count=$(git rev-list --count "$branch")
    roots=$(git rev-list --max-parents=0 "$branch" | wc -l)
    echo "  $branch: $count commits, $roots root(s)"
done
