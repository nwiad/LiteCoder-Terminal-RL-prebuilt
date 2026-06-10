## Web-based Service Discovery & Load Balancing

Implement a Python-based microservice system that supports service registration, DNS-SD-based discovery, and client-side load balancing for a replicated "time" service. Everything lives under `/app`.

### Technical Requirements

- Language: Python 3
- Dependencies: `zeroconf` for DNS-SD, `flask` or `bottle` for HTTP
- Entry point: `/app/time_service.py`

### Project Structure

```
/app/
  time_service.py      # Single CLI entry point
  README.md            # ≤ 15 lines, explains how to run N servers + 1 client
```

### CLI Interface

The entry point must support two modes via command-line arguments:

```
python time_service.py server --port <PORT>
python time_service.py client --output /app/output.json
```

- `server` mode: starts an HTTP server on the given port and announces itself via DNS-SD.
- `client` mode: discovers available servers, calls them using round-robin load balancing, writes results to the file specified by `--output` (default `/app/output.json`), then exits.

### Server Mode

1. Start an HTTP server on the port specified by `--port` (default `5000`).
2. Expose the following endpoints:

   **GET /time**
   Returns JSON with the current epoch timestamp:
   ```json
   {"time": 1718000000.123456}
   ```
   Content-Type must be `application/json`.

   **GET /**
   Returns JSON with the server's startup epoch and hostname:
   ```json
   {"startup_time": 1718000000.0, "hostname": "myhost"}
   ```

3. Register a DNS-SD service of type `_time._tcp.local.` on startup.
4. Cleanly deregister the DNS-SD service on shutdown (SIGINT/SIGTERM).

### Client Mode

1. Browse for services of type `_time._tcp.local.` using DNS-SD.
2. Maintain a list of discovered `host:port` endpoints.
3. Use round-robin selection to pick the next endpoint for each request.
4. Health-check logic: if a request to an endpoint fails (connection error or timeout > 2 seconds), remove that endpoint from the active list and retry with the next available endpoint.
5. Make exactly 5 sequential requests to `/time` across discovered endpoints.
6. Write the results to the output file as a JSON array. Each element must have:
   ```json
   {
     "endpoint": "host:port",
     "time": 1718000000.123456,
     "success": true
   }
   ```
   On failure (all endpoints exhausted), the element should be:
   ```json
   {
     "endpoint": null,
     "time": null,
     "success": false
   }
   ```
7. The output file `/app/output.json` must be a JSON array of exactly 5 such objects.

### Standalone Test Mode

To allow testing without mDNS networking, the client must also accept an `--endpoints` flag:

```
python time_service.py client --endpoints "127.0.0.1:5000,127.0.0.1:5001" --output /app/output.json
```

When `--endpoints` is provided, skip DNS-SD discovery entirely and use the given comma-separated `host:port` list directly.

### README.md

Provide `/app/README.md` (≤ 15 lines) explaining how to start N servers on different ports and 1 client, and what output to expect.
