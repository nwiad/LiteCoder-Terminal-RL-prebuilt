"""
Tests for the Encrypted Time-Capsule System.
Validates all output artifacts produced by create_capsule.py and decrypt_capsule.py.
"""
import os
import json
import struct
import hashlib
import hmac as hmac_mod
import zipfile
import subprocess
import re

APP_DIR = "/app"

def fpath(name):
    return os.path.join(APP_DIR, name)

# ---------------------------------------------------------------------------
# Helper: check file exists and is non-empty
# ---------------------------------------------------------------------------
def assert_file_exists_nonempty(name):
    p = fpath(name)
    assert os.path.isfile(p), f"{name} does not exist at {p}"
    assert os.path.getsize(p) > 0, f"{name} is empty"

# ===========================================================================
# 1. All required files exist
# ===========================================================================
REQUIRED_FILES = [
    "transparency_report_Q3_2024.pdf",
    "private_key.pem",
    "public_key.pem",
    "seal_hash.txt",
    "time_capsule_Q3_2024.enc",
    "manifest.json",
    "capsule_signature.asc",
    "Q3_2024_time_capsule.zip",
    "zip_checksum.txt",
    "create_capsule.py",
    "decrypt_capsule.py",
    "README.md",
]

def test_all_required_files_exist():
    for name in REQUIRED_FILES:
        assert_file_exists_nonempty(name)

