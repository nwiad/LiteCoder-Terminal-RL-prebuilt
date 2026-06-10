## Reverse Proxy with Rate Limiting & Caching

Configure an Nginx reverse proxy that routes traffic to two backend services, implements per-IP rate limiting, and caches responses from the marketing site.

### Technical Requirements

- **Platform:** Linux with Nginx installed and running
- **Language for mock backends:** Python 3 (using only the standard library)

### Backend Services

Create two mock backend services:

1. **Mock API** (`/app/mock_api.py`): Listens on `0.0.0.0:8080`. For any request, returns HTTP 200 with `Content-Type: application/json` and body:
   ```json
   {"service": "api", "status": "ok"}
   ```

2. **Mock Site** (`/app/mock_site.py`): Listens on `0.0.0.0:8081`. For any request, returns HTTP 200 with `Content-Type: text/html` and body:
   ```html
   <html><body><h1>Welcome</h1></body></html>
   ```

### Nginx Configuration

Write the Nginx configuration to `/etc/nginx/sites-available/reverse-proxy` and symlink it to `/etc/nginx/sites-enabled/reverse-proxy`. Remove the default site from `/etc/nginx/sites-enabled/` if present.

Nginx must listen on port **80** and implement the following:

#### Routing

- Requests matching `/api/` (and any subpath) are proxied to `http://127.0.0.1:8080`.
- All other requests (`/`) are proxied to `http://127.0.0.1:8081`.
- Both proxy locations must set the headers `X-Real-IP`, `X-Forwarded-For`, and `Host` to the appropriate values when forwarding to backends.

#### Rate Limiting

Define two `limit_req_zone` directives keyed on `$binary_remote_addr`:

- **API zone** (named `api_limit`): rate of **10r/s**, shared memory size 10m. Apply to the `/api/` location using `burst=20 nodelay`.
- **Site zone** (named `site_limit`): rate of **30r/m**, shared memory size 10m. Apply to the `/` location using `burst=10 nodelay`.

When a request is rate-limited, Nginx must return HTTP **429**.

#### Caching

- Define a cache path at `/var/cache/nginx/site_cache` with `levels=1:2`, `keys_zone=site_cache:10m`, `max_size=100m`, and `inactive=10m`.
- Cache key: `$scheme$request_method$host$request_uri`.
- Enable caching only for the `/` location (marketing site). Cache valid 200 responses for **5 minutes**.
- Do **not** cache responses for the `/api/` location.

#### Observability Headers

- Add an `X-Cache-Status` response header to the `/` location, set to the value of `$upstream_cache_status`.
- Add an `X-Rate-Limit` response header with value `"api=10r/s"` on the `/api/` location and `"site=30r/m"` on the `/` location.

### Startup Script

Create `/app/start.sh` (executable) that:

1. Starts both mock backend services in the background.
2. Starts (or reloads) Nginx.
3. Waits briefly for services to be ready.

The script must be runnable via `bash /app/start.sh`.

### Verification

After running `start.sh`, the following must hold:

- `curl -s http://localhost/api/test` returns the mock API JSON response.
- `curl -s http://localhost/` returns the mock site HTML response.
- `curl -sI http://localhost/` includes the `X-Cache-Status` header (value `MISS` on first request, `HIT` on subsequent).
- `curl -sI http://localhost/api/test` includes the `X-Rate-Limit` header.
- Rapid repeated requests to `/api/` (exceeding 10r/s + burst) eventually receive HTTP 429.
