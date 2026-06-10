"""
Tests for the static site generator with nginx and Git hooks.

Verifies:
1. Bare Git repository structure and validity
2. Post-receive hook existence and executability
3. Site output directory with correctly converted HTML files
4. Directory structure preservation during conversion
5. HTML content correctness (not empty/dummy files)
6. nginx running and serving on port 80
7. End-to-end pipeline: push new markdown -> HTML generated -> served via HTTP
"""

import os
import subprocess
import stat
import time


# ============================================================
# Paths
# ============================================================
BARE_REPO = "/app/site-repo.git"
HOOK_PATH = os.path.join(BARE_REPO, "hooks", "post-receive")
SITE_OUTPUT = "/app/site-output"
WORKDIR = "/app/site-workdir"

# Expected HTML files from the test data
EXPECTED_HTML_FILES = [
    "index.html",
    "about.html",
    "docs/intro.html",
    "docs/guide.html",
]


# ============================================================
# 1. Bare Git Repository Tests
# ============================================================

def test_bare_repo_directory_exists():
    """The bare repo directory must exist."""
    assert os.path.isdir(BARE_REPO), f"Bare repo directory not found at {BARE_REPO}"


def test_bare_repo_is_valid():
    """git rev-parse --is-bare-repository must return 'true'."""
    result = subprocess.run(
        ["git", "rev-parse", "--is-bare-repository"],
        cwd=BARE_REPO,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"git rev-parse failed: {result.stderr}"
    assert result.stdout.strip() == "true", (
        f"Expected bare repository, got: {result.stdout.strip()}"
    )


def test_bare_repo_has_commits():
    """The bare repo should have at least one commit (HEAD is valid)."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=BARE_REPO,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Bare repo has no commits or invalid HEAD: {result.stderr}"
    )


# ============================================================
# 2. Post-receive Hook Tests
# ============================================================

def test_hook_file_exists():
    """The post-receive hook file must exist."""
    assert os.path.isfile(HOOK_PATH), f"Hook not found at {HOOK_PATH}"


def test_hook_is_executable():
    """The post-receive hook must be executable."""
    assert os.path.isfile(HOOK_PATH), f"Hook not found at {HOOK_PATH}"
    mode = os.stat(HOOK_PATH).st_mode
    assert mode & stat.S_IXUSR, "Hook is not executable by owner"


def test_hook_contains_pandoc_reference():
    """The hook should reference pandoc for markdown conversion."""
    with open(HOOK_PATH, "r") as f:
        content = f.read().lower()
    assert "pandoc" in content, (
        "Hook does not reference pandoc — markdown conversion may not work"
    )


def test_hook_references_site_output():
    """The hook should reference the site-output directory."""
    with open(HOOK_PATH, "r") as f:
        content = f.read()
    assert "site-output" in content, (
        "Hook does not reference /app/site-output — output may go to wrong location"
    )


# ============================================================
# 3. Site Output Tests
# ============================================================

def test_site_output_directory_exists():
    """The site-output directory must exist."""
    assert os.path.isdir(SITE_OUTPUT), f"Site output directory not found at {SITE_OUTPUT}"


def test_index_html_exists():
    """index.html must exist in site-output (from index.md)."""
    path = os.path.join(SITE_OUTPUT, "index.html")
    assert os.path.isfile(path), f"index.html not found at {path}"


def test_about_html_exists():
    """about.html must exist in site-output (from about.md)."""
    path = os.path.join(SITE_OUTPUT, "about.html")
    assert os.path.isfile(path), f"about.html not found at {path}"


def test_docs_intro_html_exists():
    """docs/intro.html must exist — verifies subdirectory structure preservation."""
    path = os.path.join(SITE_OUTPUT, "docs", "intro.html")
    assert os.path.isfile(path), f"docs/intro.html not found at {path}"


def test_docs_guide_html_exists():
    """docs/guide.html must exist — verifies subdirectory structure preservation."""
    path = os.path.join(SITE_OUTPUT, "docs", "guide.html")
    assert os.path.isfile(path), f"docs/guide.html not found at {path}"


def test_no_md_files_in_output():
    """site-output should contain .html files, not raw .md files."""
    for root, dirs, files in os.walk(SITE_OUTPUT):
        for f in files:
            assert not f.endswith(".md"), (
                f"Raw markdown file found in site-output: {os.path.join(root, f)}"
            )


# ============================================================
# 4. HTML Content Correctness Tests
# ============================================================

def test_index_html_has_content():
    """index.html must not be empty and must contain converted markdown content."""
    path = os.path.join(SITE_OUTPUT, "index.html")
    assert os.path.isfile(path), f"index.html not found"
    content = open(path, "r").read().strip()
    assert len(content) > 20, f"index.html appears empty or too small ({len(content)} chars)"
    # The original index.md has "# Hello World" which pandoc converts to an h1
    # Check for the text content regardless of exact HTML tags
    assert "Hello World" in content, (
        "index.html does not contain 'Hello World' from index.md"
    )


def test_index_html_is_valid_html():
    """index.html should contain HTML markup (not raw markdown)."""
    path = os.path.join(SITE_OUTPUT, "index.html")
    assert os.path.isfile(path), f"index.html not found"
    content = open(path, "r").read()
    # pandoc output should contain at least some HTML tags
    has_html_tags = "<" in content and ">" in content
    assert has_html_tags, "index.html does not appear to contain HTML tags"


def test_about_html_has_content():
    """about.html must contain converted content from about.md."""
    path = os.path.join(SITE_OUTPUT, "about.html")
    assert os.path.isfile(path), f"about.html not found"
    content = open(path, "r").read().strip()
    assert len(content) > 20, f"about.html appears empty or too small"
    # about.md contains "# About" and list items
    assert "About" in content, "about.html missing 'About' heading content"


def test_docs_guide_html_has_content():
    """docs/guide.html must contain converted content from docs/guide.md."""
    path = os.path.join(SITE_OUTPUT, "docs", "guide.html")
    assert os.path.isfile(path), f"docs/guide.html not found"
    content = open(path, "r").read().strip()
    assert len(content) > 20, f"docs/guide.html appears empty or too small"
    # guide.md contains "# User Guide" and "## Installation"
    assert "User Guide" in content, "docs/guide.html missing 'User Guide' content"


def test_docs_intro_html_has_content():
    """docs/intro.html must contain converted content from docs/intro.md."""
    path = os.path.join(SITE_OUTPUT, "docs", "intro.html")
    assert os.path.isfile(path), f"docs/intro.html not found"
    content = open(path, "r").read().strip()
    assert len(content) > 20, f"docs/intro.html appears empty or too small"
    assert "Introduction" in content, "docs/intro.html missing 'Introduction' content"


# ============================================================
# 5. Working Clone Tests
# ============================================================

def test_workdir_exists():
    """The working clone directory must exist."""
    assert os.path.isdir(WORKDIR), f"Working clone not found at {WORKDIR}"


def test_workdir_is_git_repo():
    """The working clone must be a valid (non-bare) git repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=WORKDIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Working clone is not a git repo: {result.stderr}"
    assert result.stdout.strip() == "true"


def test_workdir_remote_points_to_bare_repo():
    """The working clone's origin should point to the bare repo."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=WORKDIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Could not get remote URL: {result.stderr}"
    url = result.stdout.strip()
    # Accept both absolute path and file:// URL
    assert "site-repo.git" in url, (
        f"Origin remote does not point to site-repo.git: {url}"
    )


# ============================================================
# 6. nginx Tests
# ============================================================

def _ensure_nginx_running():
    """Helper: try to start nginx if it's not running."""
    result = subprocess.run(["pgrep", "nginx"], capture_output=True)
    if result.returncode != 0:
        # Try to start nginx
        subprocess.run(["nginx"], capture_output=True)
        time.sleep(1)


def test_nginx_is_running():
    """nginx process must be running."""
    _ensure_nginx_running()
    result = subprocess.run(["pgrep", "nginx"], capture_output=True, text=True)
    assert result.returncode == 0, "nginx is not running"


def test_nginx_config_is_valid():
    """nginx configuration must pass syntax check."""
    result = subprocess.run(
        ["nginx", "-t"],
        capture_output=True,
        text=True,
    )
    # nginx -t outputs to stderr
    combined = result.stdout + result.stderr
    assert result.returncode == 0, f"nginx config test failed: {combined}"


def test_nginx_serves_index_on_port_80():
    """curl http://localhost/ must return HTTP 200 with HTML content."""
    _ensure_nginx_running()
    time.sleep(0.5)
    result = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost/"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"curl failed: {result.stderr}"
    status_code = result.stdout.strip()
    assert status_code == "200", f"Expected HTTP 200, got {status_code}"


def test_nginx_returns_html_content():
    """curl http://localhost/ must return the converted index.html content."""
    _ensure_nginx_running()
    time.sleep(0.5)
    result = subprocess.run(
        ["curl", "-s", "http://localhost/"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"curl failed: {result.stderr}"
    body = result.stdout
    assert "Hello World" in body, (
        f"Response body does not contain 'Hello World'. Got: {body[:200]}"
    )


def test_nginx_serves_about_page():
    """curl http://localhost/about.html must return about page content."""
    _ensure_nginx_running()
    time.sleep(0.5)
    result = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost/about.html"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"curl failed: {result.stderr}"
    status_code = result.stdout.strip()
    assert status_code == "200", f"Expected HTTP 200 for about.html, got {status_code}"


def test_nginx_serves_subdirectory_page():
    """curl http://localhost/docs/guide.html must return guide page."""
    _ensure_nginx_running()
    time.sleep(0.5)
    result = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost/docs/guide.html"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"curl failed: {result.stderr}"
    status_code = result.stdout.strip()
    assert status_code == "200", f"Expected HTTP 200 for docs/guide.html, got {status_code}"


def test_nginx_returns_404_for_missing():
    """nginx must return 404 for non-existent files."""
    _ensure_nginx_running()
    time.sleep(0.5)
    result = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost/nonexistent.html"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"curl failed: {result.stderr}"
    status_code = result.stdout.strip()
    assert status_code == "404", f"Expected HTTP 404 for missing file, got {status_code}"


# ============================================================
# 7. End-to-End Pipeline Test (push new content -> HTML -> HTTP)
# ============================================================

def test_end_to_end_new_push():
    """
    Push a brand-new markdown file and verify it appears as HTML
    in site-output and is served by nginx.
    """
    _ensure_nginx_running()

    new_md = os.path.join(WORKDIR, "test-e2e.md")
    new_html = os.path.join(SITE_OUTPUT, "test-e2e.html")

    # Write a new markdown file
    with open(new_md, "w") as f:
        f.write("# End to End Test\n\nThis verifies the full pipeline.\n")

    # Configure git user if not set
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=WORKDIR, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=WORKDIR, capture_output=True,
    )

    # Stage, commit, push
    subprocess.run(["git", "add", "test-e2e.md"], cwd=WORKDIR, capture_output=True)
    commit_result = subprocess.run(
        ["git", "commit", "-m", "Add e2e test file"],
        cwd=WORKDIR, capture_output=True, text=True,
    )
    assert commit_result.returncode == 0, f"Commit failed: {commit_result.stderr}"

    # Try pushing to master or main
    push_result = subprocess.run(
        ["git", "push", "origin", "HEAD"],
        cwd=WORKDIR, capture_output=True, text=True,
    )
    assert push_result.returncode == 0, f"Push failed: {push_result.stderr}"

    # Verify the HTML file was generated
    time.sleep(1)
    assert os.path.isfile(new_html), (
        f"End-to-end test failed: {new_html} not generated after push"
    )

    # Verify content
    content = open(new_html, "r").read()
    assert "End to End Test" in content, (
        f"Generated HTML does not contain expected content. Got: {content[:200]}"
    )

    # Verify nginx serves it
    result = subprocess.run(
        ["curl", "-s", "http://localhost/test-e2e.html"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, f"curl failed: {result.stderr}"
    assert "End to End Test" in result.stdout, (
        f"nginx did not serve the new file. Got: {result.stdout[:200]}"
    )
