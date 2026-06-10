"""
Tests for BIND9 to PowerDNS migration task.
Validates /app/powerdns_records.json and /app/migration_report.txt
"""

import json
import os
import re

JSON_PATH = "/app/powerdns_records.json"
REPORT_PATH = "/app/migration_report.txt"


# ─── File existence and basic validity ───────────────────────────────

def test_json_file_exists():
    assert os.path.isfile(JSON_PATH), f"{JSON_PATH} does not exist"

def test_report_file_exists():
    assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} does not exist"

def test_json_file_not_empty():
    assert os.path.getsize(JSON_PATH) > 10, "JSON file is empty or trivially small"

def test_report_file_not_empty():
    assert os.path.getsize(REPORT_PATH) > 10, "Report file is empty or trivially small"

def test_json_is_valid_json():
    with open(JSON_PATH, "r") as f:
        data = json.load(f)
    assert isinstance(data, list), "Top-level JSON must be an array"


# ─── JSON structure: zones ───────────────────────────────────────────

def _load_json():
    with open(JSON_PATH, "r") as f:
        return json.load(f)

def test_json_has_two_zones():
    data = _load_json()
    assert len(data) == 2, f"Expected 2 zones, got {len(data)}"

def test_zone_names():
    data = _load_json()
    zone_names = [z["zone"] for z in data]
    assert "corp.example.com." in zone_names, "Missing corp.example.com. zone"
    assert "dev.example.com." in zone_names, "Missing dev.example.com. zone"

def test_zone_order():
    """corp.example.com. must come before dev.example.com. (input order)."""
    data = _load_json()
    assert data[0]["zone"] == "corp.example.com."
    assert data[1]["zone"] == "dev.example.com."

def test_zone_keys():
    data = _load_json()
    for zone in data:
        assert "zone" in zone, "Zone object missing 'zone' key"
        assert "default_ttl" in zone, "Zone object missing 'default_ttl' key"
        assert "records" in zone, "Zone object missing 'records' key"
        assert isinstance(zone["records"], list), "'records' must be a list"

def test_default_ttl_corp():
    data = _load_json()
    corp = data[0]
    assert corp["default_ttl"] == 3600, f"corp default_ttl should be 3600, got {corp['default_ttl']}"

def test_default_ttl_dev():
    data = _load_json()
    dev = data[1]
    assert dev["default_ttl"] == 7200, f"dev default_ttl should be 7200, got {dev['default_ttl']}"


# ─── Record-level structure ──────────────────────────────────────────

def test_record_keys():
    data = _load_json()
    for zone in data:
        for rec in zone["records"]:
            assert "name" in rec, "Record missing 'name'"
            assert "type" in rec, "Record missing 'type'"
            assert "ttl" in rec, "Record missing 'ttl'"
            assert "content" in rec, "Record missing 'content'"

def test_record_types_are_strings():
    data = _load_json()
    valid_types = {"SOA", "NS", "A", "AAAA", "CNAME", "MX"}
    for zone in data:
        for rec in zone["records"]:
            assert rec["type"] in valid_types, f"Unexpected record type: {rec['type']}"

def test_ttl_values_are_integers():
    data = _load_json()
    for zone in data:
        for rec in zone["records"]:
            assert isinstance(rec["ttl"], int), f"TTL must be int, got {type(rec['ttl'])}"

def test_names_are_fqdn():
    """All record names must end with a trailing dot (FQDN)."""
    data = _load_json()
    for zone in data:
        for rec in zone["records"]:
            assert rec["name"].endswith("."), \
                f"Record name '{rec['name']}' is not a FQDN (missing trailing dot)"


# ─── Corp zone: record counts ───────────────────────────────────────

def _get_zone(name):
    data = _load_json()
    for z in data:
        if z["zone"] == name:
            return z
    raise AssertionError(f"Zone {name} not found")  # noqa

def _records_by_type(zone, rtype):
    return [r for r in zone["records"] if r["type"] == rtype]

def test_corp_record_count():
    corp = _get_zone("corp.example.com.")
    # SOA(1) + NS(2) + A(5: ns1,ns2,mail,app,db) + MX(1) + CNAME(1) = 10
    assert len(corp["records"]) == 10, \
        f"corp.example.com. should have 10 records, got {len(corp['records'])}"

