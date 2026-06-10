## Build a Custom Nginx Reverse Proxy from Source

Compile Nginx 1.26.0 from source with the echo-nginx-module as a dynamic module, install everything under `/opt/nginx/`, and configure it as a reverse proxy on port 8080.

### Requirements

**System user:**
- Create a dedicated system user named `nginx` (no login shell, no home directory required) to run the Nginx worker processes.

**Build & install:**
- Download and compile Nginx 1.26.0 stable source.
- Download and compile the `echo-nginx-module` (from https://github.com/openresty/echo-nginx-module) as a dynamic module (shared object).
- Install prefix: `/opt/nginx/`
- After installation the following paths must exist:
  - `/opt/nginx/sbin/nginx` — the Nginx binary
  - `/opt/nginx/modules/ngx_http_echo_module.so` — the dynamic echo module
  - `/opt/nginx/conf/nginx.conf` — the configuration file
  - `/opt/nginx/logs/` — the logs directory

**Configuration (`/opt/nginx/conf/nginx.conf`):**

1. Load the echo module dynamically via `load_module`.
2. Set `worker_processes` to `1`.
3. Set the `user` directive to `nginx`.
4. The HTTP server must listen on port `8080`.
5. Define a location block `= /echo` that uses the echo module to return the plain-text body `echo_works`.
6. Define a location block `/ ` that proxies requests to `http://httpbin.org/anything`.
7. The proxy location must add a response header `X-Upstream-Time` whose value represents the upstream response time in milliseconds (use the Nginx variable `$upstream_response_time` converted/formatted to milliseconds).
8. The `pid` directive must point to `/opt/nginx/logs/nginx.pid`.

**Runtime:**
- The Nginx master process must be startable and the server must respond to HTTP requests on port 8080.
- `GET /echo` must return an HTTP 200 response with body containing `echo_works`.
- `GET /anything` (or any path other than `/echo`) must proxy to httpbin.org and the response must include the `X-Upstream-Time` header.

### Verification

After completing the setup, start Nginx:

```
/opt/nginx/sbin/nginx
```

The server should be running and listening on port 8080. The PID file should exist at `/opt/nginx/logs/nginx.pid`.
