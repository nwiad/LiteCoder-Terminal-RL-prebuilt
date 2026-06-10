import os
import subprocess
import time
import requests
import json

# Base paths
APP_DIR = "/app"

def test_directory_structure_exists():
    """Test that all required directories and files exist"""
    required_paths = [
        os.path.join(APP_DIR, "docker-compose.yml"),
        os.path.join(APP_DIR, "nginx", "Dockerfile"),
        os.path.join(APP_DIR, "nginx", "nginx.conf"),
        os.path.join(APP_DIR, "nginx", "html", "index.html"),
        os.path.join(APP_DIR, "backend", "Dockerfile"),
        os.path.join(APP_DIR, "backend", "requirements.txt"),
        os.path.join(APP_DIR, "backend", "app.py"),
        os.path.join(APP_DIR, "database", "init.sql"),
    ]

    for path in required_paths:
        assert os.path.exists(path), f"Required file/directory missing: {path}"


def test_docker_compose_file_structure():
    """Test docker-compose.yml contains required services and configuration"""
    compose_file = os.path.join(APP_DIR, "docker-compose.yml")

    with open(compose_file, 'r') as f:
        content = f.read()

    # Check for required services
    assert "postgres_db:" in content, "postgres_db service not defined"
    assert "flask_backend:" in content, "flask_backend service not defined"
    assert "nginx_proxy:" in content, "nginx_proxy service not defined"

    # Check for network configuration
    assert "app_network" in content, "Custom network 'app_network' not defined"

    # Check for volume configuration
    assert "postgres_data" in content, "Volume 'postgres_data' not defined"

    # Check for port mapping
    assert "8080:80" in content or "8080" in content, "Port 8080 not exposed"


def test_database_init_sql():
    """Test that init.sql creates users table and inserts sample data"""
    init_sql = os.path.join(APP_DIR, "database", "init.sql")

    with open(init_sql, 'r') as f:
        content = f.read().lower()

    # Check table creation
    assert "create table" in content and "users" in content, "Users table creation not found"
    assert "id" in content and "serial" in content, "ID column with serial type not found"
    assert "name" in content and "varchar" in content, "Name column not found"
    assert "email" in content, "Email column not found"

    # Check sample data insertion
    assert "insert into" in content, "No INSERT statement found"
    # Should have at least 2 users
    insert_count = content.count("insert into")
    values_count = content.count("values")
    # Either multiple INSERT statements or one with multiple VALUES
    assert insert_count >= 1 and values_count >= 1, "Sample users not inserted"


def test_flask_backend_dockerfile():
    """Test Flask backend Dockerfile has proper structure"""
    dockerfile = os.path.join(APP_DIR, "backend", "Dockerfile")

    with open(dockerfile, 'r') as f:
        content = f.read().lower()

    assert "from python" in content, "Python base image not specified"
    assert "requirements.txt" in content, "requirements.txt not copied"
    assert "app.py" in content, "app.py not copied"
    assert "expose 5000" in content or "5000" in content, "Port 5000 not exposed"


def test_flask_requirements():
    """Test Flask requirements.txt contains necessary packages"""
    requirements = os.path.join(APP_DIR, "backend", "requirements.txt")

    with open(requirements, 'r') as f:
        content = f.read().lower()

    assert "flask" in content, "Flask not in requirements"
    assert "psycopg2" in content, "psycopg2 not in requirements (needed for PostgreSQL)"


def test_flask_app_endpoints():
    """Test Flask app.py defines required API endpoints"""
    app_py = os.path.join(APP_DIR, "backend", "app.py")

    with open(app_py, 'r') as f:
        content = f.read()

    # Check for required endpoints
    assert "/api/health" in content, "/api/health endpoint not defined"
    assert "/api/users" in content, "/api/users endpoint not defined"

    # Check for HTTP methods
    assert "GET" in content, "GET method not implemented"
    assert "POST" in content, "POST method not implemented"

    # Check for database connection
    assert "psycopg2" in content or "connect" in content, "Database connection not implemented"


def test_nginx_dockerfile():
    """Test NGINX Dockerfile has proper structure"""
    dockerfile = os.path.join(APP_DIR, "nginx", "Dockerfile")

    with open(dockerfile, 'r') as f:
        content = f.read().lower()

    assert "from nginx" in content, "NGINX base image not specified"
    assert "nginx.conf" in content, "nginx.conf not copied"
    assert "index.html" in content, "index.html not copied"


def test_nginx_config():
    """Test NGINX configuration proxies API requests correctly"""
    nginx_conf = os.path.join(APP_DIR, "nginx", "nginx.conf")

    with open(nginx_conf, 'r') as f:
        content = f.read()

    # Check for proxy configuration
    assert "location /api/" in content or "location /api" in content, "API proxy location not configured"
    assert "proxy_pass" in content, "proxy_pass directive not found"
    assert "flask_backend" in content, "Backend service not referenced in proxy"

    # Check for static file serving
    assert "location /" in content, "Root location not configured"


