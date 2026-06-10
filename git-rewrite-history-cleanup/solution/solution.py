#!/usr/bin/env python3
import subprocess, json, os, sys

REPO = "/app/project-repo"

def run(cmd, check=True):
    r = subprocess.run(cmd, shell=True, cwd=REPO,
                       capture_output=True, text=True, check=False)
    if check and r.returncode != 0:
        print(f"FAIL: {cmd}\n{r.stderr}", file=sys.stderr)
        raise RuntimeError(f"Command failed: {cmd}")
    return r.stdout.strip()

def get_commits():
    out = run("git log --reverse --format=%H%x00%s main")
    return [(h,m) for h,m in
            (l.split('\x00',1) for l in out.splitlines() if '\x00' in l)]

def find_large_files():
    large = set()
    for c in run("git rev-list main").splitlines():
        for line in run(f"git ls-tree -r -l {c}").splitlines():
            parts = line.split('\t', 1)
            if len(parts) == 2:
                size = parts[0].split()[-1]
                try:
                    if int(size) > 102400:
                        large.add(os.path.basename(parts[1]))
                except ValueError:
                    pass
    return sorted(large)

def find_temp_files():
    temps = set()
    for c in run("git rev-list main").splitlines():
        for line in run(f"git ls-tree -r {c}").splitlines():
            if '\t' in line:
                bn = os.path.basename(line.split('\t',1)[1])
                if bn.endswith('.tmp') or bn.endswith('.log'):
                    temps.add(bn)
    return sorted(temps)

def find_paths_large():
    paths = set()
    for c in run("git rev-list main").splitlines():
        for line in run(f"git ls-tree -r -l {c}").splitlines():
            parts = line.split('\t', 1)
            if len(parts) == 2:
                size = parts[0].split()[-1]
                try:
                    if int(size) > 102400:
                        paths.add(parts[1])
                except ValueError:
                    pass
    return paths

def find_paths_temp():
    paths = set()
    for c in run("git rev-list main").splitlines():
        for line in run(f"git ls-tree -r {c}").splitlines():
            if '\t' in line:
                p = line.split('\t',1)[1]
                bn = os.path.basename(p)
                if bn.endswith('.tmp') or bn.endswith('.log'):
                    paths.add(p)
    return paths

def cleanup_refs():
    run("git for-each-ref --format='%(refname)' refs/original/ | "
        "while read ref; do git update-ref -d \"$ref\"; done", check=False)
    run("git reflog expire --expire=now --all", check=False)
    run("git gc --prune=now", check=False)

def manual_linearize():
    """Recreate linear history via cherry-pick for non-merge commits."""
    info = run("git log --reverse --topo-order --format=%H%x00%P main")
    non_merge = []
    for line in info.splitlines():
        if '\x00' not in line: continue
        h, parents = line.split('\x00', 1)
        if len(parents.strip().split()) <= 1:
            non_merge.append(h.strip())
    run("git checkout --orphan linear-temp")
    run("git rm -rf . 2>/dev/null || true", check=False)
    for c in non_merge:
        msg = run(f"git log -1 --format=%B {c}").replace('"', '\\"')
        run(f"git cherry-pick --no-commit {c}", check=False)
        # Stage everything
        run("git add -A", check=False)
        run(f'git commit --allow-empty -m "{msg}"')
    run("git branch -D main", check=False)
    run("git branch -m linear-temp main")

def do_squash(commits):
    """Squash consecutive fix: commits into preceding non-fix commit.
    Returns number of fix commits squashed (absorbed)."""
    # Build groups: [(keep_message, [hashes])]
    groups = []
    for h, msg in commits:
        is_fix = msg.lower().startswith('fix:')
        if is_fix and groups:
            # Append to previous group
            groups[-1][1].append(h)
        elif is_fix and not groups:
            # Fix at start with no preceding - start new group, keep first fix msg
            groups.append((msg, [h]))
        else:
            # Non-fix commit starts a new group
            groups.append((msg, [h]))

    # Count how many fix commits get absorbed
    squashed = 0
    for msg, hashes in groups:
        for h in hashes:
            # Find original message
            for oh, om in commits:
                if oh == h and om.lower().startswith('fix:'):
                    squashed += 1
                    break
    # If first group is all fix commits, the first one survives
    if groups and groups[0][0].lower().startswith('fix:'):
        squashed -= 1

    # Build rebase todo
    todo_lines = []
    for msg, hashes in groups:
        for j, h in enumerate(hashes):
            todo_lines.append(f"pick {h}" if j == 0 else f"fixup {h}")

    todo = "\n".join(todo_lines) + "\n"
    with open("/tmp/rebase_todo.sh", 'w') as f:
        f.write("#!/bin/bash\ncat > \"$1\" << 'TODOEOF'\n")
        f.write(todo)
        f.write("TODOEOF\n")
    os.chmod("/tmp/rebase_todo.sh", 0o755)

    run("GIT_SEQUENCE_EDITOR=/tmp/rebase_todo.sh git rebase -i --root")
    return squashed

