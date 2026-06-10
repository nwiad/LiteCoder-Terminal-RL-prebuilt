#!/usr/bin/env python3
"""
Vault Encryption System
Encrypts sensitive data using a custom multi-layer encryption scheme
"""

import hashlib
import base64
import sys


def derive_key(passphrase, salt):
    """Derive encryption key from passphrase"""
    # Simple key derivation - iterate hash function
    key = passphrase.encode() + salt
    for _ in range(1000):
        key = hashlib.sha256(key).digest()
    return key


def xor_encrypt(data, key):
    """XOR encryption with key cycling"""
    result = bytearray()
    key_len = len(key)
    for i, byte in enumerate(data):
        result.append(byte ^ key[i % key_len])
    return bytes(result)


def layer1_encrypt(data, key):
    """First encryption layer - XOR with derived key"""
    return xor_encrypt(data, key)


def layer2_obfuscate(data):
    """Second layer - base64 encoding for obfuscation"""
    return base64.b64encode(data)


def layer3_scramble(data, seed):
    """Third layer - byte position scrambling"""
    data_list = list(data)
    length = len(data_list)

    # Deterministic scrambling based on seed
    for i in range(length):
        swap_idx = (i + seed) % length
        data_list[i], data_list[swap_idx] = data_list[swap_idx], data_list[i]

    return bytes(data_list)


def encrypt_vault(plaintext, passphrase):
    """Main encryption function"""
    # Fixed salt for key derivation
    salt = b"vault_salt_2024"

    # Derive encryption key
    key = derive_key(passphrase, salt)

    # Apply encryption layers
    encrypted = plaintext.encode()
    encrypted = layer1_encrypt(encrypted, key)
    encrypted = layer2_obfuscate(encrypted)

    # Scramble with fixed seed
    scramble_seed = 42
    encrypted = layer3_scramble(encrypted, scramble_seed)

    return encrypted


if __name__ == "__main__":
    # Vault contents
    secret_data = "FLAG{crypto_analysis_master_2024}"

    # Master passphrase
    master_pass = "SecureVault2024"

    # Encrypt the vault
    encrypted_vault = encrypt_vault(secret_data, master_pass)

    # Write to file
    with open("/app/vault.enc", "wb") as f:
        f.write(encrypted_vault)

    print("Vault encrypted successfully!")
