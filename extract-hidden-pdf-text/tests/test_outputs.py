"""
Tests for the hidden PDF text extraction task.

Validates:
1. Required files exist (output.json, suspect.pdf, extract.py)
2. output.json is valid JSON with correct schema
3. The known hidden message is found with correct SHA-256
4. SHA-256 hashes are self-consistent (text -> hash)
5. Visible text is NOT reported as hidden
6. suspect.pdf is a valid PDF file
"""

import os
import json
import hashlib

# ── Constants ──────────────────────────────────────────────────────────────

OUTPUT_PATH = "/app/output.json"
PDF_PATH = "/app/suspect.pdf"
EXTRACT_SCRIPT_PATH = "/app/extract.py"

HIDDEN_MESSAGE = "The meeting is at 19:30 behind the old mill."
HIDDEN_MESSAGE_SHA256 = "e3b4beed726fccc08c9efab966df2430914054c13e025ab37b25dfc007b0f32c"

VISIBLE_TEXT = "This is a normal public report with nothing unusual."


# ── Helpers ────────────────────────────────────────────────────────────────

def load_output():
    """Load and return the parsed output.json, or None on failure."""
    if not os.path.exists(OUTPUT_PATH):
        return None
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        return None
    return json.loads(content)


def compute_sha256(text: str) -> str:
    """Compute SHA-256 hex digest of UTF-8 encoded text (no trailing newline)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── Test: File existence ──────────────────────────────────────────────────

def test_output_json_exists():
    """output.json must exist and be non-empty."""
    assert os.path.exists(OUTPUT_PATH), f"{OUTPUT_PATH} does not exist"
    size = os.path.getsize(OUTPUT_PATH)
    assert size > 10, f"{OUTPUT_PATH} is too small ({size} bytes), likely empty or trivial"


def test_suspect_pdf_exists():
    """suspect.pdf must exist and look like a real PDF."""
    assert os.path.exists(PDF_PATH), f"{PDF_PATH} does not exist"
    with open(PDF_PATH, "rb") as f:
        header = f.read(8)
    assert header.startswith(b"%PDF"), (
        f"{PDF_PATH} does not start with %PDF header — not a valid PDF"
    )


def test_extract_script_exists():
    """extract.py must exist and be non-trivial."""
    assert os.path.exists(EXTRACT_SCRIPT_PATH), f"{EXTRACT_SCRIPT_PATH} does not exist"
    size = os.path.getsize(EXTRACT_SCRIPT_PATH)
    assert size > 50, (
        f"{EXTRACT_SCRIPT_PATH} is too small ({size} bytes), likely a stub"
    )


# ── Test: JSON schema ────────────────────────────────────────────────────

def test_output_is_valid_json():
    """output.json must be parseable JSON."""
    data = load_output()
    assert data is not None, f"{OUTPUT_PATH} is missing or empty"
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_output_has_hidden_texts_key():
    """output.json must contain a 'hidden_texts' key."""
    data = load_output()
    assert data is not None, f"{OUTPUT_PATH} is missing or empty"
    assert "hidden_texts" in data, "output.json missing 'hidden_texts' key"


def test_hidden_texts_is_nonempty_list():
    """hidden_texts must be a non-empty list."""
    data = load_output()
    assert data is not None
    ht = data.get("hidden_texts")
    assert isinstance(ht, list), "'hidden_texts' must be a JSON array"
    assert len(ht) > 0, "'hidden_texts' array is empty — no hidden text found"


def test_hidden_texts_entries_have_required_fields():
    """Each entry in hidden_texts must have 'text' and 'sha256' string fields."""
    data = load_output()
    assert data is not None
    for i, entry in enumerate(data["hidden_texts"]):
        assert isinstance(entry, dict), f"Entry {i} is not a JSON object"
        assert "text" in entry, f"Entry {i} missing 'text' field"
        assert "sha256" in entry, f"Entry {i} missing 'sha256' field"
        assert isinstance(entry["text"], str), f"Entry {i} 'text' is not a string"
        assert isinstance(entry["sha256"], str), f"Entry {i} 'sha256' is not a string"
        assert len(entry["text"].strip()) > 0, f"Entry {i} 'text' is blank"
        assert len(entry["sha256"]) == 64, (
            f"Entry {i} 'sha256' length is {len(entry['sha256'])}, expected 64 hex chars"
        )


# ── Test: Core content correctness ──────────────────────────────────────

def test_hidden_message_found():
    """The known hidden message must appear (possibly trimmed) in hidden_texts."""
    data = load_output()
    assert data is not None
    texts = [entry["text"].strip() for entry in data["hidden_texts"]]
    assert HIDDEN_MESSAGE in texts, (
        f"Expected hidden message not found.\n"
        f"  Expected: {HIDDEN_MESSAGE!r}\n"
        f"  Found:    {texts!r}"
    )


def test_hidden_message_sha256_correct():
    """The SHA-256 for the known hidden message must match the expected digest."""
    data = load_output()
    assert data is not None
    for entry in data["hidden_texts"]:
        if entry["text"].strip() == HIDDEN_MESSAGE:
            assert entry["sha256"].lower() == HIDDEN_MESSAGE_SHA256, (
                f"SHA-256 mismatch for hidden message.\n"
                f"  Expected: {HIDDEN_MESSAGE_SHA256}\n"
                f"  Got:      {entry['sha256']}"
            )
            return
    # If we reach here, the message wasn't found at all
    assert False, "Hidden message not found in hidden_texts (cannot verify hash)"


def test_all_sha256_hashes_self_consistent():
    """Every entry's sha256 must match sha256(text.encode('utf-8'))."""
    data = load_output()
    assert data is not None
    for i, entry in enumerate(data["hidden_texts"]):
        text = entry["text"].strip()
        expected_hash = compute_sha256(text)
        actual_hash = entry["sha256"].lower().strip()
        assert actual_hash == expected_hash, (
            f"Entry {i} hash mismatch.\n"
            f"  Text:     {text!r}\n"
            f"  Expected: {expected_hash}\n"
            f"  Got:      {actual_hash}"
        )


