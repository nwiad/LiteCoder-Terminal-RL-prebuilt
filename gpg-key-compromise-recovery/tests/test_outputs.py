"""
Tests for GPG Key Compromise & Recovery task.

Verifies all 9 steps of the key rotation process by inspecting
GPG keyring state and output files.
"""

import os
import re
import subprocess

GNUPGHOME = "/app/gpghome"
OUTPUT_DIR = "/app/output"
RELEASES_DIR = "/app/releases"
SECRETS_PLAINTEXT = "/app/secrets/secrets.txt"
OLD_FPR_FILE = "/app/old_key_fingerprint.txt"
CONTRIBUTORS = ["alice", "bob", "carol"]
CONTRIBUTOR_DIR = "/app/contributors"
VERSIONS = ["1.0", "2.0", "3.0"]

# ── Helpers ──

def gpg_cmd(args, homedir=None):
    """Run a gpg command and return (returncode, stdout, stderr)."""
    cmd = ["gpg", "--batch", "--no-tty"]
    if homedir:
        cmd += ["--homedir", homedir]
    else:
        cmd += ["--homedir", GNUPGHOME]
    cmd += args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def read_old_fingerprint():
    with open(OLD_FPR_FILE, "r") as f:
        return f.read().strip()


def parse_changelog():
    """Parse CHANGELOG.txt and return dict of key=value pairs."""
    path = os.path.join(OUTPUT_DIR, "CHANGELOG.txt")
    data = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip()
    return data


def get_primary_fingerprints_for_email(email, homedir=None):
    """Get all primary key fingerprints for a given email."""
    rc, stdout, stderr = gpg_cmd(
        ["--with-colons", "--list-keys", email], homedir=homedir
    )
    fps = []
    lines = stdout.strip().split("\n")
    for i, line in enumerate(lines):
        if line.startswith("pub:"):
            # Next fpr line is the primary key fingerprint
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("fpr:"):
                    fpr = lines[j].split(":")[9]
                    fps.append(fpr)
                    break
    return fps


def get_new_fingerprint():
    """Determine the new maintainer fingerprint (not the old one)."""
    old_fpr = read_old_fingerprint()
    all_fps = get_primary_fingerprints_for_email("maintainer@example.com")
    new_fps = [f for f in all_fps if f != old_fpr]
    assert len(new_fps) >= 1, "No new maintainer key found in keyring"
    return new_fps[0]


# ══════════════════════════════════════════════════════════════
# Test 1: All required output files exist
# ══════════════════════════════════════════════════════════════

REQUIRED_FILES = [
    "revocation.asc",
    "release-v1.0.tar.gz.sig",
    "release-v2.0.tar.gz.sig",
    "release-v3.0.tar.gz.sig",
    "secrets.txt.gpg",
    "new_maintainer_pubkey.asc",
    "CHANGELOG.txt",
    "test_message.txt",
    "test_message.txt.gpg",
    "test_message_decrypted.txt",
]


def test_output_files_exist():
    """All required output files must exist and be non-empty."""
    for fname in REQUIRED_FILES:
        path = os.path.join(OUTPUT_DIR, fname)
        assert os.path.isfile(path), f"Missing output file: {path}"
        assert os.path.getsize(path) > 0, f"Output file is empty: {path}"


# ══════════════════════════════════════════════════════════════
# Test 2: New maintainer key exists and differs from old
# ══════════════════════════════════════════════════════════════

def test_new_key_exists_and_differs():
    """A new maintainer key must exist with a different fingerprint."""
    old_fpr = read_old_fingerprint()
    new_fpr = get_new_fingerprint()
    assert len(new_fpr) == 40, f"New fingerprint not 40 hex chars: {new_fpr}"
    assert new_fpr != old_fpr, "New key fingerprint must differ from old"


# ══════════════════════════════════════════════════════════════
# Test 3: New key is RSA >= 3072 bits with required subkeys
# ══════════════════════════════════════════════════════════════

def test_new_key_algorithm_and_subkeys():
    """New key must be RSA >= 3072 with sign, encrypt, auth subkeys."""
    new_fpr = get_new_fingerprint()
    rc, stdout, stderr = gpg_cmd(["--with-colons", "--list-keys", new_fpr])
    assert rc == 0, f"Cannot list new key: {stderr}"

    lines = stdout.strip().split("\n")

    # Check primary key is RSA >= 3072
    pub_lines = [l for l in lines if l.startswith("pub:")]
    assert len(pub_lines) >= 1, "No pub record for new key"
    pub_fields = pub_lines[0].split(":")
    key_length = int(pub_fields[2])
    assert key_length >= 3072, f"Key length {key_length} < 3072"
    # RSA algo IDs: 1 (RSA)
    algo = pub_fields[3]
    assert algo in ("1",), f"Key algorithm {algo} is not RSA"

    # Check subkeys: need at least sign (s), encrypt (e), auth (a) capabilities
    sub_caps = set()
    for l in lines:
        if l.startswith("sub:"):
            fields = l.split(":")
            cap = fields[11] if len(fields) > 11 else ""
            for c in cap:
                sub_caps.add(c.lower())
    assert "s" in sub_caps, "Missing signing subkey"
    assert "e" in sub_caps, "Missing encryption subkey"
    assert "a" in sub_caps, "Missing authentication subkey"


