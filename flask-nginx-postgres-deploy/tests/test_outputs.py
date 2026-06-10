import os
import json
import subprocess
import pytest


def run_command(cmd):
    """Helper to run shell commands and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def test_postgresql_service_running():
    """Verify PostgreSQL service is active and running."""
    returncode, stdout, _ = run_command("systemctl is-active postgresql")
    assert returncode == 0, "PostgreSQL service is not running"
    assert stdout == "active", f"PostgreSQL service status is '{stdout}', expected 'active'"


def test_nginx_service_running():
    """Verify Nginx service is active and running."""
    returncode, stdout, _ = run_command("systemctl is-active nginx")
    assert returncode == 0, "Nginx service is not running"
    assert stdout == "active", f"Nginx service status is '{stdout}', expected 'active'"


def test_flaskapp_service_running():
    """Verify Flask systemd service is active and running."""
    returncode, stdout, _ = run_command("systemctl is-active flaskapp")
    assert returncode == 0, "Flask app service is not running"
    assert stdout == "active", f"Flask app service status is '{stdout}', expected 'active'"


def test_flaskapp_service_enabled():
    """Verify Flask systemd service is enabled to start on boot."""
    returncode, stdout, _ = run_command("systemctl is-enabled flaskapp")
    assert returncode == 0, "Flask app service is not enabled"
    assert stdout == "enabled", f"Flask app service enabled status is '{stdout}', expected 'enabled'"


def test_flask_root_endpoint():
    """Test Flask root endpoint returns correct JSON response."""
    returncode, stdout, _ = run_command("curl -s http://localhost/")
    assert returncode == 0, "Failed to connect to Flask app root endpoint"

    # Parse JSON response
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Root endpoint did not return valid JSON: {e}\nOutput: {stdout}")

    # Verify exact structure and values
    assert "status" in response, "Response missing 'status' field"
    assert "message" in response, "Response missing 'message' field"
    assert response["status"] == "success", f"Expected status 'success', got '{response['status']}'"
    assert response["message"] == "Flask app is running", f"Expected message 'Flask app is running', got '{response['message']}'"


def test_flask_db_check_endpoint():
    """Test Flask /db-check endpoint confirms database connectivity."""
    returncode, stdout, _ = run_command("curl -s http://localhost/db-check")
    assert returncode == 0, "Failed to connect to Flask app /db-check endpoint"

    # Parse JSON response
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"/db-check endpoint did not return valid JSON: {e}\nOutput: {stdout}")

    # Verify database connection
    assert "database" in response, "Response missing 'database' field"
    assert response["database"] == "connected", f"Database not connected: {response.get('database')}"


def test_flask_users_endpoint():
    """Test Flask /users endpoint returns valid JSON array."""
    returncode, stdout, _ = run_command("curl -s http://localhost/users")
    assert returncode == 0, "Failed to connect to Flask app /users endpoint"

    # Parse JSON response
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"/users endpoint did not return valid JSON: {e}\nOutput: {stdout}")

    # Verify it's a list (even if empty)
    assert isinstance(response, list), f"Expected list response, got {type(response).__name__}"


def test_postgresql_database_exists():
    """Verify flaskapp_db database exists."""
    returncode, stdout, _ = run_command(
        "sudo -u postgres psql -lqt | cut -d '|' -f 1 | grep -w flaskapp_db"
    )
    assert returncode == 0, "Database 'flaskapp_db' does not exist"
    assert "flaskapp_db" in stdout, "Database 'flaskapp_db' not found in PostgreSQL"


def test_postgresql_user_exists():
    """Verify flaskapp_user exists in PostgreSQL."""
    returncode, stdout, _ = run_command(
        "sudo -u postgres psql -t -c \"SELECT 1 FROM pg_roles WHERE rolname='flaskapp_user'\""
    )
    assert returncode == 0, "Failed to query PostgreSQL users"
    assert "1" in stdout, "User 'flaskapp_user' does not exist in PostgreSQL"


def test_users_table_exists():
    """Verify users table exists with correct schema."""
    returncode, stdout, _ = run_command(
        "sudo -u postgres psql -d flaskapp_db -t -c \"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position\""
    )
    assert returncode == 0, "Failed to query users table schema"

    # Check for required columns
    assert "id" in stdout, "Column 'id' missing from users table"
    assert "name" in stdout, "Column 'name' missing from users table"
    assert "email" in stdout, "Column 'email' missing from users table"
    assert "character varying" in stdout or "varchar" in stdout, "Expected varchar columns in users table"


def test_nginx_config_exists():
    """Verify Nginx configuration file exists."""
    assert os.path.exists("/etc/nginx/sites-available/flaskapp"), \
        "Nginx config file /etc/nginx/sites-available/flaskapp does not exist"


def test_nginx_site_enabled():
    """Verify Nginx site is enabled via symlink."""
    assert os.path.islink("/etc/nginx/sites-enabled/flaskapp"), \
        "Nginx site not enabled: /etc/nginx/sites-enabled/flaskapp symlink missing"

    # Verify symlink points to correct location
    link_target = os.readlink("/etc/nginx/sites-enabled/flaskapp")
    assert link_target == "/etc/nginx/sites-available/flaskapp", \
        f"Symlink points to wrong location: {link_target}"


def test_nginx_proxy_configuration():
    """Verify Nginx is configured as reverse proxy with proper headers."""
    with open("/etc/nginx/sites-available/flaskapp", "r") as f:
        config = f.read()

    # Check for proxy configuration
    assert "proxy_pass" in config, "Nginx config missing proxy_pass directive"
    assert "127.0.0.1:8000" in config or "localhost:8000" in config, \
        "Nginx not proxying to correct Gunicorn backend"

    # Check for required proxy headers
    assert "proxy_set_header Host" in config, "Missing proxy_set_header Host"
    assert "proxy_set_header X-Real-IP" in config, "Missing proxy_set_header X-Real-IP"
    assert "proxy_set_header X-Forwarded-For" in config, "Missing proxy_set_header X-Forwarded-For"
    assert "proxy_set_header X-Forwarded-Proto" in config, "Missing proxy_set_header X-Forwarded-Proto"

    # Check listening on port 80
    assert "listen 80" in config, "Nginx not configured to listen on port 80"


def test_systemd_service_file_exists():
    """Verify systemd service file exists."""
    assert os.path.exists("/etc/systemd/system/flaskapp.service"), \
        "Systemd service file /etc/systemd/system/flaskapp.service does not exist"


def test_systemd_service_configuration():
    """Verify systemd service is properly configured."""
    with open("/etc/systemd/system/flaskapp.service", "r") as f:
        service_config = f.read()

    # Check for Restart directive
    assert "Restart=" in service_config, "Systemd service missing Restart directive"

    # Check for WantedBy (enables on boot)
    assert "WantedBy=" in service_config, "Systemd service missing WantedBy directive"

    # Check for gunicorn execution
    assert "gunicorn" in service_config, "Systemd service not configured to run gunicorn"
    assert "--workers" in service_config or "-w" in service_config, \
        "Gunicorn not configured with workers"


def test_gunicorn_worker_count():
    """Verify Gunicorn is running with 3 workers."""
    with open("/etc/systemd/system/flaskapp.service", "r") as f:
        service_config = f.read()

    # Check for 3 workers in configuration
    assert "--workers 3" in service_config or "-w 3" in service_config, \
        "Gunicorn not configured with 3 workers"


def test_gunicorn_bind_address():
    """Verify Gunicorn binds to 127.0.0.1:8000."""
    with open("/etc/systemd/system/flaskapp.service", "r") as f:
        service_config = f.read()

    # Check bind address
    assert "127.0.0.1:8000" in service_config, \
        "Gunicorn not configured to bind to 127.0.0.1:8000"


def test_ufw_enabled():
    """Verify UFW firewall is enabled."""
    returncode, stdout, _ = run_command("ufw status | grep -i 'Status:'")
    assert returncode == 0, "Failed to check UFW status"
    assert "active" in stdout.lower(), f"UFW is not active: {stdout}"


def test_ufw_ssh_allowed():
    """Verify UFW allows SSH (port 22)."""
    returncode, stdout, _ = run_command("ufw status numbered")
    assert returncode == 0, "Failed to check UFW rules"
    assert "22" in stdout or "OpenSSH" in stdout or "ssh" in stdout.lower(), \
        "UFW does not allow SSH (port 22)"


def test_ufw_http_allowed():
    """Verify UFW allows HTTP (port 80)."""
    returncode, stdout, _ = run_command("ufw status numbered")
    assert returncode == 0, "Failed to check UFW rules"
    assert "80" in stdout or "Nginx" in stdout or "http" in stdout.lower(), \
        "UFW does not allow HTTP (port 80)"


def test_flask_app_files_exist():
    """Verify Flask application files exist in correct location."""
    assert os.path.exists("/app/flask_app/app.py"), \
        "Flask application file /app/flask_app/app.py does not exist"
    assert os.path.exists("/app/flask_app/requirements.txt"), \
        "Requirements file /app/flask_app/requirements.txt does not exist"
    assert os.path.exists("/app/flask_app/venv"), \
        "Virtual environment /app/flask_app/venv does not exist"


def test_flask_app_not_empty():
    """Verify Flask app.py is not just an empty or dummy file."""
    with open("/app/flask_app/app.py", "r") as f:
        content = f.read()

    # Check for actual Flask implementation
    assert len(content) > 100, "Flask app.py appears to be empty or minimal"
    assert "Flask" in content, "Flask app.py does not import Flask"
    assert "psycopg2" in content or "psycopg" in content, \
        "Flask app.py does not use psycopg2 for database connection"
    assert "def" in content or "route" in content, \
        "Flask app.py does not define any routes"


def test_nginx_actually_proxying():
    """Verify Nginx is actually proxying requests (not serving static content)."""
    # Make request through Nginx and check response headers/content
    returncode, stdout, _ = run_command("curl -s -I http://localhost/")
    assert returncode == 0, "Failed to connect to Nginx"

    # Gunicorn adds Server header, verify it's coming from app server
    returncode, stdout, _ = run_command("curl -s http://localhost/")
    assert returncode == 0, "Failed to get response from Nginx"

    # Verify it's the Flask JSON response, not a static file
    try:
        response = json.loads(stdout)
        assert "status" in response and "message" in response, \
            "Response doesn't match Flask app structure"
    except json.JSONDecodeError:
        pytest.fail("Nginx not returning JSON from Flask app")


def test_database_connection_real():
    """Verify database connection is real, not hardcoded response."""
    # First request
    returncode, stdout1, _ = run_command("curl -s http://localhost/db-check")
    assert returncode == 0, "Failed to connect to /db-check endpoint"

    response1 = json.loads(stdout1)
    assert response1.get("database") == "connected", "Database not connected"

    # Stop PostgreSQL and verify endpoint fails
    run_command("systemctl stop postgresql")
    returncode, stdout2, _ = run_command("curl -s http://localhost/db-check")

    # Restart PostgreSQL for other tests
    run_command("systemctl start postgresql")

    # The endpoint should either fail or return error when DB is down
    if returncode == 0:
        try:
            response2 = json.loads(stdout2)
            # If it still returns "connected", it's hardcoded
            assert response2.get("database") != "connected", \
                "Database check appears to be hardcoded (still returns 'connected' when PostgreSQL is stopped)"
        except json.JSONDecodeError:
            # Connection error is acceptable
            pass


def test_users_endpoint_queries_database():
    """Verify /users endpoint actually queries the database."""
    # Insert a test user
    insert_cmd = """sudo -u postgres psql -d flaskapp_db -c "INSERT INTO users (name, email) VALUES ('TestUser', 'test@example.com')" """
    returncode, _, _ = run_command(insert_cmd)
    assert returncode == 0, "Failed to insert test user into database"

    # Query /users endpoint
    returncode, stdout, _ = run_command("curl -s http://localhost/users")
    assert returncode == 0, "Failed to connect to /users endpoint"

    try:
        users = json.loads(stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"/users endpoint did not return valid JSON: {e}")

    assert isinstance(users, list), "Expected /users to return a list"

    # Verify our test user appears in the response
    user_found = any(
        user.get("name") == "TestUser" and user.get("email") == "test@example.com"
        for user in users
    )
    assert user_found, "Test user not found in /users response - endpoint may not be querying database"

    # Cleanup
    run_command("""sudo -u postgres psql -d flaskapp_db -c "DELETE FROM users WHERE name='TestUser'" """)


def test_ufw_default_deny():
    """Verify UFW has default deny policy for incoming traffic."""
    returncode, stdout, _ = run_command("ufw status verbose")
    assert returncode == 0, "Failed to check UFW status"
    assert "deny (incoming)" in stdout.lower() or "default: deny" in stdout.lower(), \
        "UFW does not have default deny policy for incoming traffic"


def test_flask_app_directory_structure():
    """Verify Flask app is in correct directory with proper structure."""
    assert os.path.isdir("/app/flask_app"), "Directory /app/flask_app does not exist"
    assert os.path.isfile("/app/flask_app/app.py"), "File /app/flask_app/app.py does not exist"
    assert os.path.isfile("/app/flask_app/requirements.txt"), \
        "File /app/flask_app/requirements.txt does not exist"
    assert os.path.isdir("/app/flask_app/venv"), \
        "Virtual environment /app/flask_app/venv does not exist"


def test_gunicorn_process_running():
    """Verify Gunicorn process is actually running."""
    returncode, stdout, _ = run_command("ps aux | grep gunicorn | grep -v grep")
    assert returncode == 0, "Gunicorn process not found"
    assert "gunicorn" in stdout, "Gunicorn process not running"

    # Verify it's binding to correct address
    returncode, stdout, _ = run_command("netstat -tlnp | grep 8000 || ss -tlnp | grep 8000")
    assert returncode == 0, "Gunicorn not listening on port 8000"
    assert "127.0.0.1:8000" in stdout or "localhost:8000" in stdout, \
        "Gunicorn not bound to 127.0.0.1:8000"


def test_nginx_listening_port_80():
    """Verify Nginx is listening on port 80."""
    returncode, stdout, _ = run_command("netstat -tlnp | grep :80 || ss -tlnp | grep :80")
    assert returncode == 0, "Nginx not listening on port 80"
    assert "nginx" in stdout.lower() or ":80" in stdout, \
        "Port 80 not bound to Nginx"


def test_systemd_service_restart_policy():
    """Verify Flask service has restart policy configured."""
    with open("/etc/systemd/system/flaskapp.service", "r") as f:
        service_config = f.read()

    # Check for restart configuration (on-failure, always, etc.)
    assert "Restart=" in service_config, "No restart policy configured"
    restart_line = [line for line in service_config.split("\n") if "Restart=" in line][0]
    assert "Restart=no" not in restart_line, "Restart policy is set to 'no'"


def test_flask_requirements_installed():
    """Verify Flask dependencies are installed in venv."""
    returncode, stdout, _ = run_command("/app/flask_app/venv/bin/pip list")
    assert returncode == 0, "Failed to list installed packages"

    assert "Flask" in stdout, "Flask not installed in virtual environment"
    assert "gunicorn" in stdout, "Gunicorn not installed in virtual environment"
    assert "psycopg2" in stdout, "psycopg2 not installed in virtual environment"


def test_postgresql_user_privileges():
    """Verify flaskapp_user has privileges on flaskapp_db."""
    # Try to connect as flaskapp_user and query
    returncode, stdout, _ = run_command(
        "PGPASSWORD='securepass123' psql -U flaskapp_user -d flaskapp_db -h localhost -c 'SELECT 1' -t"
    )
    assert returncode == 0, "User flaskapp_user cannot connect to flaskapp_db"
    assert "1" in stdout, "User flaskapp_user cannot query database"


def test_nginx_config_valid():
    """Verify Nginx configuration is syntactically valid."""
    returncode, stdout, stderr = run_command("nginx -t")
    assert returncode == 0, f"Nginx configuration test failed: {stderr}"
    assert "successful" in stdout or "successful" in stderr, \
        "Nginx configuration validation did not report success"


def test_all_services_survive_reboot_simulation():
    """Verify services are enabled to start on boot."""
    # Check PostgreSQL
    returncode, stdout, _ = run_command("systemctl is-enabled postgresql")
    assert returncode == 0 and "enabled" in stdout, "PostgreSQL not enabled for boot"

    # Check Nginx
    returncode, stdout, _ = run_command("systemctl is-enabled nginx")
    assert returncode == 0 and "enabled" in stdout, "Nginx not enabled for boot"

    # Check Flask app
    returncode, stdout, _ = run_command("systemctl is-enabled flaskapp")
    assert returncode == 0 and "enabled" in stdout, "Flask app not enabled for boot"
