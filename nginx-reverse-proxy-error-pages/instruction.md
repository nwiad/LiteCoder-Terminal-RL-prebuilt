Set up an Nginx reverse proxy that forwards requests to two backend services and serves custom HTML error pages for specific HTTP error codes (404, 500, 502, 503).

## Technical Requirements

- OS packages: Nginx, Python 3 with Flask
- Backend services: two Python Flask apps (product service on port 3000, order service on port 4000)
- Nginx listens on port 80

## Backend Services

Create two minimal Flask applications:

1. **Product service** (`/app/product_service.py`) — runs on port 3000
   - `GET /products` returns JSON `{"service": "product", "status": "ok"}` with HTTP 200
   - `GET /products/error` returns HTTP 500 with body `{"error": "internal"}` (this simulates a backend failure)

2. **Order service** (`/app/order_service.py`) — runs on port 4000
   - `GET /orders` returns JSON `{"service": "order", "status": "ok"}` with HTTP 200
   - `GET /orders/error` returns HTTP 500 with body `{"error": "internal"}`

Both services should run as background processes. Create a startup script at `/app/start_services.sh` that launches both Flask apps in the background and writes their PIDs to `/app/product_service.pid` and `/app/order_service.pid` respectively. The script must be executable.

## Nginx Configuration

Place the Nginx site configuration at `/etc/nginx/conf.d/reverse_proxy.conf`. Requirements:

- Define two upstream blocks named `product_backend` (pointing to `127.0.0.1:3000`) and `order_backend` (pointing to `127.0.0.1:4000`).
- Proxy routing rules:
  - Requests to `/products` and `/products/.*` are proxied to `product_backend`
  - Requests to `/orders` and `/orders/.*` are proxied to `order_backend`
- Set the following proxy headers on all proxied requests:
  - `X-Real-IP` set to the client's remote address
  - `X-Forwarded-For` set to the proxy add forwarded-for value
  - `Host` set to the incoming host header
- Enable custom error page handling so that when a backend returns an error, Nginx intercepts it and serves the custom error page instead.

## Custom Error Pages

Create four custom HTML error pages under `/app/error_pages/`:

| File | HTTP Code | Required content |
|------|-----------|-----------------|
| `/app/error_pages/404.html` | 404 | Must contain the exact text `Error 404` and `Page Not Found` |
| `/app/error_pages/500.html` | 500 | Must contain the exact text `Error 500` and `Internal Server Error` |
| `/app/error_pages/502.html` | 502 | Must contain the exact text `Error 502` and `Bad Gateway` |
| `/app/error_pages/503.html` | 503 | Must contain the exact text `Error 503` and `Service Unavailable` |

Each file must be a valid HTML document (containing `<html>` and `<body>` tags). The Nginx configuration must map these error codes to the corresponding files and serve them with the correct HTTP status code.

## Verification

After setup, the following must hold (with both backend services running and Nginx active):

1. `curl -s http://localhost/products` returns JSON containing `"service": "product"` with HTTP 200.
2. `curl -s http://localhost/orders` returns JSON containing `"service": "order"` with HTTP 200.
3. `curl -s -o /dev/null -w "%{http_code}" http://localhost/nonexistent` returns HTTP 404, and the response body contains `Error 404`.
4. When a backend is stopped, requests to its path return the custom 502 error page containing `Error 502`.
5. The Nginx configuration passes `nginx -t` without errors.