# ══════════════════════════════════════════════════════════════
# Test 4: Old key is revoked in the main keyring
# ══════════════════════════════════════════════════════════════

def test_old_key_revoked():
    """The old maintainer key must be marked as revoked."""
    old_fpr = read_old_fingerprint()
    rc, stdout, stderr = gpg_cmd(["--with-colons", "--list-keys", old_fpr])
    assert rc == 0, f"Cannot list old key: {stderr}"

    # In colon output, a revoked key has 'r' in the validity field (field 1)
    pub_lines = [l for l in stdout.strip().split("\n") if l.startswith("pub:")]
    assert len(pub_lines) >= 1, "Old key pub record not found"
    validity = pub_lines[0].split(":")[1]
    assert "r" in validity, (
        f"Old key not revoked. Validity field = '{validity}'. "
        "Expected 'r' for revoked."
    )


# ══════════════════════════════════════════════════════════════
# Test 5: Revocation certificate is valid ASCII-armored
# ══════════════════════════════════════════════════════════════

def test_revocation_certificate_format():
    """revocation.asc must be a valid PGP public key block (revocation)."""
    path = os.path.join(OUTPUT_DIR, "revocation.asc")
    with open(path, "r") as f:
        content = f.read()
    # Revocation certs are wrapped in PGP PUBLIC KEY BLOCK armor
    assert "-----BEGIN PGP PUBLIC KEY BLOCK-----" in content, (
        "Revocation cert missing PGP armor header"
    )
    assert "-----END PGP PUBLIC KEY BLOCK-----" in content, (
        "Revocation cert missing PGP armor footer"
    )


# ══════════════════════════════════════════════════════════════
# Test 6: Release signatures verify with the new key
# ══════════════════════════════════════════════════════════════

def test_release_signatures_verify():
    """Each release tarball signature must verify against the new key."""
    new_fpr = get_new_fingerprint()
    for ver in VERSIONS:
        tarball = os.path.join(RELEASES_DIR, f"release-v{ver}.tar.gz")
        sig = os.path.join(OUTPUT_DIR, f"release-v{ver}.tar.gz.sig")
        assert os.path.isfile(sig), f"Missing signature: {sig}"

        rc, stdout, stderr = gpg_cmd(["--verify", sig, tarball])
        # gpg --verify outputs to stderr
        combined = stdout + stderr
        assert rc == 0, (
            f"Signature verification failed for v{ver}: {combined}"
        )
        # Ensure the signature was made by the NEW key, not the old one
        assert new_fpr in combined or new_fpr[-16:] in combined, (
            f"Signature for v{ver} not made by new key {new_fpr}"
        )


# ══════════════════════════════════════════════════════════════
# Test 7: Re-encrypted secrets is decryptable by all recipients
# ══════════════════════════════════════════════════════════════

def test_secrets_reencrypted_decryptable():
    """secrets.txt.gpg must be decryptable and contain the original secrets."""
    secrets_gpg = os.path.join(OUTPUT_DIR, "secrets.txt.gpg")
    assert os.path.isfile(secrets_gpg), "Missing secrets.txt.gpg"

    # Decrypt using the main keyring (has the new maintainer private key)
    rc, stdout, stderr = gpg_cmd([
        "--pinentry-mode", "loopback", "--passphrase", "",
        "--decrypt", secrets_gpg
    ])
    assert rc == 0, f"Cannot decrypt secrets.txt.gpg: {stderr}"

    # Verify the decrypted content matches original secrets
    with open(SECRETS_PLAINTEXT, "r") as f:
        original = f.read().strip()
    assert stdout.strip() == original, (
        "Decrypted secrets do not match original plaintext"
    )


