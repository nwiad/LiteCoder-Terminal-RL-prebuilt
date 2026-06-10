#!/usr/bin/env python3
"""Git History Surgery - Reference Solution"""
import subprocess, os, json, shutil, sys

APP_DIR = os.environ.get("APP_DIR", "/app")
REPO_DIR = os.path.join(APP_DIR, "repo")
OUTPUT_PATH = os.path.join(APP_DIR, "output.json")

def run(cmd, cwd=None, check=True):
    if cwd is None:
        cwd = REPO_DIR
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"FAILED: {cmd}\nstdout: {r.stdout}\nstderr: {r.stderr}", file=sys.stderr)
        r.check_returncode()
    return r.stdout.strip()

def wf(path, content):
    fp = os.path.join(REPO_DIR, path)
    d = os.path.dirname(fp)
    if d:
        os.makedirs(d, exist_ok=True)
    mode = 'wb' if isinstance(content, bytes) else 'w'
    with open(fp, mode) as f:
        f.write(content)

# ================================================================
# PHASE 1: Build the repository with exact initial structure
# ================================================================
print("Phase 1: Creating repository")
if os.path.exists(REPO_DIR):
    shutil.rmtree(REPO_DIR)
os.makedirs(REPO_DIR)

run("git init")
run('git config user.email "developer@example.com"')
run('git config user.name "Developer"')

# -- main branch commits --
wf("README.md", "# Project Alpha")
run("git add README.md && git commit -m 'Initial commit'")

wf("config.py", 'DB_HOST = "localhost"\nDB_PORT = 5432\n')
run("git add config.py && git commit -m 'Add config'")
develop_base = run("git rev-parse HEAD")

wf("secrets.txt",
   'AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE\n'
   'AWS_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n'
   'DB_PASSWORD=SuperSecret123!\n')
run("git add secrets.txt && git commit -m 'Add credentials'")

wf("assets/logo.bin", os.urandom(1024 * 1024))
run("git add assets/logo.bin && git commit -m 'Add binary asset'")

# -- develop branch (off main after 2nd commit) --
run(f"git checkout -b develop {develop_base}")

UTILS_FULL = ('def add(a, b):\n'
              '    return a + b\n\n'
              'def subtract(a, b):\n'
              '    return a - b\n\n'
              'def multiply(a, b):\n'
              '    return a * b\n')

# Develop commit 1: "Add utils module" — squashed with the duplicate by
# construction: we write the full utils.py (all 3 functions) directly.
wf("utils.py", UTILS_FULL)
run("git add utils.py && git commit -m 'Add utils module'")

# Develop commit 2: Add credentials to dev config
wf("dev_config.py", 'API_KEY = "sk-live-abc123secretkey456"\nDEBUG = True\n')
run("git add dev_config.py && git commit -m 'Add credentials to dev config'")

# Save develop tip — feature branches will be based here so they inherit
# all of develop's content (matching the expected final state).
develop_tip = run("git rev-parse HEAD")

# -- feature-x branch (off develop tip) --
print("Creating feature-x branch")
run(f"git checkout -b feature-x {develop_tip}")

wf("feature_x.py", 'def feature_x():\n    return "Feature X is active"\n')
run("git add feature_x.py && git commit -m 'Add feature X'")

wf("test_data.bin", os.urandom(2 * 1024 * 1024))
run("git add test_data.bin && git commit -m 'Add large test data'")

# -- feature-y branch (off develop tip) --
print("Creating feature-y branch")
run(f"git checkout -b feature-y {develop_tip}")

wf("feature_y.py", 'def feature_y():\n    return "Feature Y is active"\n')
run("git add feature_y.py && git commit -m 'Add feature Y'")

wf("feature_y.py",
   'PASSWORD = "admin_password_789"\n\ndef feature_y():\n    return "Feature Y is active"\n')
run("git add feature_y.py && git commit -m 'Add hardcoded password'")

run("git checkout main")
print("Repository created. Branches:", run("git branch"))

# ================================================================
# PHASE 2: History surgery — filter all branches in one pass
# ================================================================
print("\nPhase 2: History surgery")
os.environ['FILTER_BRANCH_SQUELCH_WARNING'] = '1'

filter_sh = '/tmp/git_filter.sh'
with open(filter_sh, 'w') as f:
    f.write('#!/bin/bash\n')
    f.write('rm -f assets/logo.bin test_data.bin 2>/dev/null\n')
    f.write('rmdir assets 2>/dev/null || true\n')
    f.write('rm -f secrets.txt 2>/dev/null\n')
    f.write('if [ -f dev_config.py ]; then\n')
    f.write("  sed -i 's/API_KEY = \".*\"/API_KEY = \"REDACTED\"/' dev_config.py\n")
    f.write('fi\n')
    f.write('if [ -f feature_y.py ]; then\n')
    f.write("  sed -i '/^PASSWORD = /d' feature_y.py\n")
    f.write("  sed -i '/./,$!d' feature_y.py\n")
    f.write('fi\n')
os.chmod(filter_sh, 0o755)

run(f'git filter-branch --tree-filter "bash {filter_sh}" --prune-empty -- --all')
print("Filter-branch complete")

# ================================================================
# PHASE 3: Cleanup refs and gc
# ================================================================
print("\nPhase 3: Cleanup")
run("git for-each-ref --format='%(refname)' refs/original/ | "
    "while read ref; do git update-ref -d \"$ref\"; done", check=False)
run("git reflog expire --expire=now --all", check=False)
run("git gc --prune=now --aggressive", check=False)

# ================================================================
# PHASE 4: Verification
# ================================================================
print("\nPhase 4: Verification")

for branch in ["main", "develop", "feature-x", "feature-y"]:
    run(f"git checkout {branch}")
    files_raw = run("git ls-files")
    files = sorted([f for f in files_raw.split('\n') if f.strip()])
    print(f"  {branch}: {files}")
    for bad in ["secrets.txt", "assets/logo.bin", "test_data.bin"]:
        assert bad not in files, f"{bad} still on {branch}!"

run("git checkout develop")
utils = run("cat utils.py")
assert "def add" in utils and "def subtract" in utils and "def multiply" in utils

dc = run("cat dev_config.py")
assert 'API_KEY = "REDACTED"' in dc and "DEBUG = True" in dc

run("git checkout feature-y")
fy = run("cat feature_y.py")
assert "PASSWORD" not in fy and "def feature_y" in fy

run("git checkout feature-x")
fx = run("cat feature_x.py")
assert "def feature_x" in fx
print("All verifications passed!")

# ================================================================
# PHASE 5: Generate output.json
# ================================================================
print("\nPhase 5: Generating output.json")

output = {
    "branches": ["main", "develop", "feature-x", "feature-y"],
    "removed_files": ["secrets.txt", "assets/logo.bin", "test_data.bin"],
    "scrubbed_credentials": ["secrets.txt", "dev_config.py", "feature_y.py"]
}

for branch in ["main", "develop", "feature-x", "feature-y"]:
    run(f"git checkout {branch}")
    commit_count = int(run("git rev-list --count HEAD"))
    files_raw = run("git ls-files")
    files = sorted([f for f in files_raw.split('\n') if f.strip()])
    output[branch] = {
        "commit_count": commit_count,
        "files": files
    }

with open(OUTPUT_PATH, 'w') as f:
    json.dump(output, f, indent=2)

print(f"Output written to {OUTPUT_PATH}")
print(json.dumps(output, indent=2))
print("\nDone!")
