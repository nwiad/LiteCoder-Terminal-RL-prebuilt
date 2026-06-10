## Deploy and Validate a Local Web Service with Rate-Limiting

Build a minimal Python web service with fixed-window rate-limiting and a load-test script to verify its behavior.

### Technical Requirements

- Language: Python 3
- Framework: Flask or FastAPI (your choice)
- All project files must be placed under `/app/`
- No external services (Redis, databases, etc.) — use in-memory storage only

### File Structure

- `/app/requirements.txt` — Python dependencies
- `/app/app.py` — The web service
- `/app/test_load.py` — The load-test script

### Web Service (`app.py`)

1. Listen on `0.0.0.0:8080`.
2. Expose a single endpoint `GET /` that returns:
   - On success (HTTP 200): JSON body `{"message": "pong"}` with `Content-Type: application/json`.
   - On rate-limit exceeded (HTTP 429): a response with HTTP status code 429. The body format is not strictly required, but the status code must be exactly 429.
3. Enforce a fixed-window rate limit of **10 requests per minute per client IP**.
   - The window resets every 60 seconds from the first request of that window.
   - The 11th (and subsequent) requests within the same 60-second window from the same IP must receive HTTP 429.

### Load-Test Script (`test_load.py`)

1. Send exactly **20 sequential GET requests** to `http://127.0.0.1:8080/` (one after another, not concurrent).
2. Count the number of HTTP 200 responses and HTTP 429 responses.
3. Print results to stdout in the following exact format (one line per item):
   ```
   accepted: <count_of_200>
   rejected: <count_of_429>
   result: PASS
   ```
   - Print `result: PASS` if exactly 10 requests received HTTP 200 and exactly 10 received HTTP 429.
   - Print `result: FAIL` otherwise.
4. Write the same three lines to `/app/output.txt`.

### Running

- The service must be startable from the shell without root privileges.
- `requirements.txt` must list all dependencies needed to run both `app.py` and `test_load.py`.
- The service should be started in the background before running the load test. After the load test completes, the service should be stopped.
