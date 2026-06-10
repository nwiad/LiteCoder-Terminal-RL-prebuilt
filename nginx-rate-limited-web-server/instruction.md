## Build a Dynamic Nginx Web Server with Rate Limiting

Set up an Nginx web server that serves two web applications on different ports with rate limiting enabled to protect against abuse.

### Technical Requirements

- **Platform:** Ubuntu (use apt for package management)
- **Web Server:** Nginx
- **Ports:** 8080 (API service), 9090 (Admin dashboard)
- Nginx must be installed and running after setup is complete.

### Configuration

#### Port 8080 — Public API Service

- Serve static HTML from `/var/www/api/`.
- Create `/var/www/api/index.html` containing the text `Welcome to the API Service`.
- Apply rate limiting using a shared memory zone named `api_limit` with a rate of **10 requests per second** and a **burst of 20** (with nodelay).
- When the rate limit is exceeded, Nginx should return HTTP **429**.

#### Port 9090 — Admin Dashboard

- Serve static HTML from `/var/www/admin/`.
- Create `/var/www/admin/index.html` containing the text `Welcome to the Admin Dashboard`.
- Apply rate limiting using a shared memory zone named `admin_limit` with a rate of **2 requests per second** and a **burst of 5** (with nodelay).
- When the rate limit is exceeded, Nginx should return HTTP **429**.

#### Rate Limit Zones

Define the two `limit_req_zone` directives in the `http` block of the Nginx configuration:

- `api_limit`: keyed by `$binary_remote_addr`, size `10m`, rate `10r/s`
- `admin_limit`: keyed by `$binary_remote_addr`, size `10m`, rate `2r/s`

#### Logging

- API service access log: `/var/log/nginx/api_access.log`
- Admin dashboard access log: `/var/log/nginx/admin_access.log`

### Verification Criteria

- `curl -s http://localhost:8080/` returns HTTP 200 with body containing `Welcome to the API Service`.
- `curl -s http://localhost:9090/` returns HTTP 200 with body containing `Welcome to the Admin Dashboard`.
- Nginx configuration passes `nginx -t` syntax check.
- Both rate limit zones (`api_limit`, `admin_limit`) are defined in the Nginx configuration.
- Sending a burst of rapid requests beyond the allowed burst size returns HTTP 429 responses.
