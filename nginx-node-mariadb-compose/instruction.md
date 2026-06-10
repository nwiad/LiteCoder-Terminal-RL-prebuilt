## Multi-Container Web Stack with Nginx & Node.js

Deploy a containerized web stack under `/app` where Nginx reverse-proxies to two Node.js API services backed by a shared MariaDB database, all orchestrated via Docker Compose.

### Technical Requirements

- Language/Runtime: Node.js (any LTS version ≥ 18)
- Database: MariaDB (latest or 10.x/11.x)
- Reverse Proxy: Nginx (latest stable)
- Orchestration: Docker Compose (v3.x or later compose file format)
- Working directory: `/app`

### Required File Structure

```
/app/
├── docker-compose.yml
├── nginx.conf
├── package.json
├── Dockerfile
├── api.js        # Service A source
└── api-b.js      # Service B source
```

### Service Specifications

**Service A (`api.js`)**
- Listens on `0.0.0.0:3000`
- `GET /` returns HTTP 200 with `Content-Type: application/json` and body:
  ```json
  {"service":"A"}
  ```
- Opens a MariaDB connection on startup using environment variables (see MariaDB section below).

**Service B (`api-b.js`)**
- Identical behavior to Service A, except `GET /` returns:
  ```json
  {"service":"B"}
  ```

**Dockerfile**
- A single `Dockerfile` that can build both Service A and Service B images.
- Accept a build argument (e.g., `API_FILE`) to select which source file (`api.js` or `api-b.js`) is used inside the container.
- The resulting container should run the selected API on port 3000.

**MariaDB**
- Use the official `mariadb` image.
- Environment variables for the database:
  - `MYSQL_ROOT_PASSWORD`: `rootpass`
  - `MYSQL_DATABASE`: `appdb`
  - `MYSQL_USER`: `appuser`
  - `MYSQL_PASSWORD`: `apppass`
- Persist data to a bind-mount at `./db` on the host.

**Nginx**
- Provide `nginx.conf` that defines an upstream block containing `api-a:3000` and `api-b:3000`.
- Use round-robin load balancing (the default).
- The Nginx service must be accessible on host port `80`.

### Docker Compose Requirements

The `docker-compose.yml` must define exactly four services:

| Service Name | Image / Build | Exposed Port (host) |
|---|---|---|
| `db` | `mariadb` (official) | none required |
| `api-a` | Built from `Dockerfile` with build arg selecting `api.js` | none required on host |
| `api-b` | Built from `Dockerfile` with build arg selecting `api-b.js` | none required on host |
| `nginx` | `nginx` (official) | `80:80` |

- `api-a` and `api-b` must depend on `db`.
- `nginx` must depend on `api-a` and `api-b`.
- The Nginx service must include a health check that runs every 5 seconds.

### Verification Criteria

1. `docker compose up -d` (or `docker-compose up -d`) from `/app` starts all four containers successfully.
2. All four containers reach a running state.
3. HTTP requests to `http://localhost:80/` return valid JSON with either `{"service":"A"}` or `{"service":"B"}`.
4. Repeated requests to `http://localhost:80/` distribute across both services (round-robin).
5. The stack is restartable: `docker compose down && docker compose up -d` works cleanly.
