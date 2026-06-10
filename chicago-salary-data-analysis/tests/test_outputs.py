"""
Tests for Chicago 2013 Employee Salary Data Analysis task.

Validates:
- All 5 output files exist and are non-empty
- summary_statistics.csv has correct structure, values, and sort order
- summary_report.txt has required labels and correct numeric values
- PNG visualizations are valid image files
- Hourly employee pay is computed correctly (Hourly Rate * Typical Hours * 52)
"""

import os
import csv
import math

# All output files live in /app
APP_DIR = "/app"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _read_csv_rows(path):
    """Return (header, rows) from a CSV file."""
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return [h.strip() for h in header], rows


def _read_text(path):
    with open(path) as f:
        return f.read()


def _parse_float(s):
    """Strip $, commas, whitespace and parse to float."""
    return float(s.replace("$", "").replace(",", "").strip())


def _close(a, b, rel_tol=1e-2, abs_tol=0.5):
    """Fuzzy float comparison – tolerant of minor rounding differences."""
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


# ===========================================================================
# 1. FILE EXISTENCE & NON-EMPTY CHECKS
# ===========================================================================

EXPECTED_FILES = [
    "summary_statistics.csv",
    "salary_distribution.png",
    "top10_departments.png",
    "top5_boxplot.png",
    "summary_report.txt",
]


def test_all_output_files_exist():
    """Every required output file must exist."""
    for fname in EXPECTED_FILES:
        path = os.path.join(APP_DIR, fname)
        assert os.path.isfile(path), f"Missing output file: {path}"


def test_all_output_files_non_empty():
    """Every required output file must have content."""
    for fname in EXPECTED_FILES:
        path = os.path.join(APP_DIR, fname)
        assert os.path.getsize(path) > 0, f"Output file is empty: {path}"


# ===========================================================================
# 2. PNG VALIDATION
# ===========================================================================

PNG_HEADER = b"\x89PNG\r\n\x1a\n"

def test_salary_distribution_is_valid_png():
    path = os.path.join(APP_DIR, "salary_distribution.png")
    with open(path, "rb") as f:
        header = f.read(8)
    assert header == PNG_HEADER, "salary_distribution.png is not a valid PNG"


def test_top10_departments_is_valid_png():
    path = os.path.join(APP_DIR, "top10_departments.png")
    with open(path, "rb") as f:
        header = f.read(8)
    assert header == PNG_HEADER, "top10_departments.png is not a valid PNG"


def test_top5_boxplot_is_valid_png():
    path = os.path.join(APP_DIR, "top5_boxplot.png")
    with open(path, "rb") as f:
        header = f.read(8)
    assert header == PNG_HEADER, "top5_boxplot.png is not a valid PNG"


# ===========================================================================
# 3. SUMMARY STATISTICS CSV – STRUCTURE
# ===========================================================================

REQUIRED_COLUMNS = ["Department", "mean", "median", "min", "max", "count"]

# Pre-computed expected values from the input data (238 salaried + 5 hourly = 239 rows)
# Sorted by mean descending
EXPECTED_STATS = [
    {"Department": "BUILDINGS",     "mean": 113506.00, "median": 106104.0, "min": 101442.0, "max": 132972.0, "count": 3},
    {"Department": "WATER MGMT",    "mean": 98164.57,  "median": 95472.0,  "min": 71780.0,  "max": 132972.0, "count": 7},
    {"Department": "AVIATION",      "mean": 96381.33,  "median": 91520.0,  "min": 91520.0,  "max": 106104.0, "count": 3},
    {"Department": "FIRE",          "mean": 93312.58,  "median": 91764.0,  "min": 91764.0,  "max": 118608.0, "count": 62},
    {"Department": "FINANCE",       "mean": 86742.00,  "median": 61950.0,  "min": 53076.0,  "max": 169992.0, "count": 4},
    {"Department": "POLICE",        "mean": 82211.38,  "median": 84054.0,  "min": 18387.2,  "max": 118608.0, "count": 145},
    {"Department": "TRANSPORTN",    "mean": 77262.13,  "median": 92524.0,  "min": 20654.4,  "max": 118608.0, "count": 3},
    {"Department": "STREETS & SAN", "mean": 67085.00,  "median": 65520.0,  "min": 65520.0,  "max": 71780.0,  "count": 12},
]


def test_summary_csv_has_header_row():
    path = os.path.join(APP_DIR, "summary_statistics.csv")
    header, _ = _read_csv_rows(path)
    for col in REQUIRED_COLUMNS:
        assert col in header, f"Missing column '{col}' in summary_statistics.csv header. Got: {header}"


def test_summary_csv_has_correct_row_count():
    """Must have exactly 8 department rows (one per department)."""
    path = os.path.join(APP_DIR, "summary_statistics.csv")
    _, rows = _read_csv_rows(path)
    assert len(rows) == 8, f"Expected 8 department rows, got {len(rows)}"


