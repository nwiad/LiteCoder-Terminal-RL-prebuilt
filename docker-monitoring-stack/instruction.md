## Docker Monitoring Service with cAdvisor and Prometheus

Set up a containerized monitoring stack using cAdvisor, Prometheus, and Grafana to collect and visualize Docker container metrics.

**Technical Requirements:**
- Docker and Docker Compose
- Configuration files: `/app/docker-compose.yml`, `/app/prometheus.yml`
- Output file: `/app/monitoring_status.json`

**Implementation Requirements:**

1. **Docker Network:**
   - Create a bridge network named `monitoring-net`

2. **cAdvisor Container:**
   - Image: `gcr.io/cadvisor/cadvisor:latest`
   - Port: 8080
   - Mount Docker socket: `/var/run/docker.sock:/var/run/docker.sock:ro`
   - Mount root filesystem: `/:/rootfs:ro`, `/var/run:/var/run:ro`, `/sys:/sys:ro`, `/var/lib/docker:/var/lib/docker:ro`

3. **Prometheus Container:**
   - Image: `prom/prometheus:latest`
   - Port: 9090
   - Configuration file: `/app/prometheus.yml` mounted to `/etc/prometheus/prometheus.yml`
   - Persistent volume: `prometheus-data` mounted to `/prometheus`
   - Scrape interval: 15 seconds
   - Scrape cAdvisor metrics from `cadvisor:8080`

4. **Grafana Container:**
   - Image: `grafana/grafana:latest`
   - Port: 3000
   - Persistent volume: `grafana-data` mounted to `/var/lib/grafana`

5. **Alert Rules in prometheus.yml:**
   - Alert when container CPU usage > 80% for 2 minutes
   - Alert when container memory usage > 80% for 2 minutes

**Output Format:**

Create `/app/monitoring_status.json` with the following structure:
```json
{
  "network": "monitoring-net",
  "services": {
    "cadvisor": {
      "status": "running",
      "url": "http://localhost:8080"
    },
    "prometheus": {
      "status": "running",
      "url": "http://localhost:9090"
    },
    "grafana": {
      "status": "running",
      "url": "http://localhost:3000"
    }
  },
  "volumes": ["prometheus-data", "grafana-data"],
  "alert_rules_configured": true
}
```

All services must be accessible via their specified URLs and connected to the `monitoring-net` network.
