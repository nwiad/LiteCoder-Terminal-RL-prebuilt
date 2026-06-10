"""
Tests for the Flask Crypto Market Dashboard.

These tests validate the running Flask app at http://localhost:8080
against the requirements in instruction.md.
The app should already be running before these tests execute.
"""

import json
import math
import os
import re
import subprocess
import time

import requests

BASE_URL = "http://localhost:8080"
INPUT_FILE = "/app/input.json"
TEST_DATA_DIR = "/app/test_data"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _load_input_json(path=INPUT_FILE):
    with open(path, "r") as f:
        return json.load(f)


def _expected_values_from_file(path=INPUT_FILE):
    """Compute the expected dashboard values from an input JSON file."""
    data = _load_input_json(path)
    entry = data[-1]
    price = float(entry["price"])
    price_24h_ago = float(entry["price_24h_ago"])
    volume_24h = float(entry["volume_24h"])
    change_pct = round(((price - price_24h_ago) / price_24h_ago) * 100, 2)
    return {
        "symbol": entry["symbol"],
        "price": price,
        "change_pct": change_pct,
        "volume_24h": volume_24h,
    }


def _extract_element_text(html, element_id):
    """Extract text content of an element with the given id from HTML."""
    # Matches <tag id="element_id">content</tag> or <tag id='element_id'>content</tag>
    pattern = rf'id=["\']?{element_id}["\']?[^>]*>([^<]+)<'
    match = re.search(pattern, html)
    if match:
        return match.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# 1. File existence
# ---------------------------------------------------------------------------

def test_app_file_exists():
    """app.py must exist at /app/app.py."""
    assert os.path.isfile("/app/app.py"), "/app/app.py does not exist"


def test_app_file_not_empty():
    """app.py must not be empty."""
    size = os.path.getsize("/app/app.py")
    assert size > 100, f"/app/app.py is suspiciously small ({size} bytes)"


# ---------------------------------------------------------------------------
# 2. Server reachability
# ---------------------------------------------------------------------------

def test_server_is_running():
    """The Flask server must be reachable on port 8080."""
    try:
        resp = requests.get(BASE_URL, timeout=5)
        assert resp.status_code == 200
    except requests.ConnectionError:
        assert False, "Cannot connect to Flask server on port 8080"


# ---------------------------------------------------------------------------
# 3. GET / — HTML dashboard
# ---------------------------------------------------------------------------

def test_index_returns_html():
    """GET / must return text/html content type."""
    resp = requests.get(BASE_URL + "/", timeout=5)
    assert resp.status_code == 200
    content_type = resp.headers.get("Content-Type", "")
    assert "text/html" in content_type, f"Expected text/html, got {content_type}"

def test_index_contains_price_element():
    """HTML must contain an element with id='price' showing the correct price."""
    expected = _expected_values_from_file()
    resp = requests.get(BASE_URL + "/", timeout=5)
    html = resp.text
    price_text = _extract_element_text(html, "price")
    assert price_text is not None, "No element with id='price' found in HTML"
    price_val = float(price_text)
    assert math.isclose(price_val, expected["price"], rel_tol=1e-6), \
        f"Price mismatch: got {price_val}, expected {expected['price']}"


def test_index_contains_change_element():
    """HTML must contain an element with id='change' showing the correct 24h change %."""
    expected = _expected_values_from_file()
    resp = requests.get(BASE_URL + "/", timeout=5)
    html = resp.text
    change_text = _extract_element_text(html, "change")
    assert change_text is not None, "No element with id='change' found in HTML"
    # Strip any trailing '%' sign the agent might include inside the element
    change_text_clean = change_text.replace("%", "").strip()
    change_val = float(change_text_clean)
    assert math.isclose(change_val, expected["change_pct"], abs_tol=0.011), \
        f"Change% mismatch: got {change_val}, expected {expected['change_pct']}"


def test_index_contains_volume_element():
    """HTML must contain an element with id='volume' showing the correct 24h volume."""
    expected = _expected_values_from_file()
    resp = requests.get(BASE_URL + "/", timeout=5)
    html = resp.text
    vol_text = _extract_element_text(html, "volume")
    assert vol_text is not None, "No element with id='volume' found in HTML"
    vol_val = float(vol_text)
    assert math.isclose(vol_val, expected["volume_24h"], rel_tol=1e-6), \
        f"Volume mismatch: got {vol_val}, expected {expected['volume_24h']}"


# ---------------------------------------------------------------------------
# 4. GET /data — JSON endpoint
# ---------------------------------------------------------------------------

