"""
Tests for: Build a Static FFmpeg with VMAF Support

Validates that the agent produced a correctly built static FFmpeg binary
with VMAF filter and required codec support, plus a valid VMAF scoring result.
"""

import json
import os
import stat
import subprocess

FFMPEG_BIN = "/app/ffmpeg_static/bin/ffmpeg"
VMAF_RESULT = "/app/vmaf_result.json"
TEST_REF = "/app/test_ref.mp4"
TEST_DIST = "/app/test_dist.mp4"


# ─────────────────────────────────────────────────────────────
# 1. Binary existence and executability
# ─────────────────────────────────────────────────────────────

def test_ffmpeg_binary_exists():
    """The compiled FFmpeg binary must exist at the specified path."""
    assert os.path.isfile(FFMPEG_BIN), (
        f"FFmpeg binary not found at {FFMPEG_BIN}"
    )


def test_ffmpeg_binary_is_executable():
    """The FFmpeg binary must have the executable permission bit set."""
    assert os.path.isfile(FFMPEG_BIN), f"Binary missing: {FFMPEG_BIN}"
    mode = os.stat(FFMPEG_BIN).st_mode
    assert mode & stat.S_IXUSR, (
        f"Binary at {FFMPEG_BIN} is not executable (mode={oct(mode)})"
    )


def test_ffmpeg_binary_not_empty():
    """Guard against a lazy agent that creates an empty placeholder file."""
    assert os.path.isfile(FFMPEG_BIN), f"Binary missing: {FFMPEG_BIN}"
    size = os.path.getsize(FFMPEG_BIN)
    # A real static FFmpeg binary is at least several MB
    assert size > 1_000_000, (
        f"Binary is suspiciously small ({size} bytes). "
        "Expected a real compiled binary, not a placeholder."
    )


# ─────────────────────────────────────────────────────────────
# 2. Version output
# ─────────────────────────────────────────────────────────────

