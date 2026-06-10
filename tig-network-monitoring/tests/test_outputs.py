import os
import json
import yaml

# All paths relative to /app directory
APP_DIR = "/app"

def test_docker_compose_exists():
    """Test that docker-compose.yml exists and is not empty"""
    compose_path = os.path.join(APP_DIR, "docker-compose.yml")
    assert os.path.exists(compose_path), "docker-compose.yml does not exist"
    assert os.path.getsize(compose_path) > 0, "docker-compose.yml is empty"


def test_docker_compose_structure():
    """Test docker-compose.yml has required network and services"""
    compose_path = os.path.join(APP_DIR, "docker-compose.yml")

    with open(compose_path, 'r') as f:
        content = f.read()
        compose_data = yaml.safe_load(content)

    # Check network exists
    assert 'networks' in compose_data, "No networks defined"
    assert 'monitoring-net' in compose_data['networks'], "monitoring-net network not found"

    # Check required services
    assert 'services' in compose_data, "No services defined"
    services = compose_data['services']

    required_services = ['sender', 'receiver', 'influxdb', 'grafana']
    for service in required_services:
        assert service in services, f"Service {service} not found in docker-compose.yml"

    # Verify each service is connected to monitoring-net
    for service_name in required_services:
        service = services[service_name]
        assert 'networks' in service, f"Service {service_name} has no networks defined"
        networks = service['networks']
        if isinstance(networks, list):
            assert 'monitoring-net' in networks, f"Service {service_name} not on monitoring-net"
        elif isinstance(networks, dict):
            assert 'monitoring-net' in networks, f"Service {service_name} not on monitoring-net"


def test_influxdb_token_exists():
    """Test that influxdb-token.txt exists and contains a token"""
    token_path = os.path.join(APP_DIR, "influxdb-token.txt")
    assert os.path.exists(token_path), "influxdb-token.txt does not exist"

    with open(token_path, 'r') as f:
        token = f.read().strip()

    assert len(token) > 0, "InfluxDB token is empty"
    assert len(token) >= 10, "InfluxDB token seems too short (likely dummy)"


def test_telegraf_config_exists():
    """Test that telegraf.conf exists and is not empty"""
    telegraf_path = os.path.join(APP_DIR, "telegraf.conf")
    assert os.path.exists(telegraf_path), "telegraf.conf does not exist"
    assert os.path.getsize(telegraf_path) > 0, "telegraf.conf is empty"


def test_telegraf_config_structure():
    """Test telegraf.conf has required inputs and outputs"""
    telegraf_path = os.path.join(APP_DIR, "telegraf.conf")

    with open(telegraf_path, 'r') as f:
        content = f.read()

    # Check for InfluxDB v2 output
    assert '[[outputs.influxdb_v2]]' in content, "InfluxDB v2 output not configured"
    assert 'network-metrics' in content, "Bucket 'network-metrics' not found in config"
    assert 'monitoring-org' in content, "Organization 'monitoring-org' not found in config"

    # Check for ping input
    assert '[[inputs.ping]]' in content, "Ping input not configured"
    assert 'receiver' in content, "Receiver target not found in ping config"

    # Check for iperf3 input (via exec plugin)
    assert '[[inputs.exec]]' in content or 'iperf3' in content, "iperf3 input not configured"

    # Verify intervals
    assert 'interval' in content, "No interval configuration found"


def test_grafana_dashboard_exists():
    """Test that grafana-dashboard.json exists and is valid JSON"""
    dashboard_path = os.path.join(APP_DIR, "grafana-dashboard.json")
    assert os.path.exists(dashboard_path), "grafana-dashboard.json does not exist"

    with open(dashboard_path, 'r') as f:
        dashboard_data = json.load(f)

    assert isinstance(dashboard_data, dict), "Dashboard is not a valid JSON object"


