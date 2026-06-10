"""
Tests for Build Static FFmpeg with VMAF Support task.

Verifies all 9 criteria from instruction.md:
1. Binary exists and is executable
2. Statically linked
3. VMAF filter available
4. --enable-libvmaf in buildconf
5. --enable-libx264 in buildconf
6. --enable-libx265 in buildconf
7. Basic functionality (-version)
8. Encoder availability (libx264, libx265)
9. End-to-end VMAF scoring test
"""

import os
import subprocess
import stat
import pytest

FFMPEG_PATH = "/app/ffmpeg"

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run_ffmpeg(*args, timeout=60):
    """Run the ffmpeg binary with given arguments and return CompletedProcess."""
    cmd = [FFMPEG_PATH] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result


# ---------------------------------------------------------------------------
# 1. Binary existence and executability
# ---------------------------------------------------------------------------

class TestBinaryExists:
    def test_file_exists(self):
        """The file /app/ffmpeg must exist."""
        assert os.path.exists(FFMPEG_PATH), f"{FFMPEG_PATH} does not exist"

    def test_is_regular_file(self):
        """Must be a regular file, not a directory or symlink to nothing."""
        assert os.path.isfile(FFMPEG_PATH), f"{FFMPEG_PATH} is not a regular file"

    def test_is_executable(self):
        """Must have executable permission."""
        st = os.stat(FFMPEG_PATH)
        assert st.st_mode & stat.S_IXUSR, f"{FFMPEG_PATH} is not executable"

    def test_not_empty(self):
        """Binary must not be an empty file (lazy agent guard)."""
        size = os.path.getsize(FFMPEG_PATH)
        # A real static ffmpeg binary is at least several MB
        assert size > 1_000_000, (
            f"{FFMPEG_PATH} is suspiciously small ({size} bytes). "
            "A statically-linked FFmpeg should be several MB."
        )


# ---------------------------------------------------------------------------
# 2. Static linking
# ---------------------------------------------------------------------------

