## Docker Image Size Optimization and Security Hardening

A Python Flask web application has a bloated Docker image based on Ubuntu with unnecessary packages, build tools, and debug utilities. Optimize the image size and apply security hardening best practices for production deployment.

### Provided Files

- `/app/app.py` — Flask application source code
- `/app/requirements.txt` — Python dependencies (flask, gunicorn)
- `/app/Dockerfile.bloated` — The current bloated Dockerfile

### Requirements

1. Create an optimized Dockerfile at `/app/Dockerfile` that:
   - Uses a multi-stage build
   - Uses an Alpine-based or slim Python base image (e.g., `python:3.12-alpine`, `python:3.12-slim`) for the final stage
   - Installs only the packages listed in `requirements.txt` (no extra pip packages beyond what `requirements.txt` specifies)
   - Does not include build tools (gcc, g++, make, cmake), debug/network utilities (vim, nano, curl, wget, nmap, tcpdump, strace, telnet, net-tools, etc.), or development libraries in the final image
   - Copies only the application files needed at runtime (`app.py`, `requirements.txt`) into the final image

2. Security hardening — the final Dockerfile must:
   - Create and use a non-root user to run the application process (the `USER` directive must be set to a non-root user)
   - Not install `openssh-server` in the final image
   - Not contain any `ENV` variables with secrets or passwords
   - Use `gunicorn` as the production WSGI server in the `CMD` or `ENTRYPOINT` instruction (not the Flask development server `python3 app.py`)

3. The container must:
   - Expose port `5000`
   - Serve the Flask app so that `GET /` returns a JSON response containing `{"status": "ok"}`
   - Serve `GET /health` returning a JSON response containing `{"status": "healthy"}`
   - Serve `POST /echo` which accepts a JSON body and returns it wrapped in `{"echo": <body>}`
   - Use `WORKDIR /app` inside the container

### Output

A single file: `/app/Dockerfile`