def test_grafana_dashboard_structure():
    """Test grafana-dashboard.json has required panels and configuration"""
    dashboard_path = os.path.join(APP_DIR, "grafana-dashboard.json")

    with open(dashboard_path, 'r') as f:
        dashboard_data = json.load(f)

    # Check dashboard structure
    assert 'dashboard' in dashboard_data, "No dashboard key found"
    dashboard = dashboard_data['dashboard']

    # Check panels exist
    assert 'panels' in dashboard, "No panels defined in dashboard"
    panels = dashboard['panels']
    assert len(panels) >= 3, f"Expected at least 3 panels, found {len(panels)}"

    # Check panel types
    panel_types = [p.get('type') for p in panels]
    assert 'timeseries' in panel_types or 'graph' in panel_types, "No time series panel found"
    assert 'stat' in panel_types or 'singlestat' in panel_types, "No stat panel found"

    # Check for queries mentioning required measurements
    dashboard_str = json.dumps(dashboard)
    assert 'ping' in dashboard_str, "No ping measurement in dashboard queries"
    assert 'iperf3' in dashboard_str, "No iperf3 measurement in dashboard queries"
    assert 'network-metrics' in dashboard_str, "Bucket 'network-metrics' not referenced"

    # Check time range configuration
    assert 'time' in dashboard or 'refresh' in dashboard, "No time configuration found"

    # Verify refresh interval
    if 'refresh' in dashboard:
        refresh = dashboard['refresh']
        assert refresh in ['5s', '10s', '30s'], f"Unexpected refresh interval: {refresh}"


def test_verification_json_exists():
    """Test that verification.json exists and is valid JSON"""
    verification_path = os.path.join(APP_DIR, "verification.json")
    assert os.path.exists(verification_path), "verification.json does not exist"

    with open(verification_path, 'r') as f:
        verification_data = json.load(f)

    assert isinstance(verification_data, dict), "Verification is not a valid JSON object"


def test_verification_json_structure():
    """Test verification.json has all required fields with valid data"""
    verification_path = os.path.join(APP_DIR, "verification.json")

    with open(verification_path, 'r') as f:
        verification_data = json.load(f)

    # Check required top-level keys
    required_keys = [
        'containers_running',
        'network_created',
        'telegraf_collecting',
        'influxdb_measurements',
        'grafana_dashboard_id',
        'sample_metrics'
    ]

    for key in required_keys:
        assert key in verification_data, f"Missing required key: {key}"

    # Validate containers_running
    containers = verification_data['containers_running']
    assert isinstance(containers, list), "containers_running must be a list"
    required_containers = ['sender', 'receiver', 'influxdb', 'grafana']
    for container in required_containers:
        assert container in containers, f"Container {container} not in containers_running"

    # Validate network_created
    assert verification_data['network_created'] == 'monitoring-net', "network_created must be 'monitoring-net'"

    # Validate telegraf_collecting
    assert verification_data['telegraf_collecting'] is True, "telegraf_collecting must be true"

    # Validate influxdb_measurements
    measurements = verification_data['influxdb_measurements']
    assert isinstance(measurements, list), "influxdb_measurements must be a list"
    assert 'ping' in measurements, "ping measurement not found"
    assert 'iperf3' in measurements, "iperf3 measurement not found"

    # Validate grafana_dashboard_id
    dashboard_id = verification_data['grafana_dashboard_id']
    assert isinstance(dashboard_id, str), "grafana_dashboard_id must be a string"
    assert len(dashboard_id) > 0, "grafana_dashboard_id is empty"

    # Validate sample_metrics
    sample_metrics = verification_data['sample_metrics']
    assert isinstance(sample_metrics, dict), "sample_metrics must be a dict"

    required_metric_keys = ['avg_latency_ms', 'avg_bandwidth_mbps', 'packet_loss_percent']
    for key in required_metric_keys:
        assert key in sample_metrics, f"Missing metric: {key}"


def test_verification_metrics_realistic():
    """Test that sample metrics contain realistic values (not dummy data)"""
    verification_path = os.path.join(APP_DIR, "verification.json")

    with open(verification_path, 'r') as f:
        verification_data = json.load(f)

    metrics = verification_data['sample_metrics']

    # Check avg_latency_ms
    latency = metrics['avg_latency_ms']
    assert isinstance(latency, (int, float)), "avg_latency_ms must be numeric"
    assert latency > 0, "avg_latency_ms must be positive"
    assert latency < 1000, f"avg_latency_ms seems unrealistic: {latency}ms (too high)"

    # Check avg_bandwidth_mbps
    bandwidth = metrics['avg_bandwidth_mbps']
    assert isinstance(bandwidth, (int, float)), "avg_bandwidth_mbps must be numeric"
    assert bandwidth > 0, "avg_bandwidth_mbps must be positive"
    assert bandwidth < 100000, f"avg_bandwidth_mbps seems unrealistic: {bandwidth}Mbps (too high)"

    # Check packet_loss_percent
    packet_loss = metrics['packet_loss_percent']
    assert isinstance(packet_loss, (int, float)), "packet_loss_percent must be numeric"
    assert packet_loss >= 0, "packet_loss_percent cannot be negative"
    assert packet_loss <= 100, f"packet_loss_percent must be <= 100, got {packet_loss}"


