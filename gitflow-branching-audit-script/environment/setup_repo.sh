#!/bin/bash
set -e

REPO_DIR="/app/test_repo"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
cd "$REPO_DIR"

git init
git config user.email "test@example.com"
git config user.name "Test User"

# ============================================================
# Initial setup: create master with an initial merge commit
# ============================================================
git checkout -b master

# Create initial commit (this will be a direct commit — violation)
echo "v1.0" > VERSION
git add VERSION
GIT_AUTHOR_DATE="2024-01-01T10:00:00" GIT_COMMITTER_DATE="2024-01-01T10:00:00" \
  git commit -m "Initial commit"

# ============================================================
# Create develop branch from master
# ============================================================
git checkout -b develop

echo "develop started" > dev.txt
git add dev.txt
GIT_AUTHOR_DATE="2024-01-02T10:00:00" GIT_COMMITTER_DATE="2024-01-02T10:00:00" \
  git commit -m "Start develop branch"

# ============================================================
# Category 1: Direct commits on protected branches
# ============================================================

# Direct commit on master (non-merge commit — violation)
git checkout master
echo "hotfix inline" > hotfix_inline.txt
git add hotfix_inline.txt
GIT_AUTHOR_DATE="2024-01-03T10:00:00" GIT_COMMITTER_DATE="2024-01-03T10:00:00" \
  git commit -m "Direct hotfix on master"

# Direct commit on develop (non-merge commit — violation)
git checkout develop
echo "quick fix" > quickfix.txt
git add quickfix.txt
GIT_AUTHOR_DATE="2024-01-04T10:00:00" GIT_COMMITTER_DATE="2024-01-04T10:00:00" \
  git commit -m "Direct fix on develop"

# ============================================================
# Category 2: Feature branch merged into wrong target
# ============================================================

# feature/login merged into master instead of develop (violation)
git checkout master
git checkout -b feature/login
echo "login feature" > login.txt
git add login.txt
GIT_AUTHOR_DATE="2024-01-05T10:00:00" GIT_COMMITTER_DATE="2024-01-05T10:00:00" \
  git commit -m "Add login feature"

git checkout master
GIT_AUTHOR_DATE="2024-01-06T10:00:00" GIT_COMMITTER_DATE="2024-01-06T10:00:00" \
  git merge --no-ff feature/login -m "Merge feature/login into master"

# feature/signup merged correctly into develop (valid — no violation)
git checkout develop
git checkout -b feature/signup
echo "signup feature" > signup.txt
git add signup.txt
GIT_AUTHOR_DATE="2024-01-07T10:00:00" GIT_COMMITTER_DATE="2024-01-07T10:00:00" \
  git commit -m "Add signup feature"

git checkout develop
GIT_AUTHOR_DATE="2024-01-08T10:00:00" GIT_COMMITTER_DATE="2024-01-08T10:00:00" \
  git merge --no-ff feature/signup -m "Merge feature/signup into develop"

# ============================================================
# Category 3: Release/hotfix branches merged into wrong target
# ============================================================

# release/1.0 merged into develop instead of master (violation)
git checkout develop
git checkout -b release/1.0
echo "release 1.0" > release.txt
git add release.txt
GIT_AUTHOR_DATE="2024-01-09T10:00:00" GIT_COMMITTER_DATE="2024-01-09T10:00:00" \
  git commit -m "Prepare release 1.0"

git checkout develop
GIT_AUTHOR_DATE="2024-01-10T10:00:00" GIT_COMMITTER_DATE="2024-01-10T10:00:00" \
  git merge --no-ff release/1.0 -m "Merge release/1.0 into develop"

# hotfix/urgent merged into develop instead of master (violation)
git checkout develop
git checkout -b hotfix/urgent
echo "urgent fix" > urgent.txt
git add urgent.txt
GIT_AUTHOR_DATE="2024-01-11T10:00:00" GIT_COMMITTER_DATE="2024-01-11T10:00:00" \
  git commit -m "Urgent hotfix"

git checkout develop
GIT_AUTHOR_DATE="2024-01-12T10:00:00" GIT_COMMITTER_DATE="2024-01-12T10:00:00" \
  git merge --no-ff hotfix/urgent -m "Merge hotfix/urgent into develop"

# hotfix/security merged correctly into master (valid — no violation)
git checkout master
git checkout -b hotfix/security
echo "security patch" > security.txt
git add security.txt
GIT_AUTHOR_DATE="2024-01-13T10:00:00" GIT_COMMITTER_DATE="2024-01-13T10:00:00" \
  git commit -m "Security patch"

git checkout master
GIT_AUTHOR_DATE="2024-01-14T10:00:00" GIT_COMMITTER_DATE="2024-01-14T10:00:00" \
  git merge --no-ff hotfix/security -m "Merge hotfix/security into master"

# ============================================================
# Category 4: Long-lived branches (lifespan > 30 days)
# ============================================================

# feature/old-dashboard — first commit 2024-01-01, last commit 2024-03-15 (74 days)
git checkout develop
git checkout -b feature/old-dashboard
echo "dashboard v1" > dashboard.txt
git add dashboard.txt
GIT_AUTHOR_DATE="2024-01-01T12:00:00" GIT_COMMITTER_DATE="2024-01-01T12:00:00" \
  git commit -m "Start dashboard feature"

echo "dashboard v2" >> dashboard.txt
git add dashboard.txt
GIT_AUTHOR_DATE="2024-02-10T12:00:00" GIT_COMMITTER_DATE="2024-02-10T12:00:00" \
  git commit -m "Update dashboard"

echo "dashboard v3" >> dashboard.txt
git add dashboard.txt
GIT_AUTHOR_DATE="2024-03-15T12:00:00" GIT_COMMITTER_DATE="2024-03-15T12:00:00" \
  git commit -m "Finalize dashboard"

# feature/quick-fix — first commit and last commit same day (0 days, no violation)
git checkout develop
git checkout -b feature/quick-fix
echo "quick" > quick.txt
git add quick.txt
GIT_AUTHOR_DATE="2024-02-01T10:00:00" GIT_COMMITTER_DATE="2024-02-01T10:00:00" \
  git commit -m "Quick fix feature"

# release/2.0 — spans 45 days (violation)
git checkout master
git checkout -b release/2.0
echo "release 2.0 prep" > release2.txt
git add release2.txt
GIT_AUTHOR_DATE="2024-03-01T10:00:00" GIT_COMMITTER_DATE="2024-03-01T10:00:00" \
  git commit -m "Start release 2.0"

echo "release 2.0 final" >> release2.txt
git add release2.txt
GIT_AUTHOR_DATE="2024-04-15T10:00:00" GIT_COMMITTER_DATE="2024-04-15T10:00:00" \
  git commit -m "Finalize release 2.0"

# ============================================================
# Return to master
# ============================================================
git checkout master

echo "Test repository created at $REPO_DIR"