def test_ffmpeg_version_runs_successfully():
    """Running ffmpeg -version must exit with code 0."""
    result = subprocess.run(
        [FFMPEG_BIN, "-version"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"ffmpeg -version exited with code {result.returncode}.\n"
        f"stderr: {result.stderr[:500]}"
    )


def test_ffmpeg_version_contains_version_string():
    """The -version output must contain 'ffmpeg version'."""
    result = subprocess.run(
        [FFMPEG_BIN, "-version"],
        capture_output=True, text=True, timeout=30,
    )
    combined = result.stdout + result.stderr
    assert "ffmpeg version" in combined.lower(), (
        f"'ffmpeg version' not found in -version output:\n{combined[:500]}"
    )


# ─────────────────────────────────────────────────────────────
# 3. Static linking verification
# ─────────────────────────────────────────────────────────────

def test_static_linking():
    """
    ldd must report 'not a dynamic executable' OR show only minimal
    system-level deps. No references to libvmaf, libx264, libx265,
    or libfdk_aac shared libraries.
    """
    result = subprocess.run(
        ["ldd", FFMPEG_BIN],
        capture_output=True, text=True, timeout=30,
    )
    combined = (result.stdout + result.stderr).lower()

    # Forbidden shared library references
    forbidden = ["libvmaf", "libx264", "libx265", "libfdk_aac", "libfdk-aac"]
    for lib in forbidden:
        assert lib not in combined, (
            f"Found shared library reference '{lib}' in ldd output. "
            "The binary should be statically linked.\n"
            f"ldd output:\n{combined[:800]}"
        )


# ─────────────────────────────────────────────────────────────
# 4. VMAF filter availability
# ─────────────────────────────────────────────────────────────

def test_vmaf_filter_available():
    """ffmpeg -filters output must include 'libvmaf'."""
    result = subprocess.run(
        [FFMPEG_BIN, "-filters"],
        capture_output=True, text=True, timeout=30,
    )
    combined = (result.stdout + result.stderr).lower()
    assert "libvmaf" in combined, (
        "VMAF filter not found in -filters output.\n"
        f"Output (first 800 chars):\n{combined[:800]}"
    )


# ─────────────────────────────────────────────────────────────
# 5. Codec / encoder support
# ─────────────────────────────────────────────────────────────

def test_encoder_libx264():
    """ffmpeg -encoders must list libx264."""
    result = subprocess.run(
        [FFMPEG_BIN, "-encoders"],
        capture_output=True, text=True, timeout=30,
    )
    combined = (result.stdout + result.stderr).lower()
    assert "libx264" in combined, (
        "libx264 encoder not found in -encoders output."
    )


def test_encoder_libx265():
    """ffmpeg -encoders must list libx265."""
    result = subprocess.run(
        [FFMPEG_BIN, "-encoders"],
        capture_output=True, text=True, timeout=30,
    )
    combined = (result.stdout + result.stderr).lower()
    assert "libx265" in combined, (
        "libx265 encoder not found in -encoders output."
    )


def test_encoder_libfdk_aac():
    """ffmpeg -encoders must list libfdk_aac."""
    result = subprocess.run(
        [FFMPEG_BIN, "-encoders"],
        capture_output=True, text=True, timeout=30,
    )
    combined = (result.stdout + result.stderr).lower()
    assert "libfdk_aac" in combined, (
        "libfdk_aac encoder not found in -encoders output."
    )


# ─────────────────────────────────────────────────────────────
# 6. Test video files exist
# ─────────────────────────────────────────────────────────────

def test_reference_video_exists():
    """Reference test video must exist and not be empty."""
    assert os.path.isfile(TEST_REF), (
        f"Reference video not found at {TEST_REF}"
    )
    assert os.path.getsize(TEST_REF) > 0, (
        f"Reference video at {TEST_REF} is empty."
    )


def test_distorted_video_exists():
    """Distorted test video must exist and not be empty."""
    assert os.path.isfile(TEST_DIST), (
        f"Distorted video not found at {TEST_DIST}"
    )
    assert os.path.getsize(TEST_DIST) > 0, (
        f"Distorted video at {TEST_DIST} is empty."
    )


def test_reference_video_is_valid():
    """Reference video must be a valid media file that ffprobe/ffmpeg can read."""
    # Use the built ffmpeg to probe the file — if it can read duration, it's valid
    result = subprocess.run(
        [FFMPEG_BIN, "-i", TEST_REF, "-f", "null", "-t", "0.1", "-"],
        capture_output=True, text=True, timeout=30,
    )
    # ffmpeg returns 0 or writes stream info to stderr for valid files
    combined = (result.stdout + result.stderr).lower()
    assert "video:" in combined or "stream" in combined, (
        f"Reference video does not appear to be a valid media file.\n"
        f"ffmpeg output:\n{combined[:500]}"
    )


def test_distorted_video_is_valid():
    """Distorted video must be a valid media file."""
    result = subprocess.run(
        [FFMPEG_BIN, "-i", TEST_DIST, "-f", "null", "-t", "0.1", "-"],
        capture_output=True, text=True, timeout=30,
    )
    combined = (result.stdout + result.stderr).lower()
    assert "video:" in combined or "stream" in combined, (
        f"Distorted video does not appear to be a valid media file.\n"
        f"ffmpeg output:\n{combined[:500]}"
    )


# ─────────────────────────────────────────────────────────────
# 7. VMAF result JSON validation
# ─────────────────────────────────────────────────────────────

def test_vmaf_result_file_exists():
    """VMAF result JSON must exist and not be empty."""
    assert os.path.isfile(VMAF_RESULT), (
        f"VMAF result file not found at {VMAF_RESULT}"
    )
    assert os.path.getsize(VMAF_RESULT) > 0, (
        f"VMAF result file at {VMAF_RESULT} is empty."
    )


def test_vmaf_result_is_valid_json():
    """VMAF result must be parseable JSON, not a dummy text file."""
    assert os.path.isfile(VMAF_RESULT), f"Missing: {VMAF_RESULT}"
    with open(VMAF_RESULT, "r") as f:
        content = f.read().strip()
    assert len(content) > 10, (
        "VMAF result file is too short to be valid JSON."
    )
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"VMAF result is not valid JSON: {e}\n"
            f"Content (first 300 chars): {content[:300]}"
        )
    assert isinstance(data, dict), (
        f"VMAF result JSON root should be a dict, got {type(data).__name__}"
    )