def test_corp_soa_count():
    corp = _get_zone("corp.example.com.")
    assert len(_records_by_type(corp, "SOA")) == 1

def test_corp_ns_count():
    corp = _get_zone("corp.example.com.")
    assert len(_records_by_type(corp, "NS")) == 2

def test_corp_a_count():
    corp = _get_zone("corp.example.com.")
    assert len(_records_by_type(corp, "A")) == 5

def test_corp_mx_count():
    corp = _get_zone("corp.example.com.")
    assert len(_records_by_type(corp, "MX")) == 1

def test_corp_cname_count():
    corp = _get_zone("corp.example.com.")
    assert len(_records_by_type(corp, "CNAME")) == 1


# ─── Dev zone: record counts ────────────────────────────────────────

def test_dev_record_count():
    dev = _get_zone("dev.example.com.")
    # SOA(1) + NS(2) + A(5: ns1,ns2,web,api,mail,cache) + CNAME(1) + MX(1) + AAAA(1) = 12
    # Actually: ns1,ns2,web,api,mail,cache = 6 A records
    # SOA(1)+NS(2)+A(6)+CNAME(1)+MX(1)+AAAA(1) = 12
    assert len(dev["records"]) == 12, \
        f"dev.example.com. should have 12 records, got {len(dev['records'])}"

def test_dev_aaaa_count():
    dev = _get_zone("dev.example.com.")
    assert len(_records_by_type(dev, "AAAA")) == 1

def test_dev_a_count():
    dev = _get_zone("dev.example.com.")
    assert len(_records_by_type(dev, "A")) == 6


# ─── Specific record content validation (corp) ──────────────────────

def test_corp_soa_content():
    """SOA must have mname rname serial refresh retry expire minimum."""
    corp = _get_zone("corp.example.com.")
    soa = _records_by_type(corp, "SOA")[0]
    assert soa["name"] == "corp.example.com."
    content = re.sub(r'\s+', ' ', soa["content"].strip())
    # Must contain the key SOA fields
    assert "ns1.corp.example.com." in content
    assert "admin.corp.example.com." in content
    assert "2024010101" in content
    assert "3600" in content
    assert "900" in content
    assert "604800" in content
    assert "86400" in content

def test_corp_soa_ttl():
    corp = _get_zone("corp.example.com.")
    soa = _records_by_type(corp, "SOA")[0]
    assert soa["ttl"] == 3600

def test_corp_ns_records():
    corp = _get_zone("corp.example.com.")
    ns_recs = _records_by_type(corp, "NS")
    ns_contents = sorted([r["content"] for r in ns_recs])
    assert "ns1.corp.example.com." in ns_contents
    assert "ns2.corp.example.com." in ns_contents
    # NS records should have zone origin as name
    for r in ns_recs:
        assert r["name"] == "corp.example.com."

def test_corp_a_ns1():
    corp = _get_zone("corp.example.com.")
    a_recs = _records_by_type(corp, "A")
    ns1_recs = [r for r in a_recs if "ns1" in r["name"]]
    assert len(ns1_recs) == 1
    assert ns1_recs[0]["name"] == "ns1.corp.example.com."
    assert ns1_recs[0]["content"] == "192.168.1.1"
    assert ns1_recs[0]["ttl"] == 3600

def test_corp_mx_record():
    corp = _get_zone("corp.example.com.")
    mx = _records_by_type(corp, "MX")[0]
    assert mx["name"] == "corp.example.com."
    # Content must include priority and FQDN target
    assert "10" in mx["content"]
    assert "mail.corp.example.com." in mx["content"]

def test_corp_cname_record():
    corp = _get_zone("corp.example.com.")
    cname = _records_by_type(corp, "CNAME")[0]
    assert cname["name"] == "www.corp.example.com."
    assert cname["content"] == "corp.example.com."


# ─── Edge cases: explicit TTL, AAAA, FQDN expansion ─────────────────

def test_explicit_ttl_override():
    """cache record in dev zone has explicit TTL 1800, not zone default 7200."""
    dev = _get_zone("dev.example.com.")
    a_recs = _records_by_type(dev, "A")
    cache_recs = [r for r in a_recs if "cache" in r["name"]]
    assert len(cache_recs) == 1, "Missing 'cache' A record in dev zone"
    assert cache_recs[0]["ttl"] == 1800, \
        f"cache record TTL should be 1800 (explicit), got {cache_recs[0]['ttl']}"
    assert cache_recs[0]["content"] == "10.0.0.40"

