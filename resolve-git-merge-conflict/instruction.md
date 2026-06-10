## Feature Branch Merge Conflict Resolution

Simulate a scenario where two developers modify the same file on separate branches, creating a merge conflict. Resolve the conflict by keeping changes from both branches.

### Requirements

All work is done inside `/app`. Initialize a new Git repository there.

**Step 1: Initial commit on `main` branch**

Create `/app/app.py` with the following exact content and commit it on the `main` branch with message `"Initial commit"`:

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the app"

if __name__ == '__main__':
    app.run(debug=True)
```

**Step 2: Feature branch `feature/auth`**

Create a branch `feature/auth` from `main`. On this branch, replace the contents of `app.py` with:

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

users = {"admin": "password123"}

@app.route('/')
def home():
    return "Welcome to the app"

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if users.get(username) == password:
        return jsonify({"message": "Login successful"}), 200
    return jsonify({"message": "Invalid credentials"}), 401

if __name__ == '__main__':
    app.run(debug=True)
```

Commit with message `"Add authentication feature"`.

**Step 3: Feature branch `feature/api`**

Switch back to `main`. Create a branch `feature/api` from `main`. On this branch, replace the contents of `app.py` with:

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the app"

@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({"data": [1, 2, 3], "status": "ok"})

if __name__ == '__main__':
    app.run(debug=True)
```

Commit with message `"Add API endpoint"`.

**Step 4: Merge and resolve conflict**

1. Switch to `main`.
2. Merge `feature/auth` into `main` (this should succeed without conflict).
3. Merge `feature/api` into `main` (this should produce a merge conflict).
4. Resolve the conflict in `app.py` by combining both features — the final file must include both the `/login` route and the `/api/data` route, along with the original `/` route.
5. Commit the merge resolution with message `"Merge feature/api with conflict resolution"`.

### Final State

After all steps, the repository at `/app` must satisfy:

- The current branch is `main`.
- The git log on `main` contains at least 4 commits (initial, auth merge, api merge resolution, and possibly the merge commit for auth).
- Both branches `feature/auth` and `feature/api` exist in the repository.
- `/app/app.py` contains all three route definitions: `/`, `/login`, and `/api/data`.
- `/app/app.py` contains no conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
- `/app/app.py` is valid Python (no syntax errors).
- The imports in `app.py` include `request` and `jsonify` from flask.
- The `users` dictionary is present in the final file.
- The working tree is clean (no uncommitted changes).
