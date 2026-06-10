#!/usr/bin/env python3
"""
Build-time script to generate the encrypted vault.enc file.
This script is used during Docker build and removed afterward.
"""

import hashlib
import json
from Crypto.Cipher import AES

BLOCK_SIZE = 16
KEY_SIZE = 32

def derive_key(password: str) -> bytes:
    key = hashlib.sha256(password.encode('utf-8')).digest()
    return key[:KEY_SIZE]

def pad(data: bytes) -> bytes:
    padding_len = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([padding_len] * padding_len)

def encrypt_vault(plaintext: str, password: str) -> bytes:
    key = derive_key(password)
    cipher = AES.new(key, AES.MODE_ECB)
    padded_data = pad(plaintext.encode('utf-8'))
    ciphertext = cipher.encrypt(padded_data)
    vault_data = {
        "version": "1.0",
        "algorithm": "AES-256-ECB",
        "key_derivation": "SHA-256",
        "password_hint": "Common devops password for year 2024",
        "ciphertext_hex": ciphertext.hex()
    }
    return json.dumps(vault_data, indent=2).encode('utf-8')

if __name__ == "__main__":
    flag_content = "=== VAULT CONTENTS ===\nClassified Flag: CTF{cryptographic_vulnerabilities_exploited_successfully}\n=== END OF VAULT ==="
    password = "devops2024"

    encrypted = encrypt_vault(flag_content, password)
    with open("/app/vault.enc", "wb") as f:
        f.write(encrypted)
    print("vault.enc generated successfully")
