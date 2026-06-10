"""
Tests for Build an Optimized FFmpeg with H.265/HEVC Support task.

Validates:
1. /app/ffmpeg-static.tar.gz exists and is a valid gzip tarball containing an ffmpeg binary
2. The ffmpeg binary is a statically-linked ELF executable
3. The ffmpeg binary is stripped of debug symbols
4. ffmpeg -version reports --enable-libx265
5. ffmpeg -encoders lists libx265
6. ffmpeg -decoders lists hevc
7. /app/test_h265.mp4 exists and its video stream codec is hevc
"""

import os
import subprocess
import tarfile
import tempfile
import shutil
import stat
import pytest

TARBALL_PATH = "/app/ffmpeg-static.tar.gz"
TEST_VIDEO_PATH = "/app/test_h265.mp4"

# Shared fixture: extract ffmpeg binary from tarball once for all tests
@pytest.fixture(scope="session")
def extracted_ffmpeg(tmp_path_factory):
    """Extract the ffmpeg binary from the tarball into a temp directory."""
    assert os.path.isfile(TARBALL_PATH), f"Tarball not found at {TARBALL_PATH}"
    assert os.path.getsize(TARBALL_PATH) > 0, "Tarball is empty (0 bytes)"

    tmpdir = tmp_path_factory.mktemp("ffmpeg_extract")

    with tarfile.open(TARBALL_PATH, "r:gz") as tf:
        tf.extractall(path=str(tmpdir))

    # Find the ffmpeg binary inside the extracted contents
    ffmpeg_path = None
    for root, dirs, files in os.walk(str(tmpdir)):
        for f in files:
            if f == "ffmpeg":
                candidate = os.path.join(root, f)
                ffmpeg_path = candidate
                break
        if ffmpeg_path:
            break

    assert ffmpeg_path is not None, "No 'ffmpeg' file found inside the tarball"
    assert os.path.getsize(ffmpeg_path) > 0, "Extracted ffmpeg binary is empty (0 bytes)"

    # Make it executable
    os.chmod(ffmpeg_path, os.stat(ffmpeg_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return ffmpeg_path


# ─── Test 1: Tarball existence and validity ───

class TestTarball:
    def test_tarball_exists(self):
        """Tarball must exist at the specified path."""
        assert os.path.isfile(TARBALL_PATH), f"Expected tarball at {TARBALL_PATH}"

    def test_tarball_not_empty(self):
        """Tarball must not be empty."""
        size = os.path.getsize(TARBALL_PATH)
        assert size > 1000, f"Tarball is suspiciously small ({size} bytes); expected a real ffmpeg binary"

    def test_tarball_is_valid_gzip(self):
        """Tarball must be a valid gzip-compressed tar archive."""
        assert tarfile.is_tarfile(TARBALL_PATH), "File is not a valid tar archive"
        with tarfile.open(TARBALL_PATH, "r:gz") as tf:
            members = tf.getnames()
            assert len(members) > 0, "Tarball contains no files"

    def test_tarball_contains_ffmpeg(self):
        """Tarball must contain a file named 'ffmpeg'."""
        with tarfile.open(TARBALL_PATH, "r:gz") as tf:
            names = tf.getnames()
        # Accept ffmpeg at any path inside the tarball (e.g., "ffmpeg", "./ffmpeg", "bin/ffmpeg")
        has_ffmpeg = any(os.path.basename(n) == "ffmpeg" for n in names)
        assert has_ffmpeg, f"Tarball does not contain 'ffmpeg'. Contents: {names}"


# ─── Test 2: Binary is a statically-linked ELF ───

class TestStaticLinking:
    def test_binary_is_elf(self, extracted_ffmpeg):
        """The ffmpeg binary must be an ELF executable."""
        result = subprocess.run(["file", extracted_ffmpeg], capture_output=True, text=True)
        output = result.stdout.lower()
        assert "elf" in output, f"Binary is not an ELF file. file output: {result.stdout}"

    def test_binary_is_statically_linked(self, extracted_ffmpeg):
        """The ffmpeg binary must be statically linked."""
        # Method 1: check `file` output for "statically linked"
        file_result = subprocess.run(["file", extracted_ffmpeg], capture_output=True, text=True)
        file_output = file_result.stdout.lower()

        # Method 2: check `ldd` — should fail or say "not a dynamic executable"
        ldd_result = subprocess.run(["ldd", extracted_ffmpeg], capture_output=True, text=True)
        ldd_output = (ldd_result.stdout + ldd_result.stderr).lower()

        is_static_by_file = "statically linked" in file_output or "static" in file_output
        is_static_by_ldd = (
            ldd_result.returncode != 0
            or "not a dynamic executable" in ldd_output
            or "not a dynamic" in ldd_output
        )

        assert is_static_by_file or is_static_by_ldd, (
            f"Binary does not appear to be statically linked.\n"
            f"file: {file_result.stdout.strip()}\n"
            f"ldd: {(ldd_result.stdout + ldd_result.stderr).strip()}"
        )


# ─── Test 3: Binary is stripped ───

class TestStripped:
    def test_binary_is_stripped(self, extracted_ffmpeg):
        """The ffmpeg binary must be stripped of debug symbols."""
        file_result = subprocess.run(["file", extracted_ffmpeg], capture_output=True, text=True)
        file_output = file_result.stdout.lower()

        # `file` should say "stripped" and NOT "not stripped"
        assert "not stripped" not in file_output, (
            f"Binary is not stripped. file output: {file_result.stdout.strip()}"
        )
        assert "stripped" in file_output, (
            f"Cannot confirm binary is stripped. file output: {file_result.stdout.strip()}"
        )


# ─── Test 4: ffmpeg -version shows --enable-libx265 ───

class TestX265Configuration:
    def test_version_shows_enable_libx265(self, extracted_ffmpeg):
        """ffmpeg -version must report --enable-libx265 in its configuration."""
        result = subprocess.run(
            [extracted_ffmpeg, "-version"],
            capture_output=True, text=True, timeout=30
        )
        combined = result.stdout + result.stderr
        assert "--enable-libx265" in combined, (
            f"ffmpeg -version does not show --enable-libx265.\nOutput:\n{combined[:2000]}"
        )


# ─── Test 5: ffmpeg -encoders lists libx265 ───

class TestEncoders:
    def test_encoders_list_libx265(self, extracted_ffmpeg):
        """ffmpeg -encoders must list libx265."""
        result = subprocess.run(
            [extracted_ffmpeg, "-encoders"],
            capture_output=True, text=True, timeout=30
        )
        combined = result.stdout + result.stderr
        assert "libx265" in combined, (
            f"ffmpeg -encoders does not list libx265.\nOutput:\n{combined[:2000]}"
        )


# ─── Test 6: ffmpeg -decoders lists hevc ───

class TestDecoders:
    def test_decoders_list_hevc(self, extracted_ffmpeg):
        """ffmpeg -decoders must list hevc."""
        result = subprocess.run(
            [extracted_ffmpeg, "-decoders"],
            capture_output=True, text=True, timeout=30
        )
        combined = result.stdout + result.stderr
        assert "hevc" in combined, (
            f"ffmpeg -decoders does not list hevc.\nOutput:\n{combined[:2000]}"
        )


# ─── Test 7: Test video existence and codec ───

class TestH265Video:
    def test_video_exists(self):
        """Test video must exist at the specified path."""
        assert os.path.isfile(TEST_VIDEO_PATH), f"Test video not found at {TEST_VIDEO_PATH}"

    def test_video_not_empty(self):
        """Test video must not be empty."""
        size = os.path.getsize(TEST_VIDEO_PATH)
        assert size > 500, f"Test video is suspiciously small ({size} bytes)"

    def test_video_codec_is_hevc(self, extracted_ffmpeg):
        """Test video's video stream codec must be hevc."""
        # Try ffprobe first (may or may not be in the tarball)
        # Fall back to ffmpeg -i which prints stream info to stderr
        result = subprocess.run(
            [extracted_ffmpeg, "-i", TEST_VIDEO_PATH],
            capture_output=True, text=True, timeout=30
        )
        combined = (result.stdout + result.stderr).lower()

        # ffmpeg -i output typically shows "Video: hevc" or "Video: h265" or "Video: hevc (Main)"
        hevc_found = ("hevc" in combined or "h265" in combined or "h.265" in combined)
        assert hevc_found, (
            f"Test video codec is not hevc/h265.\nffmpeg -i output:\n{combined[:2000]}"
        )

    def test_video_is_playable(self, extracted_ffmpeg):
        """Test video must be decodable by the built ffmpeg (not a corrupt file)."""
        # Attempt to decode the video to null output — should succeed with exit code 0
        result = subprocess.run(
            [extracted_ffmpeg, "-v", "error", "-i", TEST_VIDEO_PATH,
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=60
        )
        # Allow for minor warnings, but check no fatal errors
        assert result.returncode == 0, (
            f"ffmpeg could not decode test video (exit code {result.returncode}).\n"
            f"stderr: {result.stderr[:2000]}"
        )


# ─── Test 8: Functional encode test — the binary can actually encode H.265 ───

class TestFunctionalEncode:
    def test_can_encode_h265(self, extracted_ffmpeg, tmp_path):
        """The extracted ffmpeg must be able to encode a new H.265 video from scratch."""
        output_file = str(tmp_path / "functional_test.mp4")
        result = subprocess.run(
            [extracted_ffmpeg, "-y",
             "-f", "lavfi", "-i", "color=c=red:s=64x64:d=1:r=10",
             "-c:v", "libx265",
             "-preset", "ultrafast",
             "-x265-params", "log-level=error",
             output_file],
            capture_output=True, text=True, timeout=120
        )
        assert result.returncode == 0, (
            f"Failed to encode H.265 video (exit code {result.returncode}).\n"
            f"stderr: {result.stderr[:2000]}"
        )
        assert os.path.isfile(output_file), "Encoded output file was not created"
        assert os.path.getsize(output_file) > 100, "Encoded output file is suspiciously small"
