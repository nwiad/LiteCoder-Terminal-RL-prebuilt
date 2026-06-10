Deploy a production-ready Flask application served by Nginx with PostgreSQL backend on Ubuntu 24.04. The setup must include a working Flask application accessible through Nginx reverse proxy, with proper systemd service configuration and firewall rules.

## Technical Requirements

- **Platform**: Ubuntu 24.04
- **Web Server**: Nginx (reverse proxy)
- **Application Server**: Gunicorn (WSGI server)
- **Application Framework**: Flask (Python 3.x)
- **Database**: PostgreSQL
- **Process Manager**: systemd
- **Firewall**: UFW

## Implementation Requirements

1. **PostgreSQL Setup**
   - Create database named `flaskapp_db`
   - Create database user `flaskapp_user` with password `securepass123`
   - Grant all privileges on `flaskapp_db` to `flaskapp_user`

2. **Flask Application**
   - Location: `/app/flask_app/`
   - Virtual environment: `/app/flask_app/venv/`
   - Main application file: `/app/flask_app/app.py`
   - Requirements file: `/app/flask_app/requirements.txt`
   - Application must:
     - Connect to PostgreSQL database
     - Create a `users` table with columns: `id` (serial primary key), `name` (varchar), `email` (varchar)
     - Provide route `/` that returns JSON: `{"status": "success", "message": "Flask app is running"}`
     - Provide route `/db-check` that tests database connectivity and returns JSON: `{"database": "connected"}` on success
     - Provide route `/users` that returns all users from database as JSON array

3. **Gunicorn Configuration**
   - Bind to `127.0.0.1:8000`
   - Use 3 worker processes
   - Socket file (if using unix socket): `/app/flask_app/flask_app.sock`

4. **Systemd Service**
   - Service name: `flaskapp`
   - Service file location: `/etc/systemd/system/flaskapp.service`
   - Must start on boot (enabled)
   - Must restart on failure

5. **Nginx Configuration**
   - Server block file: `/etc/nginx/sites-available/flaskapp`
   - Must be enabled via symlink in `/etc/nginx/sites-enabled/`
   - Listen on port 80
   - Server name: `localhost` or `_` (default)
   - Proxy all requests to Gunicorn backend
   - Include proper proxy headers (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto)

6. **Firewall Configuration**
   - Enable UFW
   - Allow SSH (port 22)
   - Allow HTTP (port 80)
   - Deny all other incoming traffic by default

## Verification Requirements

After setup completion, the following must be true:
- Nginx service is active and running
- PostgreSQL service is active and running
- Flask systemd service is active and running
- HTTP request to `http://localhost/` returns the Flask app JSON response
- HTTP request to `http://localhost/db-check` confirms database connectivity
- UFW is active with correct rules applied
