"""
Test suite for Network Topology Scanner
Validates output files after task completion.
"""

import os
import json
from datetime import datetime
from pathlib import Path


def test_topology_json_exists():
    """Verify topology.json file exists."""
    assert os.path.exists('/app/topology.json'), "topology.json file not found at /app/topology.json"


def test_topology_json_not_empty():
    """Verify topology.json is not empty."""
    file_size = os.path.getsize('/app/topology.json')
    assert file_size > 0, "topology.json is empty"


def test_topology_json_valid_format():
    """Verify topology.json contains valid JSON."""
    with open('/app/topology.json', 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise AssertionError(f"topology.json contains invalid JSON: {e}")

    assert isinstance(data, dict), "topology.json must contain a JSON object"


def test_topology_json_required_fields():
    """Verify topology.json has all required top-level fields."""
    with open('/app/topology.json', 'r') as f:
        data = json.load(f)

    required_fields = ['scan_time', 'subnet', 'devices', 'total_devices']
    for field in required_fields:
        assert field in data, f"Missing required field '{field}' in topology.json"


def test_topology_json_scan_time_format():
    """Verify scan_time is in ISO 8601 format."""
    with open('/app/topology.json', 'r') as f:
        data = json.load(f)

    scan_time = data['scan_time']
    assert isinstance(scan_time, str), "scan_time must be a string"

    # Try parsing as ISO 8601
    try:
        # Handle both 'Z' and '+00:00' timezone formats
        if scan_time.endswith('Z'):
            datetime.fromisoformat(scan_time.replace('Z', '+00:00'))
        else:
            datetime.fromisoformat(scan_time)
    except ValueError as e:
        raise AssertionError(f"scan_time is not in valid ISO 8601 format: {e}")


def test_topology_json_subnet_matches_config():
    """Verify subnet in output matches the input configuration."""
    with open('/app/network_config.json', 'r') as f:
        config = json.load(f)

    with open('/app/topology.json', 'r') as f:
        topology = json.load(f)

    assert topology['subnet'] == config['subnet'], \
        f"Subnet mismatch: expected {config['subnet']}, got {topology['subnet']}"


def test_topology_json_devices_is_list():
    """Verify devices field is a list."""
    with open('/app/topology.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['devices'], list), "devices field must be a list"


def test_topology_json_total_devices_matches():
    """Verify total_devices count matches actual device list length."""
    with open('/app/topology.json', 'r') as f:
        data = json.load(f)

    assert data['total_devices'] == len(data['devices']), \
        f"total_devices ({data['total_devices']}) doesn't match actual device count ({len(data['devices'])})"


def test_topology_json_has_devices():
    """Verify at least one device was discovered (network should have devices)."""
    with open('/app/topology.json', 'r') as f:
        data = json.load(f)

    assert len(data['devices']) > 0, "No devices discovered - expected at least one device"


def test_topology_json_device_structure():
    """Verify each device has required fields with correct types."""
    with open('/app/topology.json', 'r') as f:
        data = json.load(f)

    required_device_fields = ['ip', 'mac', 'hostname', 'manufacturer', 'open_ports', 'os_guess', 'response_time_ms']

    for idx, device in enumerate(data['devices']):
        assert isinstance(device, dict), f"Device {idx} is not a dictionary"

        for field in required_device_fields:
            assert field in device, f"Device {idx} missing required field '{field}'"

        # Validate field types
        assert isinstance(device['ip'], str), f"Device {idx}: ip must be a string"
        assert isinstance(device['hostname'], str), f"Device {idx}: hostname must be a string"
        assert isinstance(device['manufacturer'], str), f"Device {idx}: manufacturer must be a string"
        assert isinstance(device['open_ports'], list), f"Device {idx}: open_ports must be a list"

        # MAC and OS can be null if unavailable
        if device['mac'] is not None:
            assert isinstance(device['mac'], str), f"Device {idx}: mac must be a string or null"

        if device['os_guess'] is not None:
            assert isinstance(device['os_guess'], str), f"Device {idx}: os_guess must be a string or null"

        # response_time_ms should be a number if present
        if device['response_time_ms'] is not None:
            assert isinstance(device['response_time_ms'], (int, float)), \
                f"Device {idx}: response_time_ms must be a number or null"


def test_topology_json_ip_addresses_valid():
    """Verify IP addresses are in valid format."""
    with open('/app/topology.json', 'r') as f:
        data = json.load(f)

    import ipaddress

    for idx, device in enumerate(data['devices']):
        try:
            ipaddress.ip_address(device['ip'])
        except ValueError:
            raise AssertionError(f"Device {idx} has invalid IP address: {device['ip']}")


def test_topology_json_ip_addresses_in_subnet():
    """Verify discovered IPs are within the configured subnet."""
    with open('/app/network_config.json', 'r') as f:
        config = json.load(f)

    with open('/app/topology.json', 'r') as f:
        topology = json.load(f)

    import ipaddress

    subnet = ipaddress.ip_network(config['subnet'])

    for idx, device in enumerate(topology['devices']):
        device_ip = ipaddress.ip_address(device['ip'])
        assert device_ip in subnet, \
            f"Device {idx} IP {device['ip']} is not in configured subnet {config['subnet']}"


def test_topology_json_open_ports_from_config():
    """Verify open ports are only from the configured ports_to_scan list."""
    with open('/app/network_config.json', 'r') as f:
        config = json.load(f)

    with open('/app/topology.json', 'r') as f:
        topology = json.load(f)

    allowed_ports = set(config['ports_to_scan'])

    for idx, device in enumerate(topology['devices']):
        for port in device['open_ports']:
            assert port in allowed_ports, \
                f"Device {idx} has port {port} which is not in configured ports_to_scan {allowed_ports}"


def test_network_graph_png_exists():
    """Verify network_graph.png file exists."""
    assert os.path.exists('/app/network_graph.png'), "network_graph.png file not found at /app/network_graph.png"


def test_network_graph_png_not_empty():
    """Verify network_graph.png is not empty."""
    file_size = os.path.getsize('/app/network_graph.png')
    assert file_size > 100, f"network_graph.png is too small ({file_size} bytes) - likely invalid"


def test_network_graph_png_valid_format():
    """Verify network_graph.png is a valid PNG file."""
    with open('/app/network_graph.png', 'rb') as f:
        header = f.read(8)

    # PNG magic number: 89 50 4E 47 0D 0A 1A 0A
    png_signature = b'\x89PNG\r\n\x1a\n'
    assert header == png_signature, "network_graph.png is not a valid PNG file (invalid signature)"


def test_network_graph_png_minimum_dimensions():
    """Verify network_graph.png meets minimum dimension requirements (800x600)."""
    try:
        from PIL import Image
    except ImportError:
        # Install PIL if not available
        import subprocess
        import sys
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'Pillow'])
        from PIL import Image

    with Image.open('/app/network_graph.png') as img:
        width, height = img.size
        assert width >= 800, f"Image width {width} is less than minimum 800 pixels"
        assert height >= 600, f"Image height {height} is less than minimum 600 pixels"


