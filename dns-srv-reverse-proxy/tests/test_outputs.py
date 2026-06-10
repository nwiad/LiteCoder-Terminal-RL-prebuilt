import os
import subprocess
import time
import json
import requests
import signal
import pytest


def test_required_files_exist():
    """Test that all required files are present"""
    assert os.path.exists('/app/proxy.py'), "proxy.py must exist in /app/"
    assert os.path.exists('/app/client.py'), "client.py must exist in /app/"
    assert os.path.exists('/app/dnsmasq.conf'), "dnsmasq.conf must exist in /app/"


def test_dnsmasq_configuration():
    """Test that dnsmasq.conf has proper SRV records"""
    with open('/app/dnsmasq.conf', 'r') as f:
        content = f.read()

    # Check for SRV records
    assert '_http._tcp.services.local' in content, "SRV records must be defined for _http._tcp.services.local"
    assert 'backend1.local' in content, "backend1.local must be in dnsmasq.conf"
    assert 'backend2.local' in content, "backend2.local must be in dnsmasq.conf"

    # Check for A records
    assert 'address=/backend1.local/' in content or 'address=/backend2.local/' in content, \
        "A records must be defined for backend hostnames"


def test_backend_services_respond():
    """Test that backend services are running and respond correctly"""
    # Start dnsmasq
    dnsmasq_proc = subprocess.Popen(['dnsmasq', '-C', '/app/dnsmasq.conf', '-d'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)

    # Start backend services
    backend_procs = []
    for i in range(1, 5):
        proc = subprocess.Popen(['python3', '/app/proxy.py'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        backend_procs.append(proc)

    time.sleep(3)

    # Test at least one backend responds
    backend_found = False
    for port in [8001, 8002, 8003, 8004]:
        try:
            response = requests.get(f'http://localhost:{port}/health', timeout=2)
            if response.status_code == 200:
                data = response.json()
                assert 'status' in data, "Health endpoint must return 'status' field"
                assert data['status'] == 'healthy', "Health status must be 'healthy'"
                assert 'service' in data, "Health endpoint must return 'service' field"
                backend_found = True
                break
        except:
            continue

    # Cleanup
    for proc in backend_procs:
        proc.terminate()
    dnsmasq_proc.terminate()

    assert backend_found, "At least one backend service must be running and responding"


def test_proxy_listens_on_port_8000():
    """Test that the reverse proxy listens on port 8000"""
    # Start dnsmasq
    dnsmasq_proc = subprocess.Popen(['dnsmasq', '-C', '/app/dnsmasq.conf', '-d'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)

    # Start proxy
    proxy_proc = subprocess.Popen(['python3', '/app/proxy.py'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)

    # Test proxy responds
    try:
        response = requests.get('http://localhost:8000/', timeout=5)
        proxy_responding = response.status_code in [200, 503]  # 503 if no backends
    except:
        proxy_responding = False

    # Cleanup
    proxy_proc.terminate()
    dnsmasq_proc.terminate()

    assert proxy_responding, "Proxy must listen on port 8000 and respond to requests"


def test_proxy_routes_to_backends():
    """Test that proxy successfully routes requests to backend services"""
    # Start dnsmasq
    dnsmasq_proc = subprocess.Popen(['dnsmasq', '-C', '/app/dnsmasq.conf', '-d'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)

    # Create and start mock backends
    backend_script = """
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class BackendHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "healthy", "service": self.server.service_name}
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"message": f"Response from {self.server.service_name}", "port": self.server.server_port}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_backend(port, name):
    server = HTTPServer(('0.0.0.0', port), BackendHandler)
    server.service_name = name
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1])
    name = sys.argv[2]
    start_backend(port, name)
"""

    with open('/tmp/test_backend.py', 'w') as f:
        f.write(backend_script)

    backend_procs = []
    for i in range(1, 5):
        proc = subprocess.Popen(['python3', '/tmp/test_backend.py', str(8000 + i), f'backend{i}'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        backend_procs.append(proc)

    time.sleep(3)

    # Start proxy
    proxy_proc = subprocess.Popen(['python3', '/app/proxy.py'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)

    # Test proxy routes requests
    success_count = 0
    backend_responses = set()

    for _ in range(10):
        try:
            response = requests.get('http://localhost:8000/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'message' in data or 'port' in data:
                    success_count += 1
                    if 'port' in data:
                        backend_responses.add(data['port'])
        except:
            pass
        time.sleep(0.5)

    # Cleanup
    proxy_proc.terminate()
    for proc in backend_procs:
        proc.terminate()
    dnsmasq_proc.terminate()

    assert success_count >= 5, "Proxy must successfully route at least 5 out of 10 requests to backends"


def test_proxy_returns_503_when_no_backends():
    """Test that proxy returns 503 when no healthy backends are available"""
    # Start dnsmasq
    dnsmasq_proc = subprocess.Popen(['dnsmasq', '-C', '/app/dnsmasq.conf', '-d'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)

    # Start proxy WITHOUT backends
    proxy_proc = subprocess.Popen(['python3', '/app/proxy.py'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)

    # Test proxy returns 503
    try:
        response = requests.get('http://localhost:8000/', timeout=5)
        status_code = response.status_code
    except:
        status_code = None

    # Cleanup
    proxy_proc.terminate()
    dnsmasq_proc.terminate()

    assert status_code == 503, "Proxy must return 503 Service Unavailable when no healthy backends exist"


def test_client_script_executes():
    """Test that client.py can execute and make requests"""
    # Start dnsmasq
    dnsmasq_proc = subprocess.Popen(['dnsmasq', '-C', '/app/dnsmasq.conf', '-d'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)

    # Create and start mock backends
    backend_script = """
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class BackendHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "healthy", "service": self.server.service_name}
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"message": f"Response from {self.server.service_name}", "port": self.server.server_port}
            self.wfile.write(json.dumps(response).encode())

def start_backend(port, name):
    server = HTTPServer(('0.0.0.0', port), BackendHandler)
    server.service_name = name
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1])
    name = sys.argv[2]
    start_backend(port, name)
"""

    with open('/tmp/test_backend.py', 'w') as f:
        f.write(backend_script)

    backend_procs = []
    for i in range(1, 3):  # Start 2 backends
        proc = subprocess.Popen(['python3', '/tmp/test_backend.py', str(8000 + i), f'backend{i}'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        backend_procs.append(proc)

    time.sleep(3)

    # Start proxy
    proxy_proc = subprocess.Popen(['python3', '/app/proxy.py'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)

    # Run client script
    try:
        result = subprocess.run(['python3', '/app/client.py', '5'],
                                capture_output=True, text=True, timeout=15)
        client_output = result.stdout
        client_executed = result.returncode == 0
    except:
        client_output = ""
        client_executed = False

    # Cleanup
    proxy_proc.terminate()
    for proc in backend_procs:
        proc.terminate()
    dnsmasq_proc.terminate()

    assert client_executed, "client.py must execute successfully"
    assert len(client_output) > 0, "client.py must produce output"
    assert 'Request' in client_output or 'message' in client_output or 'port' in client_output, \
        "client.py output must show request results"


def test_client_accepts_command_line_argument():
    """Test that client.py accepts number of requests as argument"""
    # Check if client.py uses sys.argv
    with open('/app/client.py', 'r') as f:
        content = f.read()

    assert 'sys.argv' in content or 'argparse' in content, \
        "client.py must accept command-line arguments for number of requests"


def test_load_distribution():
    """Test that requests are distributed across multiple backends"""
    # Start dnsmasq
    dnsmasq_proc = subprocess.Popen(['dnsmasq', '-C', '/app/dnsmasq.conf', '-d'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)

    # Create and start mock backends
    backend_script = """
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class BackendHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "healthy", "service": self.server.service_name}
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"message": f"Response from {self.server.service_name}", "port": self.server.server_port}
            self.wfile.write(json.dumps(response).encode())

def start_backend(port, name):
    server = HTTPServer(('0.0.0.0', port), BackendHandler)
    server.service_name = name
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1])
    name = sys.argv[2]
    start_backend(port, name)
"""

    with open('/tmp/test_backend.py', 'w') as f:
        f.write(backend_script)

    backend_procs = []
    for i in range(1, 4):  # Start 3 backends
        proc = subprocess.Popen(['python3', '/tmp/test_backend.py', str(8000 + i), f'backend{i}'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        backend_procs.append(proc)

    time.sleep(3)

    # Start proxy
    proxy_proc = subprocess.Popen(['python3', '/app/proxy.py'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)

    # Make multiple requests and track which backends respond
    backend_ports = set()

    for _ in range(20):
        try:
            response = requests.get('http://localhost:8000/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'port' in data:
                    backend_ports.add(data['port'])
        except:
            pass
        time.sleep(0.3)

    # Cleanup
    proxy_proc.terminate()
    for proc in backend_procs:
        proc.terminate()
    dnsmasq_proc.terminate()

    # At least 2 different backends should have responded (demonstrating distribution)
    assert len(backend_ports) >= 2, \
        f"Requests must be distributed across multiple backends (found {len(backend_ports)} unique backends)"
