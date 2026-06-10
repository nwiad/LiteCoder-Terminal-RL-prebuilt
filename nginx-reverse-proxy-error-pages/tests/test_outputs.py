"""
Tests for Nginx Reverse Proxy with Custom Error Pages task.

Validates:
- Static file existence and content (error pages, Flask apps, startup script, nginx config)
- Nginx configuration correctness (upstreams, proxy rules, headers, error interception)
- Live integration (proxy routing, error page serving, 404 handling)
"""

import os
import re
import subprocess
import signal
import time

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def curl(url, extra_args=None):
    """Run curl and return (status_code, body)."""
    cmd = ["curl", "-s", "-o", "/dev/stdout", "-w", "\n%{http_code}", url]
    if extra_args:
        cmd = ["curl", "-s"] + extra_args + ["-o", "/dev/stdout", "-w", "\n%{http_code}", url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        lines = result.stdout.rsplit("\n", 1)
        if len(lines) == 2:
            body, code = lines
            return int(code), body
        return None, result.stdout
    except Exception:
        return None, ""


# ===========================================================================
# 1. ERROR PAGE FILE EXISTENCE & CONTENT
# ===========================================================================

class TestErrorPages:
    """Verify custom error page files exist with required content."""

    ERROR_PAGES = {
        "/app/error_pages/404.html": ("Error 404", "Page Not Found"),
        "/app/error_pages/500.html": ("Error 500", "Internal Server Error"),
        "/app/error_pages/502.html": ("Error 502", "Bad Gateway"),
        "/app/error_pages/503.html": ("Error 503", "Service Unavailable"),
    }

    def test_error_page_files_exist(self):
        for path in self.ERROR_PAGES:
            assert os.path.isfile(path), f"Missing error page: {path}"

    def test_error_pages_not_empty(self):
        for path in self.ERROR_PAGES:
            content = read_file(path)
            assert content is not None and len(content.strip()) > 20, (
                f"Error page {path} is empty or too small"
            )

    def test_error_pages_contain_required_text(self):
        for path, (code_text, desc_text) in self.ERROR_PAGES.items():
            content = read_file(path)
            assert content is not None, f"Cannot read {path}"
            assert code_text in content, (
                f"{path} must contain '{code_text}'"
            )
            assert desc_text in content, (
                f"{path} must contain '{desc_text}'"
            )

    def test_error_pages_are_valid_html(self):
        for path in self.ERROR_PAGES:
            content = read_file(path)
            assert content is not None, f"Cannot read {path}"
            lower = content.lower()
            assert "<html" in lower, f"{path} missing <html> tag"
            assert "<body" in lower, f"{path} missing <body> tag"


# ===========================================================================
# 2. BACKEND SERVICE FILES
# ===========================================================================

class TestBackendServices:
    """Verify Flask backend service files exist with correct structure."""

    def test_product_service_exists(self):
        assert os.path.isfile("/app/product_service.py"), (
            "Missing /app/product_service.py"
        )

    def test_order_service_exists(self):
        assert os.path.isfile("/app/order_service.py"), (
            "Missing /app/order_service.py"
        )

    def test_product_service_port(self):
        content = read_file("/app/product_service.py")
        assert content is not None
        assert "3000" in content, (
            "product_service.py must bind to port 3000"
        )

    def test_order_service_port(self):
        content = read_file("/app/order_service.py")
        assert content is not None
        assert "4000" in content, (
            "order_service.py must bind to port 4000"
        )

    def test_product_service_has_products_route(self):
        content = read_file("/app/product_service.py")
        assert content is not None
        assert "/products" in content, (
            "product_service.py must define /products route"
        )

    def test_order_service_has_orders_route(self):
        content = read_file("/app/order_service.py")
        assert content is not None
        assert "/orders" in content, (
            "order_service.py must define /orders route"
        )


# ===========================================================================
# 3. STARTUP SCRIPT
# ===========================================================================

class TestStartupScript:
    """Verify the startup script exists and is executable."""

    def test_startup_script_exists(self):
        assert os.path.isfile("/app/start_services.sh"), (
            "Missing /app/start_services.sh"
        )

    def test_startup_script_is_executable(self):
        assert os.access("/app/start_services.sh", os.X_OK), (
            "/app/start_services.sh must be executable"
        )

    def test_startup_script_references_both_services(self):
        content = read_file("/app/start_services.sh")
        assert content is not None
        assert "product_service" in content, (
            "start_services.sh must reference product_service"
        )
        assert "order_service" in content, (
            "start_services.sh must reference order_service"
        )

    def test_startup_script_writes_pid_files(self):
        content = read_file("/app/start_services.sh")
        assert content is not None
        assert "product_service.pid" in content, (
            "start_services.sh must write product_service.pid"
        )
        assert "order_service.pid" in content, (
            "start_services.sh must write order_service.pid"
        )


# ===========================================================================
# 4. NGINX CONFIGURATION
# ===========================================================================

class TestNginxConfig:
    """Verify Nginx reverse proxy configuration."""

    CONFIG_PATH = "/etc/nginx/conf.d/reverse_proxy.conf"

    def _read_config(self):
        content = read_file(self.CONFIG_PATH)
        assert content is not None, f"Missing {self.CONFIG_PATH}"
        return content

    def test_config_file_exists(self):
        assert os.path.isfile(self.CONFIG_PATH), (
            f"Missing Nginx config at {self.CONFIG_PATH}"
        )

    def test_config_not_empty(self):
        content = self._read_config()
        assert len(content.strip()) > 50, "Nginx config is too small"

    def test_product_upstream_defined(self):
        content = self._read_config()
        assert "product_backend" in content, (
            "Config must define upstream 'product_backend'"
        )
        assert "127.0.0.1:3000" in content or "localhost:3000" in content, (
            "product_backend must point to port 3000"
        )

    def test_order_upstream_defined(self):
        content = self._read_config()
        assert "order_backend" in content, (
            "Config must define upstream 'order_backend'"
        )
        assert "127.0.0.1:4000" in content or "localhost:4000" in content, (
            "order_backend must point to port 4000"
        )

    def test_listen_port_80(self):
        content = self._read_config()
        assert "listen" in content and "80" in content, (
            "Nginx must listen on port 80"
        )

    def test_proxy_headers_configured(self):
        content = self._read_config()
        assert "X-Real-IP" in content, "Config must set X-Real-IP header"
        assert "X-Forwarded-For" in content, (
            "Config must set X-Forwarded-For header"
        )
        assert "proxy_set_header" in content and "Host" in content, (
            "Config must set Host header"
        )

    def test_proxy_intercept_errors_enabled(self):
        content = self._read_config()
        assert "proxy_intercept_errors" in content, (
            "Config must enable proxy_intercept_errors"
        )
        assert re.search(r"proxy_intercept_errors\s+on", content), (
            "proxy_intercept_errors must be set to 'on'"
        )

    def test_error_page_directives(self):
        content = self._read_config()
        for code in ["404", "500", "502", "503"]:
            assert re.search(rf"error_page\s+{code}", content), (
                f"Config must have error_page directive for {code}"
            )

    def test_products_location_block(self):
        content = self._read_config()
        assert re.search(r"location\s+/products", content), (
            "Config must have location block for /products"
        )
        assert "product_backend" in content, (
            "Products location must proxy to product_backend"
        )

    def test_orders_location_block(self):
        content = self._read_config()
        assert re.search(r"location\s+/orders", content), (
            "Config must have location block for /orders"
        )
        assert "order_backend" in content, (
            "Orders location must proxy to order_backend"
        )

    def test_nginx_config_valid(self):
        """nginx -t must pass without errors."""
        result = subprocess.run(
            ["nginx", "-t"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, (
            f"nginx -t failed: {result.stderr}"
        )


# ===========================================================================
# 5. LIVE INTEGRATION TESTS
# ===========================================================================

class TestLiveIntegration:
    """
    Integration tests that verify the full stack is working:
    Nginx proxying to Flask backends, custom error pages served.

    These tests assume test.sh has already started the services and Nginx.
    """

    def test_products_endpoint_returns_200(self):
        """GET /products through Nginx returns 200."""
        code, body = curl("http://localhost/products")
        assert code == 200, (
            f"Expected 200 for /products, got {code}"
        )

    def test_products_endpoint_returns_json(self):
        """GET /products returns JSON with service=product."""
        code, body = curl("http://localhost/products")
        assert code == 200, f"Expected 200, got {code}"
        assert '"service"' in body and '"product"' in body, (
            f"/products response must contain service:product, got: {body[:200]}"
        )

    def test_orders_endpoint_returns_200(self):
        """GET /orders through Nginx returns 200."""
        code, body = curl("http://localhost/orders")
        assert code == 200, (
            f"Expected 200 for /orders, got {code}"
        )

    def test_orders_endpoint_returns_json(self):
        """GET /orders returns JSON with service=order."""
        code, body = curl("http://localhost/orders")
        assert code == 200, f"Expected 200, got {code}"
        assert '"service"' in body and '"order"' in body, (
            f"/orders response must contain service:order, got: {body[:200]}"
        )

    def test_nonexistent_path_returns_404(self):
        """GET /nonexistent returns 404."""
        code, body = curl("http://localhost/nonexistent")
        assert code == 404, (
            f"Expected 404 for /nonexistent, got {code}"
        )

    def test_404_serves_custom_error_page(self):
        """404 response body contains custom error page content."""
        code, body = curl("http://localhost/nonexistent")
        assert code == 404
        assert "Error 404" in body, (
            f"404 body must contain 'Error 404', got: {body[:300]}"
        )

    def test_404_page_contains_page_not_found(self):
        """404 response body contains 'Page Not Found'."""
        code, body = curl("http://localhost/nonexistent")
        assert code == 404
        assert "Page Not Found" in body, (
            f"404 body must contain 'Page Not Found', got: {body[:300]}"
        )

    def test_backend_error_returns_custom_500_page(self):
        """
        When backend returns 500, Nginx should intercept and serve
        the custom 500 error page (proxy_intercept_errors on).
        """
        code, body = curl("http://localhost/products/error")
        assert code == 500, (
            f"Expected 500 for /products/error, got {code}"
        )
        assert "Error 500" in body, (
            f"500 body must contain 'Error 500' (custom page), got: {body[:300]}"
        )

    def test_backend_error_contains_internal_server_error(self):
        """Custom 500 page must contain 'Internal Server Error'."""
        code, body = curl("http://localhost/products/error")
        assert code == 500
        assert "Internal Server Error" in body, (
            f"500 body must contain 'Internal Server Error', got: {body[:300]}"
        )

    def test_stopped_backend_returns_502(self):
        """
        When a backend is stopped, Nginx should return 502 with
        the custom error page.
        """
        # Read product service PID and kill it
        pid_content = read_file("/app/product_service.pid")
        if pid_content is not None:
            pid = pid_content.strip()
            try:
                os.kill(int(pid), signal.SIGTERM)
                time.sleep(2)
            except (ProcessLookupError, ValueError):
                pass

        # Also try to kill by process name as fallback
        subprocess.run(
            ["pkill", "-f", "product_service.py"],
            capture_output=True, timeout=5
        )
        time.sleep(2)

        code, body = curl("http://localhost/products")
        assert code == 502, (
            f"Expected 502 when backend is down, got {code}"
        )
        assert "Error 502" in body, (
            f"502 body must contain 'Error 502', got: {body[:300]}"
        )
        assert "Bad Gateway" in body, (
            f"502 body must contain 'Bad Gateway', got: {body[:300]}"
        )