def test_data_endpoint_returns_json():
    """GET /data must return application/json."""
    resp = requests.get(BASE_URL + "/data", timeout=5)
    assert resp.status_code == 200
    content_type = resp.headers.get("Content-Type", "")
    assert "application/json" in content_type, f"Expected application/json, got {content_type}"


def test_data_endpoint_has_required_keys():
    """JSON response must contain symbol, price, change_pct, volume_24h."""
    resp = requests.get(BASE_URL + "/data", timeout=5)
    data = resp.json()
    for key in ("symbol", "price", "change_pct", "volume_24h"):
        assert key in data, f"Missing key '{key}' in /data response"


def test_data_endpoint_symbol():
    """JSON symbol must match the last entry's symbol."""
    expected = _expected_values_from_file()
    resp = requests.get(BASE_URL + "/data", timeout=5)
    data = resp.json()
    assert data["symbol"] == expected["symbol"], \
        f"Symbol mismatch: got {data['symbol']}, expected {expected['symbol']}"


def test_data_endpoint_price():
    """JSON price must be a float matching the last entry's price."""
    expected = _expected_values_from_file()
    resp = requests.get(BASE_URL + "/data", timeout=5)
    data = resp.json()
    assert isinstance(data["price"], (int, float)), "price must be numeric"
    assert math.isclose(float(data["price"]), expected["price"], rel_tol=1e-6), \
        f"Price mismatch: got {data['price']}, expected {expected['price']}"

def test_data_endpoint_change_pct():
    """JSON change_pct must match the computed 24h change percentage."""
    expected = _expected_values_from_file()
    resp = requests.get(BASE_URL + "/data", timeout=5)
    data = resp.json()
    assert isinstance(data["change_pct"], (int, float)), "change_pct must be numeric"
    assert math.isclose(float(data["change_pct"]), expected["change_pct"], abs_tol=0.011), \
        f"change_pct mismatch: got {data['change_pct']}, expected {expected['change_pct']}"


def test_data_endpoint_volume():
    """JSON volume_24h must match the last entry's volume."""
    expected = _expected_values_from_file()
    resp = requests.get(BASE_URL + "/data", timeout=5)
    data = resp.json()
    assert isinstance(data["volume_24h"], (int, float)), "volume_24h must be numeric"
    assert math.isclose(float(data["volume_24h"]), expected["volume_24h"], rel_tol=1e-6), \
        f"volume_24h mismatch: got {data['volume_24h']}, expected {expected['volume_24h']}"


# ---------------------------------------------------------------------------
# 5. Verify correct computation (anti-hardcoding)
# ---------------------------------------------------------------------------

def test_change_pct_formula_correctness():
    """Verify the change_pct formula: ((price - price_24h_ago) / price_24h_ago) * 100, rounded to 2dp.

    Uses the known input.json values to independently compute and cross-check.
    """
    data = _load_input_json()
    last = data[-1]
    price = float(last["price"])
    price_24h_ago = float(last["price_24h_ago"])
    expected_change = round(((price - price_24h_ago) / price_24h_ago) * 100, 2)

    resp = requests.get(BASE_URL + "/data", timeout=5)
    result = resp.json()
    assert math.isclose(float(result["change_pct"]), expected_change, abs_tol=0.011), \
        f"change_pct formula wrong: got {result['change_pct']}, expected {expected_change}"


def test_uses_last_entry_not_first():
    """The dashboard must use the LAST entry in the array, not the first."""
    data = _load_input_json()
    if len(data) < 2:
        return  # Can't test this with single-entry data

    first_price = float(data[0]["price"])
    last_price = float(data[-1]["price"])

    # Only meaningful if first and last differ
    if math.isclose(first_price, last_price, rel_tol=1e-9):
        return

    resp = requests.get(BASE_URL + "/data", timeout=5)
    result = resp.json()
    result_price = float(result["price"])

    assert math.isclose(result_price, last_price, rel_tol=1e-6), \
        f"App seems to use first entry ({first_price}) instead of last ({last_price})"
    assert not math.isclose(result_price, first_price, rel_tol=1e-6) or \
        math.isclose(first_price, last_price, rel_tol=1e-6), \
        "App appears to use the first entry instead of the last"


# ---------------------------------------------------------------------------
# 6. Edge cases — empty array → 503
# ---------------------------------------------------------------------------

