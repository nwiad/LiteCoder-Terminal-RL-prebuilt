## Custom DNS Resolver & Web Dashboard

Build a Python-based custom DNS resolver system with query logging, statistics collection, a CLI client, and a web dashboard exposing stats via HTTP.

### Technical Requirements

- Language: Python 3.x
- No external DNS libraries for the core resolver logic (use only `socket` and `struct` for raw DNS packet construction/parsing). You may use `flask` or `aiohttp` for the web dashboard and `websockets` if needed.
- All source files should be placed under `/app/`.

### Components & File Structure

1. **DNS Resolver** (`/app/dns_resolver.py`):
   - A module providing a `resolve(domain: str, query_type: str = "A") -> dict` function.
   - `query_type` supports at minimum: `"A"`, `"AAAA"`, `"MX"`, `"CNAME"`.
   - The function must return a dict with the following structure:
     ```json
     {
       "domain": "example.com",
       "query_type": "A",
       "answers": ["93.184.216.34"],
       "response_time_ms": 12.5,
       "status": "success",
       "timestamp": "2025-01-15T10:30:00Z"
     }
     ```
   - On failure (timeout, NXDOMAIN, etc.), `"status"` must be `"error"` and `"answers"` must be an empty list `[]`. An additional `"error"` key must contain a short error description string.
   - Default upstream DNS server: `8.8.8.8` (configurable via `/app/config.json`).

2. **Configuration** (`/app/config.json`):
   - The system reads configuration from this file. If the file does not exist, use defaults.
   - Format:
     ```json
     {
       "upstream_dns": "8.8.8.8",
       "dns_port": 53,
       "web_port": 5353,
       "log_file": "/app/dns_log.json",
       "log_level": "INFO"
     }
     ```

3. **Query Logger** (`/app/query_logger.py`):
   - Provides a `log_query(result: dict) -> None` function that appends each resolved query result as a JSON line to the log file specified in config (default `/app/dns_log.json`).
   - The log file uses JSON Lines format (one JSON object per line).
   - Each log entry must contain all fields from the resolver result dict plus an `"id"` field (auto-incrementing integer starting from 1).

4. **Statistics Collector** (`/app/stats_collector.py`):
   - Provides a `compute_stats(log_file: str = "/app/dns_log.json") -> dict` function.
   - Reads the JSON Lines log file and returns a dict:
     ```json
     {
       "total_queries": 150,
       "successful_queries": 140,
       "failed_queries": 10,
       "query_type_counts": {"A": 100, "AAAA": 30, "MX": 15, "CNAME": 5},
       "avg_response_time_ms": 15.3,
       "top_domains": [
         {"domain": "example.com", "count": 25},
         {"domain": "google.com", "count": 20}
       ],
       "queries_per_minute": 2.5
     }
     ```
   - `top_domains`: list sorted by count descending, limited to top 10.
   - `avg_response_time_ms`: average across successful queries only, rounded to 1 decimal place.
   - If the log file is empty or missing, return a dict with `total_queries` = 0, empty `query_type_counts` `{}`, `top_domains` `[]`, `avg_response_time_ms` 0.0, and other numeric fields as 0.

5. **CLI Client** (`/app/cli_client.py`):
   - Runnable as: `python /app/cli_client.py <domain> [query_type]`
   - `query_type` defaults to `"A"` if omitted.
   - Prints the resolver result as pretty-printed JSON to stdout.
   - Logs the query via the query logger.
   - Exit code 0 on success, 1 on error.

6. **Web Dashboard** (`/app/web_dashboard.py`):
   - An HTTP server on the port specified in config (default `5353`).
   - `GET /api/stats` — returns the output of `compute_stats()` as JSON with `Content-Type: application/json`.
   - `GET /api/resolve?domain=<domain>&type=<query_type>` — resolves the domain, logs it, and returns the resolver result as JSON. `type` defaults to `"A"`.
   - `GET /api/logs?limit=<n>` — returns the last `n` log entries as a JSON array (default `n=50`).
   - `GET /` — serves a simple HTML page (content not tested, but must return HTTP 200).

### Output Files

- `/app/dns_log.json` — JSON Lines log file, created/appended by the query logger.
- `/app/config.json` — configuration file (create a default one if it does not already exist when any component starts).

### Error Handling

- DNS resolution must have a configurable timeout (default 5 seconds). On timeout, return an error result.
- If the upstream DNS server is unreachable, the resolver must not crash; it must return an error result.
- The web dashboard must return HTTP 400 with a JSON body `{"error": "<message>"}` if the `domain` parameter is missing on `/api/resolve`.
- The stats collector must handle a missing or empty log file gracefully as described above.
