import os
import json
import stat
import subprocess
from datetime import datetime


def test_memory_upgrade_report_exists():
    """Test that the memory upgrade report file exists"""
    assert os.path.exists('/app/memory_upgrade_report.json'), \
        "memory_upgrade_report.json does not exist at /app/"


def test_memory_upgrade_report_not_empty():
    """Test that the report file is not empty"""
    assert os.path.getsize('/app/memory_upgrade_report.json') > 0, \
        "memory_upgrade_report.json is empty"


def test_memory_upgrade_report_valid_json():
    """Test that the report is valid JSON"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON in memory_upgrade_report.json: {e}")


def test_memory_upgrade_report_required_fields():
    """Test that all required fields are present in the report"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    required_fields = [
        'initial_memory_limit',
        'initial_memory_usage',
        'new_memory_limit',
        'new_memory_usage',
        'verification_status',
        'commands_used',
        'timestamp'
    ]

    for field in required_fields:
        assert field in data, f"Required field '{field}' missing from report"


def test_initial_memory_limit_value():
    """Test that initial memory limit is 1GB (1073741824 bytes)"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    initial_limit = data.get('initial_memory_limit')
    assert initial_limit == "1073741824", \
        f"Initial memory limit should be '1073741824', got '{initial_limit}'"


def test_new_memory_limit_value():
    """Test that new memory limit is 2GB (2147483648 bytes)"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    new_limit = data.get('new_memory_limit')
    assert new_limit == "2147483648", \
        f"New memory limit should be '2147483648', got '{new_limit}'"


def test_memory_usage_values_are_numeric():
    """Test that memory usage values are numeric strings"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    initial_usage = data.get('initial_memory_usage', '')
    new_usage = data.get('new_memory_usage', '')

    # Should be numeric strings (can be converted to int)
    try:
        int(initial_usage)
    except (ValueError, TypeError):
        raise AssertionError(f"initial_memory_usage '{initial_usage}' is not a valid numeric string")

    try:
        int(new_usage)
    except (ValueError, TypeError):
        raise AssertionError(f"new_memory_usage '{new_usage}' is not a valid numeric string")


def test_verification_status_valid():
    """Test that verification_status is either 'success' or 'failed'"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    status = data.get('verification_status')
    assert status in ['success', 'failed'], \
        f"verification_status must be 'success' or 'failed', got '{status}'"


def test_verification_status_is_success():
    """Test that verification_status is 'success' (memory upgrade succeeded)"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    status = data.get('verification_status')
    assert status == 'success', \
        f"Expected verification_status to be 'success', got '{status}'"


def test_commands_used_is_list():
    """Test that commands_used is a list"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    commands = data.get('commands_used')
    assert isinstance(commands, list), \
        f"commands_used should be a list, got {type(commands).__name__}"


def test_commands_used_not_empty():
    """Test that commands_used contains at least one command"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    commands = data.get('commands_used', [])
    assert len(commands) > 0, \
        "commands_used should contain at least one command"


def test_commands_used_contains_docker_update():
    """Test that commands_used includes docker update command"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    commands = data.get('commands_used', [])
    has_update = any('docker update' in cmd and '--memory' in cmd for cmd in commands)
    assert has_update, \
        "commands_used should include 'docker update --memory' command"


