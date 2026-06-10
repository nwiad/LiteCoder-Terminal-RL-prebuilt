"""
Tests for Buildroot RISC-V Pipeline Setup task.

Validates all 6 deliverables under /app:
  1. configs/riscv64_two_stage_defconfig
  2. build.sh
  3. sdcard.img
  4. sdcard.img.sha256
  5. qemu_boot.sh
  6. cross_compile_test.sh
"""

import os
import re
import stat
import struct
import hashlib
import subprocess

APP_DIR = "/app"


def _read_text(path):
    """Read file as text, return empty string if missing."""
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _read_bytes(path):
    """Read file as bytes, return empty bytes if missing."""
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return b""


def _is_executable(path):
    """Check if file has any execute permission bit set."""
    try:
        st = os.stat(path)
        return bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    except FileNotFoundError:
        return False


# =========================================================================
# 1. Defconfig — /app/configs/riscv64_two_stage_defconfig
# =========================================================================

DEFCONFIG_PATH = os.path.join(APP_DIR, "configs", "riscv64_two_stage_defconfig")


class TestDefconfig:
    """Validate the Buildroot defconfig fragment."""

    def test_defconfig_exists(self):
        assert os.path.isfile(DEFCONFIG_PATH), (
            f"Defconfig not found at {DEFCONFIG_PATH}"
        )

    def test_defconfig_not_empty(self):
        content = _read_text(DEFCONFIG_PATH)
        # Must have meaningful content, not just whitespace
        assert len(content.strip()) > 50, "Defconfig appears empty or trivially small"

    def test_riscv_arch(self):
        content = _read_text(DEFCONFIG_PATH)
        assert re.search(r"^BR2_riscv=y", content, re.MULTILINE), (
            "Missing BR2_riscv=y"
        )

    def test_riscv_64bit(self):
        content = _read_text(DEFCONFIG_PATH)
        assert re.search(r"^BR2_RISCV_64=y", content, re.MULTILINE), (
            "Missing BR2_RISCV_64=y"
        )

    def test_glibc_toolchain(self):
        content = _read_text(DEFCONFIG_PATH)
        assert re.search(
            r"^BR2_TOOLCHAIN_BUILDROOT_GLIBC=y", content, re.MULTILINE
        ), "Missing BR2_TOOLCHAIN_BUILDROOT_GLIBC=y"

    def test_busybox_enabled(self):
        content = _read_text(DEFCONFIG_PATH)
        assert re.search(r"^BR2_PACKAGE_BUSYBOX=y", content, re.MULTILINE), (
            "Missing BR2_PACKAGE_BUSYBOX=y"
        )

    def test_dropbear_enabled(self):
        content = _read_text(DEFCONFIG_PATH)
        assert re.search(r"^BR2_PACKAGE_DROPBEAR=y", content, re.MULTILINE), (
            "Missing BR2_PACKAGE_DROPBEAR=y"
        )

    def test_rootfs_ext2(self):
        content = _read_text(DEFCONFIG_PATH)
        assert re.search(r"^BR2_TARGET_ROOTFS_EXT2=y", content, re.MULTILINE), (
            "Missing BR2_TARGET_ROOTFS_EXT2=y"
        )

    def test_kernel_version_6_1(self):
        content = _read_text(DEFCONFIG_PATH)
        assert re.search(
            r'^BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE="6\.1[^"]*"',
            content,
            re.MULTILINE,
        ), "Missing or wrong BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE (must be 6.1.x)"

    def test_defconfig_valid_lines(self):
        """Every non-blank, non-comment line must be a valid BR2_ setting."""
        content = _read_text(DEFCONFIG_PATH)
        br2_pattern = re.compile(
            r"^(BR2_\w+=.+|# BR2_\w+ is not set)$"
        )
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            assert br2_pattern.match(stripped), (
                f"Invalid defconfig line: {stripped!r}"
            )


# =========================================================================
# 2. Build Script — /app/build.sh
# =========================================================================

BUILD_SH_PATH = os.path.join(APP_DIR, "build.sh")


