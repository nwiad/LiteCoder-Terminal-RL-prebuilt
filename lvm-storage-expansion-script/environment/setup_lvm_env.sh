#!/bin/bash
# Setup script to create a simulated LVM environment for testing.
# This script creates loop-device-backed LVM volumes to simulate
# a real disk environment inside a container.
#
# Prerequisites: Must run in a privileged container with access to /dev.
#
# What this sets up:
#   - A loop device acting as the "existing" disk with an LVM VG and LV mounted at /
#     (In practice, the root FS is already on an LV in many cloud/VM setups,
#      so we create a secondary VG/LV to simulate the existing setup)
#   - A 10GB raw disk at /dev/sdb (via loop device) for the script to expand into

set -e

echo "=== Setting up LVM test environment ==="

# Install LVM tools if not present
apt-get update && apt-get install -y lvm2 parted e2fsprogs xfsprogs fdisk jq kmod && rm -rf /var/lib/apt/lists/*

# Ensure device-mapper is available
modprobe dm-mod 2>/dev/null || true

# Start lvmetad if available
service lvm2-lvmetad start 2>/dev/null || true

# Create a 10GB sparse file to act as /dev/sdb
DISK_FILE=/tmp/sdb_disk.img
truncate -s 10G "$DISK_FILE"

# Set up loop device as /dev/sdb
losetup /dev/sdb "$DISK_FILE" 2>/dev/null || {
    # If /dev/sdb is taken, find next available and symlink
    LOOP=$(losetup --find --show "$DISK_FILE")
    ln -sf "$LOOP" /dev/sdb
}

echo "=== /dev/sdb is ready (10GB raw disk) ==="
echo "=== LVM test environment setup complete ==="
echo ""
echo "The existing system should already have an LVM root filesystem."
echo "/dev/sdb is available as a raw unpartitioned 10GB disk."