def test_aaaa_record():
    """ipv6host AAAA record in dev zone."""
    dev = _get_zone("dev.example.com.")
    aaaa = _records_by_type(dev, "AAAA")
    assert len(aaaa) == 1
    assert aaaa[0]["name"] == "ipv6host.dev.example.com."
    assert aaaa[0]["content"] == "2001:db8::1"
    assert aaaa[0]["ttl"] == 7200

def test_at_symbol_expansion_corp():
    """@ in corp zone must expand to corp.example.com."""
    corp = _get_zone("corp.example.com.")
    soa = _records_by_type(corp, "SOA")[0]
    assert soa["name"] == "corp.example.com.", "@ not expanded in SOA name"
    ns_recs = _records_by_type(corp, "NS")
    for r in ns_recs:
        assert r["name"] == "corp.example.com.", "@ not expanded in NS name"

def test_at_symbol_expansion_dev():
    """@ in dev zone must expand to dev.example.com."""
    dev = _get_zone("dev.example.com.")
    soa = _records_by_type(dev, "SOA")[0]
    assert soa["name"] == "dev.example.com.", "@ not expanded in SOA name"

def test_relative_name_expansion():
    """Relative names like 'ns1' must become 'ns1.corp.example.com.'"""
    corp = _get_zone("corp.example.com.")
    a_recs = _records_by_type(corp, "A")
    names = [r["name"] for r in a_recs]
    assert "ns1.corp.example.com." in names
    assert "ns2.corp.example.com." in names
    assert "mail.corp.example.com." in names
    assert "app.corp.example.com." in names
    assert "db.corp.example.com." in names

def test_fqdn_in_content_preserved():
    """Domain names already ending with dot in content must be kept as-is."""
    corp = _get_zone("corp.example.com.")
    cname = _records_by_type(corp, "CNAME")[0]
    # corp.example.com. already has trailing dot in input
    assert cname["content"].endswith(".")

def test_dev_soa_content():
    dev = _get_zone("dev.example.com.")
    soa = _records_by_type(dev, "SOA")[0]
    content = re.sub(r'\s+', ' ', soa["content"].strip())
    assert "ns1.dev.example.com." in content
    assert "hostmaster.dev.example.com." in content
    assert "2024020201" in content

def test_dev_staging_cname():
    dev = _get_zone("dev.example.com.")
    cname = _records_by_type(dev, "CNAME")[0]
    assert cname["name"] == "staging.dev.example.com."
    assert cname["content"] == "web.dev.example.com."

def test_dev_mx_record():
    dev = _get_zone("dev.example.com.")
    mx = _records_by_type(dev, "MX")[0]
    assert mx["name"] == "dev.example.com."
    assert "20" in mx["content"]
    assert "mail.dev.example.com." in mx["content"]


# ─── Record order preservation ───────────────────────────────────────

def test_corp_record_order():
    """Records must appear in the same order as the input file."""
    corp = _get_zone("corp.example.com.")
    types_in_order = [r["type"] for r in corp["records"]]
    # Input order: SOA, NS, NS, A(ns1), A(ns2), A(mail), MX, CNAME, A(app), A(db)
    assert types_in_order[0] == "SOA"
    assert types_in_order[1] == "NS"
    assert types_in_order[2] == "NS"
    # First A record should be ns1
    assert corp["records"][3]["type"] == "A"
    assert corp["records"][3]["name"] == "ns1.corp.example.com."

def test_dev_first_record_is_soa():
    dev = _get_zone("dev.example.com.")
    assert dev["records"][0]["type"] == "SOA"


# ─── Migration report validation ────────────────────────────────────

def _load_report():
    with open(REPORT_PATH, "r") as f:
        return f.read()

def test_report_header():
    report = _load_report()
    lines = report.strip().split("\n")
    assert lines[0].strip() == "Migration Report"

def test_report_zone_count():
    report = _load_report()
    lines = report.strip().split("\n")
    zone_line = lines[1].strip()
    assert zone_line == "Zones migrated: 2", f"Expected 'Zones migrated: 2', got '{zone_line}'"

