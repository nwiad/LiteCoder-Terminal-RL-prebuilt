## DNS Load Balancing with Docker-Compose

Build a multi-host Nginx/WordPress web server cluster that is automatically load-balanced by a containerized BIND9 DNS server using round-robin A records with short TTL.

### Technical Requirements

- Docker and Docker Compose
- BIND9 DNS server
- WordPress or Nginx web servers
- Bash scripting for testing
- All files must be created in `/app` directory

### Implementation Requirements

Create a complete Docker-based load balancing solution with the following components:

**1. Docker Compose Configuration**
- File: `/app/docker-compose.yml`
- Must define a custom Docker network for DNS and web container communication
- Must include exactly 3 web server containers (WordPress or Nginx)
- Must include 1 BIND9 DNS container configured as authoritative for domain `pixelpress.test`
- Must include 1 client/test container with `dig` and `curl` utilities

**2. BIND9 DNS Server**
- File: `/app/Dockerfile.bind9` (custom BIND9 image)
- Must be authoritative for zone `pixelpress.test`
- Must serve round-robin A records for the 3 web server containers
- Must use TTL of 5 seconds for A records
- Zone configuration should accept container IPs dynamically

**3. Web Server Containers**
- File: `/app/Dockerfile.web` (if custom image needed)
- Must run 3 identical instances
- Each container must log its hostname on HTTP requests
- Must be accessible via the DNS name `pixelpress.test`

**4. Testing Script**
- File: `/app/test-loadbalancing.sh`
- Must use `dig` to query `pixelpress.test` and show DNS rotation
- Must use `curl` to make HTTP requests to `http://pixelpress.test`
- Must demonstrate that requests hit different backend containers
- Must run for at least 20 seconds to show multiple DNS TTL cycles

### Expected Behavior

When running `docker compose up`, the system must:
1. Start all containers successfully
2. DNS server responds to queries for `pixelpress.test` with rotating IP addresses
3. HTTP requests to `pixelpress.test` reach different backend containers
4. DNS TTL causes rotation every 5 seconds
5. Each web container logs its hostname when serving requests

### Validation

The solution will be tested by:
1. Running `docker compose -f /app/docker-compose.yml up -d`
2. Executing `/app/test-loadbalancing.sh` from the client container
3. Verifying DNS responses rotate through 3 different IPs
4. Verifying HTTP responses come from 3 different container hostnames
5. Confirming TTL is 5 seconds in DNS responses
