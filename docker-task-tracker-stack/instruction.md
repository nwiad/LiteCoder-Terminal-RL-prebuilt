## Full-Stack Containerized Task Tracker with Docker Networking

Design, build, and deploy a containerized "Task Tracker" web stack (PostgreSQL + Express + React + Nginx reverse proxy) on a custom Docker bridge network. All project source code, configurations, and a `docker-compose.yml` must be committed to a local Git repository.

### Technical Requirements

- **Language/Runtime:** Node.js (Express for API, React for frontend), PostgreSQL 15
- **Containerization:** Docker and Docker Compose
- **Reverse Proxy:** Nginx
- **Project root:** `/app/task-tracker/`
- **Git repo:** Initialize a Git repository at `/app/task-tracker/` with a `main` branch containing all source, configs, and tests.

### Docker Network

- Create a custom Docker bridge network named `tasknet`.
- Subnet: `172.20.0.0/16`, Gateway: `172.20.0.1`.
- All containers must be attached to `tasknet`.

### PostgreSQL Container

- Image: PostgreSQL 15
- Container name: `tasknet-postgres`
- Database name: `taskdb`
- Database user: `taskuser`, password: `taskpass`
- Use a named Docker volume `task_pgdata` mounted to the PostgreSQL data directory.
- Port 5432 must NOT be published to the host (internal only on `tasknet`).

### Express API Container

- Container name: `tasknet-api`
- The API source code lives in `/app/task-tracker/api/`.
- Connects to PostgreSQL on `tasknet` using the internal hostname `tasknet-postgres`.
- The API listens on port `4000` inside the container.
- Implements a `tasks` table with columns:
  - `id` — auto-incrementing integer primary key
  - `title` — text, required
  - `description` — text, optional (default empty string)
  - `status` — text, one of `todo`, `in-progress`, `done` (default `todo`)
  - `created_at` — timestamp, auto-set on creation

#### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tasks` | Return all tasks as a JSON array |
| POST | `/api/tasks` | Create a task. Body: `{"title": "...", "description": "...", "status": "..."}`. Returns the created task as JSON with `id` and `created_at`. |
| GET | `/api/tasks/:id` | Return a single task by id as JSON. Return 404 JSON `{"error": "Task not found"}` if not found. |
| PUT | `/api/tasks/:id` | Update a task by id. Body may contain any subset of `title`, `description`, `status`. Returns the updated task as JSON. Return 404 if not found. |
| DELETE | `/api/tasks/:id` | Delete a task by id. Return `{"message": "Task deleted"}` on success. Return 404 if not found. |

All success responses use HTTP 200 (or 201 for POST creation). All JSON responses must have `Content-Type: application/json`.

### React Frontend Container

- Container name: `tasknet-frontend`
- Source code in `/app/task-tracker/frontend/`.
- Serves the built React app (e.g., via a static file server or `serve`) on port `3000` inside the container.
- The UI must allow creating, viewing, and updating task status. Minimal styling is acceptable.

### Nginx Reverse Proxy Container

- Container name: `tasknet-nginx`
- Configuration file at `/app/task-tracker/nginx/default.conf`.
- Publishes port `80` on the host.
- Proxy rules:
  - Requests to `/api/*` are proxied to `tasknet-api:4000`.
  - All other requests are proxied to `tasknet-frontend:3000`.

### Docker Compose

- File: `/app/task-tracker/docker-compose.yml`
- Must define exactly four services: `postgres`, `api`, `frontend`, `nginx`.
- Each service must specify `container_name` matching the names above.
- All services must be on the `tasknet` network (defined as an external network or created within compose with the correct subnet/gateway).
- The `postgres` service must use the named volume `task_pgdata`.
- Running `docker-compose up -d` from `/app/task-tracker/` must bring up the entire stack.

### Integration Tests

- Test file: `/app/task-tracker/tests/api.test.js` (or `.ts`)
- At least 3 integration tests covering:
  1. Creating a task via POST and verifying the response contains `id` and `title`.
  2. Fetching all tasks via GET and verifying the response is an array.
  3. Deleting a task via DELETE and verifying a subsequent GET for that task returns 404.
- Tests should target `http://localhost/api/tasks` (through the nginx proxy on port 80).

### Final State

After completion, the full stack must be running and accessible:
- `curl http://localhost/api/tasks` returns a JSON array (HTTP 200).
- `curl -X POST http://localhost/api/tasks -H "Content-Type: application/json" -d '{"title":"Test Task"}'` returns a JSON object with an `id` field (HTTP 201).
- The Git repo at `/app/task-tracker/` has at least one commit on the `main` branch containing all project files.