def test_report_total_records():
    report = _load_report()
    lines = report.strip().split("\n")
    total_line = lines[2].strip()
    assert total_line == "Total records: 22", f"Expected 'Total records: 22', got '{total_line}'"

def test_report_contains_both_zones():
    report = _load_report()
    assert "Zone: corp.example.com." in report
    assert "Zone: dev.example.com." in report

def test_report_corp_zone_block():
    """Verify corp zone record type counts in report."""
    report = _load_report()
    lines = [l.rstrip() for l in report.strip().split("\n")]
    # Find the corp zone block
    corp_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "Zone: corp.example.com.":
            corp_idx = i
            break
    assert corp_idx is not None, "Corp zone block not found in report"
    # Collect indented lines after the zone header
    corp_lines = []
    for line in lines[corp_idx + 1:]:
        if line.startswith("  ") and ":" in line:
            corp_lines.append(line.strip())
        else:
            break
    corp_counts = {}
    for cl in corp_lines:
        parts = cl.split(":")
        corp_counts[parts[0].strip()] = int(parts[1].strip())
    assert corp_counts.get("SOA") == 1
    assert corp_counts.get("NS") == 2
    assert corp_counts.get("A") == 5
    assert corp_counts.get("MX") == 1
    assert corp_counts.get("CNAME") == 1

def test_report_dev_zone_block():
    """Verify dev zone record type counts in report."""
    report = _load_report()
    lines = [l.rstrip() for l in report.strip().split("\n")]
    dev_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "Zone: dev.example.com.":
            dev_idx = i
            break
    assert dev_idx is not None, "Dev zone block not found in report"
    dev_lines = []
    for line in lines[dev_idx + 1:]:
        if line.startswith("  ") and ":" in line:
            dev_lines.append(line.strip())
        else:
            break
    dev_counts = {}
    for dl in dev_lines:
        parts = dl.split(":")
        dev_counts[parts[0].strip()] = int(parts[1].strip())
    assert dev_counts.get("SOA") == 1
    assert dev_counts.get("NS") == 2
    assert dev_counts.get("A") == 6
    assert dev_counts.get("AAAA") == 1
    assert dev_counts.get("CNAME") == 1
    assert dev_counts.get("MX") == 1


def test_report_indentation():
    """Per-zone record type lines must be indented with exactly two spaces."""
    report = _load_report()
    lines = report.strip().split("\n")
    for line in lines:
        stripped = line.strip()
        # Lines like "  SOA: 1" should start with exactly 2 spaces
        if ":" in stripped and stripped.split(":")[0] in (
            "SOA", "NS", "A", "AAAA", "CNAME", "MX"
        ):
            assert line.startswith("  "), \
                f"Record type line not indented with 2 spaces: '{line}'"
            # Must not start with more than 2 spaces (exactly 2)
            assert not line.startswith("   "), \
                f"Record type line has more than 2 spaces indent: '{line}'"

def test_report_zone_order():
    """Corp zone must appear before dev zone in report."""
    report = _load_report()
    corp_pos = report.index("Zone: corp.example.com.")
    dev_pos = report.index("Zone: dev.example.com.")
    assert corp_pos < dev_pos, "Corp zone must appear before dev zone"

def test_report_no_zero_count_types():
    """Only record types with count > 0 should appear."""
    report = _load_report()
    lines = report.strip().split("\n")
    for line in lines:
        stripped = line.strip()
        if ":" in stripped:
            parts = stripped.split(":")
            key = parts[0].strip()
            if key in ("SOA", "NS", "A", "AAAA", "CNAME", "MX"):
                val = int(parts[1].strip())
                assert val > 0, f"Record type {key} has count 0 but should be omitted"


# ─── Anti-cheat: no @ symbols or unexpanded names in output ─────────

def test_no_raw_at_in_json():
    """Ensure no record has '@' as its name (must be expanded)."""
    data = _load_json()
    for zone in data:
        for rec in zone["records"]:
            assert rec["name"] != "@", "Found unexpanded '@' in record name"

def test_no_bare_hostnames_in_names():
    """All record names must contain at least one dot (be FQDNs)."""
    data = _load_json()
    for zone in data:
        for rec in zone["records"]:
            assert "." in rec["name"], \
                f"Record name '{rec['name']}' appears to be a bare hostname"

