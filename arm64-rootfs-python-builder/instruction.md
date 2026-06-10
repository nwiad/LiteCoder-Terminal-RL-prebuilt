## Root Filesystem Builder with Custom Python Layer

Build a minimal ARM64 root filesystem with a custom Python 3.11 interpreter and create a bootable SD card image for Raspberry Pi 4.

## Technical Requirements

- **Platform**: Linux x86_64 host system
- **Target Architecture**: ARM64 (aarch64)
- **Base System**: Ubuntu 22.04 (Jammy)
- **Python Version**: 3.11.7
- **Tools**: debootstrap, qemu-user-static, gcc-aarch64-linux-gnu, make, wget

## Input Specifications

No input files required. The task uses system tools and downloads source packages.

## Output Specifications

### 1. Root Filesystem Directory
- **Path**: `/app/rootfs/`
- **Structure**: Complete ARM64 root filesystem with:
  - `/usr/local/bin/python3.11` (cross-compiled Python interpreter)
  - `/etc/fstab` (filesystem table configuration)
  - `/etc/hostname` (system hostname)
  - `/etc/network/interfaces` (network configuration)
  - Standard FHS directories (bin, lib, usr, var, etc.)

### 2. SD Card Image
- **Path**: `/app/sdcard.img`
- **Size**: Between 1GB and 4GB
- **Partition Table**: MBR or GPT with at least 2 partitions:
  - Boot partition (FAT32, ~256MB)
  - Root partition (ext4, remaining space)

### 3. Build Manifest
- **Path**: `/app/build_manifest.json`
- **Format**: JSON with the following structure:
```json
{
  "base_system": "ubuntu-22.04",
  "architecture": "arm64",
  "python_version": "3.11.7",
  "rootfs_size_mb": <integer>,
  "image_size_mb": <integer>,
  "build_timestamp": "<ISO 8601 timestamp>",
  "partitions": [
    {"number": 1, "type": "boot", "filesystem": "vfat", "size_mb": <integer>},
    {"number": 2, "type": "root", "filesystem": "ext4", "size_mb": <integer>}
  ]
}
```

### 4. Custom Layer Structure
- **Path**: `/app/meta-custom/`
- **Contents**:
  - `conf/layer.conf` (layer configuration)
  - `recipes-python/python3/` (Python recipe directory)
  - Installation scripts for Python deployment

## Implementation Requirements

1. **Root Filesystem Creation**:
   - Use debootstrap to create Ubuntu 22.04 ARM64 base system
   - Configure QEMU user-mode emulation for ARM64 binaries
   - Install essential packages in the rootfs

2. **Python Cross-Compilation**:
   - Download Python 3.11.7 source from python.org
   - Cross-compile for aarch64-linux-gnu target
   - Build with optimization flags: `-O3` and LTO enabled
   - Install to `/usr/local` prefix in rootfs

3. **System Configuration**:
   - Create `/etc/fstab` with root and boot partition entries
   - Set hostname to "rpi4-custom"
   - Configure basic network interface (eth0 with DHCP)

4. **SD Card Image Creation**:
   - Create sparse image file
   - Partition with boot (FAT32) and root (ext4) partitions
   - Copy rootfs contents to root partition
   - Ensure image is mountable and filesystem is valid

5. **Verification**:
   - Python interpreter must be executable (ELF ARM64 binary)
   - All required configuration files must exist
   - Image must have valid partition table
   - Generate build_manifest.json with accurate metadata

## Success Criteria

- `/app/rootfs/usr/local/bin/python3.11` exists and is an ARM64 ELF binary
- `/app/sdcard.img` exists and contains valid partition table
- `/app/build_manifest.json` exists with all required fields
- `/app/meta-custom/` directory structure is created
- Root filesystem contains all essential system directories
