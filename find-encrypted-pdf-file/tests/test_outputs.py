"""
Tests for the Find Encrypted PDF task.

Validates that /app/output.txt contains the correct absolute path
to the encrypted PDF file on the filesystem.
"""

import os
import subprocess


OUTPUT_FILE = "/app/output.txt"
EXPECTED_ENCRYPTED_PATH = "/usr/local/share/.backup/2023/archives/confidential.pdf"

# Known decoy (non-encrypted) PDF paths in the environment
DECOY_PATHS = [
    "/home/readme.pdf",
    "/var/log/report.pdf",
    "/tmp/notes.pdf",
]


def _read_output():
    """Helper to read and return the content of output.txt."""
    assert os.path.exists(OUTPUT_FILE), (
        f"Output file {OUTPUT_FILE} does not exist. "
        "The task requires writing the encrypted PDF path to this file."
    )
    with open(OUTPUT_FILE, "r") as f:
        content = f.read()
    return content


class TestOutputFileExists:
    """Verify the output file exists and is non-empty."""

    def test_output_file_exists(self):
        assert os.path.exists(OUTPUT_FILE), (
            f"{OUTPUT_FILE} does not exist."
        )

    def test_output_file_not_empty(self):
        content = _read_output()
        stripped = content.strip()
        assert len(stripped) > 0, (
            f"{OUTPUT_FILE} is empty. It must contain the path to the encrypted PDF."
        )


class TestOutputFormat:
    """Verify the output format matches requirements."""

    def test_single_line(self):
        content = _read_output()
        lines = content.strip().splitlines()
        assert len(lines) == 1, (
            f"Expected exactly 1 line in output, got {len(lines)}. "
            f"Content: {repr(content)}"
        )

    def test_absolute_path(self):
        content = _read_output()
        path = content.strip()
        assert path.startswith("/"), (
            f"Path must be absolute (start with /). Got: {repr(path)}"
        )

    def test_ends_with_pdf_extension(self):
        content = _read_output()
        path = content.strip()
        assert path.lower().endswith(".pdf"), (
            f"Path must end with .pdf extension. Got: {repr(path)}"
        )

    def test_no_trailing_whitespace_on_line(self):
        content = _read_output()
        # Allow a trailing newline on the file, but the path line itself
        # should not have trailing spaces/tabs.
        lines = content.splitlines()
        if lines:
            path_line = lines[0]
            assert path_line == path_line.rstrip(), (
                f"Path line has trailing whitespace: {repr(path_line)}"
            )


class TestCorrectPath:
    """Verify the output points to the actual encrypted PDF."""

    def test_path_matches_expected(self):
        content = _read_output()
        path = content.strip()
        assert path == EXPECTED_ENCRYPTED_PATH, (
            f"Expected path: {EXPECTED_ENCRYPTED_PATH}\n"
            f"Got: {repr(path)}"
        )

    def test_referenced_file_exists(self):
        content = _read_output()
        path = content.strip()
        assert os.path.isfile(path), (
            f"The file at the reported path does not exist: {path}"
        )

    def test_not_a_decoy(self):
        content = _read_output()
        path = content.strip()
        for decoy in DECOY_PATHS:
            assert path != decoy, (
                f"Output points to a decoy (non-encrypted) PDF: {decoy}. "
                "The task requires finding the *encrypted* PDF."
            )


class TestEncryptionVerification:
    """Verify the file at the reported path is actually encrypted."""

    def test_file_is_encrypted_via_qpdf(self):
        """Use qpdf --is-encrypted to confirm the reported file is encrypted."""
        content = _read_output()
        path = content.strip()

        if not os.path.isfile(path):
            # If file doesn't exist, skip this test (covered by other test)
            assert False, f"File does not exist: {path}"

        result = subprocess.run(
            ["qpdf", "--is-encrypted", path],
            capture_output=True,
            text=True,
        )
        # qpdf --is-encrypted returns 0 if encrypted, 2 if not
        assert result.returncode == 0, (
            f"The file at {path} is NOT encrypted (qpdf exit code: {result.returncode}). "
            "The task requires finding an encrypted PDF."
        )

    def test_decoys_are_not_encrypted(self):
        """Sanity check: confirm the decoy PDFs are NOT encrypted,
        ensuring the environment is set up correctly."""
        for decoy in DECOY_PATHS:
            if os.path.isfile(decoy):
                result = subprocess.run(
                    ["qpdf", "--is-encrypted", decoy],
                    capture_output=True,
                    text=True,
                )
                assert result.returncode != 0, (
                    f"Decoy PDF {decoy} appears to be encrypted "
                    f"(exit code {result.returncode}). Environment may be misconfigured."
                )

    def test_file_is_valid_pdf(self):
        """Verify the reported file is actually a PDF (has PDF magic bytes)."""
        content = _read_output()
        path = content.strip()

        if not os.path.isfile(path):
            assert False, f"File does not exist: {path}"

        with open(path, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-", (
            f"File at {path} does not have a valid PDF header. "
            f"Got: {repr(header)}"
        )
