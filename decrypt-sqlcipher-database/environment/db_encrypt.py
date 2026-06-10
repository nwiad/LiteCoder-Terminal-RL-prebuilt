#!/usr/bin/env python3
"""
Database encryption configuration fragment
"""
import hashlib
from pysqlcipher3 import dbapi2 as sqlite

# SQLCipher configuration
PBKDF2_ITERATIONS = 64000
HASH_ALGORITHM = 'sha256'
KEY_LENGTH = 32

def open_encrypted_db(db_path, passphrase):
    """Open encrypted SQLite database with SQLCipher"""
    conn = sqlite.connect(db_path)
    conn.execute(f"PRAGMA key = '{passphrase}'")
    conn.execute(f"PRAGMA kdf_iter = {PBKDF2_ITERATIONS}")
    conn.execute(f"PRAGMA cipher_page_size = 4096")
    return conn

def derive_key(passphrase, salt):
    """Derive encryption key using PBKDF2-HMAC-SHA256"""
    return hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        passphrase.encode('utf-8'),
        salt,
        PBKDF2_ITERATIONS,
        dklen=KEY_LENGTH
    )
