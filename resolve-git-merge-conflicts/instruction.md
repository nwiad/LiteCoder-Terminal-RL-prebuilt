## Multi-Branch Git Repository Management with Merge Conflicts

Set up a Git repository with multiple branches, introduce changes that create merge conflicts, and resolve them so the final `main` branch contains both features with a clean commit history.

### Technical Requirements

- Use Git for version control.
- All work is done inside `/app/repo/` (create this directory as the Git repository root).
- Python 3.x for all source files.

### Step-by-Step Requirements

1. **Initialize the repository**
   - Create and initialize a Git repo at `/app/repo/`.
   - Configure a git user name and email for the repo (any values are fine).

2. **Create the initial codebase on `main`**
   - Create `/app/repo/main.py` with the following exact content and commit it on the `main` branch with the message `Initial commit`:

```python
def greet(name):
    return f"Hello, {name}!"

def main():
    print(greet("World"))

if __name__ == "__main__":
    main()
```

3. **Branch `feature-user-auth`**
   - From `main`, create and switch to a branch named `feature-user-auth`.
   - Replace the entire content of `/app/repo/main.py` with:

```python
def greet(name):
    return f"Hello, {name}!"

def authenticate(user, password):
    users = {"admin": "secret", "user1": "pass123"}
    return users.get(user) == password

def main():
    print(greet("World"))
    if authenticate("admin", "secret"):
        print("Authentication successful")
    else:
        print("Authentication failed")

if __name__ == "__main__":
    main()
```

   - Commit with the message `Add user authentication`.

4. **Branch `feature-logging`**
   - Switch back to `main`, then create and switch to a branch named `feature-logging`.
   - Replace the entire content of `/app/repo/main.py` with:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def greet(name):
    logger.info(f"Greeting {name}")
    return f"Hello, {name}!"

def main():
    logger.info("Application started")
    print(greet("World"))
    logger.info("Application finished")

if __name__ == "__main__":
    main()
```

   - Commit with the message `Add logging functionality`.

5. **Merge `feature-user-auth` into `main`**
   - Switch to `main` and merge `feature-user-auth`. This should be a clean merge with no conflicts.

6. **Merge `feature-logging` into `main` and resolve conflicts**
   - While still on `main`, merge `feature-logging`. This will produce merge conflicts.
   - Resolve the conflicts in `/app/repo/main.py` so that the final file incorporates both features (authentication AND logging). The resolved file must satisfy ALL of the following:
     - Contains `import logging` at the top.
     - Contains `logging.basicConfig` and `logging.getLogger` setup.
     - Defines the function `authenticate(user, password)` that returns `True` when given valid credentials and `False` otherwise.
     - Defines the function `greet(name)` that includes a `logger.info` call and returns the greeting string.
     - The `main()` function calls `greet`, `authenticate`, and uses `logger.info` at least once.
     - The file is valid Python (no syntax errors, no leftover conflict markers like `<<<<<<<`, `=======`, `>>>>>>>`).
   - Commit the merge resolution with the message `Merge feature-logging with conflict resolution`.

### Verification Criteria

After all steps are complete:

- `/app/repo/` is a valid Git repository.
- The current branch is `main`.
- Branches `feature-user-auth` and `feature-logging` both exist in the repository.
- `git log --oneline` on `main` shows at least 4 commits (initial, auth, logging merge, conflict resolution merge).
- `/app/repo/main.py` is valid Python with no syntax errors and no conflict markers.
- `/app/repo/main.py` contains both the `authenticate` function and logging setup (`import logging`, `logger`).
- Running `python /app/repo/main.py` executes without errors.
