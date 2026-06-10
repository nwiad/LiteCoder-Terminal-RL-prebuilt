## Build a Static Site Generator with nginx and Git

Create a production-ready static site hosting environment with automated deployment via Git hooks. Markdown files pushed to a Git repository are automatically converted to HTML and served by nginx.

### Technical Requirements

- **Web Server:** nginx, listening on port 80
- **Git:** A bare Git repository at `/app/site-repo.git` with a `post-receive` hook that triggers the build pipeline
- **Static Site Generator:** Use `pandoc` to convert Markdown (`.md`) files to HTML
- **Site Root:** nginx must serve static files from `/app/site-output/`

### Setup Details

1. **Bare Git Repository (`/app/site-repo.git`)**
   - Initialize as a bare Git repository.
   - Contains a `post-receive` hook (executable) at `/app/site-repo.git/hooks/post-receive`.
   - The hook must:
     - Check out the latest pushed content to a temporary working directory.
     - Convert all `.md` files found in the checkout to `.html` files using `pandoc`.
     - Place the resulting HTML files into `/app/site-output/`, preserving the relative directory structure (e.g., `docs/guide.md` becomes `/app/site-output/docs/guide.html`).
     - If an `index.md` exists at the repository root, it must produce `/app/site-output/index.html`.

2. **nginx Configuration**
   - nginx must be running and serving HTTP on port 80.
   - The server block must set `root` to `/app/site-output/`.
   - `index` directive must include `index.html`.
   - Return 404 for files that do not exist.

3. **Working Clone (`/app/site-workdir`)**
   - Create a regular (non-bare) clone of `/app/site-repo.git` at `/app/site-workdir`.
   - This clone is used by developers to push content.

### End-to-End Workflow

After setup is complete, the following workflow must succeed:

1. A developer creates `/app/site-workdir/index.md` with Markdown content (e.g., `# Hello World`).
2. The developer commits and pushes to the bare repository (`git push origin master` or `main`).
3. The `post-receive` hook fires, converts `index.md` to `index.html`, and places it in `/app/site-output/`.
4. `curl http://localhost/` returns the generated HTML containing the converted content.

### Verification Criteria

- `/app/site-repo.git` is a valid bare Git repository (`git rev-parse --is-bare-repository` returns `true`).
- `/app/site-repo.git/hooks/post-receive` exists and is executable.
- `/app/site-output/` directory exists.
- nginx is running and responds on port 80.
- Pushing a commit with `.md` files to `/app/site-repo.git` via `/app/site-workdir` produces corresponding `.html` files in `/app/site-output/`.
- `curl http://localhost/` returns HTTP 200 with HTML content after an `index.md` has been pushed.
- Subdirectory structure is preserved (e.g., pushing `docs/intro.md` produces `/app/site-output/docs/intro.html`).
