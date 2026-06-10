## Task: Multi-Site WordPress Environment Configuration

Configure a Docker-based multi-site WordPress environment on Ubuntu with Nginx reverse proxy and SSL certificates for two independent domains.

**Technical Requirements:**
- Docker and Docker Compose
- Ubuntu 22.04 environment
- Nginx as reverse proxy
- MySQL databases (one per site)
- Let's Encrypt SSL certificates
- Domain names: `site1.example.com` and `site2.example.com`

**Implementation Requirements:**

1. **Docker Compose Configuration** (`/app/docker-compose.yml`):
   - Two isolated Docker networks (one per site)
   - Two MySQL containers with separate databases
   - Two WordPress containers with proper environment variables
   - Nginx reverse proxy container
   - Certbot container for SSL management

2. **Nginx Configuration** (`/app/nginx.conf`):
   - Server blocks for both domains
   - SSL certificate paths for each domain
   - Reverse proxy settings to WordPress containers
   - HTTP to HTTPS redirect
   - Proper upstream definitions

3. **Environment Configuration** (`/app/.env`):
   - Database credentials for both sites
   - WordPress configuration variables
   - Domain names and email for Let's Encrypt

4. **Setup Documentation** (`/app/setup.md`):
   - Commands to deploy the environment
   - Firewall configuration commands
   - Certificate renewal setup
   - Verification steps

**Output Requirements:**

All configuration files must be valid and deployable. The docker-compose.yml must define:
- Network isolation between sites
- Persistent volumes for WordPress and MySQL data
- Proper port mappings (80, 443)
- Container dependencies and restart policies

The nginx.conf must include:
- SSL configuration with certificate paths
- Proxy headers (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto)
- Client max body size for WordPress uploads

**Constraints:**
- Each WordPress site must use separate MySQL databases
- Sites must be on isolated Docker networks
- SSL certificates must be configured for both domains
- All sensitive data must use environment variables