def test_summary_csv_sorted_by_mean_descending():
    """Rows must be sorted by mean in descending order."""
    path = os.path.join(APP_DIR, "summary_statistics.csv")
    header, rows = _read_csv_rows(path)
    mean_idx = header.index("mean")
    means = [float(r[mean_idx]) for r in rows]
    for i in range(len(means) - 1):
        assert means[i] >= means[i + 1], (
            f"Rows not sorted by mean descending: {means[i]} < {means[i+1]}"
        )


def test_summary_csv_departments_match():
    """All 8 expected departments must appear."""
    path = os.path.join(APP_DIR, "summary_statistics.csv")
    header, rows = _read_csv_rows(path)
    dept_idx = header.index("Department")
    actual_depts = {r[dept_idx].strip() for r in rows}
    expected_depts = {e["Department"] for e in EXPECTED_STATS}
    assert actual_depts == expected_depts, (
        f"Department mismatch.\nExpected: {expected_depts}\nGot: {actual_depts}"
    )


def test_summary_csv_mean_values():
    """Per-department mean values must be close to expected."""
    path = os.path.join(APP_DIR, "summary_statistics.csv")
    header, rows = _read_csv_rows(path)
    dept_idx = header.index("Department")
    mean_idx = header.index("mean")
    actual = {r[dept_idx].strip(): float(r[mean_idx]) for r in rows}
    for exp in EXPECTED_STATS:
        dept = exp["Department"]
        assert dept in actual, f"Department '{dept}' missing from CSV"
        assert _close(actual[dept], exp["mean"]), (
            f"{dept} mean: expected {exp['mean']}, got {actual[dept]}"
        )


def test_summary_csv_median_values():
    """Per-department median values must be close to expected."""
    path = os.path.join(APP_DIR, "summary_statistics.csv")
    header, rows = _read_csv_rows(path)
    dept_idx = header.index("Department")
    med_idx = header.index("median")
    actual = {r[dept_idx].strip(): float(r[med_idx]) for r in rows}
    for exp in EXPECTED_STATS:
        dept = exp["Department"]
        assert _close(actual[dept], exp["median"]), (
            f"{dept} median: expected {exp['median']}, got {actual[dept]}"
        )


def test_summary_csv_min_values():
    """Per-department min values must be close to expected."""
    path = os.path.join(APP_DIR, "summary_statistics.csv")
    header, rows = _read_csv_rows(path)
    dept_idx = header.index("Department")
    min_idx = header.index("min")
    actual = {r[dept_idx].strip(): float(r[min_idx]) for r in rows}
    for exp in EXPECTED_STATS:
        dept = exp["Department"]
        assert _close(actual[dept], exp["min"]), (
            f"{dept} min: expected {exp['min']}, got {actual[dept]}"
        )


def test_summary_csv_max_values():
    """Per-department max values must be close to expected."""
    path = os.path.join(APP_DIR, "summary_statistics.csv")
    header, rows = _read_csv_rows(path)
    dept_idx = header.index("Department")
    max_idx = header.index("max")
    actual = {r[dept_idx].strip(): float(r[max_idx]) for r in rows}
    for exp in EXPECTED_STATS:
        dept = exp["Department"]
        assert _close(actual[dept], exp["max"]), (
            f"{dept} max: expected {exp['max']}, got {actual[dept]}"
        )


def test_summary_csv_count_values():
    """Per-department employee counts must be exact."""
    path = os.path.join(APP_DIR, "summary_statistics.csv")
    header, rows = _read_csv_rows(path)
    dept_idx = header.index("Department")
    count_idx = header.index("count")
    actual = {r[dept_idx].strip(): int(float(r[count_idx])) for r in rows}
    for exp in EXPECTED_STATS:
        dept = exp["Department"]
        assert actual[dept] == exp["count"], (
            f"{dept} count: expected {exp['count']}, got {actual[dept]}"
        )


def test_summary_csv_police_min_reflects_hourly():
    """POLICE min must reflect hourly employees (17.68 * 20 * 52 = 18387.2), not salaried min."""
    path = os.path.join(APP_DIR, "summary_statistics.csv")
    header, rows = _read_csv_rows(path)
    dept_idx = header.index("Department")
    min_idx = header.index("min")
    for r in rows:
        if r[dept_idx].strip() == "POLICE":
            police_min = float(r[min_idx])
            # Must be close to 18387.2 (hourly employee), NOT 45708 or 80778 (salaried)
            assert _close(police_min, 18387.2), (
                f"POLICE min should be ~18387.2 (hourly employee), got {police_min}. "
                "Hourly pay must be computed as Hourly Rate * Typical Hours * 52."
            )
            return
    assert False, "POLICE department not found in summary_statistics.csv"


# ===========================================================================
# 4. SUMMARY REPORT – LABELS & VALUES
# ===========================================================================

def test_report_contains_required_labels():
    """summary_report.txt must contain all required label strings."""
    path = os.path.join(APP_DIR, "summary_report.txt")
    text = _read_text(path)
    required_labels = [
        "Total Employees:",
        "Unique Departments:",
        "Overall Mean:",
        "Overall Median:",
        "Top 5 Departments by Average Pay:",
    ]
    for label in required_labels:
        assert label in text, f"Missing required label '{label}' in summary_report.txt"


