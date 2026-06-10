## Branching Strategy Audit

Analyze a Git repository's branching history and identify violations of a Git Flow branching strategy by creating a shell script that produces a structured JSON report.

### Setup

A setup script `/app/setup_repo.sh` is provided. Run it first — it creates a local Git repository at `/app/test_repo` with a pre-built commit and branch history that includes both valid Git Flow usage and intentional violations.

### Requirements

Create an executable Bash script at `/app/gitflow_audit.sh` that:

1. Accepts a single argument: the path to a local Git repository.
2. Analyzes the repository's full branch and commit history.
3. Writes a JSON report to `/app/audit_report.json`.

The script must detect the following four categories of Git Flow violations:

**Category 1: Direct commits on protected branches (`direct_commits_on_protected`)**
Find any commit on `master` (or `main`) or `develop` that is NOT a merge commit. A merge commit is defined as a commit with two or more parents. List each violation with the branch name, commit hash (full 40-char SHA), and commit subject line.

**Category 2: Feature branches merged into wrong target (`feature_wrong_target`)**
A feature branch is any branch whose name starts with `feature/`. In Git Flow, feature branches must only be merged into `develop`. Report any feature branch that was merged into a branch other than `develop`, listing the feature branch name and the actual target branch it was merged into.

**Category 3: Release/hotfix branches merged into wrong target (`release_hotfix_wrong_target`)**
Release branches start with `release/` and hotfix branches start with `hotfix/`. These must only be merged into `master` (or `main`). Report any such branch merged into a branch other than `master`/`main`, listing the branch name and the actual target branch.

**Category 4: Long-lived branches (`long_lived_branches`)**
Any branch (excluding `master`, `main`, and `develop`) whose lifespan exceeds 30 days. The lifespan is measured from the branch's first commit date to its last commit date (or the current date if still active). List each with the branch name and the lifespan in days (integer).

### Output Format

`/app/audit_report.json` must be valid JSON with this exact top-level structure:

```json
{
  "repository": "<absolute path to the analyzed repo>",
  "direct_commits_on_protected": [
    {
      "branch": "<branch name>",
      "commit_hash": "<full 40-char SHA>",
      "subject": "<commit subject line>"
    }
  ],
  "feature_wrong_target": [
    {
      "feature_branch": "<branch name>",
      "merged_into": "<target branch name>"
    }
  ],
  "release_hotfix_wrong_target": [
    {
      "branch": "<branch name>",
      "merged_into": "<target branch name>"
    }
  ],
  "long_lived_branches": [
    {
      "branch": "<branch name>",
      "lifespan_days": <integer>
    }
  ],
  "summary": {
    "total_violations": <integer>,
    "direct_commits_on_protected_count": <integer>,
    "feature_wrong_target_count": <integer>,
    "release_hotfix_wrong_target_count": <integer>,
    "long_lived_branches_count": <integer>
  }
}
```

- Each array may be empty if no violations of that type are found.
- `total_violations` equals the sum of the four count fields.
- Arrays should contain one entry per violation found.

### Constraints

- The script must work with Bash (#!/bin/bash) and only use standard Git CLI commands (no external dependencies beyond `git`, `jq`, `date`, `awk`, `sed`, `grep`).
- The script must be executable (`chmod +x`).
- The script must exit with code 0 on success.
- The output JSON must be parseable by `jq` without errors.
