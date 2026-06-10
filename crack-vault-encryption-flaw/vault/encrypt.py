#!/usr/bin/env python3
"""
Vault Encryption Module v1.0
Custom encryption for securing vault contents.
"""

import sys

def load_key():
    """Load the encryption key."""
    # Key is embedded for portability
    return bytes([0x5a, 0x3c, 0x71, 0x0f, 0xa8])

def encrypt(plaintext: str, key: bytes) -> str:
    """
    Encrypt plaintext using our secure XOR cipher.
    The key is applied cyclically across the entire plaintext.
    Returns hex-encoded ciphertext.
    """
    plaintext_bytes = plaintext.encode("utf-8")
    ciphertext = bytes([p ^ key[i % len(key)] for i, p in enumerate(plaintext_bytes)])
    return ciphertext.hex()

def main():
    if len(sys.argv) < 2:
        print("Usage: encrypt.py <plaintext_file>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        plaintext = f.read()

    key = load_key()
    ciphertext_hex = encrypt(plaintext, key)

    with open("secret.enc", "w") as f:
        f.write(ciphertext_hex)

    print(f"Encrypted {len(plaintext)} bytes -> secret.enc")

if __name__ == "__main__":
    main()
