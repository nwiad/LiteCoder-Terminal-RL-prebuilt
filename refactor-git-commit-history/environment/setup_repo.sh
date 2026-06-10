#!/usr/bin/env bash
set -e

REPO_DIR="/app/messy-repo"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
cd "$REPO_DIR"

git init
git config user.email "dev@example.com"
git config user.name "Developer"

# Helper to make a commit with a specific message
commit() {
    git add -A
    git commit -m "$1" --allow-empty-message
}

# === Initial project setup commits (chore) ===
echo '{ "name": "myapp", "version": "1.0.0" }' > package.json
commit "init"

echo "node_modules/" > .gitignore
commit "update"

mkdir -p src
echo 'console.log("hello");' > src/index.js
commit "wip"

# === Feature: user authentication (feat) ===
echo 'function login(user, pass) { return true; }' > src/auth.js
commit "add stuff"

echo 'function logout() { return true; }' >> src/auth.js
commit "more changes"

echo 'function validateToken(token) { return token.length > 0; }' >> src/auth.js
commit "fix"

# === Bug fix: input validation (fix) ===
echo 'function sanitize(input) { return input.trim(); }' > src/validate.js
commit "wip"

echo 'function isEmail(str) { return str.includes("@"); }' >> src/validate.js
commit "update"

# === Documentation (docs) ===
echo "# MyApp" > README.md
echo "A sample application." >> README.md
commit "readme"

echo "## Installation" >> README.md
echo "Run npm install" >> README.md
commit "update"

echo "## Usage" >> README.md
echo "Run npm start" >> README.md
commit "more docs"

# === Style changes (style) ===
cat > src/index.js << 'JSEOF'
console.log("hello");
console.log("world");
JSEOF
commit "formatting"

# === Create a side branch and merge to produce merge commits ===
git checkout -b feature-logging
echo 'function log(msg) { console.log("[LOG]", msg); }' > src/logger.js
commit "add logger"

echo 'function warn(msg) { console.warn("[WARN]", msg); }' >> src/logger.js
commit "wip"

echo 'function error(msg) { console.error("[ERR]", msg); }' >> src/logger.js
commit "done"

git checkout master

# Make a commit on master so merge is not fast-forward
echo "MIT License" > LICENSE
commit "stuff"

git merge feature-logging --no-ff -m "Merge branch 'feature-logging'"

# === Another feature branch with merge ===
git checkout -b feature-config
echo 'const config = { port: 3000, host: "localhost" };' > src/config.js
commit "config"

echo 'module.exports = config;' >> src/config.js
commit "export"

git checkout master

echo '// entry point' >> src/index.js
commit "tweak"

git merge feature-config --no-ff -m "Merge branch 'feature-config'"

# === Test files (test) ===
mkdir -p tests
echo 'test("login works", () => { expect(true).toBe(true); });' > tests/auth.test.js
commit "test"

echo 'test("sanitize works", () => { expect(true).toBe(true); });' > tests/validate.test.js
commit "another test"

echo 'test("logger works", () => { expect(true).toBe(true); });' > tests/logger.test.js
commit "wip"

# === Refactor (refactor) ===
cat > src/auth.js << 'JSEOF'
function login(user, pass) {
  if (!user || !pass) return false;
  return true;
}
function logout() { return true; }
function validateToken(token) { return token && token.length > 0; }
JSEOF
commit "cleanup"

cat > src/validate.js << 'JSEOF'
function sanitize(input) {
  if (typeof input !== 'string') return '';
  return input.trim();
}
function isEmail(str) {
  return typeof str === 'string' && str.includes("@");
}
JSEOF
commit "fix stuff"

echo "Done setting up messy repo at $REPO_DIR"
echo "Total commits: $(git rev-list --count HEAD)"
echo "Merge commits: $(git rev-list --merges --count HEAD)"
