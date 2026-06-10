"""
Tests for LSB Steganography with AES-256-CBC encryption task.
Validates: file existence, image properties, metadata schema,
crypto correctness, LSB embedding, and round-trip integrity.
"""

import os
import json
import struct
import hashlib

# ---------------------------------------------------------------------------
# Paths – all relative to /app (the WORKDIR in the Dockerfile)
# ---------------------------------------------------------------------------
APP_DIR = "/app"
SECRET_PATH = os.path.join(APP_DIR, "secret.txt")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
COVER_PATH = os.path.join(APP_DIR, "cover.png")
STEGO_PATH = os.path.join(APP_DIR, "stego.png")
ENCODE_RESULT_PATH = os.path.join(APP_DIR, "encode_result.json")
DECODED_PATH = os.path.join(APP_DIR, "decoded.txt")
STEGO_PY_PATH = os.path.join(APP_DIR, "stego.py")


# ===================================================================
# 1. File existence tests
# ===================================================================

def test_stego_py_exists():
    """The entry-point script must exist."""
    assert os.path.isfile(STEGO_PY_PATH), f"{STEGO_PY_PATH} not found"


def test_cover_png_exists():
    assert os.path.isfile(COVER_PATH), f"{COVER_PATH} not found"


def test_stego_png_exists():
    assert os.path.isfile(STEGO_PATH), f"{STEGO_PATH} not found"


def test_encode_result_json_exists():
    assert os.path.isfile(ENCODE_RESULT_PATH), f"{ENCODE_RESULT_PATH} not found"


def test_decoded_txt_exists():
    assert os.path.isfile(DECODED_PATH), f"{DECODED_PATH} not found"


# ===================================================================
# 2. Image property tests
# ===================================================================

def _load_image(path):
    from PIL import Image
    img = Image.open(path)
    return img


def test_cover_is_valid_png():
    """cover.png must be a loadable PNG."""
    from PIL import Image
    img = Image.open(COVER_PATH)
    assert img.format == "PNG", f"cover.png format is {img.format}, expected PNG"


def test_stego_is_valid_png():
    """stego.png must be a loadable PNG."""
    from PIL import Image
    img = Image.open(STEGO_PATH)
    assert img.format == "PNG", f"stego.png format is {img.format}, expected PNG"


def test_cover_dimensions():
    """cover.png must be exactly 1024x1024."""
    img = _load_image(COVER_PATH)
    assert img.size == (1024, 1024), f"cover.png size is {img.size}, expected (1024, 1024)"


def test_stego_dimensions():
    """stego.png must be exactly 1024x1024."""
    img = _load_image(STEGO_PATH)
    assert img.size == (1024, 1024), f"stego.png size is {img.size}, expected (1024, 1024)"


def test_cover_rgb_mode():
    """cover.png must be RGB mode."""
    img = _load_image(COVER_PATH)
    rgb_img = img.convert("RGB")
    # The original should already be RGB (or convertible without loss)
    assert img.mode == "RGB", f"cover.png mode is {img.mode}, expected RGB"


def test_stego_rgb_mode():
    """stego.png must be RGB mode."""
    img = _load_image(STEGO_PATH)
    assert img.mode == "RGB", f"stego.png mode is {img.mode}, expected RGB"


def test_cover_non_uniform():
    """cover.png must contain non-uniform pixel data (not a single solid color)."""
    img = _load_image(COVER_PATH).convert("RGB")
    pixels = list(img.getdata())
    unique_pixels = set(pixels[:10000])  # sample first 10k pixels
    assert len(unique_pixels) > 1, "cover.png appears to be a single solid color"


def test_stego_and_cover_same_dimensions():
    """stego.png and cover.png must have identical dimensions."""
    cover = _load_image(COVER_PATH)
    stego = _load_image(STEGO_PATH)
    assert cover.size == stego.size, (
        f"Dimension mismatch: cover={cover.size}, stego={stego.size}"
    )


# ===================================================================
# 3. encode_result.json schema & value tests
# ===================================================================

