## Build a Containerized Web Application with Advanced Features

Create a containerized web application stack using Docker Compose with PostgreSQL, Express.js REST API, Redis cache, and Socket.IO real-time support. All source files should be created under `/app`.

### Technical Requirements

- Runtime: Node.js (Express.js for the API)
- Database: PostgreSQL 15+
- Cache: Redis 7+
- Real-time: Socket.IO
- Containerization: Docker and Docker Compose

### Docker Compose

Create `/app/docker-compose.yml` with the following services:

- `api` — Express.js application, exposed on host port `3000`, depends on `db` and `redis`
- `db` — PostgreSQL database, exposed on host port `5432`
- `redis` — Redis cache, exposed on host port `6379`

All three services must be on a shared Docker network named `app-network`.

### Environment Variables

The `api` service must accept these environment variables (with these exact defaults in docker-compose.yml):

| Variable | Default Value |
|---|---|
| `PORT` | `3000` |
| `DB_HOST` | `db` |
| `DB_PORT` | `5432` |
| `DB_USER` | `appuser` |
| `DB_PASSWORD` | `apppassword` |
| `DB_NAME` | `appdb` |
| `REDIS_HOST` | `redis` |
| `REDIS_PORT` | `6379` |

The `db` service must use `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` environment variables matching the API defaults above.

### Database Schema

PostgreSQL must be initialized with a table named `items`:

| Column | Type | Constraints |
|---|---|---|
| `id` | SERIAL | PRIMARY KEY |
| `name` | VARCHAR(255) | NOT NULL |
| `description` | TEXT | nullable |
| `created_at` | TIMESTAMP | DEFAULT NOW() |
| `updated_at` | TIMESTAMP | DEFAULT NOW() |

### REST API Endpoints

The Express.js API must expose the following endpoints on port 3000:

**Health Check:**
- `GET /health` — Returns JSON `{ "status": "ok", "database": "connected", "redis": "connected" }` with HTTP 200 when all services are healthy.

**CRUD for Items:**

- `GET /api/items` — Returns all items as JSON array. Response: `{ "data": [ ... ] }`
- `GET /api/items/:id` — Returns a single item by id. Response: `{ "data": { "id": 1, "name": "...", "description": "...", "created_at": "...", "updated_at": "..." } }`. Returns HTTP 404 with `{ "error": "Item not found" }` if not found.
- `POST /api/items` — Creates a new item. Request body: `{ "name": "string", "description": "string" }`. Returns HTTP 201 with `{ "data": { ... } }` containing the created item. Returns HTTP 400 with `{ "error": "Name is required" }` if `name` is missing or empty.
- `PUT /api/items/:id` — Updates an existing item. Request body: `{ "name": "string", "description": "string" }`. Returns HTTP 200 with `{ "data": { ... } }`. Returns HTTP 404 if not found.
- `DELETE /api/items/:id` — Deletes an item. Returns HTTP 200 with `{ "message": "Item deleted" }`. Returns HTTP 404 if not found.

All endpoints must accept and return `application/json`.

### Redis Caching

- `GET /api/items` results must be cached in Redis with the key `items:all` and a TTL of 60 seconds.
- `GET /api/items/:id` results must be cached in Redis with the key `items:<id>` and a TTL of 60 seconds.
- Any `POST`, `PUT`, or `DELETE` operation must invalidate the relevant cache keys (at minimum, `items:all` must be cleared on any write operation).

### Socket.IO Real-Time

The API server must serve a Socket.IO endpoint on the same port (3000). It must:

- Emit an `itemCreated` event to all connected clients when a new item is created via `POST /api/items`. The event payload must be the created item object.
- Emit an `itemUpdated` event to all connected clients when an item is updated via `PUT /api/items/:id`. The event payload must be the updated item object.
- Emit an `itemDeleted` event to all connected clients when an item is deleted via `DELETE /api/items/:id`. The event payload must be `{ "id": <deleted_id> }`.

### API Dockerfile

Create `/app/Dockerfile` for the API service. It must:

- Use a Node.js base image
- Set the working directory to `/usr/src/app`
- Copy `package.json` and install dependencies
- Copy application source code
- Expose port 3000
- Define a start command

### Project Structure

At minimum, the following files must exist:

```
/app/docker-compose.yml
/app/Dockerfile
/app/package.json
/app/init.sql          (PostgreSQL initialization script for the items table)
```

The Express.js application entry point should be referenced correctly in `package.json` (e.g., `server.js` or `src/index.js`).
