Deploy a production-ready Flask web application with HTTPS support using Docker Compose, Nginx reverse proxy, and Let's Encrypt SSL certificates with automatic renewal.

## Technical Requirements

- Python 3.x with Flask framework
- Docker and Docker Compose
- Nginx as reverse proxy
- Certbot for Let's Encrypt SSL certificates

## Implementation Requirements

Create the following files in /app:

1. **Flask Application** (`/app/app.py`):
   - Implement a Flask web server
   - Include a health check endpoint at `/health` that returns JSON: `{"status": "healthy"}`
   - Include a root endpoint at `/` that returns a simple response

2. **Dockerfile** (`/app/Dockerfile`):
   - Use Python 3.x base image
   - Install Flask and required dependencies
   - Expose port 5000
   - Set up the Flask application to run

3. **Docker Compose Configuration** (`/app/docker-compose.yml`):
   - Define at least 2 Flask application instances (containers)
   - Configure Nginx reverse proxy container
   - Set up proper networking between containers
   - Configure volume mounts for SSL certificates and Nginx configuration

4. **Nginx Configuration** (`/app/nginx.conf`):
   - Configure reverse proxy to Flask application instances
   - Implement load balancing across multiple Flask containers (upstream block)
   - Configure SSL/TLS settings (listen on port 443, ssl_certificate paths)
   - Set up HTTP to HTTPS redirect (listen on port 80)
   - Include proxy headers (X-Forwarded-For, X-Forwarded-Proto, Host)

5. **Deployment Documentation** (`/app/deployment.md`):
   - List all commands needed to deploy the application
   - Document how to verify HTTPS is working
   - Include the health check endpoint URL
   - Explain the SSL certificate renewal process

## Configuration Specifications

- Flask instances must be accessible through Nginx only (not directly exposed)
- Nginx must listen on ports 80 (HTTP) and 443 (HTTPS)
- Load balancing must distribute requests across all Flask instances
- SSL certificate paths must be configured in Nginx (even if using self-signed for testing)
- All containers must be defined in a single docker-compose.yml file

## Output Requirements

All files must be created in `/app` directory with the exact filenames specified above. The docker-compose.yml must be valid and able to start all services with `docker-compose up`.