def test_secrets_encrypted_to_contributors():
    """secrets.txt.gpg must list all 4 recipients in packet info."""
    secrets_gpg = os.path.join(OUTPUT_DIR, "secrets.txt.gpg")
    # Use --list-packets or --list-only to see recipients
    rc, stdout, stderr = gpg_cmd([
        "--pinentry-mode", "loopback", "--passphrase", "",
        "--list-packets", secrets_gpg
    ])
    combined = stdout + stderr
    # Count pubkey enc packets — should be at least 4
    enc_count = combined.count(":pubkey enc packet:")
    assert enc_count >= 4, (
        f"Expected at least 4 pubkey enc packets (4 recipients), got {enc_count}"
    )


# ══════════════════════════════════════════════════════════════
# Test 8: New public key export is valid
# ══════════════════════════════════════════════════════════════

def test_new_pubkey_export_valid():
    """new_maintainer_pubkey.asc must be a valid ASCII-armored public key."""
    path = os.path.join(OUTPUT_DIR, "new_maintainer_pubkey.asc")
    with open(path, "r") as f:
        content = f.read()

    assert "-----BEGIN PGP PUBLIC KEY BLOCK-----" in content, (
        "Public key missing PGP armor header"
    )
    assert "-----END PGP PUBLIC KEY BLOCK-----" in content, (
        "Public key missing PGP armor footer"
    )

    # Import into a temp keyring to verify it's actually the new key
    import tempfile
    tmpdir = tempfile.mkdtemp()
    os.chmod(tmpdir, 0o700)
    try:
        rc, stdout, stderr = gpg_cmd(["--import", path], homedir=tmpdir)
        assert rc == 0, f"Cannot import new pubkey: {stderr}"

        # Verify the imported key matches the new fingerprint
        new_fpr = get_new_fingerprint()
        rc2, stdout2, stderr2 = gpg_cmd(
            ["--with-colons", "--list-keys"], homedir=tmpdir
        )
        assert new_fpr in stdout2, (
            f"Exported pubkey fingerprint doesn't match new key {new_fpr}"
        )
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════
# Test 9: Contributor keyrings updated correctly
# ══════════════════════════════════════════════════════════════

def test_contributor_keyrings_have_new_key():
    """Each contributor keyring must have the new maintainer public key."""
    new_fpr = get_new_fingerprint()
    for user in CONTRIBUTORS:
        chome = os.path.join(CONTRIBUTOR_DIR, user)
        rc, stdout, stderr = gpg_cmd(
            ["--with-colons", "--list-keys", new_fpr], homedir=chome
        )
        assert rc == 0, (
            f"{user}'s keyring missing new maintainer key: {stderr}"
        )
        assert new_fpr in stdout, (
            f"{user}'s keyring does not contain new key {new_fpr}"
        )


def test_contributor_keyrings_old_key_revoked():
    """Each contributor keyring must show the old key as revoked."""
    old_fpr = read_old_fingerprint()
    for user in CONTRIBUTORS:
        chome = os.path.join(CONTRIBUTOR_DIR, user)
        rc, stdout, stderr = gpg_cmd(
            ["--with-colons", "--list-keys", old_fpr], homedir=chome
        )
        assert rc == 0, (
            f"{user}'s keyring cannot list old key: {stderr}"
        )
        pub_lines = [l for l in stdout.strip().split("\n")
                     if l.startswith("pub:")]
        assert len(pub_lines) >= 1, (
            f"Old key pub record not found in {user}'s keyring"
        )
        validity = pub_lines[0].split(":")[1]
        assert "r" in validity, (
            f"Old key not revoked in {user}'s keyring. "
            f"Validity = '{validity}'"
        )


def test_contributor_keyrings_new_key_trust():
    """Each contributor must have trust >= marginal (4) for the new key."""
    new_fpr = get_new_fingerprint()
    for user in CONTRIBUTORS:
        chome = os.path.join(CONTRIBUTOR_DIR, user)
        rc, stdout, stderr = gpg_cmd(
            ["--export-ownertrust"], homedir=chome
        )
        assert rc == 0, f"Cannot export ownertrust for {user}: {stderr}"
        # Look for the new key fingerprint in ownertrust output
        # Format: <fingerprint>:<trust_level>:
        found = False
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            if new_fpr in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    trust_level = int(parts[1])
                    assert trust_level >= 4, (
                        f"{user}'s trust for new key is {trust_level}, "
                        "expected >= 4 (marginal)"
                    )
                    found = True
                    break
        assert found, (
            f"New key {new_fpr} not found in {user}'s ownertrust"
        )


# ══════════════════════════════════════════════════════════════
# Test 10: CHANGELOG format and content
# ══════════════════════════════════════════════════════════════

