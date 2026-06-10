"""
Tests for custom kernel boot logo task.

Verifies that the agent correctly:
1. Downloaded and extracted Linux 6.8 kernel source
2. Placed a valid PPM logo at the correct path
3. Configured the kernel with required flags
4. Built the kernel (bzImage)
5. Produced all required artifact files
"""

import os
import subprocess
import struct

# ── Paths ──────────────────────────────────────────────────────────────────────
KERNEL_DIR = "/app/linux-6.8"
LOGO_PPM = os.path.join(KERNEL_DIR, "drivers/video/logo/logo_linux_clut224.ppm")
LOGO_OBJ = os.path.join(KERNEL_DIR, "drivers/video/logo/logo_linux_clut224.o")
KERNEL_CONFIG = os.path.join(KERNEL_DIR, ".config")
BZIMAGE = os.path.join(KERNEL_DIR, "arch/x86/boot/bzImage")
MAKEFILE = os.path.join(KERNEL_DIR, "Makefile")


# ── 1. Kernel source tree ─────────────────────────────────────────────────────

def test_kernel_source_directory_exists():
    """The kernel source tree must be extracted at /app/linux-6.8/."""
    assert os.path.isdir(KERNEL_DIR), (
        f"Kernel source directory not found at {KERNEL_DIR}"
    )


def test_kernel_makefile_exists():
    """The top-level Makefile must exist in the kernel source tree."""
    assert os.path.isfile(MAKEFILE), (
        f"Kernel Makefile not found at {MAKEFILE}"
    )


