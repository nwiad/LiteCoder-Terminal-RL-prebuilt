## Build a Local Git Server with WebDAV

Set up a local Git server accessible over HTTP via WebDAV with user authentication and repository browsing capabilities.

**Technical Requirements:**
- Apache web server with WebDAV and Git HTTP backend support
- HTTP Basic Authentication
- Git 2.x or higher
- Working directory: /app

**Implementation Requirements:**

1. **Apache Configuration:**
   - Configure Apache virtual host listening on port 8080
   - Enable required modules: dav, dav_fs, auth_basic, authn_file, authz_user, cgi, alias, env, rewrite
   - Set up Git HTTP backend at `/git/` URL path
   - Configure document root at `/app/git-repos`

2. **Authentication Setup:**
   - Create HTTP Basic Authentication using htpasswd
   - Store credentials in `/app/.htpasswd`
   - Create at least one user account (username: `gituser`, password: `gitpass123`)
   - Protect all Git operations with authentication

3. **Repository Structure:**
   - Create Git repositories directory at `/app/git-repos`
   - Set proper ownership and permissions (readable/writable by Apache user)
   - Initialize at least one bare Git repository named `test-repo.git`

4. **Git HTTP Backend:**
   - Configure Git smart HTTP protocol using git-http-backend CGI
   - Set GIT_PROJECT_ROOT environment variable
   - Enable both read and write operations over HTTP

5. **Verification Output:**
   - Create a JSON status file at `/app/server-status.json` with the following structure:
     ```json
     {
       "server_running": true,
       "port": 8080,
       "git_backend_enabled": true,
       "authentication_enabled": true,
       "repositories": ["test-repo.git"],
       "test_user": "gituser"
     }
     ```

6. **Functional Requirements:**
   - Server must accept Git clone operations via HTTP
   - Server must accept authenticated push operations
   - Server must accept authenticated pull operations
   - Repository must be accessible at: `http://localhost:8080/git/test-repo.git`

**Expected Deliverables:**
- Apache configuration file at `/app/apache-git.conf`
- Password file at `/app/.htpasswd`
- Initialized bare repository at `/app/git-repos/test-repo.git`
- Status output at `/app/server-status.json`
- Apache service running and accessible on port 8080
