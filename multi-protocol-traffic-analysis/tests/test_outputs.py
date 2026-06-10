"""
Tests for Multi-Protocol Traffic Analysis & Message Reconstruction.

Validates /app/output.json produced by the agent's solution against
the known-correct expected output derived from /app/input.json.
"""

import json
import os
import zlib

# ---------------------------------------------------------------------------
# Paths – the test runner cwd is /app, output lives there too
# ---------------------------------------------------------------------------
OUTPUT_PATH = "/app/output.json"
INPUT_PATH = "/app/input.json"
EXPECTED_OUTPUT_PATH = "/app/test_data/expected_output.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path):
    """Load and return parsed JSON from a file path."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    assert len(content) > 0, f"File is empty: {path}"
    return json.loads(content)


def compute_crc32(data_str: str) -> str:
    """Compute CRC32 of a UTF-8 string, returned as 8-char lowercase hex."""
    crc = zlib.crc32(data_str.encode("utf-8")) & 0xFFFFFFFF
    return format(crc, "08x")


# ---------------------------------------------------------------------------
# 1. File existence and valid JSON
# ---------------------------------------------------------------------------

def test_output_file_exists():
    """output.json must exist."""
    assert os.path.isfile(OUTPUT_PATH), (
        f"Expected output file at {OUTPUT_PATH} does not exist."
    )


def test_output_is_valid_json():
    """output.json must be parseable JSON."""
    load_json(OUTPUT_PATH)


# ---------------------------------------------------------------------------
# 2. Schema – all required top-level keys with correct types
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {
    "total_entries": int,
    "valid_fragments": int,
    "discarded_fragments": int,
    "protocols_seen": list,
    "reconstructed_message": str,
    "fragments": list,
}


def test_output_has_all_required_keys():
    data = load_json(OUTPUT_PATH)
    for key in REQUIRED_KEYS:
        assert key in data, f"Missing required key: '{key}'"


def test_output_key_types():
    data = load_json(OUTPUT_PATH)
    for key, expected_type in REQUIRED_KEYS.items():
        assert isinstance(data[key], expected_type), (
            f"Key '{key}' should be {expected_type.__name__}, "
            f"got {type(data[key]).__name__}"
        )

# ---------------------------------------------------------------------------
# 3. Counting fields – total_entries, valid_fragments, discarded_fragments
# ---------------------------------------------------------------------------

def test_total_entries():
    """total_entries must equal the number of entries in the input traffic_log."""
    data = load_json(OUTPUT_PATH)
    input_data = load_json(INPUT_PATH)
    expected_total = len(input_data.get("traffic_log", []))
    assert data["total_entries"] == expected_total, (
        f"total_entries: expected {expected_total}, got {data['total_entries']}"
    )


def test_total_entries_exact():
    """total_entries must be 7 for the provided input."""
    data = load_json(OUTPUT_PATH)
    assert data["total_entries"] == 7, (
        f"total_entries: expected 7, got {data['total_entries']}"
    )


def test_valid_fragments_count():
    """valid_fragments must be 4 (after checksum validation + deduplication)."""
    data = load_json(OUTPUT_PATH)
    assert data["valid_fragments"] == 4, (
        f"valid_fragments: expected 4, got {data['valid_fragments']}"
    )


def test_discarded_fragments_count():
    """discarded_fragments must be 2 (pkt-006 and pkt-007 have bad checksums)."""
    data = load_json(OUTPUT_PATH)
    assert data["discarded_fragments"] == 2, (
        f"discarded_fragments: expected 2, got {data['discarded_fragments']}"
    )


def test_counts_are_consistent():
    """
    valid_fragments + discarded_fragments + duplicates_removed == total_entries.
    For this input: 4 + 2 + 1 = 7.
    """
    data = load_json(OUTPUT_PATH)
    # There is 1 duplicate (pkt-005, seq=1 with later timestamp)
    # So: valid(4) + discarded(2) + deduped(1) = 7
    total = data["total_entries"]
    valid = data["valid_fragments"]
    discarded = data["discarded_fragments"]
    # valid + discarded <= total (the gap is deduped entries)
    assert valid + discarded <= total, (
        f"valid({valid}) + discarded({discarded}) > total({total})"
    )


# ---------------------------------------------------------------------------
# 4. protocols_seen – sorted alphabetically
# ---------------------------------------------------------------------------

def test_protocols_seen_content():
    """protocols_seen must contain exactly DNS, HTTP, SSH."""
    data = load_json(OUTPUT_PATH)
    assert set(data["protocols_seen"]) == {"DNS", "HTTP", "SSH"}, (
        f"protocols_seen: expected {{'DNS','HTTP','SSH'}}, "
        f"got {set(data['protocols_seen'])}"
    )


def test_protocols_seen_sorted():
    """protocols_seen must be sorted alphabetically."""
    data = load_json(OUTPUT_PATH)
    assert data["protocols_seen"] == sorted(data["protocols_seen"]), (
        f"protocols_seen is not sorted: {data['protocols_seen']}"
    )

# ---------------------------------------------------------------------------
# 5. Reconstructed message
# ---------------------------------------------------------------------------

def test_reconstructed_message_exact():
    """The reconstructed message must be exactly 'The network never forgets'."""
    data = load_json(OUTPUT_PATH)
    expected_msg = "The network never forgets"
    actual_msg = data["reconstructed_message"].strip()
    assert actual_msg == expected_msg, (
        f"reconstructed_message: expected '{expected_msg}', got '{actual_msg}'"
    )


def test_reconstructed_message_not_empty():
    """The reconstructed message must not be empty for this input."""
    data = load_json(OUTPUT_PATH)
    assert len(data["reconstructed_message"].strip()) > 0, (
        "reconstructed_message is empty but should contain a message"
    )


# ---------------------------------------------------------------------------
# 6. Fragments array – structure, ordering, and content
# ---------------------------------------------------------------------------

def test_fragments_count():
    """fragments array must have exactly 4 entries."""
    data = load_json(OUTPUT_PATH)
    assert len(data["fragments"]) == 4, (
        f"Expected 4 fragments, got {len(data['fragments'])}"
    )


def test_fragments_have_required_keys():
    """Each fragment must have seq, protocol, source_ip, data, checksum."""
    data = load_json(OUTPUT_PATH)
    required = {"seq", "protocol", "source_ip", "data", "checksum"}
    for i, frag in enumerate(data["fragments"]):
        missing = required - set(frag.keys())
        assert not missing, (
            f"Fragment {i} missing keys: {missing}"
        )


def test_fragments_ordered_by_seq():
    """Fragments must be ordered by ascending seq number."""
    data = load_json(OUTPUT_PATH)
    seqs = [f["seq"] for f in data["fragments"]]
    assert seqs == sorted(seqs), (
        f"Fragments not sorted by seq: {seqs}"
    )


def test_fragment_seq_values():
    """Fragment seq values must be [0, 1, 2, 3]."""
    data = load_json(OUTPUT_PATH)
    seqs = [f["seq"] for f in data["fragments"]]
    assert seqs == [0, 1, 2, 3], (
        f"Expected seq values [0,1,2,3], got {seqs}"
    )

# ---------------------------------------------------------------------------
# 7. Per-fragment detail validation
# ---------------------------------------------------------------------------

# Expected fragment details (derived from input.json + expected_output.json)
EXPECTED_FRAGMENTS = [
    {"seq": 0, "protocol": "HTTP", "source_ip": "192.168.1.10",
     "data": "The ", "checksum": "000b625b"},
    {"seq": 1, "protocol": "DNS", "source_ip": "192.168.1.12",
     "data": "network ", "checksum": "2bdbb465"},
    {"seq": 2, "protocol": "SSH", "source_ip": "192.168.1.15",
     "data": "never ", "checksum": "f4c1fa83"},
    {"seq": 3, "protocol": "HTTP", "source_ip": "192.168.1.10",
     "data": "forgets", "checksum": "6508f284"},
]


def test_fragment_0_details():
    """Fragment seq=0 must come from HTTP / 192.168.1.10 with data 'The '."""
    data = load_json(OUTPUT_PATH)
    frag = data["fragments"][0]
    exp = EXPECTED_FRAGMENTS[0]
    assert frag["seq"] == exp["seq"]
    assert frag["protocol"] == exp["protocol"], (
        f"seq=0 protocol: expected {exp['protocol']}, got {frag['protocol']}"
    )
    assert frag["source_ip"] == exp["source_ip"]
    assert frag["data"] == exp["data"]
    assert frag["checksum"] == exp["checksum"]


def test_fragment_1_details():
    """Fragment seq=1 must come from DNS / 192.168.1.12 (earliest timestamp)."""
    data = load_json(OUTPUT_PATH)
    frag = data["fragments"][1]
    exp = EXPECTED_FRAGMENTS[1]
    assert frag["seq"] == exp["seq"]
    assert frag["protocol"] == exp["protocol"], (
        f"seq=1 protocol: expected {exp['protocol']}, got {frag['protocol']}"
    )
    assert frag["source_ip"] == exp["source_ip"], (
        f"seq=1 source_ip: expected {exp['source_ip']}, got {frag['source_ip']}. "
        "Deduplication should keep the earliest timestamp entry."
    )
    assert frag["data"] == exp["data"]
    assert frag["checksum"] == exp["checksum"]


def test_fragment_2_details():
    """Fragment seq=2 must come from SSH / 192.168.1.15 with data 'never '."""
    data = load_json(OUTPUT_PATH)
    frag = data["fragments"][2]
    exp = EXPECTED_FRAGMENTS[2]
    assert frag["seq"] == exp["seq"]
    assert frag["protocol"] == exp["protocol"]
    assert frag["source_ip"] == exp["source_ip"]
    assert frag["data"] == exp["data"]
    assert frag["checksum"] == exp["checksum"]


def test_fragment_3_details():
    """Fragment seq=3 must come from HTTP / 192.168.1.10 with data 'forgets'."""
    data = load_json(OUTPUT_PATH)
    frag = data["fragments"][3]
    exp = EXPECTED_FRAGMENTS[3]
    assert frag["seq"] == exp["seq"]
    assert frag["protocol"] == exp["protocol"]
    assert frag["source_ip"] == exp["source_ip"]
    assert frag["data"] == exp["data"]
    assert frag["checksum"] == exp["checksum"]

# ---------------------------------------------------------------------------
# 8. CRC32 integrity – independently verify each fragment's checksum
# ---------------------------------------------------------------------------

def test_all_fragment_checksums_valid():
    """
    Re-compute CRC32 for each fragment's data and verify it matches
    the reported checksum. This catches agents that hardcode data
    without proper checksum computation.
    """
    data = load_json(OUTPUT_PATH)
    for i, frag in enumerate(data["fragments"]):
        expected_crc = compute_crc32(frag["data"])
        assert frag["checksum"] == expected_crc, (
            f"Fragment {i} (seq={frag['seq']}): CRC32 of '{frag['data']}' "
            f"should be '{expected_crc}', got '{frag['checksum']}'"
        )


# ---------------------------------------------------------------------------
# 9. Deduplication – seq=1 must use pkt-002 not pkt-005
# ---------------------------------------------------------------------------

def test_dedup_seq1_uses_earliest_timestamp():
    """
    Two entries share seq=1: pkt-002 (10:30:05, data='network ')
    and pkt-005 (10:31:00, data='XXXXXX '). The earlier one must win.
    """
    data = load_json(OUTPUT_PATH)
    seq1_frags = [f for f in data["fragments"] if f["seq"] == 1]
    assert len(seq1_frags) == 1, (
        f"Expected exactly 1 fragment with seq=1, got {len(seq1_frags)}"
    )
    frag = seq1_frags[0]
    assert frag["data"] == "network ", (
        f"seq=1 data should be 'network ' (earliest timestamp), "
        f"got '{frag['data']}'"
    )
    assert frag["source_ip"] == "192.168.1.12", (
        f"seq=1 source_ip should be 192.168.1.12 (pkt-002), "
        f"got {frag['source_ip']}"
    )


# ---------------------------------------------------------------------------
# 10. Discarded entries must NOT appear in fragments
# ---------------------------------------------------------------------------

def test_no_garbage_in_fragments():
    """pkt-006 data 'GARBAGE' (bad checksum) must not appear in fragments."""
    data = load_json(OUTPUT_PATH)
    all_data = [f["data"] for f in data["fragments"]]
    assert "GARBAGE" not in all_data, (
        "Fragment with data 'GARBAGE' should have been discarded (bad checksum)"
    )


def test_no_noise_in_fragments():
    """pkt-007 data 'NOISE' (bad checksum) must not appear in fragments."""
    data = load_json(OUTPUT_PATH)
    all_data = [f["data"] for f in data["fragments"]]
    assert "NOISE" not in all_data, (
        "Fragment with data 'NOISE' should have been discarded (bad checksum)"
    )


def test_no_duplicate_data_in_fragments():
    """pkt-005 data 'XXXXXX ' (valid but deduped) must not appear."""
    data = load_json(OUTPUT_PATH)
    all_data = [f["data"] for f in data["fragments"]]
    assert "XXXXXX " not in all_data, (
        "Fragment with data 'XXXXXX ' should have been deduped "
        "(later timestamp for seq=1)"
    )


# ---------------------------------------------------------------------------
# 11. Message is concatenation of fragment data in seq order
# ---------------------------------------------------------------------------

def test_message_equals_concatenated_fragments():
    """
    reconstructed_message must equal the concatenation of fragment data
    fields in the order they appear (which is seq order).
    """
    data = load_json(OUTPUT_PATH)
    concatenated = "".join(f["data"] for f in data["fragments"])
    assert data["reconstructed_message"] == concatenated, (
        f"reconstructed_message '{data['reconstructed_message']}' != "
        f"concatenated fragments '{concatenated}'"
    )


# ---------------------------------------------------------------------------
# 12. No extra seq values beyond expected
# ---------------------------------------------------------------------------

def test_no_extra_fragments():
    """No seq values beyond 0-3 should be present."""
    data = load_json(OUTPUT_PATH)
    seqs = {f["seq"] for f in data["fragments"]}
    unexpected = seqs - {0, 1, 2, 3}
    assert not unexpected, (
        f"Unexpected seq values in fragments: {unexpected}"
    )

