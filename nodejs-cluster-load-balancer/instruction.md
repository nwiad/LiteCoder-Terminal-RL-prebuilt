## Node.js Cluster-Based Load Balancer

Build a multi-core Node.js HTTP load balancer using the built-in `cluster` module. The load balancer distributes incoming traffic across backend worker processes with health checking and automatic failover. No external dependencies (npm packages) are allowed — use only Node.js built-in modules.

### Technical Requirements

- Language: Node.js (pure, no external npm packages)
- Entry point: `/app/index.js`
- Start command: `node /app/index.js`

### Architecture

The system consists of a **master process** and multiple **worker processes**.

**Master process:**
- Listens on port `8080` for incoming client HTTP requests.
- Forks worker processes. The number of workers must equal the number of CPU cores available (use `os.cpus().length`), with a minimum of 2 workers even if only 1 core is detected.
- Distributes incoming requests to healthy workers using a **round-robin** algorithm (skipping unhealthy workers).
- Runs a health checker that pings each worker's `/health` endpoint at a configurable interval (default: 3 seconds).
- A worker is marked **unhealthy** after 3 consecutive failed health checks.
- Automatically restarts any worker process that crashes (exits unexpectedly), up to a maximum of 5 restarts per worker within a 60-second window.
- Serves the `/lb-status` endpoint directly (see below).

**Worker processes:**
- Each worker starts an HTTP server on a unique port, assigned sequentially starting from port `3001` (i.e., worker 1 → 3001, worker 2 → 3002, etc.).
- Workers handle proxied requests from the master and return responses back.
- Each worker exposes a `GET /health` endpoint.
- For any other `GET` request, workers respond with HTTP 200 and a JSON body.

### Endpoint Specifications

**Worker: `GET /health`** (on worker ports 3001, 3002, …)

Response: HTTP 200 with `Content-Type: application/json`
```json
{
  "status": "ok",
  "workerId": <cluster.worker.id>,
  "pid": <process.pid>,
  "uptime": <process.uptime() in seconds, number>
}
```

**Worker: `GET /*`** (any other path, on worker ports)

Response: HTTP 200 with `Content-Type: application/json`
```json
{
  "workerId": <cluster.worker.id>,
  "pid": <process.pid>,
  "path": "<requested path string>"
}
```

**Master: `GET /lb-status`** (on port 8080)

Response: HTTP 200 with `Content-Type: application/json`
```json
{
  "totalWorkers": <number of forked workers>,
  "healthyWorkers": <number of currently healthy workers>,
  "unhealthyWorkers": <number of currently unhealthy workers>,
  "totalRequests": <total number of client requests proxied since start>,
  "workers": [
    {
      "workerId": <id>,
      "port": <port number>,
      "pid": <process pid>,
      "healthy": <boolean>,
      "requestsServed": <number of requests routed to this worker>
    }
  ]
}
```

**Master: `GET /*`** (any other path on port 8080, except `/lb-status`)

The master proxies the request to the next healthy worker (round-robin) and returns the worker's response to the client. If no healthy workers are available, respond with HTTP 503 and:
```json
{
  "error": "No healthy workers available"
}
```

### Behavior Requirements

1. **Round-robin distribution:** Requests to port 8080 (excluding `/lb-status`) must be distributed evenly across healthy workers in sequential order. If worker N becomes unhealthy, it is skipped in the rotation.

2. **Worker crash recovery:** When a worker process exits unexpectedly, the master must fork a new replacement worker (assigned the same port as the crashed one) and log a message to stdout: `Worker <id> died, restarting...`.

3. **Startup logging:** When the system starts, the master must log to stdout: `Master <pid> is running` and each worker must log: `Worker <id> listening on port <port>`.

4. **Graceful operation:** The load balancer must be able to start, serve requests, and report status without errors under normal operation.