# ===========================================================================
# 2. PDF validity
# ===========================================================================
def test_pdf_is_valid():
    p = fpath("transparency_report_Q3_2024.pdf")
    with open(p, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-", "transparency_report_Q3_2024.pdf does not start with %PDF-"

# ===========================================================================
# 3. RSA Key Pair validation
# ===========================================================================
def test_public_key_pem_format():
    p = fpath("public_key.pem")
    with open(p, "r") as f:
        content = f.read()
    assert "-----BEGIN PUBLIC KEY-----" in content, "public_key.pem missing PEM header"
    assert "-----END PUBLIC KEY-----" in content, "public_key.pem missing PEM footer"

def test_private_key_pem_encrypted():
    p = fpath("private_key.pem")
    with open(p, "r") as f:
        content = f.read()
    # Encrypted private key should have ENCRYPTED in header or DEK-Info
    has_encrypted_header = "ENCRYPTED" in content or "DEK-Info" in content
    assert has_encrypted_header, "private_key.pem does not appear to be encrypted"

def test_rsa_key_is_4096_bit():
    """Verify the RSA key is 4096-bit by loading it."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    p = fpath("private_key.pem")
    with open(p, "rb") as f:
        data = f.read()
    private_key = serialization.load_pem_private_key(
        data, password=b"TimeCapsule2024!", backend=default_backend()
    )
    assert private_key.key_size == 4096, f"RSA key size is {private_key.key_size}, expected 4096"

# ===========================================================================
# 4. Seal hash validation
# ===========================================================================
def test_seal_hash_format():
    with open(fpath("seal_hash.txt"), "r") as f:
        content = f.read()
    h = content.strip()
    assert len(h) == 64, f"seal_hash.txt should be 64 hex chars, got {len(h)}"
    assert re.fullmatch(r"[0-9a-f]{64}", h), "seal_hash.txt is not lowercase hex"

def test_seal_hash_matches_public_key():
    with open(fpath("public_key.pem"), "rb") as f:
        pub_bytes = f.read()
    expected = hashlib.sha256(pub_bytes).hexdigest()
    with open(fpath("seal_hash.txt"), "r") as f:
        actual = f.read().strip()
    assert actual == expected, "seal_hash.txt does not match SHA-256 of public_key.pem"

# ===========================================================================
# 5. Encrypted capsule binary format
# ===========================================================================
def test_enc_file_binary_structure():
    with open(fpath("time_capsule_Q3_2024.enc"), "rb") as f:
        data = f.read()
    assert len(data) > 8, ".enc file too small to contain valid structure"
    offset = 0
    # IV length (4 bytes big-endian)
    iv_len = struct.unpack(">I", data[offset:offset+4])[0]
    offset += 4
    assert 1 <= iv_len <= 64, f"IV length {iv_len} out of expected range"
    offset += iv_len
    # Encrypted AES key length
    assert offset + 4 <= len(data), "Not enough data for encrypted key length"
    enc_key_len = struct.unpack(">I", data[offset:offset+4])[0]
    offset += 4
    # RSA 4096-bit -> encrypted key should be 512 bytes
    assert 256 <= enc_key_len <= 1024, f"Encrypted key length {enc_key_len} unexpected"
    offset += enc_key_len
    # Remaining is ciphertext, must be non-empty and multiple of 16 (AES-CBC)
    ciphertext = data[offset:]
    assert len(ciphertext) > 0, "No ciphertext found in .enc file"
    assert len(ciphertext) % 16 == 0, "Ciphertext length not multiple of 16 (AES block)"

# ===========================================================================
# 6. Manifest JSON validation
# ===========================================================================
def test_manifest_json_schema():
    with open(fpath("manifest.json"), "r") as f:
        manifest = json.load(f)
    assert "files" in manifest, "manifest.json missing 'files' key"
    assert "hmac" in manifest, "manifest.json missing 'hmac' key"
    assert isinstance(manifest["files"], list), "'files' should be a list"
    assert len(manifest["files"]) == 3, f"Expected 3 file entries, got {len(manifest['files'])}"
    expected_names = {
        "transparency_report_Q3_2024.pdf",
        "time_capsule_Q3_2024.enc",
        "public_key.pem",
    }
    actual_names = {entry["name"] for entry in manifest["files"]}
    assert actual_names == expected_names, f"Manifest file names mismatch: {actual_names}"
    for entry in manifest["files"]:
        assert "name" in entry, "File entry missing 'name'"
        assert "size" in entry, f"Entry {entry.get('name')} missing 'size'"
        assert "sha256" in entry, f"Entry {entry.get('name')} missing 'sha256'"
        assert isinstance(entry["size"], int), f"size for {entry['name']} not int"
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), \
            f"sha256 for {entry['name']} not valid hex"

def test_manifest_file_hashes_correct():
    with open(fpath("manifest.json"), "r") as f:
        manifest = json.load(f)
    for entry in manifest["files"]:
        fp = fpath(entry["name"])
        with open(fp, "rb") as f:
            data = f.read()
        actual_hash = hashlib.sha256(data).hexdigest()
        assert actual_hash == entry["sha256"], \
            f"SHA-256 mismatch for {entry['name']}: manifest={entry['sha256']}, actual={actual_hash}"
        assert len(data) == entry["size"], \
            f"Size mismatch for {entry['name']}: manifest={entry['size']}, actual={len(data)}"

def test_manifest_hmac_valid():
    """Recompute HMAC over compact files JSON and compare."""
    HMAC_KEY = b"capsule-hmac-secret-2024"
    with open(fpath("manifest.json"), "r") as f:
        manifest = json.load(f)
    files_list = manifest["files"]
    files_json = json.dumps(files_list, separators=(",", ":"))
    expected_hmac = hmac_mod.new(HMAC_KEY, files_json.encode("utf-8"), hashlib.sha256).hexdigest()
    assert manifest["hmac"] == expected_hmac, \
        f"HMAC mismatch: manifest={manifest['hmac']}, computed={expected_hmac}"

# ===========================================================================
# 7. GPG Signature validation
# ===========================================================================
def test_gpg_signature_format():
    with open(fpath("capsule_signature.asc"), "r") as f:
        content = f.read()
    assert content.strip().startswith("-----BEGIN PGP SIGNED MESSAGE-----"), \
        "capsule_signature.asc missing PGP SIGNED MESSAGE header"
    assert "-----END PGP SIGNATURE-----" in content, \
        "capsule_signature.asc missing PGP SIGNATURE footer"

def test_gpg_signature_contains_seal():
    with open(fpath("seal_hash.txt"), "r") as f:
        seal = f.read().strip()
    with open(fpath("capsule_signature.asc"), "r") as f:
        content = f.read()
    assert f"Seal: {seal}" in content, \
        "capsule_signature.asc does not contain the Seal line with correct hash"

def test_gpg_signature_contains_unlock_after():
    with open(fpath("capsule_signature.asc"), "r") as f:
        content = f.read()
    # Should contain Unlock-After with ISO 8601 UTC timestamp
    pattern = r"Unlock-After:\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
    assert re.search(pattern, content), \
        "capsule_signature.asc missing valid Unlock-After timestamp"

def test_gpg_signature_contains_manifest():
    """The signed message should embed the manifest JSON content."""
    with open(fpath("manifest.json"), "r") as f:
        manifest_content = f.read().strip()
    with open(fpath("capsule_signature.asc"), "r") as f:
        sig_content = f.read()
    # Check that the manifest's key fields appear in the signed message
    assert '"files"' in sig_content, "Signed message does not contain manifest files key"
    assert '"hmac"' in sig_content, "Signed message does not contain manifest hmac key"

# ===========================================================================
# 8. ZIP Archive validation
# ===========================================================================
ZIP_EXPECTED_MEMBERS = sorted([
    "time_capsule_Q3_2024.enc",
    "public_key.pem",
    "manifest.json",
    "capsule_signature.asc",
])

def test_zip_is_valid():
    p = fpath("Q3_2024_time_capsule.zip")
    assert zipfile.is_zipfile(p), "Q3_2024_time_capsule.zip is not a valid ZIP"

def test_zip_contains_required_files():
    p = fpath("Q3_2024_time_capsule.zip")
    with zipfile.ZipFile(p, "r") as zf:
        members = sorted(zf.namelist())
    assert members == ZIP_EXPECTED_MEMBERS, \
        f"ZIP members mismatch: expected {ZIP_EXPECTED_MEMBERS}, got {members}"

def test_zip_checksum_correct():
    with open(fpath("Q3_2024_time_capsule.zip"), "rb") as f:
        data = f.read()
    actual = hashlib.sha256(data).hexdigest()
    with open(fpath("zip_checksum.txt"), "r") as f:
        stored = f.read().strip()
    assert actual == stored, \
        f"zip_checksum.txt mismatch: file={actual}, stored={stored}"

def test_zip_checksum_format():
    with open(fpath("zip_checksum.txt"), "r") as f:
        content = f.read().strip()
    assert re.fullmatch(r"[0-9a-f]{64}", content), \
        "zip_checksum.txt is not a valid lowercase 64-char hex string"

# ===========================================================================
# 9. Decryption round-trip validation
# ===========================================================================
def test_decryption_produces_identical_pdf():
    """Run decrypt_capsule.py and verify decrypted PDF matches original."""
    decrypt_script = fpath("decrypt_capsule.py")
    assert os.path.isfile(decrypt_script), "decrypt_capsule.py not found"
    result = subprocess.run(
        ["python3", decrypt_script],
        capture_output=True, text=True, timeout=60, cwd=APP_DIR,
    )
    assert result.returncode == 0, \
        f"decrypt_capsule.py failed: stderr={result.stderr}"
    decrypted = fpath("decrypted_report.pdf")
    assert os.path.isfile(decrypted), "decrypted_report.pdf was not created"
    with open(fpath("transparency_report_Q3_2024.pdf"), "rb") as f:
        original = f.read()
    with open(decrypted, "rb") as f:
        recovered = f.read()
    assert original == recovered, \
        "Decrypted PDF is NOT byte-identical to the original"

def test_decryption_hmac_ok():
    """decrypt_capsule.py should print HMAC OK to stdout."""
    decrypt_script = fpath("decrypt_capsule.py")
    result = subprocess.run(
        ["python3", decrypt_script],
        capture_output=True, text=True, timeout=60, cwd=APP_DIR,
    )
    assert "HMAC OK" in result.stdout, \
        f"Expected 'HMAC OK' in stdout, got: {result.stdout}"

# ===========================================================================
# 10. README exists and has content
# ===========================================================================
def test_readme_exists_and_has_content():
    p = fpath("README.md")
    assert os.path.isfile(p), "README.md not found"
    with open(p, "r") as f:
        content = f.read().strip()
    assert len(content) > 50, "README.md is too short (< 50 chars)"
    word_count = len(content.split())
    assert word_count <= 400, f"README.md exceeds 300-word limit (got ~{word_count})"

# ===========================================================================
# 11. Cross-validation: ZIP contents match originals on disk
# ===========================================================================
def test_zip_contents_match_disk_files():
    """Files inside the ZIP should be byte-identical to those on disk."""
    p = fpath("Q3_2024_time_capsule.zip")
    with zipfile.ZipFile(p, "r") as zf:
        for member in ZIP_EXPECTED_MEMBERS:
            zip_data = zf.read(member)
            with open(fpath(member), "rb") as f:
                disk_data = f.read()
            assert zip_data == disk_data, \
                f"ZIP member '{member}' differs from file on disk"

# ===========================================================================
# 12. Encryption actually encrypts (not plaintext)
# ===========================================================================
def test_enc_file_is_not_plaintext_pdf():
    """The .enc file must not contain the raw PDF header."""
    with open(fpath("time_capsule_Q3_2024.enc"), "rb") as f:
        data = f.read()
    assert b"%PDF-" not in data, \
        ".enc file contains raw PDF header — encryption may not have been applied"

# ===========================================================================
# 13. Public/private key pair consistency
# ===========================================================================
def test_key_pair_matches():
    """Public key derived from private key should match public_key.pem."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    with open(fpath("private_key.pem"), "rb") as f:
        priv = serialization.load_pem_private_key(
            f.read(), password=b"TimeCapsule2024!", backend=default_backend()
        )
    derived_pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    with open(fpath("public_key.pem"), "rb") as f:
        stored_pub = f.read()
    assert derived_pub == stored_pub, \
        "Public key on disk does not match the one derived from private key"

# ===========================================================================
# 14. No extra PDF files after creation (cleanup check)
# ===========================================================================
def test_no_extra_pdf_files():
    """Only transparency_report_Q3_2024.pdf should exist before decryption."""
    pdf_files = [f for f in os.listdir(APP_DIR)
                 if f.endswith(".pdf") and f != "transparency_report_Q3_2024.pdf"
                 and f != "decrypted_report.pdf"]
    assert len(pdf_files) == 0, \
        f"Unexpected PDF files found: {pdf_files}"
