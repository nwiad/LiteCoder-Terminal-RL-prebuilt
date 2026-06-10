## Network Performance Monitoring with TIG Stack

Set up a network monitoring solution using Docker containers with the TIG stack (Telegraf, InfluxDB, Grafana) to measure and visualize network performance metrics between two containers.

## Technical Requirements

- Docker and Docker Compose
- Two network containers: `sender` and `receiver`
- TIG Stack: Telegraf, InfluxDB 2.x, Grafana
- Network testing tools: ping, iperf3
- Custom Docker network for container communication

## Implementation Requirements

### 1. Docker Infrastructure

Create a Docker Compose configuration at `/app/docker-compose.yml` that defines:
- Custom bridge network named `monitoring-net`
- Container `sender` with Telegraf and network tools
- Container `receiver` with iperf3 server
- InfluxDB container with persistent storage
- Grafana container with persistent storage

### 2. InfluxDB Configuration

- Organization: `monitoring-org`
- Bucket: `network-metrics`
- Generate and store API token at `/app/influxdb-token.txt`

### 3. Telegraf Configuration

Create Telegraf configuration at `/app/telegraf.conf` that collects:
- Ping latency metrics from `sender` to `receiver` (interval: 10s)
- iperf3 bandwidth metrics (TCP, interval: 30s)
- Output to InfluxDB bucket `network-metrics`

Required measurements:
- `ping`: fields include `average_response_ms`, `packets_transmitted`, `packets_received`, `percent_packet_loss`
- `iperf3`: fields include `bits_per_second`, `retransmits`

### 4. Grafana Dashboard

Create a Grafana dashboard configuration at `/app/grafana-dashboard.json` with:
- Data source: InfluxDB connection
- Panel 1: Time series graph showing ping latency (ms) over time
- Panel 2: Time series graph showing bandwidth (Mbps) over time
- Panel 3: Stat panel showing current packet loss percentage
- Time range: Last 15 minutes
- Refresh interval: 10s

### 5. Verification Output

Generate a verification report at `/app/verification.json` containing:
```json
{
  "containers_running": ["sender", "receiver", "influxdb", "grafana"],
  "network_created": "monitoring-net",
  "telegraf_collecting": true,
  "influxdb_measurements": ["ping", "iperf3"],
  "grafana_dashboard_id": "<dashboard_id>",
  "sample_metrics": {
    "avg_latency_ms": <float>,
    "avg_bandwidth_mbps": <float>,
    "packet_loss_percent": <float>
  }
}
```

The sample metrics should reflect actual collected data from at least 2 minutes of monitoring.

## Success Criteria

- All containers are running and healthy
- Telegraf successfully writes metrics to InfluxDB
- InfluxDB contains at least 10 data points for both ping and iperf3 measurements
- Grafana dashboard displays real-time network metrics
- Verification file contains valid metrics data