def test_no_hardcoded_dummy_values():
    """Test that metrics are not obviously hardcoded dummy values"""
    verification_path = os.path.join(APP_DIR, "verification.json")

    with open(verification_path, 'r') as f:
        verification_data = json.load(f)

    metrics = verification_data['sample_metrics']

    # Common dummy values to reject
    dummy_values = [0, 1, 100, 999, 1000, 9999]

    latency = metrics['avg_latency_ms']
    bandwidth = metrics['avg_bandwidth_mbps']

    # At least one metric should not be a common dummy value
    # (allows for legitimate 0 packet loss)
    assert not (latency in dummy_values and bandwidth in dummy_values), \
        "Metrics appear to be hardcoded dummy values"


def test_telegraf_ping_fields():
    """Test that telegraf.conf configures ping with required fields"""
    telegraf_path = os.path.join(APP_DIR, "telegraf.conf")

    with open(telegraf_path, 'r') as f:
        content = f.read()

    # Ping plugin should collect these fields by default
    # We verify the plugin is configured, fields are implicit
    assert '[[inputs.ping]]' in content, "Ping input not found"

    # Check that receiver is targeted
    assert 'receiver' in content.lower(), "Receiver not targeted in ping config"


def test_telegraf_iperf3_fields():
    """Test that telegraf.conf configures iperf3 to collect required fields"""
    telegraf_path = os.path.join(APP_DIR, "telegraf.conf")

    with open(telegraf_path, 'r') as f:
        content = f.read()

    # Check for iperf3 execution
    assert 'iperf3' in content, "iperf3 not found in telegraf config"

    # Should target receiver
    assert 'receiver' in content.lower(), "Receiver not targeted in iperf3 config"


def test_grafana_panels_have_queries():
    """Test that Grafana panels have proper InfluxDB queries"""
    dashboard_path = os.path.join(APP_DIR, "grafana-dashboard.json")

    with open(dashboard_path, 'r') as f:
        dashboard_data = json.load(f)

    dashboard = dashboard_data['dashboard']
    panels = dashboard['panels']

    # Check that panels have targets with queries
    panels_with_queries = 0
    for panel in panels:
        if 'targets' in panel and len(panel['targets']) > 0:
            for target in panel['targets']:
                if 'query' in target and len(target['query']) > 0:
                    panels_with_queries += 1
                    break

    assert panels_with_queries >= 2, f"Expected at least 2 panels with queries, found {panels_with_queries}"


def test_grafana_time_range():
    """Test that Grafana dashboard has appropriate time range"""
    dashboard_path = os.path.join(APP_DIR, "grafana-dashboard.json")

    with open(dashboard_path, 'r') as f:
        dashboard_data = json.load(f)

    dashboard = dashboard_data['dashboard']

    # Check time configuration exists
    if 'time' in dashboard:
        time_config = dashboard['time']
        assert 'from' in time_config, "No 'from' time specified"
        assert 'to' in time_config, "No 'to' time specified"

        # Should use relative time (e.g., "now-15m")
        from_time = time_config['from']
        assert 'now' in from_time or 'relative' in str(from_time).lower(), \
            "Time range should use relative time"


def test_all_required_files_present():
    """Test that all required output files are present"""
    required_files = [
        'docker-compose.yml',
        'telegraf.conf',
        'influxdb-token.txt',
        'grafana-dashboard.json',
        'verification.json'
    ]

    for filename in required_files:
        filepath = os.path.join(APP_DIR, filename)
        assert os.path.exists(filepath), f"Required file missing: {filename}"
        assert os.path.getsize(filepath) > 0, f"Required file is empty: {filename}"
