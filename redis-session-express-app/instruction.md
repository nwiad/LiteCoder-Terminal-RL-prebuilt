## Task: Build a Redis-Based Node.js Session Store

Create a Node.js web application using Express that implements Redis-based session management with persistence and failover capabilities.

## Technical Requirements

- **Language**: Node.js (v14+)
- **Framework**: Express.js
- **Session Store**: Redis with connect-redis
- **Configuration File**: `/app/config.json`
- **Application Entry**: `/app/server.js`

## Configuration Specification

Read configuration from `/app/config.json`:
```json
{
  "port": 3000,
  "redis": {
    "host": "localhost",
    "port": 6379,
    "password": "your_redis_password"
  },
  "session": {
    "secret": "session_secret_key",
    "name": "sessionId",
    "maxAge": 3600000
  }
}
```

## Required Endpoints

1. **POST /login**
   - Request body: `{"username": "string", "password": "string"}`
   - Response: `{"success": true, "message": "Login successful", "username": "string"}` (status 200)
   - On failure: `{"success": false, "message": "Invalid credentials"}` (status 401)
   - Store username in session upon successful login

2. **GET /profile**
   - Response if authenticated: `{"username": "string", "sessionId": "string"}` (status 200)
   - Response if not authenticated: `{"error": "Not authenticated"}` (status 401)

3. **POST /logout**
   - Response: `{"success": true, "message": "Logged out"}` (status 200)
   - Destroy the session

4. **GET /health**
   - Response if Redis connected: `{"status": "healthy", "redis": "connected"}` (status 200)
   - Response if Redis disconnected: `{"status": "unhealthy", "redis": "disconnected"}` (status 503)

## Implementation Requirements

- Use `express-session` with `connect-redis` for session storage
- Configure Redis with password authentication from config file
- Implement automatic reconnection on Redis connection failures
- Enable Redis persistence (RDB and/or AOF)
- Session data must persist across server restarts
- Handle Redis connection errors gracefully without crashing the server
- Use JSON responses for all endpoints

## Redis Configuration

Configure Redis with:
- Password authentication enabled
- Persistence enabled (RDB snapshots or AOF)
- Automatic reconnection with retry strategy

## Error Handling

- Redis connection failures should not crash the application
- Failed authentication attempts should return appropriate error messages
- Session operations should handle Redis unavailability gracefully
