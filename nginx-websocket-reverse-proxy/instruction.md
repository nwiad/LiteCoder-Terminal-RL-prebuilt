## Advanced NGINX Reverse Proxy with WebSocket Support

Set up an NGINX reverse proxy configuration that handles a real-time collaborative application with WebSocket support, rate limiting, custom security headers, and comprehensive logging.

### Technical Requirements

- NGINX must be installed and running
- All configuration files go under `/etc/nginx/`
- The main site configuration must be written to `/etc/nginx/sites-available/app.conf` and symlinked to `/etc/nginx/sites-enabled/app.conf`
- A backup of the original default NGINX config must be saved to `/app/nginx_default.conf.bak`
- After all configuration is complete, generate a report file at `/app/report.txt` summarizing the setup (see below)

### Upstream Backend Services

Configure three upstream backends:

| Name           | Target             | Purpose                  |
|----------------|--------------------|--------------------------|
| main_app       | 127.0.0.1:3000     | Main web application     |
| websocket_app  | 127.0.0.1:3001     | WebSocket connections    |
| api_app        | 127.0.0.1:3002     | API services             |

### Reverse Proxy Configuration

The server must listen on port `80` with `server_name` set to `localhost`.

Configure the following `location` blocks:

1. **`/`** — proxy to `main_app` upstream
2. **`/ws/`** — proxy to `websocket_app` upstream, with WebSocket upgrade support:
   - `proxy_http_version 1.1;`
   - `proxy_set_header Upgrade $http_upgrade;`
   - `proxy_set_header Connection "upgrade";`
   - WebSocket-specific timeouts: `proxy_read_timeout 86400s;` and `proxy_send_timeout 86400s;`
3. **`/api/`** — proxy to `api_app` upstream

All three location blocks must include:
- `proxy_set_header Host $host;`
- `proxy_set_header X-Real-IP $remote_addr;`
- `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`
- `proxy_set_header X-Forwarded-Proto $scheme;`

### Rate Limiting

- Define a rate-limiting zone in the `http` block using `limit_req_zone`:
  - Key: `$binary_remote_addr`
  - Zone name: `app_limit`
  - Zone size: `10m`
  - Rate: `10r/s`
- Apply `limit_req zone=app_limit burst=20 nodelay;` inside the `/api/` location block

### Custom Security Headers

Add the following headers in the `server` block (using `add_header`):

- `X-Frame-Options "SAMEORIGIN"`
- `X-Content-Type-Options "nosniff"`
- `X-XSS-Protection "1; mode=block"`
- `Access-Control-Allow-Origin "*"`
- `Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"`
- `Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization"`

### Custom Logging

- Define a custom log format named `detailed` in the `http` block. It must include at minimum: `$remote_addr`, `$request`, `$status`, `$body_bytes_sent`, `$http_user_agent`, and `$request_time`.
- The server block must use:
  - `access_log /var/log/nginx/app_access.log detailed;`
  - `error_log /var/log/nginx/app_error.log warn;`

### NGINX Validation

- The final NGINX configuration must pass `nginx -t` syntax validation without errors.

### Report File (`/app/report.txt`)

Generate a plain-text report containing:
- Line 1: `NGINX Version: <output of nginx -v>`
- Line 2: `Config Test: pass` (only if `nginx -t` succeeds)
- Line 3: `NGINX Status: running` (only if NGINX service is active)
- Line 4: `Config File: /etc/nginx/sites-available/app.conf`
- Line 5: `Backup File: /app/nginx_default.conf.bak`