def main():
    os.chdir(REPO)
    run("git config user.email 'dev@example.com'")
    run("git config user.name 'Developer'")

    # Phase 0: Record original state
    original_count = int(run("git rev-list --count main"))
    large_files = find_large_files()
    temp_files = find_temp_files()
    orig_commits = get_commits()
    orig_fix = sum(1 for _,m in orig_commits if m.lower().startswith('fix:'))
    print(f"Original: {original_count} commits, {orig_fix} fix, "
          f"large={large_files}, temp={temp_files}")

    # Phase 1: Remove large files from history
    lp = find_paths_large()
    if lp:
        rm = " ".join(f"'{p}'" for p in lp)
        run(f"git filter-branch -f --index-filter "
            f"'git rm -rf --cached --ignore-unmatch {rm}' "
            f"--prune-empty -- --all")
        cleanup_refs()
    print("Phase 1 done: large files removed")

    # Phase 2: Remove temp/log files from history
    tp = find_paths_temp()
    if tp:
        rm = " ".join(f"'{p}'" for p in tp)
        run(f"git filter-branch -f --index-filter "
            f"'git rm -rf --cached --ignore-unmatch {rm}' "
            f"--prune-empty -- --all")
        cleanup_refs()
    print("Phase 2 done: temp files removed")

    # Delete other branches before linearize (feature-utils etc)
    branches = run("git branch --format='%(refname:short)'").splitlines()
    for b in branches:
        b = b.strip()
        if b and b != "main":
            run(f"git branch -D {b}", check=False)

    # Phase 3: Linearize history
    merges = run("git log --merges --oneline main", check=False)
    if merges:
        root = run("git rev-list --max-parents=0 main")
        run(f"git rebase {root} main", check=False)
        merges2 = run("git log --merges --oneline main", check=False)
        if merges2:
            manual_linearize()
    print("Phase 3 done: history linearized")

    # Phase 4: Squash fix commits
    cur = get_commits()
    print(f"Before squash: {len(cur)} commits")
    for i,(h,m) in enumerate(cur):
        print(f"  {i}: {h[:8]} {m}")
    squashed = do_squash(cur)
    print(f"Phase 4 done: squashed {squashed} fix commits")

    # Phase 5: Tag and branch
    run("git tag -d v1.0-clean 2>/dev/null || true", check=False)
    run("git branch -D clean-release 2>/dev/null || true", check=False)
    run('git tag -a v1.0-clean -m "Clean release v1.0"')
    run("git branch clean-release HEAD")
    print("Phase 5 done: tag and branch created")

    # Phase 6: Report
    final_count = int(run("git rev-list --count main"))
    tag_hash = run("git rev-list -1 v1.0-clean")
    is_lin = run("git log --merges --oneline main", check=False) == ""
    br_ok = run("git branch --list clean-release").strip() != ""

    report = {
        "original_commit_count": original_count,
        "final_commit_count": final_count,
        "removed_large_files": large_files,
        "removed_temp_files": temp_files,
        "squashed_fix_commits": squashed,
        "tag_name": "v1.0-clean",
        "tag_commit_hash": tag_hash,
        "clean_release_branch_exists": br_ok,
        "is_linear": is_lin
    }
    with open("/app/output.json", 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nFinal: {final_count} commits")
    print(json.dumps(report, indent=2))

    # Show final log
    print("\nFinal log:")
    print(run("git log --oneline main"))

if __name__ == "__main__":
    main()
