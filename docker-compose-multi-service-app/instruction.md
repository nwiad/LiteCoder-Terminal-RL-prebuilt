## Build a Multi-Service Web Application with Docker Compose

Set up a multi-service web application using Docker Compose that includes a Python Flask backend, a PostgreSQL database, an Nginx reverse proxy, and Redis for caching. All project files must be created under `/app`.

### Project Structure

```
/app/
├── docker-compose.yml
├── flask_app/
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
├── nginx/
│   └── nginx.conf
└── db/
    └── init.sql
```

### Technical Requirements

- **Language:** Python 3.x (Flask)
- **Services in `docker-compose.yml`** must use exactly these service names:
  - `web` — Flask application
  - `db` — PostgreSQL database
  - `redis` — Redis cache
  - `nginx` — Nginx reverse proxy

### Service Specifications

**1. Flask Application (`web`)**

- Listens on port `5000` inside the container.
- Provides the following JSON API endpoints (all request and response bodies are `application/json`):

| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Register a new user |
| POST | `/login` | Log in and receive a session/token |
| GET | `/profile` | Get the logged-in user's profile |
| GET | `/health` | Health check |

**`POST /register`**
- Request body: `{"username": "<string>", "password": "<string>"}`
- Success response (HTTP 201): `{"message": "User registered successfully"}`
- If the username already exists (HTTP 409): `{"error": "Username already exists"}`

**`POST /login`**
- Request body: `{"username": "<string>", "password": "<string>"}`
- Success response (HTTP 200): `{"message": "Login successful"}` — must also set or return a session/token.
- Invalid credentials (HTTP 401): `{"error": "Invalid credentials"}`

**`GET /profile`**
- Requires a valid session/token (obtained from `/login`).
- Success response (HTTP 200): `{"username": "<string>"}`
- Unauthorized (HTTP 401): `{"error": "Unauthorized"}`

**`GET /health`**
- Returns HTTP 200 with body: `{"status": "healthy"}`

**2. PostgreSQL (`db`)**

- Uses the official `postgres` image.
- Environment variables in docker-compose.yml:
  - `POSTGRES_USER=appuser`
  - `POSTGRES_PASSWORD=apppassword`
  - `POSTGRES_DB=appdb`
- `/app/db/init.sql` must create a `users` table with at least these columns:
  - `id` — primary key (serial/auto-increment)
  - `username` — unique, not null
  - `password` — not null (store hashed passwords)
- The `db` service must expose port `5432` inside the container.

**3. Redis (`redis`)**

- Uses the official `redis` image.
- Exposes port `6379` inside the container.
- The Flask app must use Redis for session management or caching (e.g., caching login sessions or rate limiting).

**4. Nginx (`nginx`)**

- Uses the official `nginx` image.
- Maps host port `80` to container port `80`.
- `/app/nginx/nginx.conf` must configure Nginx as a reverse proxy that forwards HTTP requests to the `web` service on port `5000`.

### Docker Compose Requirements

- `docker-compose.yml` must define all four services (`web`, `db`, `redis`, `nginx`).
- Services must be connected via a custom Docker network named `app-network`.
- The `web` service must declare `depends_on` for both `db` and `redis`.
- The `nginx` service must declare `depends_on` for `web`.
- The `db` service must use a named volume `pgdata` for persistent storage mounted at `/var/lib/postgresql/data`.

### Verification

After running `docker compose up -d` from `/app`, the following must succeed:

1. All four containers are running (`docker compose ps` shows 4 services up).
2. `curl http://localhost/health` returns `{"status": "healthy"}` with HTTP 200 (via Nginx).
3. Registering a user via `curl -X POST http://localhost/register -H "Content-Type: application/json" -d '{"username":"testuser","password":"testpass"}'` returns HTTP 201.
4. Logging in via `curl -X POST http://localhost/login -H "Content-Type: application/json" -d '{"username":"testuser","password":"testpass"}'` returns HTTP 200.
5. Duplicate registration of the same username returns HTTP 409.
