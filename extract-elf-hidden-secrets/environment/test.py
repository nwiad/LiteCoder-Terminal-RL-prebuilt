#!/usr/bin/env python3
"""Test script to validate the agent's output for the ELF secrets extraction task."""

import json
import sys
import os

OUTPUT_FILE = "/app/output.json"

EXPECTED_ENCRYPTION_METHOD = "xor"
EXPECTED_ENCRYPTION_KEY = "s3cr3tK3y!"
EXPECTED_CREDENTIALS = [
    {"username": "admin", "password": "P@ssw0rd_2024!"},
    {"username": "backup_svc", "password": "Bkup#Secure99"},
    {"username": "root", "password": "R00t$hell_Access"},
]

def test_output_file_exists():
    assert os.path.isfile(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"

def test_valid_json():
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Output must be a JSON object"
    return data

def test_required_fields(data):
    required = ["encryption_method", "encryption_key", "credentials"]
    for field in required:
        assert field in data, f"Missing required field: '{field}'"

def test_encryption_method(data):
    method = data["encryption_method"].strip().lower()
    assert method == EXPECTED_ENCRYPTION_METHOD, (
        f"Expected encryption_method '{EXPECTED_ENCRYPTION_METHOD}', got '{method}'"
    )

def test_encryption_key(data):
    key = data["encryption_key"].strip()
    assert key == EXPECTED_ENCRYPTION_KEY, (
        f"Expected encryption_key '{EXPECTED_ENCRYPTION_KEY}', got '{key}'"
    )

def test_credentials(data):
    creds = data["credentials"]
    assert isinstance(creds, list), "credentials must be a list"
    assert len(creds) == len(EXPECTED_CREDENTIALS), (
        f"Expected {len(EXPECTED_CREDENTIALS)} credentials, got {len(creds)}"
    )

    # Check each credential exists (order-independent)
    for expected in EXPECTED_CREDENTIALS:
        found = False
        for actual in creds:
            if (actual.get("username", "").strip() == expected["username"] and
                    actual.get("password", "").strip() == expected["password"]):
                found = True
                break
        assert found, (
            f"Missing credential: username='{expected['username']}', "
            f"password='{expected['password']}'"
        )

def main():
    results = []
    total = 0
    passed = 0

    # Test 1: file exists
    total += 1
    try:
        test_output_file_exists()
        results.append(("output_file_exists", True, ""))
        passed += 1
    except AssertionError as e:
        results.append(("output_file_exists", False, str(e)))
        # Cannot continue without the file
        print(json.dumps({"total": total, "passed": passed, "tests": results}, indent=2))
        sys.exit(1)

    # Test 2: valid JSON
    total += 1
    try:
        data = test_valid_json()
        results.append(("valid_json", True, ""))
        passed += 1
    except (AssertionError, json.JSONDecodeError) as e:
        results.append(("valid_json", False, str(e)))
        print(json.dumps({"total": total, "passed": passed, "tests": results}, indent=2))
        sys.exit(1)

    # Test 3: required fields
    total += 1
    try:
        test_required_fields(data)
        results.append(("required_fields", True, ""))
        passed += 1
    except AssertionError as e:
        results.append(("required_fields", False, str(e)))

    # Test 4: encryption method
    total += 1
    try:
        test_encryption_method(data)
        results.append(("encryption_method", True, ""))
        passed += 1
    except (AssertionError, KeyError) as e:
        results.append(("encryption_method", False, str(e)))

    # Test 5: encryption key
    total += 1
    try:
        test_encryption_key(data)
        results.append(("encryption_key", True, ""))
        passed += 1
    except (AssertionError, KeyError) as e:
        results.append(("encryption_key", False, str(e)))

    # Test 6: credentials
    total += 1
    try:
        test_credentials(data)
        results.append(("credentials", True, ""))
        passed += 1
    except (AssertionError, KeyError, TypeError) as e:
        results.append(("credentials", False, str(e)))

    report = {"total": total, "passed": passed, "tests": results}
    print(json.dumps(report, indent=2))

    if passed == total:
        print(f"\nAll {total} tests passed.")
        sys.exit(0)
    else:
        print(f"\n{passed}/{total} tests passed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
