## Task: Build Kubernetes Manifests and Application Code for a Three-Tier Web App ("StickyNotes")

Create the complete set of Kubernetes manifests and application source code for a horizontally-scalable three-tier note-taking web service called "StickyNotes," consisting of an Nginx frontend, a Node.js/Express API, and a MySQL 8 database.

### Technical Requirements

- **Language/Runtime:** Node.js (Express) for the API tier; plain HTML/JS for the frontend; MySQL 8 for the database
- **All output files** must be placed under `/app/` using the exact directory structure specified below

### Required Directory Structure

```
/app/
├── k8s/
│   ├── namespace.yaml
│   ├── secrets.yaml
│   ├── configmap.yaml
│   ├── mysql-statefulset.yaml
│   ├── api-deployment.yaml
│   ├── api-service.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── api-hpa.yaml
│   ├── frontend-hpa.yaml
│   ├── clusterissuer.yaml
│   ├── certificate.yaml
│   └── ingress.yaml
├── api/
│   ├── Dockerfile
│   ├── package.json
│   └── server.js
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── index.html
└── db/
    └── init.sql
```

### Namespace

All Kubernetes resources must be in namespace `stickynotes`.

### Database Tier (`/app/db/` and `/app/k8s/mysql-statefulset.yaml`)

1. `/app/db/init.sql` must create a database called `stickynotes` and a table called `notes` with at minimum these columns:
   - `id` — integer, primary key, auto-increment
   - `title` — varchar, not null
   - `content` — text
   - `created_at` — timestamp, defaults to current timestamp
2. `/app/k8s/mysql-statefulset.yaml` must define a `StatefulSet` named `mysql` with:
   - Exactly 1 replica
   - Container image reference `mysql:8`
   - A `volumeClaimTemplate` for persistent storage (at least 1Gi, access mode `ReadWriteOnce`)
   - Environment variable `MYSQL_ROOT_PASSWORD` sourced from a Secret
   - Environment variable `MYSQL_DATABASE` set to `stickynotes`
3. A headless `Service` for MySQL named `mysql` (clusterIP: None) must be included in the same file or as a separate manifest.

### API Tier (`/app/api/` and `/app/k8s/api-deployment.yaml`)

1. `/app/api/server.js` must implement an Express application exposing these JSON REST endpoints:
   - `GET /api/notes` — returns all notes as a JSON array
   - `POST /api/notes` — accepts `{"title": "...", "content": "..."}` and returns the created note with its `id`
   - `DELETE /api/notes/:id` — deletes a note by id and returns `{"success": true}`
   - The server must listen on port `3000`
2. `/app/api/package.json` must list `express` and `mysql2` as dependencies.
3. `/app/api/Dockerfile` must produce a working container image for the API.
4. `/app/k8s/api-deployment.yaml` must define a `Deployment` named `api` with at least 2 replicas, container port `3000`, and environment variables for the MySQL host (`mysql.stickynotes.svc.cluster.local`), database name, user, and password (password from the Secret).

### Frontend Tier (`/app/frontend/` and `/app/k8s/frontend-deployment.yaml`)

1. `/app/frontend/index.html` must contain an HTML page that uses `fetch()` to call `/api/notes` (GET and POST at minimum).
2. `/app/frontend/nginx.conf` must configure Nginx to:
   - Serve static files from the default document root
   - Reverse-proxy requests matching `/api/` to the API service (`http://api.stickynotes.svc.cluster.local:3000`)
3. `/app/frontend/Dockerfile` must produce a working container image based on `nginx`.
4. `/app/k8s/frontend-deployment.yaml` must define a `Deployment` named `frontend` with at least 2 replicas and container port `80`.

### Secrets and ConfigMap

1. `/app/k8s/secrets.yaml` must define a `Secret` named `stickynotes-secret` in namespace `stickynotes` of type `Opaque` containing at least the key `MYSQL_ROOT_PASSWORD` (base64-encoded).
2. `/app/k8s/configmap.yaml` must define a `ConfigMap` named `stickynotes-config` in namespace `stickynotes` containing at least `MYSQL_HOST` and `MYSQL_DATABASE` keys.

### Services

1. `/app/k8s/api-service.yaml` — a `Service` named `api` of type `ClusterIP` targeting port `3000`.
2. `/app/k8s/frontend-service.yaml` — a `Service` named `frontend` of type `ClusterIP` targeting port `80`.

### HorizontalPodAutoscalers

1. `/app/k8s/api-hpa.yaml` — HPA named `api-hpa` targeting the `api` Deployment, min 2 / max 10 replicas, CPU target utilization `60`.
2. `/app/k8s/frontend-hpa.yaml` — HPA named `frontend-hpa` targeting the `frontend` Deployment, min 2 / max 10 replicas, CPU target utilization `60`.

### TLS and Ingress

1. `/app/k8s/clusterissuer.yaml` — a cert-manager `ClusterIssuer` named `letsencrypt-staging` using the ACME protocol with Let's Encrypt staging URL (`https://acme-staging-v02.api.letsencrypt.org/directory`) and an `http01` solver.
2. `/app/k8s/certificate.yaml` — a cert-manager `Certificate` named `stickynotes-tls` for the DNS name `stickynotes.local`, referencing the `letsencrypt-staging` ClusterIssuer, with secret name `stickynotes-tls-secret`.
3. `/app/k8s/ingress.yaml` — an `Ingress` named `stickynotes-ingress` for host `stickynotes.local` with TLS enabled (using secret `stickynotes-tls-secret`) and two path rules:
   - `/api/` routed to service `api` port `3000`
   - `/` routed to service `frontend` port `80`

### Manifest Format Requirements

- All YAML manifests must include `apiVersion`, `kind`, and `metadata.name`.
- All resources (except `ClusterIssuer`) must include `metadata.namespace: stickynotes`.
- `/app/k8s/namespace.yaml` must define the `stickynotes` Namespace.
