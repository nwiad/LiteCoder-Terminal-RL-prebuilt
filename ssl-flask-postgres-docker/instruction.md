## SSL-Enabled REST API with Containerized PostgreSQL

Build a secure REST API using Python Flask that connects to a containerized PostgreSQL database, running behind an Nginx reverse proxy with SSL/TLS encryption. All services are orchestrated via Docker Compose.

### Technical Requirements

- Language: Python 3.x with Flask
- Database: PostgreSQL (containerized)
- Reverse Proxy: Nginx with SSL termination
- Orchestration: Docker Compose
- Working directory: /app

### Project Structure

All files must be created under `/app/`. The project must include at minimum:

- `app.py` — Flask application entry point
- `requirements.txt` — Python dependencies
- `Dockerfile` — for the Flask application
- `docker-compose.yml` — orchestrates all services
- `nginx/nginx.conf` — Nginx configuration with SSL termination
- `certs/` — directory containing generated self-signed SSL certificates (`server.crt` and `server.key`)
- `.env` — environment variables for sensitive configuration (DB credentials, secret key, etc.)

### Docker Compose Services

`docker-compose.yml` must define exactly three services:

1. **web** — the Flask application container, must NOT expose port 443 or 80 directly to the host
2. **db** — PostgreSQL container, using the official `postgres` image
3. **nginx** — Nginx reverse proxy container, mapping host port `443` to container port `443`

All three services must be on a shared Docker network defined in the compose file.

### SSL/TLS Certificates

Generate self-signed SSL certificates and place them at:
- `/app/certs/server.crt`
- `/app/certs/server.key`

The certificate must have a validity of at least 365 days.

### Nginx Configuration

The file `/app/nginx/nginx.conf` must:
- Listen on port `443` with SSL enabled
- Reference the SSL certificate and key from the certs directory
- Proxy requests to the Flask `web` service
- Include at least one security header (e.g., `X-Content-Type-Options`, `X-Frame-Options`, or `Strict-Transport-Security`)

### Flask API Endpoints

The Flask app must implement the following JSON REST endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/register` | Register a new user |
| POST | `/api/login` | Authenticate a user |
| GET | `/api/health` | Health check endpoint |

**POST /api/register**
- Request body: `{"username": "<string>", "email": "<string>", "password": "<string>"}`
- Success response (HTTP 201): `{"message": "User registered successfully", "user_id": <int>}`
- If username or email already exists (HTTP 409): `{"error": "User already exists"}`
- If required fields are missing (HTTP 400): `{"error": "Missing required fields"}`

**POST /api/login**
- Request body: `{"username": "<string>", "password": "<string>"}`
- Success response (HTTP 200): `{"message": "Login successful", "token": "<string>"}`
- Invalid credentials (HTTP 401): `{"error": "Invalid credentials"}`

**GET /api/health**
- Success response (HTTP 200): `{"status": "healthy", "database": "connected"}`
- If DB is unreachable (HTTP 503): `{"status": "unhealthy", "database": "disconnected"}`

### Database

- PostgreSQL must store users in a table named `users` with at minimum columns: `id` (serial primary key), `username` (unique), `email` (unique), `password` (hashed, never stored in plaintext).
- Database credentials must be read from environment variables defined in `.env`, not hardcoded in application code.
- The Flask app must use a database connection pool (e.g., via SQLAlchemy with pool configuration or `psycopg2.pool`).

### Security Requirements

- Passwords must be hashed before storage (e.g., using `bcrypt` or `werkzeug.security`).
- The `.env` file must contain at least: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `SECRET_KEY`.
- The Flask app must include rate limiting on `/api/login` (max 5 requests per minute per IP).

### Validation

Running `docker compose config` from `/app/` must succeed without errors, confirming the compose file is valid.
