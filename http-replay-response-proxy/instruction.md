## HTTP Request Replay & Response Modification

Build a system that includes an HTTP server, a response-modifying proxy, and a script that exercises both to demonstrate HTTP request replay and real-time response modification.

### Technical Requirements

- Language/tools: Python 3 for the HTTP server; standard Linux networking utilities (`curl`, `socat` or `netcat`, `sed`) for the proxy and testing.
- All scripts and artifacts must be placed under `/app/`.

### Components

#### 1. HTTP Server — `/app/server.py`

A Python HTTP server that listens on port **8080** and handles:

- `GET /api/data` — returns a JSON response with Content-Type `application/json`:
  ```json
  {"status": "success", "message": "original response", "count": 42}
  ```
- `GET /api/health` — returns:
  ```json
  {"status": "healthy"}
  ```
- Any other path — returns HTTP 404 with:
  ```json
  {"error": "not found"}
  ```

The server must run in the foreground when executed as `python3 /app/server.py` and be ready to accept connections on port 8080.

#### 2. Response-Modifying Proxy — `/app/proxy.sh`

A Bash script that starts a proxy listener on port **8081**. The proxy must:

- Forward every incoming HTTP request to `localhost:8080`.
- Modify the response body in real-time using `sed` before returning it to the client, applying these two substitutions:
  - Replace the string `original response` with `modified response`.
  - Replace the string `"count": 42` with `"count": 100`.
- Run in the foreground when executed as `bash /app/proxy.sh` and be ready to accept connections on port 8081.

#### 3. Test / Replay Script — `/app/test_replay.sh`

A Bash script (`bash /app/test_replay.sh`) that:

1. Starts the server (`/app/server.py`) in the background.
2. Starts the proxy (`/app/proxy.sh`) in the background.
3. Waits until both ports (8080 and 8081) are accepting connections.
4. Sends a `GET /api/data` request directly to the server (port 8080) and saves the full response body to `/app/output_direct.json`.
5. Sends a `GET /api/data` request through the proxy (port 8081) and saves the full response body to `/app/output_proxied.json`.
6. Sends a `GET /api/health` request through the proxy (port 8081) and saves the full response body to `/app/output_health.json`.
7. Cleans up all background processes before exiting.

### Output Files

After running `bash /app/test_replay.sh`, the following files must exist and contain valid JSON:

| File | Expected content |
|---|---|
| `/app/output_direct.json` | `{"status": "success", "message": "original response", "count": 42}` |
| `/app/output_proxied.json` | `{"status": "success", "message": "modified response", "count": 100}` |
| `/app/output_health.json` | `{"status": "healthy"}` |

Each output file must contain only the JSON body (no HTTP headers, no trailing newlines beyond what the server produces).