def _extract_vmaf_score(data):
    """
    Walk the VMAF JSON structure to find the aggregate VMAF score.
    Handles multiple VMAF output formats across versions:
      - data["VMAF score"]
      - data["pooled_metrics"]["vmaf"]["mean"]
      - data["pooled_metrics"]["vmaf"]["harmonic_mean"]
      - data["aggregate"]["VMAF_score"]
    Returns the score as a float, or None if not found.
    """
    # Direct top-level key
    for key in ("VMAF score", "vmaf", "VMAF_score"):
        if key in data:
            val = data[key]
            if isinstance(val, (int, float)):
                return float(val)

    # pooled_metrics.vmaf.mean (common in newer VMAF versions)
    pooled = data.get("pooled_metrics", {})
    if isinstance(pooled, dict):
        vmaf_section = pooled.get("vmaf", {})
        if isinstance(vmaf_section, dict):
            for stat_key in ("mean", "harmonic_mean", "min", "max"):
                if stat_key in vmaf_section:
                    val = vmaf_section[stat_key]
                    if isinstance(val, (int, float)):
                        return float(val)

    # aggregate.VMAF_score (older format)
    aggregate = data.get("aggregate", {})
    if isinstance(aggregate, dict):
        for key in ("VMAF_score", "vmaf", "VMAF score"):
            if key in aggregate:
                val = aggregate[key]
                if isinstance(val, (int, float)):
                    return float(val)

    # Walk frames to compute mean as last resort
    frames = data.get("frames", [])
    if isinstance(frames, list) and len(frames) > 0:
        scores = []
        for frame in frames:
            metrics = frame.get("metrics", {})
            if isinstance(metrics, dict):
                for key in ("vmaf", "VMAF_score", "VMAF score"):
                    if key in metrics:
                        val = metrics[key]
                        if isinstance(val, (int, float)):
                            scores.append(float(val))
                            break
        if scores:
            return sum(scores) / len(scores)

    return None


def test_vmaf_result_contains_score():
    """VMAF JSON must contain a numeric VMAF score between 0 and 100."""
    assert os.path.isfile(VMAF_RESULT), f"Missing: {VMAF_RESULT}"
    with open(VMAF_RESULT, "r") as f:
        data = json.load(f)

    score = _extract_vmaf_score(data)
    assert score is not None, (
        "Could not find a VMAF score in the result JSON. "
        "Expected a numeric value under keys like 'VMAF score', "
        "'pooled_metrics.vmaf.mean', 'aggregate.VMAF_score', "
        "or per-frame 'metrics.vmaf'.\n"
        f"Top-level keys: {list(data.keys())}"
    )
    assert 0 <= score <= 100, (
        f"VMAF score {score} is outside the valid range [0, 100]."
    )


def test_vmaf_score_is_realistic():
    """
    The VMAF score should be a meaningful value — not exactly 0 or 100,
    which would suggest a dummy or broken result. A real comparison
    between a high-quality reference and a distorted version should
    produce a score roughly between 5 and 99.
    """
    assert os.path.isfile(VMAF_RESULT), f"Missing: {VMAF_RESULT}"
    with open(VMAF_RESULT, "r") as f:
        data = json.load(f)

    score = _extract_vmaf_score(data)
    if score is None:
        return  # Already caught by test_vmaf_result_contains_score

    assert 1 < score < 100, (
        f"VMAF score of {score} looks unrealistic. "
        "A real comparison between different-quality videos should "
        "produce a score between ~5 and ~99."
    )


# ─────────────────────────────────────────────────────────────
# 8. FFmpeg configuration flags (bonus structural check)
# ─────────────────────────────────────────────────────────────

def test_ffmpeg_configuration_includes_required_flags():
    """
    The ffmpeg -version output includes the configuration line.
    Verify key --enable flags are present.
    """
    result = subprocess.run(
        [FFMPEG_BIN, "-version"],
        capture_output=True, text=True, timeout=30,
    )
    combined = (result.stdout + result.stderr).lower()

    required_flags = [
        "--enable-gpl",
        "--enable-nonfree",
        "--enable-libvmaf",
        "--enable-libx264",
        "--enable-libx265",
        "--enable-libfdk-aac",
    ]
    for flag in required_flags:
        assert flag in combined, (
            f"Required configure flag '{flag}' not found in "
            f"ffmpeg -version output.\nOutput:\n{combined[:1000]}"
        )