class TestBuildScript:
    """Validate the two-stage build script."""

    def test_build_sh_exists(self):
        assert os.path.isfile(BUILD_SH_PATH), f"build.sh not found at {BUILD_SH_PATH}"

    def test_build_sh_executable(self):
        assert _is_executable(BUILD_SH_PATH), "build.sh is not executable"

    def test_build_sh_shebang(self):
        content = _read_text(BUILD_SH_PATH)
        assert content.startswith("#!/bin/bash") or content.startswith("#!/usr/bin/env bash"), (
            "build.sh must start with a bash shebang"
        )

    def test_buildroot_version_variable(self):
        content = _read_text(BUILD_SH_PATH)
        assert re.search(
            r'BUILDROOT_VERSION\s*=\s*["\']?2023\.02\.\d+', content
        ), "build.sh must define BUILDROOT_VERSION set to a 2023.02.x release"

    def test_stage1_present(self):
        content = _read_text(BUILD_SH_PATH)
        # Accept various naming conventions
        pattern = re.compile(r"(stage.?1|Stage.?1|STAGE.?1)", re.IGNORECASE)
        assert pattern.search(content), (
            "build.sh must contain a stage-1 section (stage1/Stage 1/STAGE_1)"
        )

    def test_stage2_present(self):
        content = _read_text(BUILD_SH_PATH)
        pattern = re.compile(r"(stage.?2|Stage.?2|STAGE.?2)", re.IGNORECASE)
        assert pattern.search(content), (
            "build.sh must contain a stage-2 section (stage2/Stage 2/STAGE_2)"
        )

    def test_sha256sum_invocation(self):
        content = _read_text(BUILD_SH_PATH)
        assert "sha256sum" in content, (
            "build.sh must invoke sha256sum for tarball verification"
        )

    def test_cross_compiler_reference(self):
        content = _read_text(BUILD_SH_PATH)
        assert "riscv64-linux-gcc" in content, (
            "build.sh must reference riscv64-linux-gcc cross-compiler"
        )

    def test_sdcard_img_reference(self):
        content = _read_text(BUILD_SH_PATH)
        assert "sdcard.img" in content, (
            "build.sh must reference sdcard.img for disk-image packaging"
        )

    def test_tarball_download(self):
        """Stage 1 must download or reference the Buildroot tarball."""
        content = _read_text(BUILD_SH_PATH)
        assert re.search(r"(wget|curl|buildroot.*\.tar)", content, re.IGNORECASE), (
            "build.sh must download or reference a Buildroot tarball"
        )

    def test_toolchain_build_step(self):
        """Stage 1 must build the toolchain."""
        content = _read_text(BUILD_SH_PATH)
        assert re.search(r"make\s+toolchain", content), (
            "build.sh stage 1 must invoke 'make toolchain'"
        )


# =========================================================================
# 3. Disk Image — /app/sdcard.img
# =========================================================================

SDCARD_PATH = os.path.join(APP_DIR, "sdcard.img")
EXPECTED_IMG_SIZE = 8 * 1024 * 1024  # 8 MiB = 8388608 bytes


class TestDiskImage:
    """Validate the raw disk image structure."""

    def test_sdcard_exists(self):
        assert os.path.isfile(SDCARD_PATH), f"sdcard.img not found at {SDCARD_PATH}"

    def test_sdcard_size_exactly_8mib(self):
        size = os.path.getsize(SDCARD_PATH)
        assert size == EXPECTED_IMG_SIZE, (
            f"sdcard.img must be exactly 8 MiB (8388608 bytes), got {size}"
        )

    def test_sdcard_has_mbr_signature(self):
        """MBR images end with the 0x55AA boot signature at offset 510."""
        data = _read_bytes(SDCARD_PATH)
        assert len(data) >= 512, "sdcard.img too small for MBR"
        assert data[510:512] == b"\x55\xaa", (
            "sdcard.img missing MBR boot signature (0x55AA) at offset 510"
        )

    def test_partition1_type_linux(self):
        """First partition entry in MBR must have type 0x83 (Linux)."""
        data = _read_bytes(SDCARD_PATH)
        assert len(data) >= 512, "sdcard.img too small for MBR"
        # MBR partition table entry 1 starts at offset 446, type byte at +4
        part1_type = data[446 + 4]
        assert part1_type == 0x83, (
            f"Partition 1 type must be 0x83 (Linux), got 0x{part1_type:02x}"
        )

    def test_partition1_starts_at_sector_2048(self):
        """Partition 1 LBA start must be 2048 (1 MiB offset)."""
        data = _read_bytes(SDCARD_PATH)
        assert len(data) >= 512, "sdcard.img too small"
        # LBA start is a 4-byte little-endian value at partition entry offset +8
        lba_start = struct.unpack_from("<I", data, 446 + 8)[0]
        assert lba_start == 2048, (
            f"Partition 1 must start at sector 2048 (1 MiB), got {lba_start}"
        )

    def test_ext2_magic_number(self):
        """The ext2 superblock at partition offset has magic 0xEF53."""
        data = _read_bytes(SDCARD_PATH)
        # Partition starts at 1 MiB = 1048576 bytes
        # ext2 superblock is at offset 1024 within the partition
        sb_offset = 1048576 + 1024
        assert len(data) >= sb_offset + 2, "sdcard.img too small for ext2 superblock"
        magic = struct.unpack_from("<H", data, sb_offset + 56)[0]
        assert magic == 0xEF53, (
            f"ext2 magic number expected 0xEF53 at partition offset, got 0x{magic:04x}"
        )


# =========================================================================
# 4. SHA-256 Hash — /app/sdcard.img.sha256
# =========================================================================

SHA256_PATH = os.path.join(APP_DIR, "sdcard.img.sha256")