def _restart_app_with_input(json_path):
    """Helper: copy a test JSON to /app/input.json, restart the Flask app,
    and wait for it to be ready. Returns True if server came up."""
    import shutil
    import signal

    # Kill existing app
    subprocess.run(["pkill", "-f", "python.*app.py"], capture_output=True)
    time.sleep(1)

    # Swap input file
    shutil.copy2(json_path, INPUT_FILE)

    # Start app
    proc = subprocess.Popen(
        ["python3", "/app/app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for server
    for _ in range(20):
        try:
            requests.get(BASE_URL + "/", timeout=1)
            return proc
        except Exception:
            time.sleep(0.5)
    return proc

def _restore_original_input():
    """Restore the original input.json and restart the app."""
    import shutil
    # The original input.json is backed up before edge-case tests
    backup = "/app/input.json.bak"
    if os.path.isfile(backup):
        shutil.copy2(backup, INPUT_FILE)
    subprocess.run(["pkill", "-f", "python.*app.py"], capture_output=True)
    time.sleep(1)
    proc = subprocess.Popen(
        ["python3", "/app/app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        try:
            requests.get(BASE_URL + "/", timeout=1)
            return proc
        except Exception:
            time.sleep(0.5)
    return proc


def test_edge_case_empty_array():
    """Both endpoints must return 503 when input.json is an empty array."""
    import shutil
    # Backup original
    shutil.copy2(INPUT_FILE, "/app/input.json.bak")

    empty_path = os.path.join(TEST_DATA_DIR, "empty_array.json")
    proc = None
    try:
        proc = _restart_app_with_input(empty_path)
        # Test GET /
        resp_html = requests.get(BASE_URL + "/", timeout=5)
        assert resp_html.status_code == 503, \
            f"GET / with empty array should return 503, got {resp_html.status_code}"
        # Test GET /data
        resp_data = requests.get(BASE_URL + "/data", timeout=5)
        assert resp_data.status_code == 503, \
            f"GET /data with empty array should return 503, got {resp_data.status_code}"
    finally:
        if proc:
            proc.terminate()
            proc.wait()
        _restore_original_input()


def test_edge_case_missing_fields():
    """Both endpoints must return 503 when required fields are missing."""
    import shutil
    shutil.copy2(INPUT_FILE, "/app/input.json.bak")

    missing_path = os.path.join(TEST_DATA_DIR, "missing_fields.json")
    proc = None
    try:
        proc = _restart_app_with_input(missing_path)
        resp_html = requests.get(BASE_URL + "/", timeout=5)
        assert resp_html.status_code == 503, \
            f"GET / with missing fields should return 503, got {resp_html.status_code}"
        resp_data = requests.get(BASE_URL + "/data", timeout=5)
        assert resp_data.status_code == 503, \
            f"GET /data with missing fields should return 503, got {resp_data.status_code}"
    finally:
        if proc:
            proc.terminate()
            proc.wait()
        _restore_original_input()


# ---------------------------------------------------------------------------
# 7. Verify values are numeric, not strings, in JSON endpoint
# ---------------------------------------------------------------------------

def test_data_endpoint_values_are_numeric():
    """price, change_pct, volume_24h in /data must be numbers, not strings."""
    resp = requests.get(BASE_URL + "/data", timeout=5)
    data = resp.json()
    for key in ("price", "change_pct", "volume_24h"):
        val = data.get(key)
        assert isinstance(val, (int, float)), \
            f"'{key}' should be numeric, got {type(val).__name__}: {val}"


# ---------------------------------------------------------------------------
# 8. HTML and JSON consistency
# ---------------------------------------------------------------------------

def test_html_and_json_values_match():
    """The values shown in the HTML dashboard must match the JSON /data endpoint."""
    resp_html = requests.get(BASE_URL + "/", timeout=5)
    resp_json = requests.get(BASE_URL + "/data", timeout=5)
    json_data = resp_json.json()
    html = resp_html.text

    html_price = float(_extract_element_text(html, "price"))
    html_change = float(_extract_element_text(html, "change").replace("%", "").strip())
    html_volume = float(_extract_element_text(html, "volume"))

    assert math.isclose(html_price, float(json_data["price"]), rel_tol=1e-6), \
        "Price mismatch between HTML and JSON"
    assert math.isclose(html_change, float(json_data["change_pct"]), abs_tol=0.011), \
        "change_pct mismatch between HTML and JSON"
    assert math.isclose(html_volume, float(json_data["volume_24h"]), rel_tol=1e-6), \
        "volume_24h mismatch between HTML and JSON"


# ---------------------------------------------------------------------------
# 9. Port binding
# ---------------------------------------------------------------------------

def test_app_binds_to_port_8080():
    """The app must be accessible on port 8080 (not some other port)."""
    try:
        resp = requests.get("http://localhost:8080/data", timeout=5)
        assert resp.status_code == 200
    except requests.ConnectionError:
        assert False, "App is not listening on port 8080"
