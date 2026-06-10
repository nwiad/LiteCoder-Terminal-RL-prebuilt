"""
Tests for the statically-linked FFmpeg binary build task.

Verifies:
1. Binary existence, executability, and minimum size
2. Static linking (no shared library dependencies)
3. All 7 required encoders present
4. All 7 required decoders present
5. GPL and nonfree license configuration
6. Version command succeeds
7. Functional test: can generate a real video file
"""

import os
import subprocess
import stat

FFMPEG_BIN = "/app/ffmpeg"

# ─── Helpers ────────────────────────────────────────────────────────────────

def run(cmd, timeout=30):
    """Run a command and return CompletedProcess. Never raises on non-zero exit."""
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )


# ─── 1. Binary existence and basic properties ──────────────────────────────

class TestBinaryExists:

    def test_ffmpeg_file_exists(self):
        """The binary must exist at /app/ffmpeg."""
        assert os.path.exists(FFMPEG_BIN), f"{FFMPEG_BIN} does not exist"

    def test_ffmpeg_is_a_file(self):
        """Must be a regular file, not a directory or symlink to nothing."""
        assert os.path.isfile(FFMPEG_BIN), f"{FFMPEG_BIN} is not a regular file"

    def test_ffmpeg_is_executable(self):
        """The binary must have the executable permission bit set."""
        mode = os.stat(FFMPEG_BIN).st_mode
        assert mode & stat.S_IXUSR, f"{FFMPEG_BIN} is not executable"

    def test_ffmpeg_minimum_size(self):
        """
        A real statically-linked FFmpeg with 7 codec libs is at least several MB.
        Reject trivially small files (e.g. empty file, shell script wrapper).
        """
        size = os.path.getsize(FFMPEG_BIN)
        # A static ffmpeg with these codecs is typically 30-80+ MB.
        # Use 5 MB as a generous lower bound to catch fakes.
        assert size > 5 * 1024 * 1024, (
            f"{FFMPEG_BIN} is only {size} bytes — too small for a static FFmpeg build"
        )

    def test_ffmpeg_is_elf_binary(self):
        """The file must be an ELF executable, not a script or text file."""
        result = run(f"file {FFMPEG_BIN}")
        assert result.returncode == 0
        output = result.stdout.lower()
        assert "elf" in output, (
            f"{FFMPEG_BIN} does not appear to be an ELF binary. "
            f"file output: {result.stdout.strip()}"
        )


# ─── 2. Static linking verification ────────────────────────────────────────

class TestStaticLinking:

    def test_file_reports_statically_linked(self):
        """
        `file /app/ffmpeg` must contain 'statically linked'.
        This is the primary static-linking check.
        """
        result = run(f"file {FFMPEG_BIN}")
        assert result.returncode == 0
        output = result.stdout.lower()
        assert "statically linked" in output, (
            f"Binary is not statically linked. file output: {result.stdout.strip()}"
        )

    def test_ldd_reports_not_dynamic(self):
        """
        `ldd /app/ffmpeg` should fail or report 'not a dynamic executable'.
        A statically linked binary has no shared library dependencies.
        """
        result = run(f"ldd {FFMPEG_BIN}")
        combined = (result.stdout + result.stderr).lower()
        # ldd on a static binary typically returns non-zero and/or prints
        # "not a dynamic executable"
        is_static = (
            "not a dynamic executable" in combined
            or "statically linked" in combined
            or result.returncode != 0
        )
        assert is_static, (
            f"ldd suggests the binary has shared deps. Output: {combined.strip()}"
        )


# ─── 3. Version command ────────────────────────────────────────────────────

class TestVersionCommand:

    def test_version_exits_zero(self):
        """`/app/ffmpeg -version` must exit with code 0."""
        result = run(f"{FFMPEG_BIN} -version")
        assert result.returncode == 0, (
            f"ffmpeg -version exited with code {result.returncode}. "
            f"stderr: {result.stderr.strip()}"
        )

    def test_version_output_contains_ffmpeg(self):
        """Version output should mention 'ffmpeg'."""
        result = run(f"{FFMPEG_BIN} -version")
        assert "ffmpeg" in result.stdout.lower(), (
            f"Version output does not mention ffmpeg: {result.stdout[:200]}"
        )


