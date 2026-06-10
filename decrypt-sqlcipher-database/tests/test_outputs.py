import os
import json
import hashlib

def test_result_file_exists():
    """Test that result.json file exists"""
    assert os.path.exists('/app/result.json'), "result.json file not found at /app/result.json"

def test_result_file_not_empty():
    """Test that result.json is not empty"""
    assert os.path.getsize('/app/result.json') > 0, "result.json file is empty"

def test_result_valid_json():
    """Test that result.json contains valid JSON"""
    with open('/app/result.json', 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            assert False, f"result.json is not valid JSON: {e}"

def test_result_has_required_fields():
    """Test that result.json has passphrase and client_records fields"""
    with open('/app/result.json', 'r') as f:
        data = json.load(f)

    assert 'passphrase' in data, "Missing 'passphrase' field in result.json"
    assert 'client_records' in data, "Missing 'client_records' field in result.json"

def test_passphrase_is_string():
    """Test that passphrase is a non-empty string"""
    with open('/app/result.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['passphrase'], str), "passphrase must be a string"
    assert len(data['passphrase']) > 0, "passphrase cannot be empty"

def test_passphrase_in_wordlist():
    """Test that the passphrase exists in the wordlist"""
    with open('/app/result.json', 'r') as f:
        data = json.load(f)

    with open('/app/wordlist.txt', 'r') as f:
        wordlist = [line.strip() for line in f if line.strip()]

    assert data['passphrase'] in wordlist, f"Passphrase '{data['passphrase']}' not found in wordlist.txt"

def test_passphrase_matches_kdf():
    """Test that passphrase derives the correct key from memory dump"""
    with open('/app/result.json', 'r') as f:
        data = json.load(f)

    passphrase = data['passphrase']

    # Extract salt and key from memory dump
    with open('/app/mem.dump', 'rb') as f:
        mem_data = f.read()

    salt_marker = b'SALT_MARKER:'
    salt_idx = mem_data.find(salt_marker)
    assert salt_idx != -1, "SALT_MARKER not found in mem.dump"

    salt_start = salt_idx + len(salt_marker)
    salt = mem_data[salt_start:salt_start + 16]

    key_marker = b'KEY_MATERIAL:'
    key_idx = mem_data.find(key_marker)
    assert key_idx != -1, "KEY_MATERIAL not found in mem.dump"

    key_start = key_idx + len(key_marker)
    expected_key = mem_data[key_start:key_start + 32]

    # Derive key from passphrase using PBKDF2 parameters from db_encrypt.py
    derived_key = hashlib.pbkdf2_hmac(
        'sha256',
        passphrase.encode('utf-8'),
        salt,
        64000,  # PBKDF2_ITERATIONS from db_encrypt.py
        dklen=32
    )

    assert derived_key == expected_key, f"Passphrase '{passphrase}' does not derive the correct key"

def test_client_records_is_list():
    """Test that client_records is a list"""
    with open('/app/result.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['client_records'], list), "client_records must be a list"

def test_client_records_not_empty():
    """Test that client_records contains at least one record"""
    with open('/app/result.json', 'r') as f:
        data = json.load(f)

    assert len(data['client_records']) > 0, "client_records cannot be empty"

def test_client_records_are_dicts():
    """Test that each client record is a dictionary"""
    with open('/app/result.json', 'r') as f:
        data = json.load(f)

    for i, record in enumerate(data['client_records']):
        assert isinstance(record, dict), f"Record {i} is not a dictionary"
        assert len(record) > 0, f"Record {i} is empty"

def test_client_records_have_consistent_fields():
    """Test that all client records have the same fields"""
    with open('/app/result.json', 'r') as f:
        data = json.load(f)

    if len(data['client_records']) == 0:
        return

    # Get field names from first record
    first_record_fields = set(data['client_records'][0].keys())

    # Check all records have the same fields
    for i, record in enumerate(data['client_records']):
        record_fields = set(record.keys())
        assert record_fields == first_record_fields, \
            f"Record {i} has different fields: {record_fields} vs {first_record_fields}"

def test_client_records_not_dummy_data():
    """Test that client records are not obviously fake/hardcoded data"""
    with open('/app/result.json', 'r') as f:
        data = json.load(f)

    # Check that records aren't all identical (lazy hardcoding)
    if len(data['client_records']) > 1:
        first_record = json.dumps(data['client_records'][0], sort_keys=True)
        all_identical = all(
            json.dumps(record, sort_keys=True) == first_record
            for record in data['client_records']
        )
        assert not all_identical, "All client records are identical - likely hardcoded dummy data"

    # Check that records don't contain obvious placeholder values
    for i, record in enumerate(data['client_records']):
        record_str = json.dumps(record).lower()
        forbidden_patterns = ['dummy', 'placeholder', 'test123', 'fake', 'example']
        for pattern in forbidden_patterns:
            assert pattern not in record_str, \
                f"Record {i} contains suspicious placeholder value: {pattern}"

def test_passphrase_not_hardcoded():
    """Test that passphrase is not a common hardcoded guess"""
    with open('/app/result.json', 'r') as f:
        data = json.load(f)

    passphrase = data['passphrase']

    # The passphrase should not be these common lazy attempts
    lazy_attempts = ['password', 'admin', '123456', 'test', '', 'null', 'none']
    assert passphrase.lower() not in lazy_attempts, \
        f"Passphrase '{passphrase}' appears to be a lazy hardcoded guess"

def test_database_actually_decrypted():
    """Test that the database was actually decrypted, not just guessed"""
    with open('/app/result.json', 'r') as f:
        data = json.load(f)

    # The correct passphrase must:
    # 1. Be in the wordlist (already tested)
    # 2. Derive the correct PBKDF2 key (already tested)
    # 3. Produce non-trivial client records

    assert len(data['client_records']) >= 1, \
        "Database appears not to have been decrypted - no records found"

    # Check that records have reasonable structure (multiple fields)
    first_record = data['client_records'][0]
    assert len(first_record) >= 2, \
        "Client records have too few fields - database may not be properly decrypted"
