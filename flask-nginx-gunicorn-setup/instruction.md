## Local Development Server Setup with Python, Nginx, and Gunicorn

Set up a local development environment where a Python Flask application is served by Gunicorn and reverse-proxied by Nginx, accessible via the custom domain `myapp.local`.

### Technical Requirements

- **Language/Framework:** Python 3, Flask
- **Application Server:** Gunicorn
- **Reverse Proxy:** Nginx
- **Domain:** `myapp.local` resolving to `127.0.0.1`

### 1. Flask Application

- Create the Flask application at `/app/myapp/app.py`.
- The app must expose a `GET /hello` endpoint that returns a JSON response with `Content-Type: application/json`:
  ```json
  {"message": "Hello from Flask!"}
  ```
  with HTTP status code `200`.
- The Flask app must include a `GET /health` endpoint that returns:
  ```json
  {"status": "healthy"}
  ```
  with HTTP status code `200`.

### 2. Gunicorn Configuration

- Create a Gunicorn configuration file at `/app/myapp/gunicorn_config.py`.
- Gunicorn must bind to `127.0.0.1:8000`.
- Gunicorn must use `2` worker processes.
- Create a systemd service unit file at `/etc/systemd/system/myapp-gunicorn.service` that:
  - Runs Gunicorn serving the Flask app from `/app/myapp/`.
  - Uses the Gunicorn config file `/app/myapp/gunicorn_config.py`.
  - Starts after `network.target`.
- Start and enable the `myapp-gunicorn` service so Gunicorn is running and listening on port `8000`.

### 3. Nginx Configuration

- Create an Nginx server block configuration file at `/etc/nginx/sites-available/myapp.local`.
- Symlink it to `/etc/nginx/sites-enabled/myapp.local`.
- The Nginx server block must:
  - Listen on port `80`.
  - Use `server_name myapp.local`.
  - Proxy requests on location `/` to `http://127.0.0.1:8000`.
  - Set the headers `X-Forwarded-For`, `X-Forwarded-Proto`, and `Host` when proxying.
  - Serve static files from `/var/www/myapp/static/` at the URL path `/static/`.
- Nginx must be running with the configuration loaded (no configuration errors).

### 4. Host Resolution

- Add an entry in `/etc/hosts` so that `myapp.local` resolves to `127.0.0.1`.

### 5. Static Files

- Create the directory `/var/www/myapp/static/`.
- Place a file at `/var/www/myapp/static/test.html` with the following exact content:
  ```html
  <h1>Static file served by Nginx</h1>
  ```

### 6. Verification

When the full setup is complete:

- `curl http://myapp.local/hello` must return `{"message": "Hello from Flask!"}` with HTTP status `200`.
- `curl http://myapp.local/health` must return `{"status": "healthy"}` with HTTP status `200`.
- `curl http://myapp.local/static/test.html` must return the content of `test.html` with HTTP status `200`.
- Gunicorn must be running and listening on `127.0.0.1:8000`.
- Nginx must be running and listening on port `80`.
