## Nginx Service Recovery and Optimization

Restore a broken Nginx web server to full functionality on Ubuntu 22.04, fix all configuration issues, resolve port conflicts, optimize performance settings, and produce a documented change log.

### Environment

- OS: Ubuntu 22.04 (Docker container)
- Working directory: /app

### Setup (run before starting)

Execute the setup script to create the broken Nginx environment:

```bash
bash /app/setup.sh
```

The setup script will:
1. Install Nginx (if not already installed)
2. Introduce configuration errors into `/etc/nginx/nginx.conf` and `/etc/nginx/sites-enabled/default`
3. Start a dummy process occupying port 80 to simulate a port conflict
4. Leave Nginx in a failed/stopped state

### Requirements

#### 1. Resolve Port Conflicts
- Identify and stop any non-Nginx process occupying port 80.
- After resolution, port 80 must be free for Nginx to bind to.

#### 2. Fix Nginx Configuration
- Fix all syntax errors in `/etc/nginx/nginx.conf` and any files under `/etc/nginx/sites-enabled/`.
- `nginx -t` must pass with "syntax is ok" and "test is successful".
- Nginx must serve content on port 80. A request to `http://localhost/` must return HTTP 200.

#### 3. Configure a Virtual Host for API
- Create or fix the server block so that requests to `http://localhost/api/health` return HTTP 200 with a JSON response body: `{"status": "ok"}`.
- This can be achieved via a `location /api/health` block that returns the JSON directly using an Nginx directive (no upstream/proxy required).

#### 4. Optimize Nginx Performance
Apply the following performance tuning in `/etc/nginx/nginx.conf`:
- `worker_processes` set to `auto`
- `worker_connections` set to at least `1024`
- `gzip` enabled (`gzip on;`)
- `keepalive_timeout` set to a value between 15 and 65 (inclusive)
- `server_tokens` set to `off`

#### 5. Create Configuration Backup
- Copy the working `/etc/nginx/nginx.conf` to `/app/nginx.conf.backup`.
- Copy the working default site config to `/app/default.backup`.

#### 6. Document Changes
Write a change log file at `/app/changes.txt` that contains:
- At least 3 lines, each describing a specific change made (one change per line).
- The file must be non-empty plain text.

### Verification Criteria

After all tasks are completed, the following must hold true:
1. `nginx -t` exits with code 0.
2. Nginx process is running (`pgrep nginx` returns at least one PID).
3. `curl -s -o /dev/null -w "%{http_code}" http://localhost/` returns `200`.
4. `curl -s http://localhost/api/health` returns valid JSON containing `"status": "ok"`.
5. `/etc/nginx/nginx.conf` contains the required performance directives.
6. `/app/nginx.conf.backup` and `/app/default.backup` exist and are non-empty.
7. `/app/changes.txt` exists, is non-empty, and has at least 3 lines.
8. No non-Nginx process is listening on port 80.
