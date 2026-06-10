import os
import subprocess
import struct

def test_iso_file_exists():
    """Test that the ISO file exists at the expected location."""
    assert os.path.exists("/app/mini-linux.iso"), "ISO file /app/mini-linux.iso does not exist"

def test_iso_file_not_empty():
    """Test that the ISO file is not empty."""
    size = os.path.getsize("/app/mini-linux.iso")
    assert size > 0, "ISO file is empty"

def test_iso_size_under_20mb():
    """Test that the ISO file is under 20 MB (20971520 bytes)."""
    size = os.path.getsize("/app/mini-linux.iso")
    max_size = 20971520  # 20 MB in bytes
    assert size <= max_size, f"ISO size {size} bytes exceeds maximum {max_size} bytes ({size / 1024 / 1024:.2f} MB > 20 MB)"

def test_iso_format_valid():
    """Test that the file is a valid ISO 9660 filesystem."""
    # ISO 9660 has specific magic bytes at offset 0x8001 and 0x8801
    with open("/app/mini-linux.iso", "rb") as f:
        # Check primary volume descriptor at sector 16 (0x8000)
        f.seek(0x8001)
        magic = f.read(5)
        assert magic == b"CD001", f"Invalid ISO 9660 magic bytes: expected b'CD001', got {magic}"

def test_iso_has_minimum_size():
    """Test that the ISO has a reasonable minimum size (at least 5 MB) to contain kernel and initramfs."""
    size = os.path.getsize("/app/mini-linux.iso")
    min_size = 5 * 1024 * 1024  # 5 MB
    assert size >= min_size, f"ISO size {size} bytes is suspiciously small (< 5 MB), likely not a real bootable system"

def test_build_log_exists():
    """Test that the build log file exists."""
    assert os.path.exists("/app/build.log"), "Build log /app/build.log does not exist"

def test_build_log_not_empty():
    """Test that the build log is not empty."""
    size = os.path.getsize("/app/build.log")
    assert size > 0, "Build log is empty"

def test_build_log_contains_key_steps():
    """Test that the build log contains evidence of key build steps."""
    with open("/app/build.log", "r") as f:
        content = f.read()

    # Check for kernel-related content
    assert any(keyword in content.lower() for keyword in ["kernel", "linux", "bzimage", "vmlinuz"]), \
        "Build log does not mention kernel build"

    # Check for busybox-related content
    assert "busybox" in content.lower(), "Build log does not mention BusyBox"

    # Check for initramfs-related content
    assert "initramfs" in content.lower() or "initrd" in content.lower(), \
        "Build log does not mention initramfs/initrd"

