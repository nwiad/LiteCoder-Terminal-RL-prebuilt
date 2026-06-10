import os
import json
import subprocess
import time
import requests

# Test configuration
BASE_URL = "http://localhost:3000"
CONFIG_PATH = "/app/config.json"
SERVER_JS_PATH = "/app/server.js"

def test_config_file_exists():
    """Verify config.json exists and is readable"""
    assert os.path.exists(CONFIG_PATH), "config.json must exist at /app/config.json"

def test_config_file_valid_json():
    """Verify config.json contains valid JSON"""
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    assert isinstance(config, dict), "config.json must be a valid JSON object"

def test_config_has_required_fields():
    """Verify config.json has all required fields"""
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    assert "port" in config, "config.json must have 'port' field"
    assert "redis" in config, "config.json must have 'redis' field"
    assert "session" in config, "config.json must have 'session' field"

    assert "host" in config["redis"], "redis config must have 'host'"
    assert "port" in config["redis"], "redis config must have 'port'"
    assert "password" in config["redis"], "redis config must have 'password'"

    assert "secret" in config["session"], "session config must have 'secret'"
    assert "name" in config["session"], "session config must have 'name'"
    assert "maxAge" in config["session"], "session config must have 'maxAge'"

def test_server_js_exists():
    """Verify server.js exists"""
    assert os.path.exists(SERVER_JS_PATH), "server.js must exist at /app/server.js"

def test_redis_running():
    """Verify Redis server is running"""
    result = subprocess.run(['pgrep', '-f', 'redis-server'], capture_output=True)
    assert result.returncode == 0, "Redis server must be running"

def test_server_running():
    """Verify Node.js server is running and responding"""
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            assert response.status_code in [200, 503], "Server must respond to requests"
            return
        except requests.exceptions.ConnectionError:
            if i < max_retries - 1:
                time.sleep(1)
            else:
                raise AssertionError("Server is not running or not responding")