def test_network_graph_png_not_blank():
    """Verify network_graph.png is not a blank/solid color image."""
    try:
        from PIL import Image
    except ImportError:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'Pillow'])
        from PIL import Image

    with Image.open('/app/network_graph.png') as img:
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Get color statistics
        extrema = img.getextrema()

        # Check if image has variation (not all pixels the same color)
        has_variation = False
        for channel_min, channel_max in extrema:
            if channel_max - channel_min > 10:  # Allow small variations
                has_variation = True
                break

        assert has_variation, "network_graph.png appears to be blank or solid color"


def test_integration_device_count_reasonable():
    """Verify discovered device count is reasonable for the subnet."""
    with open('/app/topology.json', 'r') as f:
        data = json.load(f)

    device_count = len(data['devices'])

    # For a /24 subnet, expect at least 1 device and not more than 254
    assert 1 <= device_count <= 254, \
        f"Device count {device_count} is unreasonable for a /24 subnet"


def test_integration_no_duplicate_ips():
    """Verify no duplicate IP addresses in discovered devices."""
    with open('/app/topology.json', 'r') as f:
        data = json.load(f)

    ips = [device['ip'] for device in data['devices']]
    unique_ips = set(ips)

    assert len(ips) == len(unique_ips), \
        f"Duplicate IP addresses found: {len(ips)} total, {len(unique_ips)} unique"