# ── Test: No visible text leakage ───────────────────────────────────────

def test_visible_text_not_in_hidden():
    """The known visible text must NOT appear in hidden_texts."""
    data = load_output()
    assert data is not None
    texts = [entry["text"].strip() for entry in data["hidden_texts"]]
    assert VISIBLE_TEXT not in texts, (
        f"Visible text was incorrectly reported as hidden: {VISIBLE_TEXT!r}"
    )


# ── Test: PDF contains hidden text that is genuinely embedded ────────────

def test_pdf_contains_hidden_message_bytes():
    """The hidden message bytes must be present somewhere in the PDF file,
    proving it was genuinely embedded (not just fabricated in output.json)."""
    assert os.path.exists(PDF_PATH), f"{PDF_PATH} does not exist"
    with open(PDF_PATH, "rb") as f:
        pdf_bytes = f.read()
    # The hidden message should be in the PDF in some form.
    # It could be in a compressed stream or in plaintext.
    # Check for plaintext first; if not found, try decompressing streams.
    msg_bytes = HIDDEN_MESSAGE.encode("latin-1")
    if msg_bytes in pdf_bytes:
        return  # Found in plaintext

    # Try decompressing FlateDecode streams
    import re
    import zlib
    stream_starts = [m.end() for m in re.finditer(rb'stream\r?\n', pdf_bytes)]
    stream_ends = [m.start() for m in re.finditer(rb'\r?\nendstream', pdf_bytes)]
    for s, e in zip(stream_starts, stream_ends):
        raw = pdf_bytes[s:e]
        try:
            decompressed = zlib.decompress(raw)
            if msg_bytes in decompressed:
                return  # Found in compressed stream
        except Exception:
            continue

    # Also check after %%EOF
    eof_pos = pdf_bytes.rfind(b"%%EOF")
    if eof_pos != -1:
        after_eof = pdf_bytes[eof_pos + 5:]
        if msg_bytes in after_eof:
            return

    assert False, (
        "Hidden message not found anywhere in suspect.pdf "
        "(neither in plaintext, compressed streams, nor after %%EOF)"
    )


# ── Test: Robustness — output.json is not just a hardcoded stub ─────────

def test_sha256_not_trivially_wrong():
    """Guard against agents that output a plausible-looking but wrong hash
    (e.g., sha256 of text+newline instead of text alone)."""
    data = load_output()
    assert data is not None
    for entry in data["hidden_texts"]:
        if entry["text"].strip() == HIDDEN_MESSAGE:
            # Verify it's NOT the hash of text+newline (common mistake)
            wrong_hash = hashlib.sha256(
                (HIDDEN_MESSAGE + "\n").encode("utf-8")
            ).hexdigest()
            actual = entry["sha256"].lower().strip()
            # The actual hash should match the correct one, not the wrong one
            assert actual != wrong_hash or actual == HIDDEN_MESSAGE_SHA256, (
                "SHA-256 appears to be computed with a trailing newline"
            )
            return