class TestSha256:
    """Validate the SHA-256 hash file."""

    def test_sha256_file_exists(self):
        assert os.path.isfile(SHA256_PATH), (
            f"sdcard.img.sha256 not found at {SHA256_PATH}"
        )

    def test_sha256_is_64_hex_chars(self):
        content = _read_text(SHA256_PATH).strip()
        # Extract the first token (hash may be followed by filename)
        token = content.split()[0] if content.split() else ""
        assert re.fullmatch(r"[0-9a-fA-F]{64}", token), (
            f"SHA-256 file must contain a 64-char hex hash, got: {token!r}"
        )

    def test_sha256_matches_actual_image(self):
        """The stored hash must match the actual SHA-256 of sdcard.img."""
        if not os.path.isfile(SDCARD_PATH) or not os.path.isfile(SHA256_PATH):
            assert False, "Cannot verify hash: sdcard.img or sha256 file missing"

        # Compute actual hash
        h = hashlib.sha256()
        with open(SDCARD_PATH, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        actual_hash = h.hexdigest()

        # Read stored hash
        stored = _read_text(SHA256_PATH).strip().split()[0].lower()
        assert stored == actual_hash, (
            f"SHA-256 mismatch: stored={stored}, actual={actual_hash}"
        )


# =========================================================================
# 5. QEMU Boot Script — /app/qemu_boot.sh
# =========================================================================

QEMU_BOOT_PATH = os.path.join(APP_DIR, "qemu_boot.sh")


class TestQemuBootScript:
    """Validate the QEMU boot script."""

    def test_qemu_boot_exists(self):
        assert os.path.isfile(QEMU_BOOT_PATH), (
            f"qemu_boot.sh not found at {QEMU_BOOT_PATH}"
        )

    def test_qemu_boot_executable(self):
        assert _is_executable(QEMU_BOOT_PATH), "qemu_boot.sh is not executable"

    def test_qemu_boot_shebang(self):
        content = _read_text(QEMU_BOOT_PATH)
        first_line = content.split("\n")[0] if content else ""
        assert first_line.startswith("#!") and "bash" in first_line or "sh" in first_line, (
            "qemu_boot.sh must have a shell shebang"
        )

    def test_qemu_system_riscv64_reference(self):
        content = _read_text(QEMU_BOOT_PATH)
        assert "qemu-system-riscv64" in content, (
            "qemu_boot.sh must reference qemu-system-riscv64"
        )

    def test_nographic_flag(self):
        content = _read_text(QEMU_BOOT_PATH)
        assert "-nographic" in content, (
            "qemu_boot.sh must include -nographic flag"
        )

    def test_machine_type(self):
        content = _read_text(QEMU_BOOT_PATH)
        assert re.search(r"-machine\s+(virt|sifive_u)", content), (
            "qemu_boot.sh must specify -machine virt or sifive_u"
        )

    def test_disk_or_kernel_reference(self):
        content = _read_text(QEMU_BOOT_PATH)
        assert "sdcard.img" in content or "Image" in content or "rootfs" in content, (
            "qemu_boot.sh must reference sdcard.img or a kernel/rootfs path"
        )


# =========================================================================
# 6. Cross-Compile Test Script — /app/cross_compile_test.sh
# =========================================================================

CROSS_COMPILE_PATH = os.path.join(APP_DIR, "cross_compile_test.sh")


class TestCrossCompileScript:
    """Validate the cross-compile test script."""

    def test_cross_compile_exists(self):
        assert os.path.isfile(CROSS_COMPILE_PATH), (
            f"cross_compile_test.sh not found at {CROSS_COMPILE_PATH}"
        )

    def test_cross_compile_executable(self):
        assert _is_executable(CROSS_COMPILE_PATH), (
            "cross_compile_test.sh is not executable"
        )

    def test_cross_compile_shebang(self):
        content = _read_text(CROSS_COMPILE_PATH)
        first_line = content.split("\n")[0] if content else ""
        assert first_line.startswith("#!") and ("bash" in first_line or "sh" in first_line), (
            "cross_compile_test.sh must have a shell shebang"
        )

    def test_riscv64_gcc_reference(self):
        """Must invoke a RISC-V cross-compiler."""
        content = _read_text(CROSS_COMPILE_PATH)
        assert re.search(r"riscv64.*gcc", content, re.IGNORECASE), (
            "cross_compile_test.sh must reference a riscv64 gcc cross-compiler"
        )

    def test_hello_c_program(self):
        """Must contain or reference a C hello-world program."""
        content = _read_text(CROSS_COMPILE_PATH)
        has_inline_c = "printf" in content or 'puts' in content or "Hello" in content
        has_c_file_ref = "hello.c" in content
        assert has_inline_c or has_c_file_ref, (
            "cross_compile_test.sh must contain a Hello C program or reference hello.c"
        )

    def test_qemu_user_mode_reference(self):
        """Must reference qemu-riscv64 (user-mode) or qemu-system-riscv64."""
        content = _read_text(CROSS_COMPILE_PATH)
        assert "qemu-riscv64" in content or "qemu-system-riscv64" in content, (
            "cross_compile_test.sh must reference qemu-riscv64 or qemu-system-riscv64"
        )

    def test_cross_compile_not_trivially_empty(self):
        """Script must have meaningful content."""
        content = _read_text(CROSS_COMPILE_PATH)
        # Must have at least a few lines of real content
        non_empty_lines = [
            l for l in content.splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
        assert len(non_empty_lines) >= 3, (
            "cross_compile_test.sh appears trivially empty"
        )
