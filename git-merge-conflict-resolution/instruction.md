## Git Repository Merging with Conflict Resolution

Set up a Git repository with two diverged feature branches that modify the same files, then merge them into `main`, resolving all conflicts so that both features are preserved.

### Technical Requirements

- All work is done inside `/app/repo/` (initialize the Git repo there).
- Use Git with a default user config (`git config user.name "Developer"` and `git config user.email "dev@example.com"`).
- Branch names: `feature/user-auth` and `feature/profile-page`.
- Conflicting files: `app.js` and `config.json`.

### Step-by-step Requirements

#### 1. Initialize repository with initial commit

Create `/app/repo/` as a Git repository. Add the following two files and make an initial commit on `main` with message `Initial commit`.

**app.js**
```js
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.send('Welcome to the app');
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

**config.json**
```json
{
  "appName": "MyApp",
  "version": "1.0.0",
  "port": 3000,
  "features": []
}
```

#### 2. Create `feature/user-auth` branch (from `main`)

Branch off `main`. Replace `app.js` and `config.json` with the content below, then commit with message `Add user authentication`.

**app.js**
```js
const express = require('express');
const app = express();
const authMiddleware = require('./auth');

app.use(authMiddleware);

app.get('/', (req, res) => {
  res.send('Welcome to the app');
});

app.post('/login', (req, res) => {
  res.send('Login endpoint');
});

app.post('/register', (req, res) => {
  res.send('Register endpoint');
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

**config.json**
```json
{
  "appName": "MyApp",
  "version": "1.1.0",
  "port": 3000,
  "features": ["authentication"],
  "auth": {
    "tokenExpiry": 3600,
    "provider": "local"
  }
}
```

#### 3. Create `feature/profile-page` branch (from `main`, NOT from `feature/user-auth`)

Switch back to `main`, then create this branch. Replace `app.js` and `config.json` with the content below, then commit with message `Add profile page`.

**app.js**
```js
const express = require('express');
const app = express();
const profileRouter = require('./profile');

app.use('/profile', profileRouter);

app.get('/', (req, res) => {
  res.send('Welcome to the app');
});

app.get('/profile/:id', (req, res) => {
  res.send('Profile page for user ' + req.params.id);
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

**config.json**
```json
{
  "appName": "MyApp",
  "version": "1.1.0",
  "port": 3000,
  "features": ["profile"],
  "profile": {
    "avatarMaxSize": 2048,
    "defaultAvatar": "default.png"
  }
}
```

#### 4. Merge both branches into `main`

1. Switch to `main`.
2. Merge `feature/user-auth` into `main` (this should be a clean fast-forward or simple merge).
3. Merge `feature/profile-page` into `main` — this will produce conflicts in both `app.js` and `config.json`.
4. Resolve all conflicts so the final files combine both features (see expected output below).
5. Commit the merge with message `Merge feature/profile-page into main`.

### Expected Final State (on `main` after all merges)

**app.js** must contain all of the following elements:
- `require('./auth')` and `require('./profile')` imports
- `app.use(authMiddleware)` middleware
- `app.use('/profile', profileRouter)` middleware
- The `/login` and `/register` POST routes
- The `/profile/:id` GET route
- The original `GET /` route
- The `app.listen` call on port 3000

**config.json** must be valid JSON and contain:
- `"version": "1.1.0"`
- `"features"` array containing both `"authentication"` and `"profile"`
- The `"auth"` object with `"tokenExpiry"` and `"provider"` keys
- The `"profile"` object with `"avatarMaxSize"` and `"defaultAvatar"` keys

### Git History Requirements

- `main` must have at least 3 commits (initial + merge of first branch + merge of second branch).
- Both `feature/user-auth` and `feature/profile-page` branches must still exist.
- The most recent commit on `main` must be a merge commit (i.e., have 2 parents).
- Running `git log --oneline --all` from `/app/repo/` must show commits from both feature branches.