def test_iso_contains_bootloader():
    """Test that the ISO contains bootloader files (isolinux)."""
    # Mount the ISO and check for bootloader files
    mount_point = "/tmp/iso_mount"
    os.makedirs(mount_point, exist_ok=True)

    try:
        # Mount the ISO
        result = subprocess.run(
            ["mount", "-o", "loop", "/app/mini-linux.iso", mount_point],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # If mount fails, try to check with isoinfo
            result = subprocess.run(
                ["isoinfo", "-l", "-i", "/app/mini-linux.iso"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, "Failed to read ISO contents"
            output = result.stdout.lower()
            assert "isolinux" in output or "syslinux" in output or "boot" in output, \
                "ISO does not appear to contain bootloader files"
        else:
            # Check for bootloader files
            found_bootloader = False
            for root, dirs, files in os.walk(mount_point):
                for file in files:
                    if file.lower() in ["isolinux.bin", "syslinux.bin", "ldlinux.c32"]:
                        found_bootloader = True
                        break
                if found_bootloader:
                    break

            # Unmount
            subprocess.run(["umount", mount_point], capture_output=True)

            assert found_bootloader, "ISO does not contain bootloader files (isolinux.bin or syslinux.bin)"
    finally:
        # Cleanup
        subprocess.run(["umount", mount_point], capture_output=True, stderr=subprocess.DEVNULL)
        if os.path.exists(mount_point):
            os.rmdir(mount_point)

def test_iso_contains_kernel():
    """Test that the ISO contains a kernel image."""
    mount_point = "/tmp/iso_mount_kernel"
    os.makedirs(mount_point, exist_ok=True)

    try:
        result = subprocess.run(
            ["mount", "-o", "loop", "/app/mini-linux.iso", mount_point],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # Use isoinfo as fallback
            result = subprocess.run(
                ["isoinfo", "-l", "-i", "/app/mini-linux.iso"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, "Failed to read ISO contents"
            output = result.stdout.lower()
            assert any(name in output for name in ["vmlinuz", "bzimage", "kernel", "vmlinux"]), \
                "ISO does not appear to contain a kernel image"
        else:
            # Check for kernel files
            found_kernel = False
            for root, dirs, files in os.walk(mount_point):
                for file in files:
                    if any(name in file.lower() for name in ["vmlinuz", "bzimage", "kernel", "vmlinux"]):
                        # Verify it's not empty and has reasonable size (at least 1 MB)
                        kernel_path = os.path.join(root, file)
                        kernel_size = os.path.getsize(kernel_path)
                        if kernel_size >= 1024 * 1024:  # At least 1 MB
                            found_kernel = True
                            break
                if found_kernel:
                    break

            subprocess.run(["umount", mount_point], capture_output=True)

            assert found_kernel, "ISO does not contain a valid kernel image (>= 1 MB)"
    finally:
        subprocess.run(["umount", mount_point], capture_output=True, stderr=subprocess.DEVNULL)
        if os.path.exists(mount_point):
            os.rmdir(mount_point)

def test_iso_contains_initramfs():
    """Test that the ISO contains an initramfs/initrd image."""
    mount_point = "/tmp/iso_mount_initramfs"
    os.makedirs(mount_point, exist_ok=True)

    try:
        result = subprocess.run(
            ["mount", "-o", "loop", "/app/mini-linux.iso", mount_point],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # Use isoinfo as fallback
            result = subprocess.run(
                ["isoinfo", "-l", "-i", "/app/mini-linux.iso"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, "Failed to read ISO contents"
            output = result.stdout.lower()
            assert any(name in output for name in ["initramfs", "initrd", "initram"]), \
                "ISO does not appear to contain an initramfs/initrd image"
        else:
            # Check for initramfs files
            found_initramfs = False
            for root, dirs, files in os.walk(mount_point):
                for file in files:
                    if any(name in file.lower() for name in ["initramfs", "initrd", "initram"]):
                        # Verify it's not empty and has reasonable size (at least 100 KB)
                        initramfs_path = os.path.join(root, file)
                        initramfs_size = os.path.getsize(initramfs_path)
                        if initramfs_size >= 100 * 1024:  # At least 100 KB
                            found_initramfs = True
                            break
                if found_initramfs:
                    break

            subprocess.run(["umount", mount_point], capture_output=True)

            assert found_initramfs, "ISO does not contain a valid initramfs/initrd image (>= 100 KB)"
    finally:
        subprocess.run(["umount", mount_point], capture_output=True, stderr=subprocess.DEVNULL)
        if os.path.exists(mount_point):
            os.rmdir(mount_point)

def test_iso_bootable_structure():
    """Test that the ISO has a bootable structure with boot catalog."""
    # Check for El Torito boot record (bootable CD signature)
    with open("/app/mini-linux.iso", "rb") as f:
        # El Torito boot record is typically at sector 17 (0x8800)
        # Look for boot record volume descriptor
        found_boot_record = False
        for sector in range(16, 32):  # Check sectors 16-31
            f.seek(sector * 2048)
            data = f.read(2048)
            if b"EL TORITO" in data or b"BOOT" in data:
                found_boot_record = True
                break

        assert found_boot_record, "ISO does not appear to have El Torito boot record (not bootable)"