def _load_encode_result():
    with open(ENCODE_RESULT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_encode_result_has_required_keys():
    data = _load_encode_result()
    required = {"iv", "payload_bits", "image_capacity_bits",
                "cover_size_bytes", "stego_size_bytes"}
    missing = required - set(data.keys())
    assert not missing, f"encode_result.json missing keys: {missing}"


def test_iv_is_valid_hex_32_chars():
    """IV must be a hex string representing exactly 16 bytes (32 hex chars)."""
    data = _load_encode_result()
    iv_hex = data["iv"]
    assert isinstance(iv_hex, str), "iv must be a string"
    assert len(iv_hex) == 32, f"iv hex length is {len(iv_hex)}, expected 32"
    # Must be valid hex
    try:
        bytes.fromhex(iv_hex)
    except ValueError:
        assert False, f"iv is not valid hex: {iv_hex}"


def test_image_capacity_bits():
    """image_capacity_bits must equal 1024 * 1024 * 3 = 3145728."""
    data = _load_encode_result()
    expected = 1024 * 1024 * 3
    assert data["image_capacity_bits"] == expected, (
        f"image_capacity_bits is {data['image_capacity_bits']}, expected {expected}"
    )


def test_payload_bits_positive_and_within_capacity():
    """payload_bits must be > 0 and <= image_capacity_bits."""
    data = _load_encode_result()
    pb = data["payload_bits"]
    cap = data["image_capacity_bits"]
    assert isinstance(pb, int) and pb > 0, f"payload_bits must be positive int, got {pb}"
    assert pb <= cap, f"payload_bits ({pb}) exceeds capacity ({cap})"


def test_payload_bits_is_multiple_of_8():
    """payload_bits must be a multiple of 8 (whole bytes: 4-byte length prefix + ciphertext)."""
    data = _load_encode_result()
    pb = data["payload_bits"]
    assert pb % 8 == 0, f"payload_bits ({pb}) is not a multiple of 8"


def test_cover_size_bytes_matches_file():
    """cover_size_bytes must match the actual file size of cover.png."""
    data = _load_encode_result()
    actual = os.path.getsize(COVER_PATH)
    assert data["cover_size_bytes"] == actual, (
        f"cover_size_bytes={data['cover_size_bytes']}, actual={actual}"
    )


def test_stego_size_bytes_matches_file():
    """stego_size_bytes must match the actual file size of stego.png."""
    data = _load_encode_result()
    actual = os.path.getsize(STEGO_PATH)
    assert data["stego_size_bytes"] == actual, (
        f"stego_size_bytes={data['stego_size_bytes']}, actual={actual}"
    )


# ===================================================================
# 4. Round-trip integrity – THE critical test
# ===================================================================

def test_decoded_is_byte_identical_to_secret():
    """decoded.txt must be byte-for-byte identical to secret.txt."""
    with open(SECRET_PATH, "rb") as f:
        secret = f.read()
    with open(DECODED_PATH, "rb") as f:
        decoded = f.read()
    assert secret == decoded, (
        f"decoded.txt ({len(decoded)} bytes) differs from secret.txt ({len(secret)} bytes). "
        f"SHA256 secret={hashlib.sha256(secret).hexdigest()}, "
        f"decoded={hashlib.sha256(decoded).hexdigest()}"
    )


# ===================================================================
# 5. Independent LSB extraction – catches fake stego images
# ===================================================================

def _extract_lsb_bits(image_path, num_bits):
    """Extract num_bits from the LSB of RGB channels in row-major order."""
    from PIL import Image
    img = Image.open(image_path).convert("RGB")
    pixels = list(img.getdata())
    bits = []
    idx = 0
    for pixel in pixels:
        for c in range(3):
            if idx >= num_bits:
                return bits
            bits.append(pixel[c] & 1)
            idx += 1
    return bits


def _bits_to_bytes(bits):
    """Convert a list of bits (MSB first per byte) to bytes."""
    result = bytearray()
    for i in range(0, len(bits), 8):
        chunk = bits[i:i + 8]
        if len(chunk) < 8:
            chunk.extend([0] * (8 - len(chunk)))
        val = 0
        for b in chunk:
            val = (val << 1) | b
        result.append(val)
    return bytes(result)


def test_lsb_contains_valid_length_prefix():
    """The first 32 bits embedded in stego.png must be a valid big-endian
    length prefix that, combined with the 4-byte header, equals
    payload_bits / 8 total payload bytes."""
    data = _load_encode_result()
    payload_bits = data["payload_bits"]

    # Extract just the first 32 bits (4 bytes = length prefix)
    bits = _extract_lsb_bits(STEGO_PATH, 32)
    assert len(bits) == 32, "Could not extract 32 bits from stego.png"
    length_bytes = _bits_to_bytes(bits)
    ciphertext_len = struct.unpack(">I", length_bytes)[0]

    # Total payload = 4 (length prefix) + ciphertext_len
    expected_payload_bytes = payload_bits // 8
    assert 4 + ciphertext_len == expected_payload_bytes, (
        f"Length prefix says ciphertext is {ciphertext_len} bytes, "
        f"so total payload = {4 + ciphertext_len}, but encode_result says "
        f"{expected_payload_bytes} bytes"
    )


def test_lsb_extracted_ciphertext_decrypts_to_secret():
    """Independently extract the full payload from stego.png LSBs,
    decrypt with AES-256-CBC using the recorded IV, and verify
    the plaintext matches secret.txt byte-for-byte.
    This catches agents that fake stego.png or decoded.txt."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_padding
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend

    # Load config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    passphrase = config["passphrase"]
    salt = bytes.fromhex(config["salt"])

    # Load encode result
    data = _load_encode_result()
    iv = bytes.fromhex(data["iv"])
    payload_bits_count = data["payload_bits"]

    # Extract all payload bits from stego image
    extracted_bits = _extract_lsb_bits(STEGO_PATH, payload_bits_count)
    payload_bytes = _bits_to_bytes(extracted_bits)

    # Parse length prefix
    ciphertext_length = struct.unpack(">I", payload_bytes[:4])[0]
    ciphertext = payload_bytes[4:4 + ciphertext_length]

    # Derive key with PBKDF2-HMAC-SHA256, 100000 iterations
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )
    key = kdf.derive(passphrase.encode("utf-8"))

    # Decrypt AES-256-CBC
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    # Remove PKCS7 padding
    unpadder = sym_padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()

    # Compare with original secret
    with open(SECRET_PATH, "rb") as f:
        secret = f.read()

    assert plaintext == secret, (
        f"Independent LSB extraction + AES decrypt produced {len(plaintext)} bytes "
        f"that differ from secret.txt ({len(secret)} bytes). "
        f"SHA256 extracted={hashlib.sha256(plaintext).hexdigest()}, "
        f"secret={hashlib.sha256(secret).hexdigest()}"
    )


# ===================================================================
# 6. Ciphertext sanity checks
# ===================================================================

def test_ciphertext_length_is_multiple_of_16():
    """AES-256-CBC with PKCS7 padding always produces ciphertext whose
    length is a multiple of 16 bytes (the AES block size)."""
    data = _load_encode_result()
    payload_bits = data["payload_bits"]
    payload_bytes_count = payload_bits // 8
    # ciphertext length = payload_bytes - 4 (length prefix)
    ciphertext_len = payload_bytes_count - 4
    assert ciphertext_len > 0, "Ciphertext length must be > 0"
    assert ciphertext_len % 16 == 0, (
        f"Ciphertext length {ciphertext_len} is not a multiple of 16 (AES block size)"
    )


def test_ciphertext_is_at_least_one_block():
    """Even a 1-byte plaintext with PKCS7 padding produces at least 16 bytes."""
    data = _load_encode_result()
    payload_bytes_count = data["payload_bits"] // 8
    ciphertext_len = payload_bytes_count - 4
    assert ciphertext_len >= 16, (
        f"Ciphertext length {ciphertext_len} is less than one AES block (16 bytes)"
    )


# ===================================================================
# 7. Stego image differs from cover (embedding actually happened)
# ===================================================================

def test_stego_differs_from_cover():
    """stego.png must differ from cover.png in at least some pixels,
    proving that LSB embedding actually modified the image."""
    from PIL import Image
    cover = Image.open(COVER_PATH).convert("RGB")
    stego = Image.open(STEGO_PATH).convert("RGB")
    cover_px = list(cover.getdata())
    stego_px = list(stego.getdata())

    diffs = 0
    sample_size = min(len(cover_px), 50000)  # check first 50k pixels
    for i in range(sample_size):
        if cover_px[i] != stego_px[i]:
            diffs += 1

    assert diffs > 0, (
        "stego.png is pixel-identical to cover.png — no LSB embedding detected"
    )


# ===================================================================
# 8. stego.py script structure test
# ===================================================================

def test_stego_py_contains_encode_decode():
    """stego.py must handle both 'encode' and 'decode' subcommands."""
    with open(STEGO_PY_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    assert "encode" in content.lower(), "stego.py does not reference 'encode'"
    assert "decode" in content.lower(), "stego.py does not reference 'decode'"


def test_decoded_txt_not_empty():
    """decoded.txt must not be empty."""
    size = os.path.getsize(DECODED_PATH)
    assert size > 0, "decoded.txt is empty (0 bytes)"


def test_cover_png_not_trivially_small():
    """A 1024x1024 RGB PNG should be at least a few KB."""
    size = os.path.getsize(COVER_PATH)
    assert size > 1000, f"cover.png is suspiciously small: {size} bytes"


def test_stego_png_not_trivially_small():
    """A 1024x1024 RGB PNG should be at least a few KB."""
    size = os.path.getsize(STEGO_PATH)
    assert size > 1000, f"stego.png is suspiciously small: {size} bytes"

