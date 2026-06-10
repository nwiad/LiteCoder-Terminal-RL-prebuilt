## Historical Commit Analysis & Restoration

Set up a Git repository simulating a Python project called "DataForge" with a realistic commit history, then use Git tools to find and restore a deleted utility file with modern improvements.

### Technical Requirements

- Git for version control
- Python 3.x for the utility file
- All work done in `/app/` as the project root

### Step-by-step Requirements

**1. Initialize the repository and create project structure**

Initialize a Git repository in `/app/`. Create the following directory structure and make an initial commit with message `"Initial commit: DataForge project structure"`:

```
/app/
├── README.md              (contains at least the text "DataForge")
├── setup.py
├── dataforge/
│   ├── __init__.py
│   └── core.py
├── utils/
│   └── __init__.py
└── tests/
    └── __init__.py
```

**2. Create `utils/data_cleaner.py` with legacy functions**

Create `/app/utils/data_cleaner.py` containing exactly these 4 functions (with working implementations):

- `remove_duplicates(data: list) -> list` — removes duplicate entries from a list
- `normalize_whitespace(text: str) -> str` — collapses multiple whitespace characters into single spaces and strips leading/trailing whitespace
- `convert_dates(date_str: str, input_format: str, output_format: str) -> str` — converts a date string from one format to another
- `fill_missing_values(data: dict, defaults: dict) -> dict` — fills missing keys in `data` using values from `defaults`

Commit with message: `"Add data_cleaner utility with legacy cleaning functions"`

**3. Simulate development history**

Create at least 3 additional commits that add or modify files in the repository (e.g., adding features to `dataforge/core.py`, updating `README.md`, adding test files). Each commit must have a distinct, descriptive message.

**4. Delete `utils/data_cleaner.py` in a refactoring commit**

Remove the file `/app/utils/data_cleaner.py` and commit with a message that contains the word `"refactor"` (case-insensitive). After this commit, add at least 1 more commit that modifies other files.

**5. Analyze Git history to locate the deletion**

Use Git commands to find:
- The commit hash where `utils/data_cleaner.py` was deleted
- The commit hash where `utils/data_cleaner.py` was originally added

Write the results to `/app/analysis.txt` with exactly this format (one item per line, using full 40-character commit hashes):

```
deletion_commit: <full_hash>
addition_commit: <full_hash>
```

**6. Restore and modernize the file**

Restore the file from Git history to `/app/utils/data_cleaner.py` and improve it with all of the following:

- Every function must have a proper docstring (triple-quoted string as the first statement in the function body)
- Every function must have type hints on all parameters and the return type
- Every function must include at least one `raise` statement for input validation (e.g., raising `TypeError` or `ValueError` on invalid input)
- The file must contain all 4 original functions: `remove_duplicates`, `normalize_whitespace`, `convert_dates`, `fill_missing_values`

Commit the restored file with a message that contains the word `"restore"` (case-insensitive).

**7. Write a restoration summary**

Create `/app/restoration_summary.txt` containing:
- Line 1: The deletion commit hash (full 40-char)
- Line 2: The addition commit hash (full 40-char)
- Line 3: The total number of commits in the repository (just the integer)

Commit this file with any descriptive message.

### Final State

After all steps, the repository at `/app/` must:
- Be a valid Git repository with at least 8 commits
- Contain `/app/utils/data_cleaner.py` with all 4 modernized functions
- Contain `/app/analysis.txt` with the correct commit hashes
- Contain `/app/restoration_summary.txt` with the required 3 lines
- Have a clean working tree (no uncommitted changes)