def test_timestamp_format():
    """Test that timestamp is in ISO 8601 format"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    timestamp = data.get('timestamp', '')

    # Try to parse as ISO 8601
    try:
        # Handle both with and without 'Z' suffix
        if timestamp.endswith('Z'):
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            datetime.fromisoformat(timestamp)
    except (ValueError, AttributeError) as e:
        raise AssertionError(f"timestamp '{timestamp}' is not valid ISO 8601 format: {e}")


def test_monitor_script_exists():
    """Test that the monitoring script exists"""
    assert os.path.exists('/app/monitor_memory.sh'), \
        "monitor_memory.sh does not exist at /app/"


def test_monitor_script_not_empty():
    """Test that the monitoring script is not empty"""
    assert os.path.getsize('/app/monitor_memory.sh') > 0, \
        "monitor_memory.sh is empty"


def test_monitor_script_is_executable():
    """Test that the monitoring script has executable permissions"""
    st = os.stat('/app/monitor_memory.sh')
    is_executable = bool(st.st_mode & stat.S_IXUSR)
    assert is_executable, \
        "monitor_memory.sh is not executable (missing execute permission)"


def test_monitor_script_is_bash():
    """Test that the monitoring script is a bash script"""
    with open('/app/monitor_memory.sh', 'r') as f:
        first_line = f.readline().strip()

    assert first_line.startswith('#!') and 'bash' in first_line, \
        f"monitor_memory.sh should start with bash shebang, got '{first_line}'"


def test_monitor_script_contains_webapp_reference():
    """Test that the monitoring script references the webapp container"""
    with open('/app/monitor_memory.sh', 'r') as f:
        content = f.read()

    assert 'webapp' in content, \
        "monitor_memory.sh should reference the 'webapp' container"


def test_monitor_script_contains_docker_commands():
    """Test that the monitoring script uses docker commands"""
    with open('/app/monitor_memory.sh', 'r') as f:
        content = f.read()

    # Should contain docker inspect or docker stats
    has_docker = 'docker inspect' in content or 'docker stats' in content
    assert has_docker, \
        "monitor_memory.sh should contain docker inspect or docker stats commands"


def test_memory_limit_increased():
    """Test that new memory limit is greater than initial limit"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    initial = int(data.get('initial_memory_limit', '0'))
    new = int(data.get('new_memory_limit', '0'))

    assert new > initial, \
        f"New memory limit ({new}) should be greater than initial limit ({initial})"


def test_memory_limit_doubled():
    """Test that memory limit was approximately doubled (1GB to 2GB)"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    initial = int(data.get('initial_memory_limit', '0'))
    new = int(data.get('new_memory_limit', '0'))

    # New should be approximately 2x initial (allowing small variance)
    ratio = new / initial if initial > 0 else 0
    assert 1.9 <= ratio <= 2.1, \
        f"Memory should be doubled (ratio ~2.0), got ratio {ratio:.2f}"


def test_no_hardcoded_dummy_data():
    """Test that the report doesn't contain obvious dummy/placeholder data"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    # Check that usage values are not suspiciously round numbers or zeros
    initial_usage = int(data.get('initial_memory_usage', '0'))
    new_usage = int(data.get('new_memory_usage', '0'))

    # Usage should be greater than 0 (container has some baseline usage)
    assert initial_usage > 0, \
        "initial_memory_usage should be greater than 0 (container has baseline usage)"

    assert new_usage > 0, \
        "new_memory_usage should be greater than 0 (container has baseline usage)"


def test_commands_are_strings():
    """Test that all commands in commands_used are strings"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    commands = data.get('commands_used', [])
    for i, cmd in enumerate(commands):
        assert isinstance(cmd, str), \
            f"Command at index {i} should be a string, got {type(cmd).__name__}"


def test_memory_usage_reasonable():
    """Test that memory usage values are within reasonable bounds"""
    with open('/app/memory_upgrade_report.json', 'r') as f:
        data = json.load(f)

    initial_limit = int(data.get('initial_memory_limit', '0'))
    new_limit = int(data.get('new_memory_limit', '0'))
    initial_usage = int(data.get('initial_memory_usage', '0'))
    new_usage = int(data.get('new_memory_usage', '0'))

    # Usage should not exceed limits (with some tolerance for measurement timing)
    assert initial_usage <= initial_limit * 1.1, \
        f"initial_memory_usage ({initial_usage}) exceeds initial_memory_limit ({initial_limit})"

    assert new_usage <= new_limit * 1.1, \
        f"new_memory_usage ({new_usage}) exceeds new_memory_limit ({new_limit})"
