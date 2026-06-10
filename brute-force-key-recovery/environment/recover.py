#!/usr/bin/env python3
"""
Key-Recovery Service – internal derivation module
==================================================
Given a *service_code* (a single printable English word) and a fixed
64-byte *service_salt*, derive a 32-byte encryption key that is then
hex-encoded to produce the 64-character master key.

The derivation intentionally uses a home-grown scheme (NOT a standard
KDF) so that the key space is small enough to brute-force once the
algorithm is understood.
"""

import hashlib
import struct

SERVICE_SALT = bytes.fromhex(
    "a3f1c6d924e8b05739d2c4f8e61a7b3c"
    "5d9f0e2a4b8c1d6e3f7a0b5c9d2e8f4a"
    "1b6c3d8e5f0a2b7c4d9e1f6a3b8c5d0e"
    "2f7a4b9c6d1e3f8a5b0c7d2e4f9a1b6c"
)

def _rotate_left(val, n, width=32):
    """Rotate a 32-bit integer left by n bits."""
    n = n % width
    return ((val << n) | (val >> (width - n))) & 0xFFFFFFFF


def _custom_mix(block_a, block_b):
    """Mix two 4-byte blocks together with rotation and XOR."""
    a = struct.unpack(">I", block_a)[0]
    b = struct.unpack(">I", block_b)[0]
    mixed = _rotate_left(a ^ b, (a + b) % 17)
    mixed = (mixed + 0x9E3779B9) & 0xFFFFFFFF          # golden-ratio constant
    mixed = mixed ^ _rotate_left(b, 13)
    return struct.pack(">I", mixed)


def derive_key(service_code: str) -> str:
    """
    Derive the 64-character hex master key from *service_code*.

    Steps
    -----
    1. SHA-256 hash the service_code to get a 32-byte digest.
    2. XOR the digest with the first 32 bytes of SERVICE_SALT.
    3. Split the result into eight 4-byte blocks.
    4. For 64 rounds, mix adjacent block pairs using _custom_mix,
       feeding in successive 4-byte chunks of SERVICE_SALT (cycling).
    5. Concatenate the eight blocks and SHA-256 hash the result to
       produce the final 32-byte key.
    6. Return the hex-encoded key (64 hex characters).
    """
    # Step 1
    digest = hashlib.sha256(service_code.encode("utf-8")).digest()

    # Step 2
    state = bytes(d ^ s for d, s in zip(digest, SERVICE_SALT[:32]))

    # Step 3
    blocks = [state[i:i+4] for i in range(0, 32, 4)]

    # Step 4
    for r in range(64):
        salt_offset = (r * 4) % len(SERVICE_SALT)
        salt_chunk = SERVICE_SALT[salt_offset:salt_offset+4]
        i = r % len(blocks)
        j = (i + 1) % len(blocks)
        blocks[i] = _custom_mix(blocks[i], salt_chunk)
        blocks[j] = _custom_mix(blocks[j], blocks[i])

    # Step 5
    concatenated = b"".join(blocks)
    final = hashlib.sha256(concatenated).digest()

    # Step 6
    return final.hex()


def encrypt(plaintext: bytes, key_hex: str) -> bytes:
    """
    Simple repeating-XOR encryption using the raw bytes of the hex key.
    Returns the ciphertext bytes.
    """
    key_bytes = key_hex.encode("ascii")          # 64 ASCII bytes
    return bytes(p ^ key_bytes[i % len(key_bytes)] for i, p in enumerate(plaintext))


def decrypt(ciphertext: bytes, key_hex: str) -> bytes:
    """Decryption is identical to encryption (XOR is symmetric)."""
    return encrypt(ciphertext, key_hex)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <service_code>")
        sys.exit(1)
    code = sys.argv[1]
    key = derive_key(code)
    print(f"Derived master key: {key}")