def test_health_endpoint_structure():
    """Verify /health endpoint returns correct structure"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code in [200, 503], "Health endpoint must return 200 or 503"

    data = response.json()
    assert "status" in data, "Health response must have 'status' field"
    assert "redis" in data, "Health response must have 'redis' field"
    assert data["status"] in ["healthy", "unhealthy"], "Status must be 'healthy' or 'unhealthy'"
    assert data["redis"] in ["connected", "disconnected"], "Redis status must be 'connected' or 'disconnected'"

def test_health_endpoint_redis_connected():
    """Verify /health shows Redis as connected"""
    response = requests.get(f"{BASE_URL}/health")
    data = response.json()

    # If Redis is properly configured, it should be connected
    assert data["redis"] == "connected", "Redis should be connected"
    assert data["status"] == "healthy", "Status should be healthy when Redis is connected"
    assert response.status_code == 200, "Health endpoint should return 200 when healthy"

def test_login_endpoint_success():
    """Verify /login endpoint works with valid credentials"""
    response = requests.post(
        f"{BASE_URL}/login",
        json={"username": "testuser", "password": "testpass"}
    )

    assert response.status_code == 200, "Login with valid credentials should return 200"
    data = response.json()

    assert "success" in data, "Login response must have 'success' field"
    assert data["success"] == True, "Login should succeed with valid credentials"
    assert "message" in data, "Login response must have 'message' field"
    assert "username" in data, "Login response must have 'username' field"
    assert data["username"] == "testuser", "Username should match the login request"

def test_login_endpoint_failure():
    """Verify /login endpoint rejects invalid credentials"""
    # Test with empty username
    response = requests.post(
        f"{BASE_URL}/login",
        json={"username": "", "password": "testpass"}
    )
    assert response.status_code == 401, "Login with empty username should return 401"
    data = response.json()
    assert data["success"] == False, "Login should fail with empty username"

    # Test with missing password
    response = requests.post(
        f"{BASE_URL}/login",
        json={"username": "testuser"}
    )
    assert response.status_code == 401, "Login with missing password should return 401"
    data = response.json()
    assert data["success"] == False, "Login should fail with missing password"

def test_profile_endpoint_not_authenticated():
    """Verify /profile returns 401 when not authenticated"""
    # Create a new session without logging in
    session = requests.Session()
    response = session.get(f"{BASE_URL}/profile")

    assert response.status_code == 401, "Profile without authentication should return 401"
    data = response.json()
    assert "error" in data, "Unauthenticated profile response must have 'error' field"
    assert data["error"] == "Not authenticated", "Error message should indicate not authenticated"

def test_profile_endpoint_authenticated():
    """Verify /profile returns user data when authenticated"""
    session = requests.Session()

    # Login first
    login_response = session.post(
        f"{BASE_URL}/login",
        json={"username": "profileuser", "password": "pass123"}
    )
    assert login_response.status_code == 200, "Login should succeed"

    # Access profile
    profile_response = session.get(f"{BASE_URL}/profile")
    assert profile_response.status_code == 200, "Profile should return 200 when authenticated"

    data = profile_response.json()
    assert "username" in data, "Profile response must have 'username' field"
    assert "sessionId" in data, "Profile response must have 'sessionId' field"
    assert data["username"] == "profileuser", "Username should match logged in user"
    assert len(data["sessionId"]) > 0, "SessionId should not be empty"

def test_session_persistence():
    """Verify session persists across multiple requests"""
    session = requests.Session()

    # Login
    session.post(
        f"{BASE_URL}/login",
        json={"username": "persistuser", "password": "pass456"}
    )

    # Make multiple profile requests
    for i in range(3):
        response = session.get(f"{BASE_URL}/profile")
        assert response.status_code == 200, f"Profile request {i+1} should succeed"
        data = response.json()
        assert data["username"] == "persistuser", "Username should persist across requests"

def test_logout_endpoint():
    """Verify /logout destroys the session"""
    session = requests.Session()

    # Login
    session.post(
        f"{BASE_URL}/login",
        json={"username": "logoutuser", "password": "pass789"}
    )

    # Verify logged in
    profile_response = session.get(f"{BASE_URL}/profile")
    assert profile_response.status_code == 200, "Should be authenticated after login"

    # Logout
    logout_response = session.post(f"{BASE_URL}/logout")
    assert logout_response.status_code == 200, "Logout should return 200"

    data = logout_response.json()
    assert "success" in data, "Logout response must have 'success' field"
    assert data["success"] == True, "Logout should succeed"
    assert "message" in data, "Logout response must have 'message' field"

    # Verify logged out
    profile_after_logout = session.get(f"{BASE_URL}/profile")
    assert profile_after_logout.status_code == 401, "Should not be authenticated after logout"

def test_session_isolation():
    """Verify sessions are isolated between different clients"""
    session1 = requests.Session()
    session2 = requests.Session()

    # Login with different users
    session1.post(
        f"{BASE_URL}/login",
        json={"username": "user1", "password": "pass1"}
    )
    session2.post(
        f"{BASE_URL}/login",
        json={"username": "user2", "password": "pass2"}
    )

    # Check profiles
    profile1 = session1.get(f"{BASE_URL}/profile").json()
    profile2 = session2.get(f"{BASE_URL}/profile").json()

    assert profile1["username"] == "user1", "Session 1 should have user1"
    assert profile2["username"] == "user2", "Session 2 should have user2"
    assert profile1["sessionId"] != profile2["sessionId"], "Sessions should have different IDs"

def test_redis_stores_session_data():
    """Verify sessions are actually stored in Redis"""
    session = requests.Session()

    # Login
    session.post(
        f"{BASE_URL}/login",
        json={"username": "redisuser", "password": "redispass"}
    )

    # Check Redis has keys (sessions are stored)
    result = subprocess.run(
        ['redis-cli', '-a', 'your_redis_password', 'KEYS', '*'],
        capture_output=True,
        text=True
    )

    # Redis should have at least one session key
    assert result.returncode == 0, "Redis CLI should execute successfully"
    assert len(result.stdout.strip()) > 0, "Redis should contain session data"

def test_login_response_format_exact():
    """Verify login response matches exact specification"""
    response = requests.post(
        f"{BASE_URL}/login",
        json={"username": "formattest", "password": "formatpass"}
    )

    data = response.json()
    # Must have exactly these fields for success
    assert set(data.keys()) == {"success", "message", "username"}, \
        "Login success response must have exactly: success, message, username"
    assert data["message"] == "Login successful", "Success message must match specification"

def test_logout_always_succeeds():
    """Verify logout returns success even without active session"""
    session = requests.Session()

    # Logout without logging in
    response = session.post(f"{BASE_URL}/logout")
    assert response.status_code == 200, "Logout should return 200 even without session"

    data = response.json()
    assert data["success"] == True, "Logout should always succeed"
    assert "message" in data, "Logout response must have message"

def test_multiple_logins_same_session():
    """Verify logging in again overwrites previous session data"""
    session = requests.Session()

    # First login
    session.post(
        f"{BASE_URL}/login",
        json={"username": "firstuser", "password": "pass1"}
    )

    profile1 = session.get(f"{BASE_URL}/profile").json()
    assert profile1["username"] == "firstuser"

    # Second login with same session
    session.post(
        f"{BASE_URL}/login",
        json={"username": "seconduser", "password": "pass2"}
    )

    profile2 = session.get(f"{BASE_URL}/profile").json()
    assert profile2["username"] == "seconduser", "Session should update to new username"

def test_config_values_used():
    """Verify server uses values from config.json"""
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    # Verify server is running on configured port
    response = requests.get(f"http://localhost:{config['port']}/health")
    assert response.status_code in [200, 503], f"Server should be running on port {config['port']}"

    # Verify session cookie name matches config
    session = requests.Session()
    session.post(
        f"{BASE_URL}/login",
        json={"username": "configtest", "password": "configpass"}
    )

    cookies = session.cookies.get_dict()
    assert config["session"]["name"] in cookies, f"Session cookie should use name '{config['session']['name']}' from config"
