## Django API Rate Limiting & Security Hardening

Build a production-ready Django REST API project at `/app/ratelimit_api/` with Redis-backed rate limiting, JWT authentication, and security headers.

### Technical Requirements

- Python 3.x, Django 4.x+, Django REST Framework
- `djangorestframework-simplejwt` for JWT authentication
- `django-ratelimit` for rate limiting with Redis backend
- Redis server running on `localhost:6379` (default)
- Django project name: `ratelimit_api`, main app name: `api`

### Project Structure

```
/app/ratelimit_api/
├── manage.py
├── ratelimit_api/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── api/
    ├── models.py
    ├── views.py
    ├── urls.py
    └── serializers.py
```

### Django Settings (`ratelimit_api/settings.py`)

1. `INSTALLED_APPS` must include `rest_framework`, `rest_framework_simplejwt`, and `api`.
2. Configure `REST_FRAMEWORK` default authentication class to use `JWTAuthentication`.
3. Configure Redis as the Django cache backend with the alias `"default"`, pointing to `redis://localhost:6379/1`.
4. Set `RATELIMIT_USE_CACHE = "default"` to route django-ratelimit through Redis.
5. Enable the following security settings (all set to `True` unless noted):
   - `SECURE_BROWSER_XSS_FILTER`
   - `SECURE_CONTENT_TYPE_NOSNIFF`
   - `X_FRAME_OPTIONS = "DENY"`
   - `CSRF_COOKIE_SECURE`
   - `SESSION_COOKIE_SECURE`
6. Include `django.middleware.security.SecurityMiddleware` in `MIDDLEWARE`.
7. Configure `SIMPLE_JWT` with `ACCESS_TOKEN_LIFETIME` set to 30 minutes and `REFRESH_TOKEN_LIFETIME` set to 1 day.

### API Endpoints (`api/urls.py` and `api/views.py`)

All endpoints must be wired under the `/api/` URL prefix.

| Endpoint | Method | Auth Required | Rate Limit | Description |
|---|---|---|---|---|
| `/api/token/` | POST | No | 5/minute | Obtain JWT token pair (username + password) |
| `/api/token/refresh/` | POST | No | 10/minute | Refresh JWT access token |
| `/api/public/` | GET | No | 20/minute | Returns `{"message": "public endpoint", "status": "ok"}` |
| `/api/protected/` | GET | Yes (JWT) | 10/minute | Returns `{"message": "protected endpoint", "user": "<username>"}` |
| `/api/health/` | GET | No | 60/minute | Returns `{"status": "healthy", "redis": "connected"}` after verifying Redis connectivity; returns `{"status": "unhealthy", "redis": "disconnected"}` if Redis is unreachable |

- Rate limits on `/api/public/`, `/api/protected/`, and `/api/health/` must be enforced using the `@ratelimit` decorator from `django-ratelimit`, with `key="ip"` and `block=True`.
- Rate limits on `/api/token/` and `/api/token/refresh/` must be enforced using the `@ratelimit` decorator with `key="ip"` and `block=True`.
- When a rate limit is exceeded and `block=True`, the view must return an HTTP 403 response.

### Authentication

- `/api/token/` must accept POST with JSON body `{"username": "...", "password": "..."}` and return `{"access": "...", "refresh": "..."}`.
- `/api/protected/` must return HTTP 401 if no valid JWT token is provided in the `Authorization: Bearer <token>` header.
- `/api/protected/` must return HTTP 200 with the authenticated user's username when a valid token is provided.

### Logging

Configure a logger named `security` in Django `LOGGING` settings that:
- Logs to a file at `/app/ratelimit_api/logs/security.log`
- Uses log level `WARNING` or lower (i.e., captures WARNING and above)
- Log format must include timestamp, level, and message

Rate limit violations and authentication failures should be logged to this logger.

### Output Verification File

After the project is fully set up, generate a file at `/app/output.json` containing:

```json
{
  "project_path": "/app/ratelimit_api",
  "django_project": "ratelimit_api",
  "app_name": "api",
  "endpoints": [
    {"path": "/api/token/", "method": "POST", "auth_required": false, "rate_limit": "5/m"},
    {"path": "/api/token/refresh/", "method": "POST", "auth_required": false, "rate_limit": "10/m"},
    {"path": "/api/public/", "method": "GET", "auth_required": false, "rate_limit": "20/m"},
    {"path": "/api/protected/", "method": "GET", "auth_required": true, "rate_limit": "10/m"},
    {"path": "/api/health/", "method": "GET", "auth_required": false, "rate_limit": "60/m"}
  ],
  "security_settings": {
    "xss_filter": true,
    "content_type_nosniff": true,
    "x_frame_options": "DENY",
    "csrf_cookie_secure": true,
    "session_cookie_secure": true
  },
  "redis_cache_backend": "django.core.cache.backends.redis.RedisCache",
  "jwt_access_lifetime_minutes": 30,
  "jwt_refresh_lifetime_days": 1,
  "log_file": "/app/ratelimit_api/logs/security.log"
}
```
