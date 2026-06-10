"""
Tests for GitHub Issue Resolution Trends analysis task.
Validates: issues_cleaned.csv, summary.json, histogram.png, boxplot.png, scatter.png
"""

import os
import csv
import json
import math
import struct

# ---------------------------------------------------------------------------
# Paths – all outputs live under /app
# ---------------------------------------------------------------------------
BASE = "/app"
CSV_PATH = os.path.join(BASE, "issues_cleaned.csv")
JSON_PATH = os.path.join(BASE, "summary.json")
HIST_PATH = os.path.join(BASE, "histogram.png")
BOX_PATH = os.path.join(BASE, "boxplot.png")
SCATTER_PATH = os.path.join(BASE, "scatter.png")

# ---------------------------------------------------------------------------
# Helper: read PNG dimensions without PIL
# ---------------------------------------------------------------------------

def png_dimensions(path):
    """Return (width, height) of a PNG file by reading the IHDR chunk."""
    with open(path, "rb") as f:
        header = f.read(24)
        # PNG signature: 8 bytes, then IHDR chunk (length 4, type 4, width 4, height 4)
        assert header[:8] == b'\x89PNG\r\n\x1a\n', "Not a valid PNG file"
        width = struct.unpack(">I", header[16:20])[0]
        height = struct.unpack(">I", header[20:24])[0]
    return width, height


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

def test_csv_exists():
    assert os.path.isfile(CSV_PATH), f"Missing {CSV_PATH}"
    assert os.path.getsize(CSV_PATH) > 100, "CSV file appears empty or too small"

def test_json_exists():
    assert os.path.isfile(JSON_PATH), f"Missing {JSON_PATH}"
    assert os.path.getsize(JSON_PATH) > 50, "JSON file appears empty or too small"

def test_histogram_exists():
    assert os.path.isfile(HIST_PATH), f"Missing {HIST_PATH}"
    assert os.path.getsize(HIST_PATH) > 1000, "histogram.png appears too small"

def test_boxplot_exists():
    assert os.path.isfile(BOX_PATH), f"Missing {BOX_PATH}"
    assert os.path.getsize(BOX_PATH) > 1000, "boxplot.png appears too small"

def test_scatter_exists():
    assert os.path.isfile(SCATTER_PATH), f"Missing {SCATTER_PATH}"
    assert os.path.getsize(SCATTER_PATH) > 1000, "scatter.png appears too small"


# ===========================================================================
# 2. CSV STRUCTURE & CONTENT TESTS
# ===========================================================================

EXPECTED_COLUMNS = [
    "issue_number", "title", "created_at", "closed_at",
    "labels", "open_duration_days", "quarter_opened", "quarter_closed",
]

