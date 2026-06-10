## Task: Git Bisect Debugging

Use git bisect to identify the exact commit that introduced a bug in a Python function.

## Technical Requirements

- Git version control system
- Python 3.x
- Repository: https://github.com/datasleek-testing/test-git-bisect.git
- Output file: /app/result.txt

## Task Description

A Python function `add_numbers` in the repository is broken and returns incorrect results. Your task is to:

1. Clone the repository to /app/test-git-bisect
2. Use git bisect to find the exact commit SHA that introduced the bug
3. Write the commit SHA to /app/result.txt

## Function Specification

The `add_numbers` function should satisfy:
- Input: Two integers
- Expected behavior: Returns the sum of the two integers
- Test case: `add_numbers(2, 3)` should return `5`

## Output Format

Write the commit SHA (40-character hexadecimal string) to /app/result.txt:

```
<commit_sha>
```

Example:
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

## Requirements

- Clone the repository before starting the bisect process
- Identify a known good commit (where the function works correctly)
- Mark the current HEAD as bad (where the function is broken)
- Use git bisect to systematically find the breaking commit
- The output must contain only the commit SHA of the first bad commit