# ─── 4. License / build configuration ──────────────────────────────────────

class TestBuildConfiguration:

    def test_gpl_enabled(self):
        """FFmpeg must be built with --enable-gpl."""
        result = run(f"{FFMPEG_BIN} -version")
        assert result.returncode == 0
        output = result.stdout.lower()
        assert "--enable-gpl" in output, (
            "FFmpeg was not built with --enable-gpl"
        )

    def test_nonfree_enabled(self):
        """FFmpeg must be built with --enable-nonfree (required for fdk-aac)."""
        result = run(f"{FFMPEG_BIN} -version")
        assert result.returncode == 0
        output = result.stdout.lower()
        assert "--enable-nonfree" in output, (
            "FFmpeg was not built with --enable-nonfree"
        )


# ─── 5. Required encoders ──────────────────────────────────────────────────

REQUIRED_ENCODERS = [
    "libx264",
    "libx265",
    "libvpx_vp9",
    "libaom_av1",
    "libfdk_aac",
    "libmp3lame",
    "libopus",
]


class TestEncoders:
    """Each required encoder must appear in `ffmpeg -encoders` output."""

    def _get_encoders_output(self):
        result = run(f"{FFMPEG_BIN} -encoders")
        assert result.returncode == 0, (
            f"ffmpeg -encoders failed: {result.stderr.strip()}"
        )
        return result.stdout

    def test_encoder_libx264(self):
        output = self._get_encoders_output()
        assert "libx264" in output, "Encoder libx264 not found"

    def test_encoder_libx265(self):
        output = self._get_encoders_output()
        assert "libx265" in output, "Encoder libx265 not found"

    def test_encoder_libvpx_vp9(self):
        output = self._get_encoders_output()
        assert "libvpx_vp9" in output, "Encoder libvpx_vp9 not found"

    def test_encoder_libaom_av1(self):
        output = self._get_encoders_output()
        assert "libaom_av1" in output, "Encoder libaom_av1 not found"

    def test_encoder_libfdk_aac(self):
        output = self._get_encoders_output()
        assert "libfdk_aac" in output, "Encoder libfdk_aac not found"

    def test_encoder_libmp3lame(self):
        output = self._get_encoders_output()
        assert "libmp3lame" in output, "Encoder libmp3lame not found"

    def test_encoder_libopus(self):
        output = self._get_encoders_output()
        assert "libopus" in output, "Encoder libopus not found"


# ─── 6. Required decoders ──────────────────────────────────────────────────

REQUIRED_DECODERS = [
    "h264",
    "hevc",
    "vp9",
    "av1",
    "aac",
    "mp3",
    "opus",
]


class TestDecoders:
    """Each required decoder must appear in `ffmpeg -decoders` output."""

    def _get_decoders_output(self):
        result = run(f"{FFMPEG_BIN} -decoders")
        assert result.returncode == 0, (
            f"ffmpeg -decoders failed: {result.stderr.strip()}"
        )
        return result.stdout

    def _check_decoder(self, name):
        """
        Check decoder presence. We search for the decoder name surrounded by
        whitespace to avoid false positives (e.g. 'aac' matching 'libfdk_aac').
        The -decoders output format has columns separated by spaces, with the
        decoder name as a distinct token.
        """
        output = self._get_decoders_output()
        # Split each line into tokens and check if the decoder name is one of them
        for line in output.splitlines():
            tokens = line.split()
            if name in tokens:
                return
        assert False, f"Decoder '{name}' not found in ffmpeg -decoders output"

    def test_decoder_h264(self):
        self._check_decoder("h264")

    def test_decoder_hevc(self):
        self._check_decoder("hevc")

    def test_decoder_vp9(self):
        self._check_decoder("vp9")

    def test_decoder_av1(self):
        self._check_decoder("av1")

    def test_decoder_aac(self):
        self._check_decoder("aac")

    def test_decoder_mp3(self):
        self._check_decoder("mp3")

    def test_decoder_opus(self):
        self._check_decoder("opus")


# ─── 7. Functional test — generate a real video ────────────────────────────