def test_changelog_exists_and_format():
    """CHANGELOG.txt must have the three required key=value lines."""
    path = os.path.join(OUTPUT_DIR, "CHANGELOG.txt")
    assert os.path.isfile(path), "Missing CHANGELOG.txt"

    with open(path, "r") as f:
        content = f.read()

    # Must contain all three required lines
    assert "OLD_FINGERPRINT=" in content, "CHANGELOG missing OLD_FINGERPRINT="
    assert "NEW_FINGERPRINT=" in content, "CHANGELOG missing NEW_FINGERPRINT="
    assert "REVOCATION_CERT=" in content, "CHANGELOG missing REVOCATION_CERT="


def test_changelog_fingerprints_correct():
    """CHANGELOG fingerprints must match actual keyring state."""
    data = parse_changelog()
    old_fpr = read_old_fingerprint()
    new_fpr = get_new_fingerprint()

    assert "OLD_FINGERPRINT" in data, "CHANGELOG missing OLD_FINGERPRINT key"
    assert "NEW_FINGERPRINT" in data, "CHANGELOG missing NEW_FINGERPRINT key"

    assert data["OLD_FINGERPRINT"] == old_fpr, (
        f"CHANGELOG OLD_FINGERPRINT={data['OLD_FINGERPRINT']} "
        f"doesn't match actual old key {old_fpr}"
    )
    assert data["NEW_FINGERPRINT"] == new_fpr, (
        f"CHANGELOG NEW_FINGERPRINT={data['NEW_FINGERPRINT']} "
        f"doesn't match actual new key {new_fpr}"
    )

    # Both must be 40 hex characters
    assert re.match(r'^[A-Fa-f0-9]{40}$', data["OLD_FINGERPRINT"]), (
        "OLD_FINGERPRINT is not a valid 40-char hex fingerprint"
    )
    assert re.match(r'^[A-Fa-f0-9]{40}$', data["NEW_FINGERPRINT"]), (
        "NEW_FINGERPRINT is not a valid 40-char hex fingerprint"
    )


def test_changelog_revocation_path():
    """CHANGELOG REVOCATION_CERT must point to the actual revocation file."""
    data = parse_changelog()
    assert "REVOCATION_CERT" in data, "CHANGELOG missing REVOCATION_CERT key"
    assert data["REVOCATION_CERT"] == "/app/output/revocation.asc", (
        f"REVOCATION_CERT path wrong: {data['REVOCATION_CERT']}"
    )


# ══════════════════════════════════════════════════════════════
# Test 11: Round-trip encryption/decryption
# ══════════════════════════════════════════════════════════════

def test_roundtrip_test_message():
    """test_message.txt must contain ROUNDTRIP_OK."""
    path = os.path.join(OUTPUT_DIR, "test_message.txt")
    with open(path, "r") as f:
        content = f.read().strip()
    assert content == "ROUNDTRIP_OK", (
        f"test_message.txt content is '{content}', expected 'ROUNDTRIP_OK'"
    )


def test_roundtrip_decrypted_matches():
    """test_message_decrypted.txt must exactly match ROUNDTRIP_OK."""
    path = os.path.join(OUTPUT_DIR, "test_message_decrypted.txt")
    with open(path, "r") as f:
        content = f.read().strip()
    assert content == "ROUNDTRIP_OK", (
        f"Decrypted message is '{content}', expected 'ROUNDTRIP_OK'"
    )


def test_roundtrip_encrypted_file_is_gpg():
    """test_message.txt.gpg must be a valid GPG encrypted file."""
    path = os.path.join(OUTPUT_DIR, "test_message.txt.gpg")
    # Try decrypting it independently to verify it's real GPG data
    rc, stdout, stderr = gpg_cmd([
        "--pinentry-mode", "loopback", "--passphrase", "",
        "--decrypt", path
    ])
    assert rc == 0, f"Cannot decrypt test_message.txt.gpg: {stderr}"
    assert stdout.strip() == "ROUNDTRIP_OK", (
        f"Independent decryption got '{stdout.strip()}', expected 'ROUNDTRIP_OK'"
    )


# ══════════════════════════════════════════════════════════════
# Test 12: Old key signatures on releases are no longer valid
# ══════════════════════════════════════════════════════════════

def test_old_signatures_not_reused():
    """Output signatures must NOT be the same as the original old-key sigs."""
    old_fpr = read_old_fingerprint()
    for ver in VERSIONS:
        sig = os.path.join(OUTPUT_DIR, f"release-v{ver}.tar.gz.sig")
        tarball = os.path.join(RELEASES_DIR, f"release-v{ver}.tar.gz")
        rc, stdout, stderr = gpg_cmd(["--verify", sig, tarball])
        combined = stdout + stderr
        # The signature should NOT reference the old key fingerprint
        assert old_fpr not in combined, (
            f"Signature for v{ver} still references old key {old_fpr}"
        )
