import os
import json
import subprocess
import re

# Base paths - tests run from /app, outputs are in /app
ROOTFS_PATH = "/app/rootfs"
SDCARD_IMAGE = "/app/sdcard.img"
BUILD_MANIFEST = "/app/build_manifest.json"
META_CUSTOM = "/app/meta-custom"
PYTHON_BINARY = "/app/rootfs/usr/local/bin/python3.11"


def run_command(cmd):
    """Execute command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_python_binary_exists():
    """Test that Python 3.11 binary exists"""
    assert os.path.exists(PYTHON_BINARY), f"Python binary not found at {PYTHON_BINARY}"


def test_python_binary_is_arm64_elf():
    """Test that Python binary is a valid ARM64 ELF executable"""
    returncode, stdout, stderr = run_command(f"file {PYTHON_BINARY}")
    assert returncode == 0, f"Failed to run file command: {stderr}"

    # Check for ARM64/aarch64 architecture
    assert "aarch64" in stdout.lower() or "arm64" in stdout.lower(), \
        f"Python binary is not ARM64 architecture: {stdout}"

    # Check for ELF format
    assert "ELF" in stdout, f"Python binary is not ELF format: {stdout}"

    # Check it's executable
    assert "executable" in stdout.lower(), f"Python binary is not executable: {stdout}"


def test_python_binary_not_empty():
    """Test that Python binary is not empty or trivially small"""
    size = os.path.getsize(PYTHON_BINARY)
    # A real Python binary should be at least 1MB
    assert size > 1_000_000, f"Python binary is suspiciously small: {size} bytes"


def test_sdcard_image_exists():
    """Test that SD card image file exists"""
    assert os.path.exists(SDCARD_IMAGE), f"SD card image not found at {SDCARD_IMAGE}"


def test_sdcard_image_size_in_range():
    """Test that SD card image is within specified size range (1GB-4GB)"""
    size_bytes = os.path.getsize(SDCARD_IMAGE)
    size_mb = size_bytes / (1024 * 1024)

    assert 1000 <= size_mb <= 4096, \
        f"SD card image size {size_mb:.0f}MB is outside valid range (1000-4096 MB)"


def test_sdcard_image_has_partition_table():
    """Test that SD card image has a valid partition table"""
    returncode, stdout, stderr = run_command(f"fdisk -l {SDCARD_IMAGE}")
    assert returncode == 0, f"Failed to read partition table: {stderr}"

    # Check for partition table presence
    assert "Disk" in stdout, f"No partition table found in image"

    # Should have at least 2 partitions
    partition_count = stdout.count(f"{SDCARD_IMAGE}")
    # Subtract 1 for the header line
    assert partition_count >= 3, f"Expected at least 2 partitions, found {partition_count - 1}"


def test_sdcard_image_has_boot_partition():
    """Test that SD card image has a boot partition (FAT32)"""
    returncode, stdout, stderr = run_command(f"fdisk -l {SDCARD_IMAGE}")
    assert returncode == 0, f"Failed to read partition table: {stderr}"

    # Check for FAT partition (W95 FAT32, FAT16, etc.)
    assert "FAT" in stdout or "W95" in stdout or "c" in stdout.lower(), \
        f"No FAT boot partition found: {stdout}"


def test_sdcard_image_has_linux_partition():
    """Test that SD card image has a Linux root partition"""
    returncode, stdout, stderr = run_command(f"fdisk -l {SDCARD_IMAGE}")
    assert returncode == 0, f"Failed to read partition table: {stderr}"

    # Check for Linux partition
    assert "Linux" in stdout or "83" in stdout, \
        f"No Linux root partition found: {stdout}"


def test_build_manifest_exists():
    """Test that build manifest JSON exists"""
    assert os.path.exists(BUILD_MANIFEST), f"Build manifest not found at {BUILD_MANIFEST}"


def test_build_manifest_valid_json():
    """Test that build manifest is valid JSON"""
    with open(BUILD_MANIFEST, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            assert False, f"Build manifest is not valid JSON: {e}"


def test_build_manifest_required_fields():
    """Test that build manifest contains all required fields"""
    with open(BUILD_MANIFEST, 'r') as f:
        manifest = json.load(f)

    required_fields = [
        "base_system",
        "architecture",
        "python_version",
        "rootfs_size_mb",
        "image_size_mb",
        "build_timestamp",
        "partitions"
    ]

    for field in required_fields:
        assert field in manifest, f"Missing required field: {field}"


def test_build_manifest_base_system():
    """Test that base_system is ubuntu-22.04"""
    with open(BUILD_MANIFEST, 'r') as f:
        manifest = json.load(f)

    assert manifest["base_system"] == "ubuntu-22.04", \
        f"Expected base_system 'ubuntu-22.04', got '{manifest['base_system']}'"


def test_build_manifest_architecture():
    """Test that architecture is arm64"""
    with open(BUILD_MANIFEST, 'r') as f:
        manifest = json.load(f)

    assert manifest["architecture"] == "arm64", \
        f"Expected architecture 'arm64', got '{manifest['architecture']}'"


def test_build_manifest_python_version():
    """Test that python_version is 3.11.7"""
    with open(BUILD_MANIFEST, 'r') as f:
        manifest = json.load(f)

    assert manifest["python_version"] == "3.11.7", \
        f"Expected python_version '3.11.7', got '{manifest['python_version']}'"


def test_build_manifest_sizes_reasonable():
    """Test that manifest sizes are reasonable integers"""
    with open(BUILD_MANIFEST, 'r') as f:
        manifest = json.load(f)

    # Check rootfs_size_mb is positive integer
    assert isinstance(manifest["rootfs_size_mb"], int), \
        f"rootfs_size_mb should be integer, got {type(manifest['rootfs_size_mb'])}"
    assert manifest["rootfs_size_mb"] > 0, \
        f"rootfs_size_mb should be positive, got {manifest['rootfs_size_mb']}"

    # Check image_size_mb is positive integer and within range
    assert isinstance(manifest["image_size_mb"], int), \
        f"image_size_mb should be integer, got {type(manifest['image_size_mb'])}"
    assert 1000 <= manifest["image_size_mb"] <= 4096, \
        f"image_size_mb should be 1000-4096, got {manifest['image_size_mb']}"


def test_build_manifest_timestamp_format():
    """Test that build_timestamp is valid ISO 8601 format"""
    with open(BUILD_MANIFEST, 'r') as f:
        manifest = json.load(f)

    timestamp = manifest["build_timestamp"]

    # Check for ISO 8601 format (basic validation)
    iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    assert re.match(iso_pattern, timestamp), \
        f"build_timestamp is not ISO 8601 format: {timestamp}"


def test_build_manifest_partitions_structure():
    """Test that partitions array has correct structure"""
    with open(BUILD_MANIFEST, 'r') as f:
        manifest = json.load(f)

    partitions = manifest["partitions"]

    # Should have exactly 2 partitions
    assert len(partitions) == 2, \
        f"Expected 2 partitions, got {len(partitions)}"

    # Check partition 1 (boot)
    p1 = partitions[0]
    assert p1["number"] == 1, f"Partition 1 number should be 1, got {p1['number']}"
    assert p1["type"] == "boot", f"Partition 1 type should be 'boot', got {p1['type']}"
    assert p1["filesystem"] == "vfat", f"Partition 1 filesystem should be 'vfat', got {p1['filesystem']}"
    assert isinstance(p1["size_mb"], int) and p1["size_mb"] > 0, \
        f"Partition 1 size_mb should be positive integer, got {p1['size_mb']}"

    # Check partition 2 (root)
    p2 = partitions[1]
    assert p2["number"] == 2, f"Partition 2 number should be 2, got {p2['number']}"
    assert p2["type"] == "root", f"Partition 2 type should be 'root', got {p2['type']}"
    assert p2["filesystem"] == "ext4", f"Partition 2 filesystem should be 'ext4', got {p2['filesystem']}"
    assert isinstance(p2["size_mb"], int) and p2["size_mb"] > 0, \
        f"Partition 2 size_mb should be positive integer, got {p2['size_mb']}"


def test_meta_custom_layer_exists():
    """Test that meta-custom layer directory exists"""
    assert os.path.exists(META_CUSTOM), f"Meta-custom layer not found at {META_CUSTOM}"
    assert os.path.isdir(META_CUSTOM), f"Meta-custom should be a directory"


def test_meta_custom_layer_conf_exists():
    """Test that layer.conf exists in meta-custom"""
    layer_conf = os.path.join(META_CUSTOM, "conf", "layer.conf")
    assert os.path.exists(layer_conf), f"layer.conf not found at {layer_conf}"


def test_meta_custom_layer_conf_content():
    """Test that layer.conf has valid content"""
    layer_conf = os.path.join(META_CUSTOM, "conf", "layer.conf")

    with open(layer_conf, 'r') as f:
        content = f.read()

    # Check for essential layer configuration elements
    assert "BBPATH" in content, "layer.conf missing BBPATH"
    assert "BBFILES" in content, "layer.conf missing BBFILES"
    assert "BBFILE_COLLECTIONS" in content, "layer.conf missing BBFILE_COLLECTIONS"
    assert "meta-custom" in content, "layer.conf missing meta-custom reference"


def test_meta_custom_python_recipe_dir_exists():
    """Test that Python recipe directory exists"""
    recipe_dir = os.path.join(META_CUSTOM, "recipes-python", "python3")
    assert os.path.exists(recipe_dir), f"Python recipe directory not found at {recipe_dir}"
    assert os.path.isdir(recipe_dir), f"Python recipe path should be a directory"


def test_rootfs_directory_exists():
    """Test that rootfs directory exists"""
    assert os.path.exists(ROOTFS_PATH), f"Rootfs directory not found at {ROOTFS_PATH}"
    assert os.path.isdir(ROOTFS_PATH), f"Rootfs should be a directory"


def test_rootfs_has_standard_directories():
    """Test that rootfs has standard FHS directories"""
    standard_dirs = ["bin", "lib", "usr", "var", "etc", "tmp"]

    for dir_name in standard_dirs:
        dir_path = os.path.join(ROOTFS_PATH, dir_name)
        assert os.path.exists(dir_path), f"Standard directory missing: {dir_name}"


def test_fstab_exists():
    """Test that /etc/fstab exists in rootfs"""
    fstab = os.path.join(ROOTFS_PATH, "etc", "fstab")
    assert os.path.exists(fstab), f"fstab not found at {fstab}"


def test_fstab_content():
    """Test that fstab has required mount entries"""
    fstab = os.path.join(ROOTFS_PATH, "etc", "fstab")

    with open(fstab, 'r') as f:
        content = f.read()

    # Check for root partition entry
    assert "/dev/mmcblk0p2" in content or "ext4" in content, \
        "fstab missing root partition entry"

    # Check for boot partition entry
    assert "/dev/mmcblk0p1" in content or "vfat" in content or "/boot" in content, \
        "fstab missing boot partition entry"


def test_hostname_exists():
    """Test that /etc/hostname exists in rootfs"""
    hostname_file = os.path.join(ROOTFS_PATH, "etc", "hostname")
    assert os.path.exists(hostname_file), f"hostname file not found at {hostname_file}"


def test_hostname_content():
    """Test that hostname is set to rpi4-custom"""
    hostname_file = os.path.join(ROOTFS_PATH, "etc", "hostname")

    with open(hostname_file, 'r') as f:
        content = f.read().strip()

    assert content == "rpi4-custom", \
        f"Expected hostname 'rpi4-custom', got '{content}'"


def test_network_interfaces_exists():
    """Test that /etc/network/interfaces exists in rootfs"""
    interfaces = os.path.join(ROOTFS_PATH, "etc", "network", "interfaces")
    assert os.path.exists(interfaces), f"network interfaces file not found at {interfaces}"


def test_network_interfaces_content():
    """Test that network interfaces has eth0 DHCP configuration"""
    interfaces = os.path.join(ROOTFS_PATH, "etc", "network", "interfaces")

    with open(interfaces, 'r') as f:
        content = f.read()

    # Check for loopback interface
    assert "lo" in content and "loopback" in content, \
        "network interfaces missing loopback configuration"

    # Check for eth0 with DHCP
    assert "eth0" in content, "network interfaces missing eth0 configuration"
    assert "dhcp" in content.lower(), "network interfaces missing DHCP configuration"


def test_rootfs_not_empty():
    """Test that rootfs is not trivially empty"""
    # Count files in rootfs (should have many files)
    returncode, stdout, stderr = run_command(f"find {ROOTFS_PATH} -type f | wc -l")
    assert returncode == 0, f"Failed to count files in rootfs: {stderr}"

    file_count = int(stdout.strip())
    # A real rootfs should have at least 100 files
    assert file_count > 100, \
        f"Rootfs appears empty or incomplete: only {file_count} files found"


def test_manifest_sizes_match_actual():
    """Test that manifest sizes are reasonably close to actual sizes"""
    with open(BUILD_MANIFEST, 'r') as f:
        manifest = json.load(f)

    # Check image size matches actual file size (within 10% tolerance)
    actual_image_mb = os.path.getsize(SDCARD_IMAGE) / (1024 * 1024)
    manifest_image_mb = manifest["image_size_mb"]

    # Allow some variance due to sparse files and rounding
    tolerance = 0.15  # 15% tolerance
    lower_bound = manifest_image_mb * (1 - tolerance)
    upper_bound = manifest_image_mb * (1 + tolerance)

    assert lower_bound <= actual_image_mb <= upper_bound, \
        f"Manifest image_size_mb ({manifest_image_mb}) doesn't match actual size ({actual_image_mb:.0f}MB)"
