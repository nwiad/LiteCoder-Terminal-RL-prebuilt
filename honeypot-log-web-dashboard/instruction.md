## Honeypot Log Monitor & Web Dashboard

Build a Python-based honeypot log monitoring system that parses SSH honeypot JSON logs and serves a real-time web dashboard using Flask and Server-Sent Events (SSE).

### Technical Requirements

- Language: Python 3
- Framework: Flask
- No external SSE libraries allowed — implement SSE streaming manually using Flask's `Response` with `text/event-stream` content type
- All source files must be placed under `/app/`

### Input

A JSON-lines log file at `/app/honeypot_log.jsonl`. Each line is a valid JSON object representing one honeypot event. The file may be appended to over time (simulating a live honeypot).

Each log entry has the following fields:

```json
{"timestamp": "2025-06-15T08:23:01Z", "src_ip": "192.168.1.50", "username": "root", "password": "admin123", "success": false, "session_id": "abc-001"}
```

Field definitions:
- `timestamp`: ISO 8601 UTC string
- `src_ip`: attacker source IP (IPv4)
- `username`: attempted login username (string)
- `password`: attempted login password (string)
- `success`: whether the login was accepted by the honeypot (boolean)
- `session_id`: unique session identifier (string)

The log file may contain malformed lines (invalid JSON). These must be silently skipped.

### Output

#### 1. Log Parser Module — `/app/log_parser.py`

Implement a module with the following function:

```python
def parse_log(filepath: str) -> list[dict]:
```

- Reads the JSONL file at `filepath` and returns a list of dicts, one per valid log entry.
- Each returned dict must contain all six fields listed above with their original keys and types.
- Malformed lines (invalid JSON or missing required fields) must be silently skipped.
- Returns an empty list if the file is empty or all lines are invalid.

#### 2. Stats Generator Module — `/app/stats.py`

Implement a module with the following function:

```python
def compute_stats(entries: list[dict]) -> dict:
```

Takes the list returned by `parse_log` and returns a dict with these exact keys:

- `total_attempts` (int): total number of log entries
- `unique_ips` (int): number of distinct `src_ip` values
- `top_usernames` (list of `[username, count]` pairs): the top 5 most attempted usernames, sorted by count descending then username ascending; fewer than 5 if not enough distinct usernames
- `top_ips` (list of `[ip, count]` pairs): the top 5 most frequent attacker IPs, sorted by count descending then IP string ascending; fewer than 5 if not enough distinct IPs
- `earliest_timestamp` (str): the earliest `timestamp` value (ISO 8601 string), or `null` if no entries
- `latest_timestamp` (str): the latest `timestamp` value (ISO 8601 string), or `null` if no entries
- `success_count` (int): number of entries where `success` is `true`

#### 3. Flask Web Application — `/app/app.py`

A Flask application that provides:

- `GET /` — returns an HTML page (status 200) that includes:
  - A `<table>` element with `id="log-table"` for displaying log entries
  - A `<div>` element with `id="stats"` for displaying summary statistics
  - Inline or linked JavaScript that connects to the `/events` SSE endpoint

- `GET /api/stats` — returns JSON (Content-Type `application/json`, status 200) with the output of `compute_stats` for the current contents of `/app/honeypot_log.jsonl`

- `GET /events` — an SSE endpoint (Content-Type `text/event-stream`) that:
  - Streams existing log entries on initial connection, one per SSE `data:` message, each as a JSON-encoded string of the log entry dict
  - Continues to watch `/app/honeypot_log.jsonl` for new lines appended after the initial read, streaming each new valid entry as it appears
  - Polls for new lines at most every 1 second
  - Each SSE message must use the format: `data: <json>\n\n`

#### 4. Sample Log File — `/app/honeypot_log.jsonl`

Provide a sample log file with at least 10 valid log entries and at least 2 malformed lines, using at least 3 distinct `src_ip` values and at least 4 distinct `username` values.

### Running

The application must be runnable via:

```bash
cd /app && python app.py
```

The Flask server must listen on `0.0.0.0` port `8080`.
