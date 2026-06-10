import os
import json
import subprocess
import time


def test_server_status_json_exists():
    """Verify server-status.json exists"""
    assert os.path.exists("/app/server-status.json"), "server-status.json not found at /app/"


def test_server_status_json_structure():
    """Verify server-status.json has correct structure and values"""
    with open("/app/server-status.json", "r") as f:
        status = json.load(f)

    # Check all required fields exist
    required_fields = ["server_running", "port", "git_backend_enabled",
                      "authentication_enabled", "repositories", "test_user"]
    for field in required_fields:
        assert field in status, f"Missing required field: {field}"

    # Verify correct values
    assert status["server_running"] == True, "Server should be running"
    assert status["port"] == 8080, "Port should be 8080"
    assert status["git_backend_enabled"] == True, "Git backend should be enabled"
    assert status["authentication_enabled"] == True, "Authentication should be enabled"
    assert "test-repo.git" in status["repositories"], "test-repo.git should be in repositories list"
    assert status["test_user"] == "gituser", "Test user should be 'gituser'"


def test_apache_config_exists():
    """Verify Apache configuration file exists"""
    assert os.path.exists("/app/apache-git.conf"), "apache-git.conf not found at /app/"


def test_apache_config_content():
    """Verify Apache configuration has required settings"""
    with open("/app/apache-git.conf", "r") as f:
        config = f.read()

    # Check critical configuration elements
    assert "Listen 8080" in config, "Apache should listen on port 8080"
    assert "GIT_PROJECT_ROOT" in config, "GIT_PROJECT_ROOT should be set"
    assert "/app/git-repos" in config, "Config should reference /app/git-repos"
    assert "git-http-backend" in config, "Git HTTP backend should be configured"
    assert "AuthType Basic" in config, "Basic authentication should be configured"
    assert "/app/.htpasswd" in config, "htpasswd file should be referenced"


def test_htpasswd_file_exists():
    """Verify htpasswd file exists and is not empty"""
    assert os.path.exists("/app/.htpasswd"), ".htpasswd not found at /app/"

    # Verify file is not empty
    with open("/app/.htpasswd", "r") as f:
        content = f.read().strip()
    assert len(content) > 0, ".htpasswd file should not be empty"
    assert "gituser:" in content, "htpasswd should contain gituser entry"


def test_git_repos_directory_exists():
    """Verify git-repos directory exists"""
    assert os.path.exists("/app/git-repos"), "git-repos directory not found at /app/"
    assert os.path.isdir("/app/git-repos"), "/app/git-repos should be a directory"


def test_bare_repository_exists():
    """Verify test-repo.git bare repository exists and is properly initialized"""
    repo_path = "/app/git-repos/test-repo.git"
    assert os.path.exists(repo_path), "test-repo.git not found"
    assert os.path.isdir(repo_path), "test-repo.git should be a directory"

    # Check for bare repository structure
    assert os.path.exists(os.path.join(repo_path, "HEAD")), "Bare repo should have HEAD file"
    assert os.path.exists(os.path.join(repo_path, "config")), "Bare repo should have config file"
    assert os.path.exists(os.path.join(repo_path, "refs")), "Bare repo should have refs directory"
    assert os.path.exists(os.path.join(repo_path, "objects")), "Bare repo should have objects directory"


def test_git_repository_config():
    """Verify Git repository has correct HTTP configuration"""
    repo_path = "/app/git-repos/test-repo.git"
    config_path = os.path.join(repo_path, "config")

    with open(config_path, "r") as f:
        config = f.read()

    # Check that HTTP receive/upload pack is enabled
    assert "receivepack" in config.lower() or "uploadpack" in config.lower(), \
        "Git config should enable HTTP operations"


def test_apache_server_running():
    """Verify Apache server is actually running"""
    result = subprocess.run(
        ["service", "apache2", "status"],
        capture_output=True,
        text=True
    )

    # Apache should be running (exit code 0 or output contains "running")
    assert result.returncode == 0 or "running" in result.stdout.lower(), \
        "Apache service should be running"