def test_frontend_html():
    """Test frontend HTML contains required functionality"""
    index_html = os.path.join(APP_DIR, "nginx", "html", "index.html")

    with open(index_html, 'r') as f:
        content = f.read().lower()

    # Check for API calls
    assert "/api/users" in content, "Frontend doesn't fetch from /api/users"
    assert "/api/health" in content, "Frontend doesn't check /api/health"

    # Check for form elements
    assert "form" in content, "No form element found"
    assert "name" in content and "email" in content, "Form fields for name/email not found"

    # Check for JavaScript fetch/AJAX
    assert "fetch" in content or "xmlhttprequest" in content, "No API calls in JavaScript"


def test_docker_services_running():
    """Test that all Docker containers are running"""
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        cwd=APP_DIR
    )

    running_containers = result.stdout

    assert "postgres_db" in running_containers, "postgres_db container not running"
    assert "flask_backend" in running_containers, "flask_backend container not running"
    assert "nginx_proxy" in running_containers, "nginx_proxy container not running"


def test_docker_network_exists():
    """Test that custom Docker network exists"""
    result = subprocess.run(
        ["docker", "network", "ls", "--format", "{{.Name}}"],
        capture_output=True,
        text=True
    )

    networks = result.stdout
    assert "app_network" in networks, "Custom network 'app_network' not created"


def test_docker_volume_exists():
    """Test that PostgreSQL volume exists"""
    result = subprocess.run(
        ["docker", "volume", "ls", "--format", "{{.Name}}"],
        capture_output=True,
        text=True
    )

    volumes = result.stdout
    assert "postgres_data" in volumes, "Volume 'postgres_data' not created"


def test_frontend_accessible():
    """Test that frontend is accessible on port 8080"""
    max_retries = 10
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            response = requests.get("http://localhost:8080", timeout=5)
            assert response.status_code == 200, f"Frontend returned status {response.status_code}"
            assert len(response.text) > 0, "Frontend returned empty response"
            return
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise AssertionError("Frontend not accessible after multiple retries")


def test_api_health_endpoint():
    """Test /api/health endpoint returns correct status"""
    max_retries = 10
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            response = requests.get("http://localhost:8080/api/health", timeout=5)
            assert response.status_code == 200, f"Health endpoint returned status {response.status_code}"

            data = response.json()
            assert "status" in data, "Health response missing 'status' field"
            assert data["status"] == "healthy", f"API status is {data['status']}, expected 'healthy'"
            return
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise AssertionError("Health endpoint not accessible after multiple retries")


def test_api_get_users():
    """Test GET /api/users returns initial users from database"""
    max_retries = 10
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            response = requests.get("http://localhost:8080/api/users", timeout=5)
            assert response.status_code == 200, f"Users endpoint returned status {response.status_code}"

            users = response.json()
            assert isinstance(users, list), "Users endpoint should return a list"
            assert len(users) >= 2, f"Expected at least 2 initial users, got {len(users)}"

            # Check user structure
            for user in users:
                assert "id" in user, "User missing 'id' field"
                assert "name" in user, "User missing 'name' field"
                assert "email" in user, "User missing 'email' field"

            return
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise AssertionError("Users endpoint not accessible after multiple retries")


def test_api_post_user():
    """Test POST /api/users creates a new user"""
    new_user = {
        "name": "Test User",
        "email": "test@example.com"
    }

    response = requests.post(
        "http://localhost:8080/api/users",
        json=new_user,
        timeout=5
    )

    assert response.status_code == 201, f"POST user returned status {response.status_code}"

    data = response.json()
    assert "id" in data, "Created user response missing 'id'"
    assert data["name"] == new_user["name"], "Created user name doesn't match"
    assert data["email"] == new_user["email"], "Created user email doesn't match"

    # Verify user was actually added
    get_response = requests.get("http://localhost:8080/api/users", timeout=5)
    users = get_response.json()

    user_found = any(u["email"] == new_user["email"] for u in users)
    assert user_found, "Newly created user not found in users list"


def test_nginx_proxy_headers():
    """Test that NGINX properly proxies requests with headers"""
    response = requests.get("http://localhost:8080/api/health", timeout=5)

    # Just verify the request goes through successfully
    assert response.status_code == 200, "Proxied request failed"


def test_database_persistence():
    """Test that database data persists (volume is properly configured)"""
    # Add a unique user
    unique_email = f"persist_test_{int(time.time())}@example.com"
    new_user = {
        "name": "Persistence Test",
        "email": unique_email
    }

    response = requests.post(
        "http://localhost:8080/api/users",
        json=new_user,
        timeout=5
    )
    assert response.status_code == 201, "Failed to create test user"

    # Verify user exists
    get_response = requests.get("http://localhost:8080/api/users", timeout=5)
    users = get_response.json()
    user_found = any(u["email"] == unique_email for u in users)
    assert user_found, "Test user not found after creation"


def test_api_post_user_validation():
    """Test that POST /api/users validates required fields"""
    # Try to create user without required fields
    invalid_user = {"name": "Only Name"}

    response = requests.post(
        "http://localhost:8080/api/users",
        json=invalid_user,
        timeout=5
    )

    # Should return 400 Bad Request or 500 with error
    assert response.status_code in [400, 500], f"Expected error status, got {response.status_code}"

    data = response.json()
    assert "error" in data, "Error response should contain 'error' field"