def test_kernel_version_is_6_8():
    """The kernel source must be version 6.8.x (check Makefile VERSION/PATCHLEVEL)."""
    assert os.path.isfile(MAKEFILE), f"Makefile not found at {MAKEFILE}"

    version = None
    patchlevel = None
    with open(MAKEFILE, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("VERSION") and "=" in line:
                parts = line.split("=", 1)
                val = parts[1].strip()
                if val.isdigit():
                    version = int(val)
            elif line.startswith("PATCHLEVEL") and "=" in line:
                parts = line.split("=", 1)
                val = parts[1].strip()
                if val.isdigit():
                    patchlevel = int(val)
            # Stop after finding both
            if version is not None and patchlevel is not None:
                break

    assert version == 6, f"Expected kernel VERSION=6, got {version}"
    assert patchlevel == 8, f"Expected kernel PATCHLEVEL=8, got {patchlevel}"


# ── 2. Logo PPM file ──────────────────────────────────────────────────────────

def test_logo_ppm_exists():
    """The logo PPM file must exist at the correct kernel path."""
    assert os.path.isfile(LOGO_PPM), (
        f"Logo PPM file not found at {LOGO_PPM}"
    )


def test_logo_ppm_not_empty():
    """The logo PPM file must not be empty or trivially small."""
    assert os.path.isfile(LOGO_PPM), f"Logo PPM not found at {LOGO_PPM}"
    size = os.path.getsize(LOGO_PPM)
    # An 80x80 PPM with any real content should be at least a few hundred bytes
    assert size > 500, (
        f"Logo PPM file is suspiciously small ({size} bytes). "
        "Expected a valid 80x80 image."
    )


def _parse_ppm_header(filepath):
    """Parse PPM header, supporting both P3 (ASCII) and P6 (binary).
    Returns (magic, width, height, maxval).
    """
    with open(filepath, "rb") as f:
        raw = f.read()

    # Read magic number
    idx = 0
    # Skip any leading whitespace
    while idx < len(raw) and raw[idx:idx+1] in (b' ', b'\t', b'\n', b'\r'):
        idx += 1

    magic = raw[idx:idx+2].decode("ascii", errors="replace")
    idx += 2

    # Helper to read next token (skip whitespace and comments)
    def next_token(start):
        i = start
        # Skip whitespace and comments
        while i < len(raw):
            if raw[i:i+1] in (b' ', b'\t', b'\n', b'\r'):
                i += 1
            elif raw[i:i+1] == b'#':
                # Skip comment line
                while i < len(raw) and raw[i:i+1] != b'\n':
                    i += 1
                i += 1  # skip the newline
            else:
                break
        # Read token
        token_start = i
        while i < len(raw) and raw[i:i+1] not in (b' ', b'\t', b'\n', b'\r'):
            i += 1
        token = raw[token_start:i].decode("ascii", errors="replace")
        return token, i

    width_str, idx = next_token(idx)
    height_str, idx = next_token(idx)
    maxval_str, idx = next_token(idx)

    return magic, int(width_str), int(height_str), int(maxval_str)


def test_logo_ppm_valid_format():
    """The logo must be a valid PPM file (P3 or P6 magic number)."""
    assert os.path.isfile(LOGO_PPM), f"Logo PPM not found at {LOGO_PPM}"
    magic, width, height, maxval = _parse_ppm_header(LOGO_PPM)
    assert magic in ("P3", "P6"), (
        f"Logo PPM has invalid magic number '{magic}'. Expected P3 or P6."
    )


def test_logo_ppm_dimensions():
    """The logo must be exactly 80x80 pixels."""
    assert os.path.isfile(LOGO_PPM), f"Logo PPM not found at {LOGO_PPM}"
    magic, width, height, maxval = _parse_ppm_header(LOGO_PPM)
    assert width == 80, f"Logo width is {width}, expected 80"
    assert height == 80, f"Logo height is {height}, expected 80"


def test_logo_ppm_maxval():
    """The logo PPM maxval must be 255 (standard 8-bit color)."""
    assert os.path.isfile(LOGO_PPM), f"Logo PPM not found at {LOGO_PPM}"
    magic, width, height, maxval = _parse_ppm_header(LOGO_PPM)
    assert maxval == 255, f"Logo PPM maxval is {maxval}, expected 255"


def _count_unique_colors_p3(filepath):
    """Count unique colors in a P3 (ASCII) PPM file."""
    with open(filepath, "r") as f:
        content = f.read()

    # Remove comments
    lines = []
    for line in content.split("\n"):
        comment_idx = line.find("#")
        if comment_idx >= 0:
            line = line[:comment_idx]
        lines.append(line)
    content = " ".join(lines)
    tokens = content.split()

    # tokens[0] = P3, tokens[1] = width, tokens[2] = height, tokens[3] = maxval
    # pixel data starts at tokens[4]
    pixel_tokens = tokens[4:]
    colors = set()
    for i in range(0, len(pixel_tokens) - 2, 3):
        r, g, b = pixel_tokens[i], pixel_tokens[i+1], pixel_tokens[i+2]
        colors.add((r, g, b))
    return len(colors)


def _count_unique_colors_p6(filepath):
    """Count unique colors in a P6 (binary) PPM file."""
    with open(filepath, "rb") as f:
        raw = f.read()

    # Parse header to find where pixel data starts
    idx = 0
    # Skip magic
    while idx < len(raw) and raw[idx:idx+1] not in (b' ', b'\t', b'\n', b'\r'):
        idx += 1

    def skip_ws_comments(start):
        i = start
        while i < len(raw):
            if raw[i:i+1] in (b' ', b'\t', b'\n', b'\r'):
                i += 1
            elif raw[i:i+1] == b'#':
                while i < len(raw) and raw[i:i+1] != b'\n':
                    i += 1
                i += 1
            else:
                break
        return i

    def read_token(start):
        i = skip_ws_comments(start)
        token_start = i
        while i < len(raw) and raw[i:i+1] not in (b' ', b'\t', b'\n', b'\r'):
            i += 1
        return raw[token_start:i].decode("ascii"), i

    width_str, idx = read_token(idx)
    height_str, idx = read_token(idx)
    maxval_str, idx = read_token(idx)

    # After maxval, exactly one whitespace character before pixel data
    idx += 1

    pixel_data = raw[idx:]
    colors = set()
    for i in range(0, len(pixel_data) - 2, 3):
        colors.add((pixel_data[i], pixel_data[i+1], pixel_data[i+2]))
    return len(colors)


def test_logo_has_multiple_colors():
    """The logo must contain at least 2 distinct colors (not blank/single-color)."""
    assert os.path.isfile(LOGO_PPM), f"Logo PPM not found at {LOGO_PPM}"
    magic, width, height, maxval = _parse_ppm_header(LOGO_PPM)

    if magic == "P3":
        num_colors = _count_unique_colors_p3(LOGO_PPM)
    elif magic == "P6":
        num_colors = _count_unique_colors_p6(LOGO_PPM)
    else:
        assert False, f"Unknown PPM format: {magic}"

    assert num_colors >= 2, (
        f"Logo has only {num_colors} unique color(s). "
        "Must contain at least 2 distinct colors."
    )


def test_logo_at_most_224_colors():
    """The logo must have at most 224 unique colors (Clut224 format)."""
    assert os.path.isfile(LOGO_PPM), f"Logo PPM not found at {LOGO_PPM}"
    magic, width, height, maxval = _parse_ppm_header(LOGO_PPM)

    if magic == "P3":
        num_colors = _count_unique_colors_p3(LOGO_PPM)
    elif magic == "P6":
        num_colors = _count_unique_colors_p6(LOGO_PPM)
    else:
        assert False, f"Unknown PPM format: {magic}"

    assert num_colors <= 224, (
        f"Logo has {num_colors} unique colors, exceeds 224 limit for Clut224."
    )


# ── 3. Kernel config ──────────────────────────────────────────────────────────

def test_kernel_config_exists():
    """The kernel .config file must exist."""
    assert os.path.isfile(KERNEL_CONFIG), (
        f"Kernel config not found at {KERNEL_CONFIG}"
    )


def test_kernel_config_not_empty():
    """The kernel .config must not be empty."""
    assert os.path.isfile(KERNEL_CONFIG), f"Config not found at {KERNEL_CONFIG}"
    size = os.path.getsize(KERNEL_CONFIG)
    # A real defconfig-based .config is typically 100KB+
    assert size > 10000, (
        f"Kernel .config is only {size} bytes, too small for a real config."
    )


def _read_config_value(key):
    """Read a config key from the kernel .config file.
    Returns the value string (e.g. 'y', 'm', or a quoted string),
    or None if not found / commented out.
    """
    if not os.path.isfile(KERNEL_CONFIG):
        return None
    with open(KERNEL_CONFIG, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                continue
            if line.startswith(key + "="):
                return line.split("=", 1)[1]
    return None


def test_config_logo_enabled():
    """CONFIG_LOGO must be set to 'y' in the kernel config."""
    val = _read_config_value("CONFIG_LOGO")
    assert val == "y", (
        f"CONFIG_LOGO is '{val}', expected 'y'. "
        "Logo support must be built-in."
    )


def test_config_logo_clut224_enabled():
    """CONFIG_LOGO_LINUX_CLUT224 must be set to 'y' in the kernel config."""
    val = _read_config_value("CONFIG_LOGO_LINUX_CLUT224")
    assert val == "y", (
        f"CONFIG_LOGO_LINUX_CLUT224 is '{val}', expected 'y'. "
        "The 224-color Linux logo must be built-in."
    )


# ── 4. Built kernel image (bzImage) ───────────────────────────────────────────

def test_bzimage_exists():
    """The built bzImage must exist at the expected path."""
    assert os.path.isfile(BZIMAGE), (
        f"bzImage not found at {BZIMAGE}"
    )


def test_bzimage_not_trivially_small():
    """The bzImage must be a real kernel image, not a dummy file.
    A minimal x86_64 bzImage is typically several MB.
    """
    assert os.path.isfile(BZIMAGE), f"bzImage not found at {BZIMAGE}"
    size = os.path.getsize(BZIMAGE)
    # A real bzImage is at least 1MB; typically 5-15MB
    min_size = 1 * 1024 * 1024  # 1 MB
    assert size >= min_size, (
        f"bzImage is only {size} bytes ({size / 1024 / 1024:.2f} MB). "
        f"A real kernel image should be at least 1 MB."
    )


def test_bzimage_is_linux_kernel():
    """The bzImage must be identified as a Linux kernel boot image by `file`."""
    assert os.path.isfile(BZIMAGE), f"bzImage not found at {BZIMAGE}"
    result = subprocess.run(
        ["file", BZIMAGE],
        capture_output=True, text=True, timeout=10
    )
    output = result.stdout.lower()
    # `file` typically reports something like:
    # "Linux kernel x86 boot executable bzImage, ..."
    assert "linux" in output and "boot" in output, (
        f"bzImage does not appear to be a Linux kernel boot image. "
        f"`file` output: {result.stdout.strip()}"
    )


# ── 5. Logo object file ───────────────────────────────────────────────────────

def test_logo_object_file_exists():
    """The compiled logo object file must exist, proving the logo was compiled."""
    assert os.path.isfile(LOGO_OBJ), (
        f"Logo object file not found at {LOGO_OBJ}. "
        "This file is produced when the logo is compiled into the kernel."
    )


def test_logo_object_file_not_empty():
    """The logo .o file must not be empty."""
    assert os.path.isfile(LOGO_OBJ), f"Logo .o not found at {LOGO_OBJ}"
    size = os.path.getsize(LOGO_OBJ)
    # A compiled logo object should be at least a few KB
    assert size > 1000, (
        f"Logo object file is only {size} bytes, too small for a real "
        "compiled logo object."
    )


def test_logo_object_is_elf():
    """The logo .o file must be a valid ELF object file."""
    assert os.path.isfile(LOGO_OBJ), f"Logo .o not found at {LOGO_OBJ}"
    with open(LOGO_OBJ, "rb") as f:
        magic = f.read(4)
    assert magic == b'\x7fELF', (
        f"Logo object file does not have ELF magic bytes. "
        f"Got: {magic!r}"
    )
