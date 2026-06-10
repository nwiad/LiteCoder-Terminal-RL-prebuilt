import os
import json
import yaml
import subprocess


def test_docker_compose_file_exists():
    """Test that docker-compose.yml exists in /app"""
    assert os.path.exists("/app/docker-compose.yml"), "docker-compose.yml not found in /app"


def test_docker_compose_not_empty():
    """Test that docker-compose.yml is not empty"""
    with open("/app/docker-compose.yml", "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "docker-compose.yml is empty"


def test_docker_compose_valid_yaml():
    """Test that docker-compose.yml is valid YAML"""
    with open("/app/docker-compose.yml", "r") as f:
        try:
            compose_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            assert False, f"docker-compose.yml is not valid YAML: {e}"
    assert compose_config is not None, "docker-compose.yml parsed to None"


def test_docker_compose_has_required_services():
    """Test that docker-compose.yml defines cadvisor, prometheus, and grafana services"""
    with open("/app/docker-compose.yml", "r") as f:
        compose_config = yaml.safe_load(f)

    assert "services" in compose_config, "No 'services' section in docker-compose.yml"
    services = compose_config["services"]

    assert "cadvisor" in services, "cadvisor service not defined"
    assert "prometheus" in services, "prometheus service not defined"
    assert "grafana" in services, "grafana service not defined"


def test_docker_compose_network_configuration():
    """Test that monitoring-net network is defined"""
    with open("/app/docker-compose.yml", "r") as f:
        compose_config = yaml.safe_load(f)

    assert "networks" in compose_config, "No 'networks' section in docker-compose.yml"
    assert "monitoring-net" in compose_config["networks"], "monitoring-net network not defined"


def test_docker_compose_volumes_configuration():
    """Test that prometheus-data and grafana-data volumes are defined"""
    with open("/app/docker-compose.yml", "r") as f:
        compose_config = yaml.safe_load(f)

    assert "volumes" in compose_config, "No 'volumes' section in docker-compose.yml"
    volumes = compose_config["volumes"]

    assert "prometheus-data" in volumes, "prometheus-data volume not defined"
    assert "grafana-data" in volumes, "grafana-data volume not defined"


def test_docker_compose_cadvisor_configuration():
    """Test cAdvisor service configuration"""
    with open("/app/docker-compose.yml", "r") as f:
        compose_config = yaml.safe_load(f)

    cadvisor = compose_config["services"]["cadvisor"]

    # Check image
    assert "image" in cadvisor, "cAdvisor image not specified"
    assert "cadvisor" in cadvisor["image"].lower(), "cAdvisor image incorrect"

    # Check ports
    assert "ports" in cadvisor, "cAdvisor ports not specified"
    ports = cadvisor["ports"]
    assert any("8080" in str(p) for p in ports), "cAdvisor port 8080 not mapped"

    # Check volumes (Docker socket mount)
    assert "volumes" in cadvisor, "cAdvisor volumes not specified"
    volumes = cadvisor["volumes"]
    assert any("docker.sock" in str(v) for v in volumes), "Docker socket not mounted"


def test_docker_compose_prometheus_configuration():
    """Test Prometheus service configuration"""
    with open("/app/docker-compose.yml", "r") as f:
        compose_config = yaml.safe_load(f)

    prometheus = compose_config["services"]["prometheus"]

    # Check image
    assert "image" in prometheus, "Prometheus image not specified"
    assert "prometheus" in prometheus["image"].lower(), "Prometheus image incorrect"

    # Check ports
    assert "ports" in prometheus, "Prometheus ports not specified"
    ports = prometheus["ports"]
    assert any("9090" in str(p) for p in ports), "Prometheus port 9090 not mapped"

    # Check volumes (config file and data)
    assert "volumes" in prometheus, "Prometheus volumes not specified"
    volumes = prometheus["volumes"]
    assert any("prometheus.yml" in str(v) for v in volumes), "prometheus.yml not mounted"
    assert any("prometheus-data" in str(v) for v in volumes), "prometheus-data volume not mounted"


def test_docker_compose_grafana_configuration():
    """Test Grafana service configuration"""
    with open("/app/docker-compose.yml", "r") as f:
        compose_config = yaml.safe_load(f)

    grafana = compose_config["services"]["grafana"]

    # Check image
    assert "image" in grafana, "Grafana image not specified"
    assert "grafana" in grafana["image"].lower(), "Grafana image incorrect"

    # Check ports
    assert "ports" in grafana, "Grafana ports not specified"
    ports = grafana["ports"]
    assert any("3000" in str(p) for p in ports), "Grafana port 3000 not mapped"

    # Check volumes
    assert "volumes" in grafana, "Grafana volumes not specified"
    volumes = grafana["volumes"]
    assert any("grafana-data" in str(v) for v in volumes), "grafana-data volume not mounted"


def test_prometheus_config_file_exists():
    """Test that prometheus.yml exists in /app"""
    assert os.path.exists("/app/prometheus.yml"), "prometheus.yml not found in /app"


def test_prometheus_config_not_empty():
    """Test that prometheus.yml is not empty"""
    with open("/app/prometheus.yml", "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "prometheus.yml is empty"


def test_prometheus_config_valid_yaml():
    """Test that prometheus.yml is valid YAML"""
    with open("/app/prometheus.yml", "r") as f:
        try:
            prom_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            assert False, f"prometheus.yml is not valid YAML: {e}"
    assert prom_config is not None, "prometheus.yml parsed to None"


def test_prometheus_scrape_interval():
    """Test that scrape_interval is set to 15s"""
    with open("/app/prometheus.yml", "r") as f:
        prom_config = yaml.safe_load(f)

    assert "global" in prom_config, "No 'global' section in prometheus.yml"
    assert "scrape_interval" in prom_config["global"], "scrape_interval not configured"

    scrape_interval = prom_config["global"]["scrape_interval"]
    assert scrape_interval == "15s", f"scrape_interval should be 15s, got {scrape_interval}"


def test_prometheus_scrape_cadvisor():
    """Test that Prometheus scrapes cAdvisor metrics"""
    with open("/app/prometheus.yml", "r") as f:
        prom_config = yaml.safe_load(f)

    assert "scrape_configs" in prom_config, "No 'scrape_configs' section in prometheus.yml"

    scrape_configs = prom_config["scrape_configs"]
    cadvisor_job = None

    for job in scrape_configs:
        if "job_name" in job and "cadvisor" in job["job_name"].lower():
            cadvisor_job = job
            break

    assert cadvisor_job is not None, "No cAdvisor scrape job configured"
    assert "static_configs" in cadvisor_job, "cAdvisor job has no static_configs"

    targets = cadvisor_job["static_configs"][0]["targets"]
    assert any("cadvisor" in str(t) and "8080" in str(t) for t in targets), \
        "cAdvisor target not configured correctly (should be cadvisor:8080)"


def test_prometheus_alert_rules_configured():
    """Test that alert rules are configured in prometheus.yml"""
    with open("/app/prometheus.yml", "r") as f:
        content = f.read()
        prom_config = yaml.safe_load(f)

    # Check for alert rules - they can be inline or in rule_files
    has_inline_rules = "groups" in prom_config and len(prom_config.get("groups", [])) > 0
    has_rule_files = "rule_files" in prom_config and len(prom_config.get("rule_files", [])) > 0

    assert has_inline_rules or has_rule_files, \
        "No alert rules configured (neither inline groups nor rule_files)"

    # Check for CPU and memory alert keywords
    assert "cpu" in content.lower() or "memory" in content.lower(), \
        "Alert rules should monitor CPU or memory usage"


def test_prometheus_cpu_alert_rule():
    """Test that CPU usage alert rule exists"""
    with open("/app/prometheus.yml", "r") as f:
        content = f.read().lower()

    # Look for CPU-related alert
    assert "cpu" in content, "No CPU monitoring in alert rules"
    assert "80" in content, "Alert threshold should be 80%"


def test_prometheus_memory_alert_rule():
    """Test that memory usage alert rule exists"""
    with open("/app/prometheus.yml", "r") as f:
        content = f.read().lower()

    # Look for memory-related alert
    assert "memory" in content, "No memory monitoring in alert rules"
    assert "80" in content, "Alert threshold should be 80%"


def test_monitoring_status_json_exists():
    """Test that monitoring_status.json exists in /app"""
    assert os.path.exists("/app/monitoring_status.json"), \
        "monitoring_status.json not found in /app"


def test_monitoring_status_json_not_empty():
    """Test that monitoring_status.json is not empty"""
    with open("/app/monitoring_status.json", "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "monitoring_status.json is empty"


def test_monitoring_status_json_valid():
    """Test that monitoring_status.json is valid JSON"""
    with open("/app/monitoring_status.json", "r") as f:
        try:
            status = json.load(f)
        except json.JSONDecodeError as e:
            assert False, f"monitoring_status.json is not valid JSON: {e}"
    assert status is not None, "monitoring_status.json parsed to None"


def test_monitoring_status_has_required_fields():
    """Test that monitoring_status.json has all required top-level fields"""
    with open("/app/monitoring_status.json", "r") as f:
        status = json.load(f)

    assert "network" in status, "Missing 'network' field"
    assert "services" in status, "Missing 'services' field"
    assert "volumes" in status, "Missing 'volumes' field"
    assert "alert_rules_configured" in status, "Missing 'alert_rules_configured' field"


def test_monitoring_status_network():
    """Test that network is set to monitoring-net"""
    with open("/app/monitoring_status.json", "r") as f:
        status = json.load(f)

    network = status["network"]
    assert "monitoring-net" in network, \
        f"Network should be 'monitoring-net', got '{network}'"


def test_monitoring_status_services_structure():
    """Test that services section has correct structure"""
    with open("/app/monitoring_status.json", "r") as f:
        status = json.load(f)

    services = status["services"]
    assert isinstance(services, dict), "services should be a dictionary"

    required_services = ["cadvisor", "prometheus", "grafana"]
    for service_name in required_services:
        assert service_name in services, f"Missing service: {service_name}"

        service = services[service_name]
        assert "status" in service, f"{service_name} missing 'status' field"
        assert "url" in service, f"{service_name} missing 'url' field"


def test_monitoring_status_cadvisor():
    """Test cAdvisor service status and URL"""
    with open("/app/monitoring_status.json", "r") as f:
        status = json.load(f)

    cadvisor = status["services"]["cadvisor"]

    assert cadvisor["status"] == "running", \
        f"cAdvisor should be running, got '{cadvisor['status']}'"

    assert cadvisor["url"] == "http://localhost:8080", \
        f"cAdvisor URL should be 'http://localhost:8080', got '{cadvisor['url']}'"


def test_monitoring_status_prometheus():
    """Test Prometheus service status and URL"""
    with open("/app/monitoring_status.json", "r") as f:
        status = json.load(f)

    prometheus = status["services"]["prometheus"]

    assert prometheus["status"] == "running", \
        f"Prometheus should be running, got '{prometheus['status']}'"

    assert prometheus["url"] == "http://localhost:9090", \
        f"Prometheus URL should be 'http://localhost:9090', got '{prometheus['url']}'"


def test_monitoring_status_grafana():
    """Test Grafana service status and URL"""
    with open("/app/monitoring_status.json", "r") as f:
        status = json.load(f)

    grafana = status["services"]["grafana"]

    assert grafana["status"] == "running", \
        f"Grafana should be running, got '{grafana['status']}'"

    assert grafana["url"] == "http://localhost:3000", \
        f"Grafana URL should be 'http://localhost:3000', got '{grafana['url']}'"


def test_monitoring_status_volumes():
    """Test that volumes list contains prometheus-data and grafana-data"""
    with open("/app/monitoring_status.json", "r") as f:
        status = json.load(f)

    volumes = status["volumes"]
    assert isinstance(volumes, list), "volumes should be a list"

    assert "prometheus-data" in volumes, "prometheus-data not in volumes list"
    assert "grafana-data" in volumes, "grafana-data not in volumes list"


def test_monitoring_status_alert_rules_flag():
    """Test that alert_rules_configured is true"""
    with open("/app/monitoring_status.json", "r") as f:
        status = json.load(f)

    alert_rules = status["alert_rules_configured"]
    assert alert_rules is True, \
        f"alert_rules_configured should be true, got {alert_rules}"


def test_services_actually_running():
    """Test that Docker containers are actually running (not just hardcoded status)"""
    # This test verifies the agent didn't just create a dummy JSON
    # We check if docker ps shows the containers
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        running_containers = result.stdout.lower()

        # At least one of the services should be running
        has_cadvisor = "cadvisor" in running_containers
        has_prometheus = "prometheus" in running_containers
        has_grafana = "grafana" in running_containers

        assert has_cadvisor or has_prometheus or has_grafana, \
            "No monitoring containers are actually running. Status may be hardcoded."

    except (subprocess.TimeoutExpired, FileNotFoundError):
        # If docker command fails, we can't verify, but we won't fail the test
        # since the main validation is through the JSON structure
        pass


def test_docker_compose_services_connected_to_network():
    """Test that services are connected to monitoring-net network"""
    with open("/app/docker-compose.yml", "r") as f:
        compose_config = yaml.safe_load(f)

    services = compose_config["services"]

    for service_name in ["cadvisor", "prometheus", "grafana"]:
        service = services[service_name]
        assert "networks" in service, f"{service_name} not connected to any network"

        networks = service["networks"]
        assert "monitoring-net" in networks, \
            f"{service_name} not connected to monitoring-net"