class TestStaticLinking:
    def test_file_reports_statically_linked(self):
        """Running `file /app/ffmpeg` must contain 'statically linked'."""
        result = subprocess.run(
            ["file", FFMPEG_PATH],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"`file` command failed: {result.stderr}"
        output = result.stdout.lower()
        assert "statically linked" in output, (
            f"Binary is not statically linked. `file` output:\n{result.stdout}"
        )

    def test_not_dynamically_linked(self):
        """Double-check: output must NOT say 'dynamically linked'."""
        result = subprocess.run(
            ["file", FFMPEG_PATH],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.lower()
        assert "dynamically linked" not in output, (
            f"Binary appears dynamically linked. `file` output:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# 3 & 4 & 5 & 6. Build configuration flags
# ---------------------------------------------------------------------------

class TestBuildConf:
    @pytest.fixture(scope="class")
    def buildconf_output(self):
        """Capture -buildconf output once for all tests in this class."""
        result = run_ffmpeg("-buildconf")
        # -buildconf writes to stderr
        combined = result.stdout + result.stderr
        return combined

    def test_enable_libvmaf(self, buildconf_output):
        """buildconf must contain --enable-libvmaf."""
        assert "--enable-libvmaf" in buildconf_output, (
            f"--enable-libvmaf not found in buildconf output:\n{buildconf_output}"
        )

    def test_enable_libx264(self, buildconf_output):
        """buildconf must contain --enable-libx264."""
        assert "--enable-libx264" in buildconf_output, (
            f"--enable-libx264 not found in buildconf output:\n{buildconf_output}"
        )

    def test_enable_libx265(self, buildconf_output):
        """buildconf must contain --enable-libx265."""
        assert "--enable-libx265" in buildconf_output, (
            f"--enable-libx265 not found in buildconf output:\n{buildconf_output}"
        )

    def test_enable_gpl(self, buildconf_output):
        """GPL must be enabled (required for x264/x265)."""
        assert "--enable-gpl" in buildconf_output, (
            f"--enable-gpl not found in buildconf output:\n{buildconf_output}"
        )


# ---------------------------------------------------------------------------
# 7. Basic functionality
# ---------------------------------------------------------------------------

class TestBasicFunctionality:
    def test_version_exits_zero(self):
        """`/app/ffmpeg -version` must exit with code 0."""
        result = run_ffmpeg("-version")
        assert result.returncode == 0, (
            f"ffmpeg -version exited with code {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_version_output_contains_ffmpeg(self):
        """Output must include 'ffmpeg version'."""
        result = run_ffmpeg("-version")
        combined = (result.stdout + result.stderr).lower()
        assert "ffmpeg version" in combined, (
            f"'ffmpeg version' not found in output:\n{result.stdout}\n{result.stderr}"
        )


# ---------------------------------------------------------------------------
# 3 (continued). VMAF filter available
# ---------------------------------------------------------------------------

class TestVMAFFilter:
    def test_libvmaf_in_filters(self):
        """`/app/ffmpeg -filters` must list libvmaf."""
        result = run_ffmpeg("-filters")
        combined = result.stdout + result.stderr
        assert "libvmaf" in combined, (
            f"libvmaf not found in -filters output:\n{combined[:2000]}"
        )


# ---------------------------------------------------------------------------
# 8. Encoder availability
# ---------------------------------------------------------------------------

class TestEncoders:
    @pytest.fixture(scope="class")
    def encoders_output(self):
        result = run_ffmpeg("-encoders")
        combined = result.stdout + result.stderr
        return combined

    def test_libx264_encoder(self, encoders_output):
        """-encoders must list libx264."""
        assert "libx264" in encoders_output, (
            f"libx264 not found in -encoders output:\n{encoders_output[:2000]}"
        )

    def test_libx265_encoder(self, encoders_output):
        """-encoders must list libx265."""
        assert "libx265" in encoders_output, (
            f"libx265 not found in -encoders output:\n{encoders_output[:2000]}"
        )


# ---------------------------------------------------------------------------
# 9. End-to-end VMAF scoring test
# ---------------------------------------------------------------------------

class TestVMAFEndToEnd:
    """
    Generate two synthetic test videos, then run a VMAF comparison.
    This is the strongest integration test — it exercises libx264 encoding
    and the libvmaf filter in a real pipeline.
    """

    REF_VIDEO = "/app/ref_test.mp4"
    DIST_VIDEO = "/app/dist_test.mp4"

    @pytest.fixture(scope="class", autouse=True)
    def generate_test_videos(self):
        """Generate reference and distorted test videos."""
        # Clean up any previous runs
        for f in [self.REF_VIDEO, self.DIST_VIDEO]:
            if os.path.exists(f):
                os.remove(f)

        # Generate reference video
        ref_result = run_ffmpeg(
            "-f", "lavfi",
            "-i", "testsrc=duration=1:size=320x240:rate=10",
            "-c:v", "libx264",
            "-y", self.REF_VIDEO,
            timeout=120,
        )
        assert ref_result.returncode == 0, (
            f"Failed to generate reference video.\n"
            f"stdout: {ref_result.stdout}\nstderr: {ref_result.stderr}"
        )

        # Generate distorted video
        dist_result = run_ffmpeg(
            "-f", "lavfi",
            "-i", "testsrc2=duration=1:size=320x240:rate=10",
            "-c:v", "libx264",
            "-y", self.DIST_VIDEO,
            timeout=120,
        )
        assert dist_result.returncode == 0, (
            f"Failed to generate distorted video.\n"
            f"stdout: {dist_result.stdout}\nstderr: {dist_result.stderr}"
        )

        yield

        # Cleanup
        for f in [self.REF_VIDEO, self.DIST_VIDEO]:
            if os.path.exists(f):
                os.remove(f)

    def test_reference_video_created(self):
        """Reference video must exist and be non-empty."""
        assert os.path.exists(self.REF_VIDEO), "Reference video was not created"
        assert os.path.getsize(self.REF_VIDEO) > 0, "Reference video is empty"

    def test_distorted_video_created(self):
        """Distorted video must exist and be non-empty."""
        assert os.path.exists(self.DIST_VIDEO), "Distorted video was not created"
        assert os.path.getsize(self.DIST_VIDEO) > 0, "Distorted video is empty"

    def test_vmaf_comparison_succeeds(self):
        """
        Run VMAF comparison between distorted and reference videos.
        This must exit with code 0, proving the full VMAF pipeline works.
        """
        result = run_ffmpeg(
            "-i", self.DIST_VIDEO,
            "-i", self.REF_VIDEO,
            "-lavfi", "libvmaf",
            "-f", "null",
            "-",
            timeout=180,
        )
        assert result.returncode == 0, (
            f"VMAF comparison failed with exit code {result.returncode}.\n"
            f"stderr: {result.stderr[-2000:]}"
        )

    def test_vmaf_outputs_score(self):
        """
        VMAF comparison must produce a VMAF score in the output.
        The score line typically looks like: 'VMAF score: XX.XXXXXX'
        or contains 'vmaf' with a numeric value.
        """
        result = run_ffmpeg(
            "-i", self.DIST_VIDEO,
            "-i", self.REF_VIDEO,
            "-lavfi", "libvmaf",
            "-f", "null",
            "-",
            timeout=180,
        )
        combined = (result.stdout + result.stderr).lower()
        # FFmpeg VMAF filter outputs a line containing "vmaf" and a score
        assert "vmaf" in combined, (
            f"No VMAF-related output found.\n{combined[-2000:]}"
        )


# ---------------------------------------------------------------------------
# Bonus: x265 encoder actually works
# ---------------------------------------------------------------------------

class TestX265Encoding:
    """Verify x265 encoder works by generating a short HEVC video."""

    OUTPUT = "/app/x265_test.mp4"

    def test_x265_encoding(self):
        """Generate a short video with libx265 to confirm it works."""
        if os.path.exists(self.OUTPUT):
            os.remove(self.OUTPUT)

        result = run_ffmpeg(
            "-f", "lavfi",
            "-i", "testsrc=duration=1:size=320x240:rate=10",
            "-c:v", "libx265",
            "-y", self.OUTPUT,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"x265 encoding failed with exit code {result.returncode}.\n"
            f"stderr: {result.stderr[-2000:]}"
        )
        assert os.path.exists(self.OUTPUT), "x265 output file was not created"
        assert os.path.getsize(self.OUTPUT) > 0, "x265 output file is empty"

        # Cleanup
        if os.path.exists(self.OUTPUT):
            os.remove(self.OUTPUT)