def test_report_total_employees():
    """Total Employees must be 239."""
    path = os.path.join(APP_DIR, "summary_report.txt")
    text = _read_text(path)
    for line in text.splitlines():
        if "Total Employees:" in line:
            val = int(line.split("Total Employees:")[-1].strip())
            assert val == 239, f"Total Employees: expected 239, got {val}"
            return
    assert False, "Could not find 'Total Employees:' line"


def test_report_unique_departments():
    """Unique Departments must be 8."""
    path = os.path.join(APP_DIR, "summary_report.txt")
    text = _read_text(path)
    for line in text.splitlines():
        if "Unique Departments:" in line:
            val = int(line.split("Unique Departments:")[-1].strip())
            assert val == 8, f"Unique Departments: expected 8, got {val}"
            return
    assert False, "Could not find 'Unique Departments:' line"


def test_report_overall_mean():
    """Overall Mean must be close to 85383.34."""
    path = os.path.join(APP_DIR, "summary_report.txt")
    text = _read_text(path)
    for line in text.splitlines():
        if "Overall Mean:" in line:
            val = _parse_float(line.split("Overall Mean:")[-1])
            assert _close(val, 85383.34), (
                f"Overall Mean: expected ~85383.34, got {val}"
            )
            return
    assert False, "Could not find 'Overall Mean:' line"


def test_report_overall_median():
    """Overall Median must be close to 84054.0."""
    path = os.path.join(APP_DIR, "summary_report.txt")
    text = _read_text(path)
    for line in text.splitlines():
        if "Overall Median:" in line:
            val = _parse_float(line.split("Overall Median:")[-1])
            assert _close(val, 84054.0), (
                f"Overall Median: expected ~84054.0, got {val}"
            )
            return
    assert False, "Could not find 'Overall Median:' line"


def test_report_top5_departments_listed():
    """The top 5 departments section must list exactly the correct 5 departments."""
    path = os.path.join(APP_DIR, "summary_report.txt")
    text = _read_text(path)

    expected_top5 = ["BUILDINGS", "WATER MGMT", "AVIATION", "FIRE", "FINANCE"]

    # Find the section after the header
    marker = "Top 5 Departments by Average Pay:"
    assert marker in text, f"Missing '{marker}' section header"
    section = text.split(marker, 1)[1].strip()
    lines = [l.strip() for l in section.splitlines() if l.strip()]

    # Each of the top 5 departments must appear somewhere in the section
    for dept in expected_top5:
        found = any(dept in line for line in lines)
        assert found, f"Department '{dept}' missing from Top 5 section"


def test_report_top5_values():
    """The average pay values in the top 5 section must be approximately correct."""
    path = os.path.join(APP_DIR, "summary_report.txt")
    text = _read_text(path)

    expected_top5_values = {
        "BUILDINGS": 113506.00,
        "WATER MGMT": 98164.57,
        "AVIATION": 96381.33,
        "FIRE": 93312.58,
        "FINANCE": 86742.00,
    }

    marker = "Top 5 Departments by Average Pay:"
    section = text.split(marker, 1)[1].strip()
    lines = [l.strip() for l in section.splitlines() if l.strip()]

    for dept, expected_val in expected_top5_values.items():
        for line in lines:
            if dept in line:
                # Extract numeric value after $ or : sign
                # Handle formats like "BUILDINGS: $113506.00" or "BUILDINGS: 113506.00"
                parts = line.split(":")
                if len(parts) >= 2:
                    val = _parse_float(parts[-1])
                    assert _close(val, expected_val), (
                        f"{dept} avg pay: expected ~{expected_val}, got {val}"
                    )
                break


# ===========================================================================
# 5. CROSS-VALIDATION: CSV vs REPORT CONSISTENCY
# ===========================================================================

def test_csv_and_report_mean_consistent():
    """The overall mean implied by the CSV data should match the report's Overall Mean."""
    csv_path = os.path.join(APP_DIR, "summary_statistics.csv")
    report_path = os.path.join(APP_DIR, "summary_report.txt")

    header, rows = _read_csv_rows(csv_path)
    mean_idx = header.index("mean")
    count_idx = header.index("count")

    # Weighted mean from per-department stats
    total_pay = sum(float(r[mean_idx]) * float(r[count_idx]) for r in rows)
    total_count = sum(float(r[count_idx]) for r in rows)
    csv_overall_mean = total_pay / total_count

    # Extract from report
    text = _read_text(report_path)
    report_mean = None
    for line in text.splitlines():
        if "Overall Mean:" in line:
            report_mean = _parse_float(line.split("Overall Mean:")[-1])
            break

    assert report_mean is not None, "Could not find Overall Mean in report"
    assert _close(csv_overall_mean, report_mean, rel_tol=0.02), (
        f"CSV-implied overall mean ({csv_overall_mean:.2f}) != report mean ({report_mean})"
    )
