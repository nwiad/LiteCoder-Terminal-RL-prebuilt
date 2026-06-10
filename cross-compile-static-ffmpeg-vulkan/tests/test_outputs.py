"""
Tests for cross-compile-static-ffmpeg-vulkan task.

Verifies:
  1. /app/ffmpeg exists and is a valid statically-linked ELF x86_64 binary
  2. The binary executes correctly (ffmpeg -version)
  3. Vulkan filters are present in the binary
  4. /app/build_report.json exists, is valid JSON, has correct schema
  5. Report consistency: md5, size, static_linked, vulkan_filters
  6. Minimum codec requirements (x264, x265)
"""

import hashlib
import json
import os
import re
import stat
import subprocess

FFMPEG_BIN = "/app/ffmpeg"
REPORT_PATH = "/app/build_report.json"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def run_cmd(cmd, timeout=30):
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", "command not found"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def load_report():
    """Load and return the build report as a dict, or None."""
    if not os.path.isfile(REPORT_PATH):
        return None
    with open(REPORT_PATH, "r") as f:
        return json.load(f)


def md5_of_file(path):
    """Compute MD5 hex digest of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ===========================================================================
# 1. Binary existence and basic properties
# ===========================================================================

def test_ffmpeg_binary_exists():
    """The ffmpeg binary must exist at /app/ffmpeg."""
    assert os.path.isfile(FFMPEG_BIN), f"{FFMPEG_BIN} does not exist"


def test_ffmpeg_binary_not_empty():
    """The binary must not be an empty file."""
    size = os.path.getsize(FFMPEG_BIN)
    # A real statically-linked ffmpeg is at least several MB
    assert size > 1_000_000, (
        f"{FFMPEG_BIN} is only {size} bytes — too small for a static ffmpeg"
    )


def test_ffmpeg_binary_is_executable():
    """The binary must have the executable permission bit set."""
    mode = os.stat(FFMPEG_BIN).st_mode
    assert mode & stat.S_IXUSR, f"{FFMPEG_BIN} is not executable"


# ===========================================================================
# 2. ELF / x86_64 / static linking checks
# ===========================================================================

def test_ffmpeg_is_elf_x86_64():
    """'file' output must indicate ELF 64-bit x86-64."""
    rc, stdout, stderr = run_cmd(["file", FFMPEG_BIN])
    combined = stdout + stderr
    assert rc == 0, f"file command failed: {combined}"
    assert "ELF" in combined, f"Not an ELF binary: {combined}"
    assert "x86-64" in combined or "x86_64" in combined, (
        f"Not x86-64 architecture: {combined}"
    )


def test_ffmpeg_statically_linked_file():
    """'file' output must say 'statically linked'."""
    rc, stdout, stderr = run_cmd(["file", FFMPEG_BIN])
    combined = (stdout + stderr).lower()
    assert "statically linked" in combined, (
        f"Binary is not statically linked per 'file': {stdout + stderr}"
    )


def test_ffmpeg_statically_linked_ldd():
    """'ldd' must report 'not a dynamic executable' or similar."""
    rc, stdout, stderr = run_cmd(["ldd", FFMPEG_BIN])
    combined = (stdout + stderr).lower()
    # ldd returns non-zero for static binaries on most systems
    assert (
        "not a dynamic executable" in combined
        or "statically linked" in combined
        or "not a dynamic" in combined  # some ldd variants
    ), f"ldd suggests dynamic linking: {stdout + stderr}"


# ===========================================================================
# 3. Binary execution and version
# ===========================================================================

def test_ffmpeg_version_runs():
    """/app/ffmpeg -version must exit 0."""
    rc, stdout, stderr = run_cmd([FFMPEG_BIN, "-version"])
    assert rc == 0, (
        f"ffmpeg -version exited with code {rc}. "
        f"stdout={stdout[:500]}, stderr={stderr[:500]}"
    )


def test_ffmpeg_version_output_nonempty():
    """Version output must contain 'ffmpeg version'."""
    rc, stdout, stderr = run_cmd([FFMPEG_BIN, "-version"])
    combined = stdout + stderr
    assert "ffmpeg version" in combined.lower(), (
        f"Version output missing 'ffmpeg version': {combined[:500]}"
    )


# ===========================================================================
# 4. Vulkan filter support
# ===========================================================================

def _get_vulkan_filter_names():
    """Return list of vulkan filter names from ffmpeg -filters."""
    rc, stdout, stderr = run_cmd([FFMPEG_BIN, "-filters"])
    combined = stdout + stderr
    filters = []
    for line in combined.splitlines():
        # Filter lines: "  T.C scale_vulkan  V->V  ..."
        m = re.match(r"\s+[A-Z.]{3}\s+(\S+)", line)
        if m:
            name = m.group(1)
            if "vulkan" in name.lower():
                filters.append(name)
    return filters


def test_vulkan_filters_present():
    """ffmpeg -filters must list at least one vulkan filter."""
    filters = _get_vulkan_filter_names()
    assert len(filters) >= 1, (
        "No Vulkan filters found in 'ffmpeg -filters' output"
    )


# ===========================================================================
# 5. Build report — existence and schema
# ===========================================================================

def test_report_exists():
    """/app/build_report.json must exist."""
    assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} does not exist"


def test_report_valid_json():
    """The report must be parseable JSON."""
    with open(REPORT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "build_report.json is empty or trivial"
    data = json.loads(content)  # will raise on invalid JSON
    assert isinstance(data, dict), "Top-level JSON must be an object"


REQUIRED_KEYS = [
    "ffmpeg_version",
    "binary_path",
    "binary_size_bytes",
    "binary_md5",
    "docker_image",
    "static_linked",
    "vulkan_filters",
    "enabled_encoders",
    "enabled_decoders",
]


def test_report_has_all_required_keys():
    """Report must contain every required key."""
    data = load_report()
    assert data is not None, "Could not load report"
    missing = [k for k in REQUIRED_KEYS if k not in data]
    assert not missing, f"Missing keys in report: {missing}"


def test_report_field_types():
    """Each field must have the correct type."""
    data = load_report()
    assert data is not None

    assert isinstance(data["ffmpeg_version"], str) and len(data["ffmpeg_version"]) > 0
    assert isinstance(data["binary_path"], str) and len(data["binary_path"]) > 0
    assert isinstance(data["binary_size_bytes"], int)
    assert isinstance(data["binary_md5"], str) and len(data["binary_md5"]) == 32
    assert isinstance(data["docker_image"], str) and len(data["docker_image"]) > 0
    assert data["static_linked"] is True  # must be boolean true
    assert isinstance(data["vulkan_filters"], list)
    assert isinstance(data["enabled_encoders"], list)
    assert isinstance(data["enabled_decoders"], list)


# ===========================================================================
# 6. Report consistency — cross-checks against actual binary
# ===========================================================================

def test_report_static_linked_is_true():
    """The static_linked field must be boolean true."""
    data = load_report()
    assert data is not None
    assert data["static_linked"] is True, (
        f"static_linked is {data['static_linked']!r}, expected True"
    )


def test_report_binary_size_matches():
    """binary_size_bytes must match the actual file size of /app/ffmpeg."""
    data = load_report()
    assert data is not None
    actual_size = os.path.getsize(FFMPEG_BIN)
    reported_size = data["binary_size_bytes"]
    assert reported_size == actual_size, (
        f"Size mismatch: report says {reported_size}, actual is {actual_size}"
    )


def test_report_binary_md5_matches():
    """binary_md5 must match the actual MD5 of /app/ffmpeg."""
    data = load_report()
    assert data is not None
    actual_md5 = md5_of_file(FFMPEG_BIN)
    reported_md5 = data["binary_md5"].strip().lower()
    assert reported_md5 == actual_md5, (
        f"MD5 mismatch: report says {reported_md5}, actual is {actual_md5}"
    )


def test_report_binary_path():
    """binary_path should reference /app/ffmpeg."""
    data = load_report()
    assert data is not None
    assert data["binary_path"].rstrip("/") == "/app/ffmpeg", (
        f"binary_path is {data['binary_path']!r}, expected '/app/ffmpeg'"
    )


# ===========================================================================
# 7. Report — Vulkan filters
# ===========================================================================

def test_report_vulkan_filters_nonempty():
    """vulkan_filters must be a non-empty list."""
    data = load_report()
    assert data is not None
    vf = data["vulkan_filters"]
    assert isinstance(vf, list) and len(vf) > 0, (
        f"vulkan_filters is empty or not a list: {vf!r}"
    )


def test_report_vulkan_filters_contain_vulkan_substring():
    """Every entry in vulkan_filters must contain 'vulkan' (case-insensitive)."""
    data = load_report()
    assert data is not None
    for name in data["vulkan_filters"]:
        assert "vulkan" in name.lower(), (
            f"Filter name '{name}' does not contain 'vulkan'"
        )


def test_report_vulkan_filters_consistent_with_binary():
    """Vulkan filters in the report should be a subset of what the binary reports."""
    data = load_report()
    assert data is not None
    binary_vulkan = set(_get_vulkan_filter_names())
    report_vulkan = set(data["vulkan_filters"])
    # The report should not list filters the binary doesn't have
    extra = report_vulkan - binary_vulkan
    # Allow minor differences (e.g. naming), but report should not be fabricated
    # At minimum, the intersection must be non-empty
    intersection = report_vulkan & binary_vulkan
    assert len(intersection) > 0 or len(extra) == 0, (
        f"Report vulkan_filters don't match binary. "
        f"Report: {report_vulkan}, Binary: {binary_vulkan}"
    )


# ===========================================================================
# 8. Report — Encoders and decoders (minimum: x264, x265)
# ===========================================================================

def test_report_encoders_nonempty():
    """enabled_encoders must not be empty."""
    data = load_report()
    assert data is not None
    assert len(data["enabled_encoders"]) > 0, "enabled_encoders is empty"


def test_report_decoders_nonempty():
    """enabled_decoders must not be empty."""
    data = load_report()
    assert data is not None
    assert len(data["enabled_decoders"]) > 0, "enabled_decoders is empty"


def test_report_has_x264_encoder():
    """At minimum, x264 encoder must be present (libx264)."""
    data = load_report()
    assert data is not None
    enc_lower = [e.lower() for e in data["enabled_encoders"]]
    assert any("x264" in e or "libx264" in e for e in enc_lower), (
        f"No x264/libx264 encoder found in: {data['enabled_encoders'][:20]}"
    )


def test_report_has_x265_encoder():
    """At minimum, x265 encoder must be present (libx265)."""
    data = load_report()
    assert data is not None
    enc_lower = [e.lower() for e in data["enabled_encoders"]]
    assert any("x265" in e or "libx265" in e for e in enc_lower), (
        f"No x265/libx265 encoder found in: {data['enabled_encoders'][:20]}"
    )


# ===========================================================================
# 9. Docker image field
# ===========================================================================

def test_report_docker_image_is_ubuntu():
    """docker_image should reference an Ubuntu base image."""
    data = load_report()
    assert data is not None
    img = data["docker_image"].lower()
    assert "ubuntu" in img, (
        f"docker_image '{data['docker_image']}' does not reference Ubuntu"
    )


# ===========================================================================
# 10. Version string consistency
# ===========================================================================

def test_report_version_matches_binary():
    """ffmpeg_version in report should match the first line of ffmpeg -version."""
    data = load_report()
    assert data is not None
    rc, stdout, stderr = run_cmd([FFMPEG_BIN, "-version"])
    assert rc == 0, "ffmpeg -version failed"
    combined = stdout + stderr
    first_line = combined.strip().split("\n")[0].strip()
    reported = data["ffmpeg_version"].strip()
    # Allow the report to be a substring or equal (some may include extra info)
    assert (
        reported == first_line
        or reported in first_line
        or first_line in reported
    ), (
        f"Version mismatch: report='{reported}', binary='{first_line}'"
    )
