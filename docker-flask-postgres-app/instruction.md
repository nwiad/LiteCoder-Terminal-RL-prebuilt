Build and deploy a multi-tier web application using Docker containers with NGINX reverse proxy, Flask REST API backend, and PostgreSQL database, orchestrated with Docker Compose.

## Technical Requirements

- Docker and Docker Compose
- Python 3.x with Flask
- PostgreSQL 13 or higher
- NGINX
- All services must run in separate containers
- Services must communicate through a custom Docker network

## Application Structure

Create the following directory structure in /app:
```
/app
├── docker-compose.yml
├── nginx/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── html/
│       └── index.html
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
└── database/
    └── init.sql
```

## Component Specifications

### 1. PostgreSQL Database
- Container name: `postgres_db`
- Database name: `appdb`
- User: `appuser`
- Password: `apppass`
- Initialize with a `users` table containing columns: `id` (serial primary key), `name` (varchar), `email` (varchar)
- Insert at least 2 sample users during initialization
- Expose port 5432 internally (not to host)

### 2. Flask Backend API
- Container name: `flask_backend`
- Must connect to PostgreSQL database
- Implement the following REST API endpoints:
  - `GET /api/users` - Return all users as JSON array
  - `POST /api/users` - Create new user (accept JSON with `name` and `email`)
  - `GET /api/health` - Return health status as JSON
- Run on port 5000 internally
- Include proper error handling for database connection failures

### 3. NGINX Reverse Proxy
- Container name: `nginx_proxy`
- Serve static HTML from `/usr/share/nginx/html/`
- Proxy requests to `/api/*` to Flask backend
- Expose port 80 to host machine (mapped to port 8080)
- Configure proper proxy headers

### 4. Frontend
- Single HTML page (`index.html`) with JavaScript
- Display list of users fetched from `/api/users`
- Include a form to add new users via POST to `/api/users`
- Show API health status from `/api/health`

## Docker Compose Configuration

- Define a custom bridge network named `app_network`
- All services must be connected to this network
- PostgreSQL data must persist using a named volume `postgres_data`
- Services must start in correct order (database → backend → nginx)

## Expected Behavior

After running `docker-compose up -d`:
1. Access `http://localhost:8080` to view the frontend
2. Frontend displays existing users from database
3. Users can add new users through the form
4. All API requests are proxied through NGINX
5. Database changes persist across container restarts

## Output Files

All configuration files, Dockerfiles, and application code must be created in the specified directory structure under /app.