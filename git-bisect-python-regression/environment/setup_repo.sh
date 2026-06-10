#!/bin/bash
set -e

# Create the repository directory
mkdir -p /app/repo
cd /app/repo

# Initialize git repository
git init
git config user.email "test@example.com"
git config user.name "Test User"

# Commit 1: Initial working service
cat > main.py << 'EOF'
#!/usr/bin/env python3
import sys

def initialize_service():
    """Initialize the web service"""
    config = {
        'host': '0.0.0.0',
        'port': 8080
    }
    return config

def main():
    print("Starting web service...")
    config = initialize_service()
    print(f"Service initialized on {config['host']}:{config['port']}")
    print("Service started successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF
chmod +x main.py
git add main.py
git commit -m "Initial commit: Basic web service"

# Commit 2: Add logging
cat > main.py << 'EOF'
#!/usr/bin/env python3
import sys

def initialize_service():
    """Initialize the web service"""
    config = {
        'host': '0.0.0.0',
        'port': 8080,
        'debug': False
    }
    return config

def main():
    print("Starting web service...")
    config = initialize_service()
    print(f"Service initialized on {config['host']}:{config['port']}")
    print(f"Debug mode: {config['debug']}")
    print("Service started successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF
git add main.py
git commit -m "Add debug configuration"

# Commit 3: Add database config
cat > main.py << 'EOF'
#!/usr/bin/env python3
import sys

def initialize_service():
    """Initialize the web service"""
    config = {
        'host': '0.0.0.0',
        'port': 8080,
        'debug': False,
        'database': 'sqlite:///app.db'
    }
    return config

def main():
    print("Starting web service...")
    config = initialize_service()
    print(f"Service initialized on {config['host']}:{config['port']}")
    print(f"Debug mode: {config['debug']}")
    print(f"Database: {config['database']}")
    print("Service started successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF
git add main.py
git commit -m "Add database configuration"

# Commit 4: Add request handler
cat > main.py << 'EOF'
#!/usr/bin/env python3
import sys

def initialize_service():
    """Initialize the web service"""
    config = {
        'host': '0.0.0.0',
        'port': 8080,
        'debug': False,
        'database': 'sqlite:///app.db'
    }
    return config

def handle_request(path):
    """Handle incoming requests"""
    return f"Response for {path}"

def main():
    print("Starting web service...")
    config = initialize_service()
    print(f"Service initialized on {config['host']}:{config['port']}")
    print(f"Debug mode: {config['debug']}")
    print(f"Database: {config['database']}")
    print("Request handler registered")
    print("Service started successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF
git add main.py
git commit -m "Add request handler"

# Commit 5: Add middleware support
cat > main.py << 'EOF'
#!/usr/bin/env python3
import sys

def initialize_service():
    """Initialize the web service"""
    config = {
        'host': '0.0.0.0',
        'port': 8080,
        'debug': False,
        'database': 'sqlite:///app.db',
        'middleware': []
    }
    return config

def handle_request(path):
    """Handle incoming requests"""
    return f"Response for {path}"

def main():
    print("Starting web service...")
    config = initialize_service()
    print(f"Service initialized on {config['host']}:{config['port']}")
    print(f"Debug mode: {config['debug']}")
    print(f"Database: {config['database']}")
    print("Request handler registered")
    print("Middleware stack initialized")
    print("Service started successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF
git add main.py
git commit -m "Add middleware support"

# Commit 6: BUG - Introduce syntax error
cat > main.py << 'EOF'
#!/usr/bin/env python3
import sys

def initialize_service():
    """Initialize the web service"""
    config = {
        'host': '0.0.0.0',
        'port': 8080,
        'debug': False,
        'database': 'sqlite:///app.db',
        'middleware': [],
        'auth': {'enabled': True, 'type': 'jwt'
    }
    return config

def handle_request(path):
    """Handle incoming requests"""
    return f"Response for {path}"

def main():
    print("Starting web service...")
    config = initialize_service()
    print(f"Service initialized on {config['host']}:{config['port']}")
    print(f"Debug mode: {config['debug']}")
    print(f"Database: {config['database']}")
    print("Request handler registered")
    print("Middleware stack initialized")
    print(f"Authentication: {config['auth']['type']}")
    print("Service started successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF
git add main.py
git commit -m "Add authentication configuration"

# Commit 7: Add rate limiting
cat > main.py << 'EOF'
#!/usr/bin/env python3
import sys

def initialize_service():
    """Initialize the web service"""
    config = {
        'host': '0.0.0.0',
        'port': 8080,
        'debug': False,
        'database': 'sqlite:///app.db',
        'middleware': [],
        'auth': {'enabled': True, 'type': 'jwt',
        'rate_limit': {'requests': 100, 'window': 60}
    }
    return config

def handle_request(path):
    """Handle incoming requests"""
    return f"Response for {path}"

def main():
    print("Starting web service...")
    config = initialize_service()
    print(f"Service initialized on {config['host']}:{config['port']}")
    print(f"Debug mode: {config['debug']}")
    print(f"Database: {config['database']}")
    print("Request handler registered")
    print("Middleware stack initialized")
    print(f"Authentication: {config['auth']['type']}")
    print(f"Rate limit: {config['rate_limit']['requests']}/min")
    print("Service started successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF
git add main.py
git commit -m "Add rate limiting"

# Commit 8: Add CORS support
cat > main.py << 'EOF'
#!/usr/bin/env python3
import sys

def initialize_service():
    """Initialize the web service"""
    config = {
        'host': '0.0.0.0',
        'port': 8080,
        'debug': False,
        'database': 'sqlite:///app.db',
        'middleware': [],
        'auth': {'enabled': True, 'type': 'jwt',
        'rate_limit': {'requests': 100, 'window': 60},
        'cors': {'enabled': True, 'origins': ['*']}
    }
    return config

def handle_request(path):
    """Handle incoming requests"""
    return f"Response for {path}"

def main():
    print("Starting web service...")
    config = initialize_service()
    print(f"Service initialized on {config['host']}:{config['port']}")
    print(f"Debug mode: {config['debug']}")
    print(f"Database: {config['database']}")
    print("Request handler registered")
    print("Middleware stack initialized")
    print(f"Authentication: {config['auth']['type']}")
    print(f"Rate limit: {config['rate_limit']['requests']}/min")
    print(f"CORS enabled: {config['cors']['enabled']}")
    print("Service started successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF
git add main.py
git commit -m "Add CORS support"

# Commit 9: Add health check endpoint
cat > main.py << 'EOF'
#!/usr/bin/env python3
import sys

def initialize_service():
    """Initialize the web service"""
    config = {
        'host': '0.0.0.0',
        'port': 8080,
        'debug': False,
        'database': 'sqlite:///app.db',
        'middleware': [],
        'auth': {'enabled': True, 'type': 'jwt',
        'rate_limit': {'requests': 100, 'window': 60},
        'cors': {'enabled': True, 'origins': ['*']},
        'health_check': '/health'
    }
    return config

def handle_request(path):
    """Handle incoming requests"""
    return f"Response for {path}"

def health_check():
    """Health check endpoint"""
    return {'status': 'healthy'}

def main():
    print("Starting web service...")
    config = initialize_service()
    print(f"Service initialized on {config['host']}:{config['port']}")
    print(f"Debug mode: {config['debug']}")
    print(f"Database: {config['database']}")
    print("Request handler registered")
    print("Middleware stack initialized")
    print(f"Authentication: {config['auth']['type']}")
    print(f"Rate limit: {config['rate_limit']['requests']}/min")
    print(f"CORS enabled: {config['cors']['enabled']}")
    print(f"Health check endpoint: {config['health_check']}")
    print("Service started successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF
git add main.py
git commit -m "Add health check endpoint"

# Commit 10: Add metrics collection
cat > main.py << 'EOF'
#!/usr/bin/env python3
import sys

def initialize_service():
    """Initialize the web service"""
    config = {
        'host': '0.0.0.0',
        'port': 8080,
        'debug': False,
        'database': 'sqlite:///app.db',
        'middleware': [],
        'auth': {'enabled': True, 'type': 'jwt',
        'rate_limit': {'requests': 100, 'window': 60},
        'cors': {'enabled': True, 'origins': ['*']},
        'health_check': '/health',
        'metrics': {'enabled': True, 'endpoint': '/metrics'}
    }
    return config

def handle_request(path):
    """Handle incoming requests"""
    return f"Response for {path}"

def health_check():
    """Health check endpoint"""
    return {'status': 'healthy'}

def collect_metrics():
    """Collect service metrics"""
    return {'requests': 0, 'errors': 0}

def main():
    print("Starting web service...")
    config = initialize_service()
    print(f"Service initialized on {config['host']}:{config['port']}")
    print(f"Debug mode: {config['debug']}")
    print(f"Database: {config['database']}")
    print("Request handler registered")
    print("Middleware stack initialized")
    print(f"Authentication: {config['auth']['type']}")
    print(f"Rate limit: {config['rate_limit']['requests']}/min")
    print(f"CORS enabled: {config['cors']['enabled']}")
    print(f"Health check endpoint: {config['health_check']}")
    print(f"Metrics endpoint: {config['metrics']['endpoint']}")
    print("Service started successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF
git add main.py
git commit -m "Add metrics collection"

# Create test script
cat > test_service.sh << 'EOF'
#!/bin/bash
# Test if the service starts successfully

python3 main.py > /tmp/service_output.txt 2>&1
exit_code=$?

if [ $exit_code -eq 0 ]; then
    if grep -q "Service started successfully" /tmp/service_output.txt; then
        exit 0
    else
        exit 1
    fi
else
    exit 1
fi
EOF
chmod +x test_service.sh

echo "Repository setup complete with 10 commits"
