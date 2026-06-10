## Configuring a Multi-Service Production Environment

Set up a secure, containerized environment that hosts a Node.js application, a PostgreSQL database, and nginx as a reverse proxy, all orchestrated with docker-compose and accessible through HTTPS.

### Technical Requirements

- Platform: Ubuntu with Docker and docker-compose installed
- Working directory: `/app`
- Source repo: Clone `https://github.com/alexbrault/mock-express-api.git` into `/app/mock-express-api/`

### File Structure

All configuration files must be created under `/app/` with the following layout:

- `/app/Dockerfile` — Production Dockerfile for the Node.js application
- `/app/docker-compose.yml` — Orchestration file for all three services
- `/app/nginx.conf` — Nginx configuration for reverse proxy with SSL termination
- `/app/.env` — Environment variables file (must contain `POSTGRES_PASSWORD` set to a randomly generated value of at least 16 characters)
- `/app/init.sql` — SQL initialization script for PostgreSQL
- `/app/deployment-notes.md` — Documentation of the final environment

### Service Specifications

The `docker-compose.yml` must define exactly three services with these names:

1. **node-app** — The Node.js Express API
   - Built from `/app/Dockerfile`
   - Must run as a non-root user inside the container
   - The Dockerfile must use a multi-stage build
   - The Dockerfile must include a HEALTHCHECK instruction
   - Must have resource limits: `cpus: '0.5'` and `memory: 256m` (under `deploy.resources.limits`)
   - Must have a restart policy set to `unless-stopped` or `always`
   - Must expose the application on port 3000 internally (not published to host directly)

2. **postgres-db** — PostgreSQL database
   - Must use an official `postgres` image
   - Must read credentials from the `/app/.env` file
   - Must mount `/app/init.sql` to the container's docker-entrypoint-initdb.d directory so it runs on first startup
   - Must have a restart policy
   - Must use a named volume for data persistence

3. **nginx-proxy** — Nginx reverse proxy
   - Must use an official `nginx` image or build from one
   - Must publish port 443 on the host mapped to 443 in the container
   - Must mount or include the nginx configuration and SSL certificates
   - Must have a restart policy

### Networking

- The docker-compose file must define at least one custom network
- Services must communicate over the custom network(s), not the default bridge

### SSL / TLS

- Generate a self-signed SSL certificate and key
- The certificate subject must use: `C=US, ST=CA, L=SF, O=Example, CN=localhost`
- Nginx must be configured to listen on port 443 with SSL using these certificate files
- Nginx must proxy HTTPS requests to the node-app service on port 3000

### Nginx Configuration (`/app/nginx.conf`)

- Must contain an `upstream` or `proxy_pass` directive pointing to `node-app:3000`
- Must configure `ssl_certificate` and `ssl_certificate_key` directives
- Must listen on port 443 with SSL enabled

### Database Initialization (`/app/init.sql`)

- Must create a table named `items` with at least the following columns:
  - `id` — integer, primary key
  - `name` — text/varchar, not null
- The SQL must use `CREATE TABLE` syntax

### Logging

- At least one service in docker-compose must specify a logging driver configuration (e.g., `json-file` with `max-size` and `max-file` options)

### Deployment Notes (`/app/deployment-notes.md`)

This markdown file must document:
- All exposed/published ports
- All custom networks defined
- All named volumes defined
- All environment variables used (names only, not secret values)

### Verification

After setup, the full stack should start successfully with `docker-compose up -d` from `/app/`, all three containers should reach healthy/running state, and `https://localhost/items` should return a valid response (accepting the self-signed certificate).
