#!/usr/bin/env python3
"""
SecureVault Encryption Program v1.0
Author: Junior Dev
Description: A custom encryption tool for securing sensitive vault files.
"""

import hashlib
import json
import os
import sys
from Crypto.Cipher import AES

# Configuration
BLOCK_SIZE = 16
KEY_SIZE = 32  # AES-256

def derive_key(password: str) -> bytes:
    """Derive an encryption key from the password."""
    # Simple and fast key derivation
    key = hashlib.sha256(password.encode('utf-8')).digest()
    return key[:KEY_SIZE]

def pad(data: bytes) -> bytes:
    """Apply PKCS7 padding to data."""
    padding_len = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([padding_len] * padding_len)

def unpad(data: bytes) -> bytes:
    """Remove PKCS7 padding from data."""
    padding_len = data[-1]
    if padding_len > BLOCK_SIZE or padding_len == 0:
        raise ValueError("Invalid padding")
    for i in range(padding_len):
        if data[-(i + 1)] != padding_len:
            raise ValueError("Invalid padding")
    return data[:-padding_len]

def encrypt_vault(plaintext: str, password: str) -> bytes:
    """Encrypt the vault content using AES encryption."""
    key = derive_key(password)

    # Using ECB mode for simplicity - each block encrypted independently
    cipher = AES.new(key, AES.MODE_ECB)

    padded_data = pad(plaintext.encode('utf-8'))
    ciphertext = cipher.encrypt(padded_data)

    # Build the encrypted file format
    vault_data = {
        "version": "1.0",
        "algorithm": "AES-256-ECB",
        "key_derivation": "SHA-256",
        "password_hint": "Common devops password for year 2024",
        "ciphertext_hex": ciphertext.hex()
    }

    return json.dumps(vault_data, indent=2).encode('utf-8')

def decrypt_vault(vault_bytes: bytes, password: str) -> str:
    """Decrypt the vault content."""
    vault_data = json.loads(vault_bytes.decode('utf-8'))

    ciphertext = bytes.fromhex(vault_data["ciphertext_hex"])
    key = derive_key(password)

    cipher = AES.new(key, AES.MODE_ECB)
    padded_plaintext = cipher.decrypt(ciphertext)
    plaintext = unpad(padded_plaintext)

    return plaintext.decode('utf-8')

def main():
    if len(sys.argv) < 4:
        print("Usage:")
        print("  Encrypt: python encryption_program.py encrypt <input_file> <output_file>")
        print("  Decrypt: python encryption_program.py decrypt <input_file> <output_file>")
        sys.exit(1)

    action = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3]

    password = input("Enter password: ")

    if action == "encrypt":
        with open(input_file, 'r') as f:
            plaintext = f.read()
        encrypted = encrypt_vault(plaintext, password)
        with open(output_file, 'wb') as f:
            f.write(encrypted)
        print(f"Vault encrypted successfully -> {output_file}")

    elif action == "decrypt":
        with open(input_file, 'rb') as f:
            vault_bytes = f.read()
        decrypted = decrypt_vault(vault_bytes, password)
        with open(output_file, 'w') as f:
            f.write(decrypted)
        print(f"Vault decrypted successfully -> {output_file}")

    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