def test_port_8080_listening():
    """Verify server is listening on port 8080"""
    result = subprocess.run(
        ["netstat", "-tuln"],
        capture_output=True,
        text=True
    )

    assert ":8080" in result.stdout, "Server should be listening on port 8080"


def test_git_http_backend_accessible():
    """Verify Git HTTP backend responds (even if auth required)"""
    import requests

    # Try to access without auth - should get 401 Unauthorized
    try:
        response = requests.get("http://localhost:8080/git/test-repo.git/info/refs?service=git-upload-pack", timeout=5)
        # Should get 401 (auth required) not 404 (not found) or 500 (server error)
        assert response.status_code == 401, f"Expected 401 Unauthorized, got {response.status_code}"
    except requests.exceptions.RequestException as e:
        assert False, f"Failed to connect to Git server: {e}"


def test_git_authentication_works():
    """Verify authentication with correct credentials works"""
    import requests
    from requests.auth import HTTPBasicAuth

    # Try with correct credentials
    try:
        response = requests.get(
            "http://localhost:8080/git/test-repo.git/info/refs?service=git-upload-pack",
            auth=HTTPBasicAuth("gituser", "gitpass123"),
            timeout=5
        )
        # Should get 200 OK with valid credentials
        assert response.status_code == 200, f"Expected 200 OK with valid auth, got {response.status_code}"
        assert "service=git-upload-pack" in response.text, "Response should contain Git protocol data"
    except requests.exceptions.RequestException as e:
        assert False, f"Failed to authenticate: {e}"


def test_git_clone_operation():
    """Verify Git clone operation works end-to-end"""
    import tempfile
    import shutil

    # Create temporary directory for clone
    temp_dir = tempfile.mkdtemp()

    try:
        # Attempt to clone the repository
        result = subprocess.run(
            ["git", "clone", "http://gituser:gitpass123@localhost:8080/git/test-repo.git",
             os.path.join(temp_dir, "cloned-repo")],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Clone should succeed (even if repo is empty)
        assert result.returncode == 0, f"Git clone failed: {result.stderr}"

        # Verify cloned directory exists
        cloned_path = os.path.join(temp_dir, "cloned-repo")
        assert os.path.exists(cloned_path), "Cloned repository directory should exist"
        assert os.path.exists(os.path.join(cloned_path, ".git")), "Cloned repo should have .git directory"

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_git_push_operation():
    """Verify Git push operation works"""
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()

    try:
        # Clone the repository
        clone_path = os.path.join(temp_dir, "test-clone")
        subprocess.run(
            ["git", "clone", "http://gituser:gitpass123@localhost:8080/git/test-repo.git", clone_path],
            capture_output=True,
            timeout=10
        )

        # Configure git user for commit
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=clone_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=clone_path, capture_output=True)

        # Create a test file and commit
        test_file = os.path.join(clone_path, "test.txt")
        with open(test_file, "w") as f:
            f.write("Test content")

        subprocess.run(["git", "add", "test.txt"], cwd=clone_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Test commit"], cwd=clone_path, capture_output=True)

        # Push to remote
        result = subprocess.run(
            ["git", "push", "origin", "master"],
            cwd=clone_path,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Push should succeed
        assert result.returncode == 0, f"Git push failed: {result.stderr}"

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_authentication_blocks_invalid_credentials():
    """Verify invalid credentials are rejected"""
    import requests
    from requests.auth import HTTPBasicAuth

    # Try with wrong credentials
    response = requests.get(
        "http://localhost:8080/git/test-repo.git/info/refs?service=git-upload-pack",
        auth=HTTPBasicAuth("wronguser", "wrongpass"),
        timeout=5
    )

    # Should get 401 Unauthorized
    assert response.status_code == 401, f"Expected 401 for invalid credentials, got {response.status_code}"