def _read_csv_rows():
    """Read CSV and return list of dicts."""
    with open(CSV_PATH, "r", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def test_csv_header():
    _, fieldnames = _read_csv_rows()
    assert fieldnames == EXPECTED_COLUMNS, (
        f"CSV header mismatch. Expected {EXPECTED_COLUMNS}, got {fieldnames}"
    )


def test_csv_row_count():
    rows, _ = _read_csv_rows()
    assert len(rows) == 35, f"Expected 35 rows, got {len(rows)}"


def test_csv_sorted_by_issue_number():
    rows, _ = _read_csv_rows()
    issue_nums = [int(r["issue_number"]) for r in rows]
    assert issue_nums == sorted(issue_nums), "Rows not sorted by issue_number ascending"
    assert issue_nums[0] == 101 and issue_nums[-1] == 135


def test_csv_issue_numbers_complete():
    rows, _ = _read_csv_rows()
    issue_nums = {int(r["issue_number"]) for r in rows}
    expected = set(range(101, 136))
    assert issue_nums == expected, f"Missing or extra issue numbers: {expected.symmetric_difference(issue_nums)}"


def test_csv_quarter_format():
    """All quarter_opened and quarter_closed must match YYYY-QN pattern."""
    import re
    pattern = re.compile(r"^\d{4}-Q[1-4]$")
    rows, _ = _read_csv_rows()
    for r in rows:
        assert pattern.match(r["quarter_opened"]), (
            f"Issue {r['issue_number']}: bad quarter_opened '{r['quarter_opened']}'"
        )
        assert pattern.match(r["quarter_closed"]), (
            f"Issue {r['issue_number']}: bad quarter_closed '{r['quarter_closed']}'"
        )


def test_csv_open_duration_nonnegative():
    """All open_duration_days must be >= 0."""
    rows, _ = _read_csv_rows()
    for r in rows:
        val = float(r["open_duration_days"])
        assert val >= 0.0, f"Issue {r['issue_number']}: negative duration {val}"


def test_csv_zero_duration_edge_cases():
    """Issues 104 and 115 have created_at == closed_at → 0.0 days."""
    rows, _ = _read_csv_rows()
    by_num = {int(r["issue_number"]): r for r in rows}
    for inum in [104, 115]:
        val = float(by_num[inum]["open_duration_days"])
        assert val == 0.0, f"Issue {inum}: expected 0.0, got {val}"


def test_csv_specific_durations():
    """Spot-check several computed open_duration_days values."""
    rows, _ = _read_csv_rows()
    by_num = {int(r["issue_number"]): r for r in rows}
    # (issue_number, expected_duration) — hand-computed from input.json
    checks = [
        (101, 1.0),
        (102, 2.81),
        (103, 12.33),
        (108, 9.85),
        (112, 21.27),
        (126, 35.08),
        (135, 39.38),
    ]
    for inum, expected in checks:
        actual = float(by_num[inum]["open_duration_days"])
        assert math.isclose(actual, expected, abs_tol=0.02), (
            f"Issue {inum}: expected ~{expected}, got {actual}"
        )


def test_csv_specific_quarters():
    """Spot-check quarter_opened assignments."""
    rows, _ = _read_csv_rows()
    by_num = {int(r["issue_number"]): r for r in rows}
    checks = [
        (101, "2022-Q1"),
        (108, "2022-Q2"),
        (116, "2022-Q3"),
        (123, "2022-Q4"),
        (129, "2023-Q1"),
    ]
    for inum, expected_q in checks:
        assert by_num[inum]["quarter_opened"] == expected_q, (
            f"Issue {inum}: expected quarter_opened={expected_q}, got {by_num[inum]['quarter_opened']}"
        )


def test_csv_null_labels_handling():
    """Issue 112 has labels:null in input → should be empty string in CSV."""
    rows, _ = _read_csv_rows()
    by_num = {int(r["issue_number"]): r for r in rows}
    labels_112 = by_num[112]["labels"].strip()
    assert labels_112 == "", f"Issue 112: expected empty labels, got '{labels_112}'"


def test_csv_empty_labels_handling():
    """Issue 135 has labels:[] in input → should be empty string in CSV."""
    rows, _ = _read_csv_rows()
    by_num = {int(r["issue_number"]): r for r in rows}
    labels_135 = by_num[135]["labels"].strip()
    assert labels_135 == "", f"Issue 135: expected empty labels, got '{labels_135}'"


def test_csv_semicolon_labels():
    """Issue 102 has ['bug','ui'] → should be 'bug;ui' (semicolon-separated)."""
    rows, _ = _read_csv_rows()
    by_num = {int(r["issue_number"]): r for r in rows}
    labels_102 = by_num[102]["labels"].strip()
    parts = [p.strip() for p in labels_102.split(";")]
    assert set(parts) == {"bug", "ui"}, (
        f"Issue 102: expected labels 'bug;ui', got '{labels_102}'"
    )


# ===========================================================================
# 3. SUMMARY JSON TESTS
# ===========================================================================

def _load_summary():
    with open(JSON_PATH, "r") as f:
        return json.load(f)


def test_json_valid():
    """summary.json must be valid JSON."""
    data = _load_summary()
    assert isinstance(data, dict), "summary.json root must be a JSON object"


def test_json_top_level_keys():
    data = _load_summary()
    required = {"total_issues", "mean_open_duration_days",
                "median_open_duration_days", "quarterly_stats", "trend"}
    assert required.issubset(data.keys()), (
        f"Missing keys: {required - set(data.keys())}"
    )


def test_json_total_issues():
    data = _load_summary()
    assert data["total_issues"] == 35, f"Expected 35, got {data['total_issues']}"


def test_json_overall_mean():
    data = _load_summary()
    # Expected ~20.32 (tolerance for minor rounding differences)
    assert math.isclose(data["mean_open_duration_days"], 20.32, abs_tol=0.15), (
        f"Expected mean ~20.32, got {data['mean_open_duration_days']}"
    )


def test_json_overall_median():
    data = _load_summary()
    # Expected ~21.17
    assert math.isclose(data["median_open_duration_days"], 21.17, abs_tol=0.15), (
        f"Expected median ~21.17, got {data['median_open_duration_days']}"
    )


def test_json_trend_increasing():
    data = _load_summary()
    assert data["trend"] == "increasing", (
        f"Expected trend='increasing', got '{data['trend']}'"
    )


def test_json_quarterly_stats_count():
    data = _load_summary()
    qs = data["quarterly_stats"]
    assert isinstance(qs, list), "quarterly_stats must be a list"
    assert len(qs) == 5, f"Expected 5 quarters, got {len(qs)}"


def test_json_quarterly_stats_sorted():
    data = _load_summary()
    qs = data["quarterly_stats"]
    quarters = [q["quarter"] for q in qs]
    expected_order = ["2022-Q1", "2022-Q2", "2022-Q3", "2022-Q4", "2023-Q1"]
    assert quarters == expected_order, (
        f"Quarters not in chronological order: {quarters}"
    )


def test_json_quarterly_stats_keys():
    """Each quarterly_stats entry must have the required keys."""
    data = _load_summary()
    required = {"quarter", "issue_count", "mean_open_duration_days",
                "median_open_duration_days"}
    for entry in data["quarterly_stats"]:
        assert required.issubset(entry.keys()), (
            f"Quarter {entry.get('quarter','?')}: missing keys {required - set(entry.keys())}"
        )


def test_json_quarterly_issue_counts():
    """Verify per-quarter issue counts."""
    data = _load_summary()
    qs = {q["quarter"]: q for q in data["quarterly_stats"]}
    expected_counts = {
        "2022-Q1": 7,
        "2022-Q2": 8,
        "2022-Q3": 7,
        "2022-Q4": 6,
        "2023-Q1": 7,
    }
    for quarter, expected in expected_counts.items():
        assert quarter in qs, f"Missing quarter {quarter}"
        actual = qs[quarter]["issue_count"]
        assert actual == expected, (
            f"{quarter}: expected count={expected}, got {actual}"
        )


def test_json_quarterly_issue_counts_sum():
    """Sum of quarterly issue counts must equal total_issues."""
    data = _load_summary()
    total_from_quarters = sum(q["issue_count"] for q in data["quarterly_stats"])
    assert total_from_quarters == data["total_issues"], (
        f"Sum of quarterly counts ({total_from_quarters}) != total_issues ({data['total_issues']})"
    )


def test_json_quarterly_means():
    """Spot-check quarterly mean open durations."""
    data = _load_summary()
    qs = {q["quarter"]: q for q in data["quarterly_stats"]}
    expected_means = {
        "2022-Q1": 5.13,
        "2022-Q2": 14.10,
        "2022-Q3": 19.35,
        "2022-Q4": 29.24,
        "2023-Q1": 35.96,
    }
    for quarter, expected in expected_means.items():
        actual = qs[quarter]["mean_open_duration_days"]
        assert math.isclose(actual, expected, abs_tol=0.15), (
            f"{quarter}: expected mean ~{expected}, got {actual}"
        )


def test_json_quarterly_medians():
    """Spot-check quarterly median open durations."""
    data = _load_summary()
    qs = {q["quarter"]: q for q in data["quarterly_stats"]}
    expected_medians = {
        "2022-Q1": 5.38,
        "2022-Q2": 15.28,
        "2022-Q3": 21.17,
        "2022-Q4": 28.25,
        "2023-Q1": 36.21,
    }
    for quarter, expected in expected_medians.items():
        actual = qs[quarter]["median_open_duration_days"]
        assert math.isclose(actual, expected, abs_tol=0.15), (
            f"{quarter}: expected median ~{expected}, got {actual}"
        )


# ===========================================================================
# 4. PNG VISUALIZATION TESTS
# ===========================================================================

def test_histogram_valid_png():
    """histogram.png must be a valid PNG with minimum 800x600."""
    w, h = png_dimensions(HIST_PATH)
    assert w >= 800, f"histogram.png width {w} < 800"
    assert h >= 600, f"histogram.png height {h} < 600"


def test_boxplot_valid_png():
    """boxplot.png must be a valid PNG with minimum 800x600."""
    w, h = png_dimensions(BOX_PATH)
    assert w >= 800, f"boxplot.png width {w} < 800"
    assert h >= 600, f"boxplot.png height {h} < 600"


def test_scatter_valid_png():
    """scatter.png must be a valid PNG with minimum 800x600."""
    w, h = png_dimensions(SCATTER_PATH)
    assert w >= 800, f"scatter.png width {w} < 800"
    assert h >= 600, f"scatter.png height {h} < 600"


# ===========================================================================
# 5. CROSS-VALIDATION: CSV vs JSON consistency
# ===========================================================================

def test_csv_json_total_issues_match():
    """Number of CSV rows must match summary.json total_issues."""
    rows, _ = _read_csv_rows()
    data = _load_summary()
    assert len(rows) == data["total_issues"], (
        f"CSV has {len(rows)} rows but summary says {data['total_issues']}"
    )


def test_csv_json_quarter_counts_match():
    """Issue counts per quarter in CSV must match quarterly_stats in JSON."""
    rows, _ = _read_csv_rows()
    from collections import Counter
    csv_counts = Counter(r["quarter_opened"] for r in rows)

    data = _load_summary()
    json_counts = {q["quarter"]: q["issue_count"] for q in data["quarterly_stats"]}

    for quarter, count in json_counts.items():
        assert csv_counts.get(quarter, 0) == count, (
            f"{quarter}: CSV has {csv_counts.get(quarter, 0)} issues, "
            f"JSON says {count}"
        )


def test_csv_json_mean_duration_consistency():
    """Overall mean from CSV durations should match summary.json mean."""
    rows, _ = _read_csv_rows()
    durations = [float(r["open_duration_days"]) for r in rows]
    csv_mean = sum(durations) / len(durations)

    data = _load_summary()
    json_mean = data["mean_open_duration_days"]

    assert math.isclose(csv_mean, json_mean, abs_tol=0.15), (
        f"CSV-derived mean {csv_mean:.2f} != JSON mean {json_mean}"
    )

