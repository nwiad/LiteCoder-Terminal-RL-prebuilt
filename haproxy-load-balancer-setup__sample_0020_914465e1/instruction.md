## Multi-Server Load Balancer Setup with HAProxy

Set up HAProxy to distribute HTTP traffic across multiple backend web servers with health checks and monitoring capabilities.

**Technical Requirements:**
- HAProxy (latest available version)
- Apache web servers (or any HTTP server)
- Configuration file: `/app/haproxy.cfg`
- Verification output: `/app/verification.json`

**Implementation Requirements:**

1. **Backend Servers Setup:**
   - Configure 3 backend web servers listening on ports 8081, 8082, and 8083
   - Each server must serve a unique HTML page at the root path (/)
   - HTML pages must contain identifiable content (e.g., "Server 1", "Server 2", "Server 3")

2. **HAProxy Configuration (`/app/haproxy.cfg`):**
   - Frontend listening on port 80
   - Backend with round-robin load balancing algorithm
   - All 3 backend servers configured with their respective ports
   - Health checks enabled with the following parameters:
     - Check interval: 3 seconds
     - Check method: HTTP GET request
   - HAProxy stats page enabled and accessible at `/haproxy?stats`

3. **Verification Output (`/app/verification.json`):**

   Provide a JSON file documenting the configuration and test results:
   ```json
   {
     "haproxy_frontend_port": 80,
     "backend_servers": [
       {"name": "server1", "host": "127.0.0.1", "port": 8081, "status": "up"},
       {"name": "server2", "host": "127.0.0.1", "port": 8082, "status": "up"},
       {"name": "server3", "host": "127.0.0.1", "port": 8083, "status": "up"}
     ],
     "load_balancing_algorithm": "roundrobin",
     "health_check_enabled": true,
     "stats_page_enabled": true,
     "stats_page_path": "/haproxy?stats",
     "load_distribution_test": {
       "total_requests": 9,
       "server1_hits": 3,
       "server2_hits": 3,
       "server3_hits": 3
     }
   }
   ```

**Expected Behavior:**
- Requests to port 80 are distributed evenly across the 3 backend servers
- Health checks automatically detect and exclude failed servers from rotation
- Stats page provides real-time monitoring of backend server status
- Configuration persists in `/app/haproxy.cfg` for review