class TestFunctional:

    TEST_OUTPUT = "/tmp/ffmpeg_test_output.mp4"

    def _cleanup(self):
        if os.path.exists(self.TEST_OUTPUT):
            os.remove(self.TEST_OUTPUT)

    def test_generate_test_video(self):
        """
        The binary must be able to generate a synthetic test video using
        libx264 for video and aac for audio, producing a valid MP4 file.
        This is the exact command from the instruction.
        """
        self._cleanup()
        cmd = (
            f"{FFMPEG_BIN} -y "
            f"-f lavfi -i testsrc=duration=1:size=320x240:rate=10 "
            f"-f lavfi -i sine=frequency=440:duration=1 "
            f"-c:v libx264 -c:a aac -shortest "
            f"{self.TEST_OUTPUT}"
        )
        result = run(cmd, timeout=60)
        assert result.returncode == 0, (
            f"ffmpeg test encode failed (exit {result.returncode}). "
            f"stderr: {result.stderr[:500]}"
        )
        assert os.path.exists(self.TEST_OUTPUT), (
            f"Output file {self.TEST_OUTPUT} was not created"
        )
        size = os.path.getsize(self.TEST_OUTPUT)
        assert size > 0, f"Output file {self.TEST_OUTPUT} is empty"
        # A 1-second 320x240 h264+aac MP4 should be at least a few KB
        assert size > 1000, (
            f"Output file is suspiciously small ({size} bytes) — "
            f"likely not a valid video"
        )
        self._cleanup()

    def test_generate_video_with_libfdk_aac(self):
        """
        Verify fdk-aac actually works by encoding audio with it.
        This catches cases where the library is listed but broken.
        """
        out = "/tmp/ffmpeg_test_fdk.mp4"
        if os.path.exists(out):
            os.remove(out)
        cmd = (
            f"{FFMPEG_BIN} -y "
            f"-f lavfi -i sine=frequency=440:duration=1 "
            f"-c:a libfdk_aac "
            f"{out}"
        )
        result = run(cmd, timeout=30)
        assert result.returncode == 0, (
            f"fdk-aac encoding failed (exit {result.returncode}). "
            f"stderr: {result.stderr[:500]}"
        )
        assert os.path.exists(out) and os.path.getsize(out) > 0, (
            "fdk-aac encoding produced no output"
        )
        if os.path.exists(out):
            os.remove(out)

    def test_generate_video_with_libmp3lame(self):
        """
        Verify libmp3lame actually works by encoding audio with it.
        """
        out = "/tmp/ffmpeg_test_mp3.mp3"
        if os.path.exists(out):
            os.remove(out)
        cmd = (
            f"{FFMPEG_BIN} -y "
            f"-f lavfi -i sine=frequency=440:duration=1 "
            f"-c:a libmp3lame "
            f"{out}"
        )
        result = run(cmd, timeout=30)
        assert result.returncode == 0, (
            f"libmp3lame encoding failed (exit {result.returncode}). "
            f"stderr: {result.stderr[:500]}"
        )
        assert os.path.exists(out) and os.path.getsize(out) > 0, (
            "libmp3lame encoding produced no output"
        )
        if os.path.exists(out):
            os.remove(out)


# ─── 8. Library enable flags in build configuration ────────────────────────

class TestLibraryFlags:
    """
    Verify that ffmpeg -version / -buildconf output contains the
    --enable-lib* flags for all required libraries.
    """

    def _get_config_output(self):
        """Get combined version + buildconf output."""
        r1 = run(f"{FFMPEG_BIN} -version")
        r2 = run(f"{FFMPEG_BIN} -buildconf")
        return (r1.stdout + " " + r2.stdout).lower()

    def test_enable_libx264(self):
        assert "--enable-libx264" in self._get_config_output()

    def test_enable_libx265(self):
        assert "--enable-libx265" in self._get_config_output()

    def test_enable_libvpx(self):
        assert "--enable-libvpx" in self._get_config_output()

    def test_enable_libaom(self):
        assert "--enable-libaom" in self._get_config_output()

    def test_enable_libfdk_aac(self):
        assert "--enable-libfdk-aac" in self._get_config_output()

    def test_enable_libmp3lame(self):
        assert "--enable-libmp3lame" in self._get_config_output()

    def test_enable_libopus(self):
        assert "--enable-libopus" in self._get_config_output()
