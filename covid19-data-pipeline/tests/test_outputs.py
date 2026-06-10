"""
Tests for COVID-19 Data Processing and Analysis Pipeline.

Validates all 6 output files produced by the pipeline:
  1. /app/cleaned_data.csv  — cleaned, deduped, sorted CSV
  2. /app/summary.json      — per-country aggregate statistics
  3. /app/cases_trend.png   — time-series line chart
  4. /app/death_rate_chart.png — bar chart
  5. /app/vaccination_chart.png — vaccination line chart
  6. /app/report.txt        — plain-text report
"""

import os
import json
import csv
import struct
import math

# ── Paths ────────────────────────────────────────────────────────────
CLEANED_CSV = "/app/cleaned_data.csv"
SUMMARY_JSON = "/app/summary.json"
CASES_PNG = "/app/cases_trend.png"
DEATH_PNG = "/app/death_rate_chart.png"
VACC_PNG = "/app/vaccination_chart.png"
REPORT_TXT = "/app/report.txt"
INPUT_CSV = "/app/input.csv"

COUNTRIES = ["CountryA", "CountryB", "CountryC"]

# Expected summary values (pre-computed from input.csv after cleaning)
EXPECTED_SUMMARY = {
    "CountryA": {
        "total_cases": 54750,
        "total_deaths": 1302,
        "max_daily_cases": 800,
        "max_daily_deaths": 20,
        "death_rate": 0.0238,
        "vaccination_rate": 0.012,
    },
    "CountryB": {
        "total_cases": 23150,
        "total_deaths": 867,
        "max_daily_cases": 600,
        "max_daily_deaths": 13,
        "death_rate": 0.0375,
        "vaccination_rate": 0.004,
    },
    "CountryC": {
        "total_cases": 109450,
        "total_deaths": 3771,
        "max_daily_cases": 1500,
        "max_daily_deaths": 40,
        "death_rate": 0.0345,
        "vaccination_rate": 0.0227,
    },
}

# ── Helpers ──────────────────────────────────────────────────────────

def _png_dimensions(path):
    """Read width and height from a PNG file header (IHDR chunk)."""
    with open(path, "rb") as f:
        sig = f.read(8)
        assert sig[:4] == b"\x89PNG", "Not a valid PNG file"
        # Skip chunk length (4 bytes) and chunk type 'IHDR' (4 bytes)
        f.read(8)
        width = struct.unpack(">I", f.read(4))[0]
        height = struct.unpack(">I", f.read(4))[0]
    return width, height


def _close(a, b, rel_tol=1e-3, abs_tol=1e-4):
    """Fuzzy float comparison."""
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


# =====================================================================
# 1. CLEANED DATA CSV TESTS
# =====================================================================

class TestCleanedCSV:
    """Validate /app/cleaned_data.csv."""

    def test_file_exists(self):
        assert os.path.isfile(CLEANED_CSV), f"{CLEANED_CSV} not found"

    def test_file_not_empty(self):
        assert os.path.getsize(CLEANED_CSV) > 0, "cleaned_data.csv is empty"

    def test_has_correct_columns(self):
        with open(CLEANED_CSV) as f:
            reader = csv.DictReader(f)
            cols = set(reader.fieldnames)
        expected = {"date", "country", "new_cases", "new_deaths",
                    "total_cases", "total_deaths", "people_vaccinated", "population"}
        assert expected.issubset(cols), f"Missing columns: {expected - cols}"

    def test_duplicates_removed(self):
        """Input has 33 data rows (30 unique + 3 dupes). After dedup → 30."""
        with open(CLEANED_CSV) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 30, f"Expected 30 rows after dedup, got {len(rows)}"

    def test_sorted_by_country_then_date(self):
        with open(CLEANED_CSV) as f:
            rows = list(csv.DictReader(f))
        pairs = [(r["country"], r["date"]) for r in rows]
        assert pairs == sorted(pairs), "Rows not sorted by country asc, date asc"

    def test_no_negative_new_cases(self):
        with open(CLEANED_CSV) as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            val = int(float(r["new_cases"]))
            assert val >= 0, f"Negative new_cases found: {r}"

    def test_no_negative_new_deaths(self):
        with open(CLEANED_CSV) as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            val = int(float(r["new_deaths"]))
            assert val >= 0, f"Negative new_deaths found: {r}"

    def test_missing_values_filled(self):
        """No empty cells in numeric columns after cleaning."""
        numeric_cols = ["new_cases", "new_deaths", "total_cases",
                        "total_deaths", "people_vaccinated", "population"]
        with open(CLEANED_CSV) as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            for col in numeric_cols:
                val = r[col].strip()
                assert val != "", f"Empty value in {col} for row {r}"
                # Must be parseable as a number
                float(val)

    def test_ten_rows_per_country(self):
        with open(CLEANED_CSV) as f:
            rows = list(csv.DictReader(f))
        from collections import Counter
        counts = Counter(r["country"] for r in rows)
        for c in COUNTRIES:
            assert counts[c] == 10, f"{c} has {counts[c]} rows, expected 10"


# =====================================================================
# 2. SUMMARY JSON TESTS
# =====================================================================

class TestSummaryJSON:
    """Validate /app/summary.json."""

    def test_file_exists(self):
        assert os.path.isfile(SUMMARY_JSON), f"{SUMMARY_JSON} not found"

    def test_file_not_empty(self):
        assert os.path.getsize(SUMMARY_JSON) > 0, "summary.json is empty"

    def test_valid_json(self):
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        assert isinstance(data, list), "summary.json root must be a JSON array"

    def test_three_countries(self):
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        assert len(data) == 3, f"Expected 3 country entries, got {len(data)}"

    def test_sorted_alphabetically(self):
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        names = [entry["country"] for entry in data]
        assert names == sorted(names), f"Countries not sorted: {names}"

    def test_required_fields(self):
        required = {"country", "total_cases", "total_deaths",
                    "max_daily_cases", "max_daily_deaths",
                    "death_rate", "vaccination_rate"}
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        for entry in data:
            missing = required - set(entry.keys())
            assert not missing, f"Missing fields {missing} in {entry.get('country', '?')}"

    def test_country_names(self):
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        names = {entry["country"] for entry in data}
        assert names == set(COUNTRIES), f"Unexpected countries: {names}"

    def test_total_cases_values(self):
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        for entry in data:
            c = entry["country"]
            expected = EXPECTED_SUMMARY[c]["total_cases"]
            assert entry["total_cases"] == expected, \
                f"{c} total_cases: got {entry['total_cases']}, expected {expected}"

    def test_total_deaths_values(self):
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        for entry in data:
            c = entry["country"]
            expected = EXPECTED_SUMMARY[c]["total_deaths"]
            assert entry["total_deaths"] == expected, \
                f"{c} total_deaths: got {entry['total_deaths']}, expected {expected}"

    def test_max_daily_cases_values(self):
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        for entry in data:
            c = entry["country"]
            expected = EXPECTED_SUMMARY[c]["max_daily_cases"]
            assert entry["max_daily_cases"] == expected, \
                f"{c} max_daily_cases: got {entry['max_daily_cases']}, expected {expected}"

    def test_max_daily_deaths_values(self):
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        for entry in data:
            c = entry["country"]
            expected = EXPECTED_SUMMARY[c]["max_daily_deaths"]
            assert entry["max_daily_deaths"] == expected, \
                f"{c} max_daily_deaths: got {entry['max_daily_deaths']}, expected {expected}"

    def test_death_rate_values(self):
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        for entry in data:
            c = entry["country"]
            expected = EXPECTED_SUMMARY[c]["death_rate"]
            assert _close(entry["death_rate"], expected), \
                f"{c} death_rate: got {entry['death_rate']}, expected {expected}"

    def test_vaccination_rate_values(self):
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        for entry in data:
            c = entry["country"]
            expected = EXPECTED_SUMMARY[c]["vaccination_rate"]
            assert _close(entry["vaccination_rate"], expected), \
                f"{c} vaccination_rate: got {entry['vaccination_rate']}, expected {expected}"

    def test_integer_types_for_counts(self):
        """total_cases, total_deaths, max_daily_cases, max_daily_deaths must be ints."""
        with open(SUMMARY_JSON) as f:
            data = json.load(f)
        int_fields = ["total_cases", "total_deaths", "max_daily_cases", "max_daily_deaths"]
        for entry in data:
            for field in int_fields:
                val = entry[field]
                assert isinstance(val, int), \
                    f"{entry['country']}.{field} should be int, got {type(val).__name__}"


# =====================================================================
# 3. VISUALIZATION / PNG TESTS
# =====================================================================

class TestCasesTrendPNG:
    """Validate /app/cases_trend.png."""

    def test_file_exists(self):
        assert os.path.isfile(CASES_PNG), f"{CASES_PNG} not found"

    def test_file_not_empty(self):
        assert os.path.getsize(CASES_PNG) > 1000, \
            "cases_trend.png is suspiciously small (< 1 KB)"

    def test_valid_png(self):
        with open(CASES_PNG, "rb") as f:
            sig = f.read(8)
        assert sig[:4] == b"\x89PNG", "cases_trend.png is not a valid PNG"

    def test_minimum_dimensions(self):
        w, h = _png_dimensions(CASES_PNG)
        assert w >= 800 and h >= 600, \
            f"cases_trend.png is {w}x{h}, minimum 800x600 required"


class TestDeathRateChartPNG:
    """Validate /app/death_rate_chart.png."""

    def test_file_exists(self):
        assert os.path.isfile(DEATH_PNG), f"{DEATH_PNG} not found"

    def test_file_not_empty(self):
        assert os.path.getsize(DEATH_PNG) > 1000, \
            "death_rate_chart.png is suspiciously small (< 1 KB)"

    def test_valid_png(self):
        with open(DEATH_PNG, "rb") as f:
            sig = f.read(8)
        assert sig[:4] == b"\x89PNG", "death_rate_chart.png is not a valid PNG"

    def test_minimum_dimensions(self):
        w, h = _png_dimensions(DEATH_PNG)
        assert w >= 800 and h >= 600, \
            f"death_rate_chart.png is {w}x{h}, minimum 800x600 required"


class TestVaccinationChartPNG:
    """Validate /app/vaccination_chart.png."""

    def test_file_exists(self):
        assert os.path.isfile(VACC_PNG), f"{VACC_PNG} not found"

    def test_file_not_empty(self):
        assert os.path.getsize(VACC_PNG) > 1000, \
            "vaccination_chart.png is suspiciously small (< 1 KB)"

    def test_valid_png(self):
        with open(VACC_PNG, "rb") as f:
            sig = f.read(8)
        assert sig[:4] == b"\x89PNG", "vaccination_chart.png is not a valid PNG"

    def test_minimum_dimensions(self):
        w, h = _png_dimensions(VACC_PNG)
        assert w >= 800 and h >= 600, \
            f"vaccination_chart.png is {w}x{h}, minimum 800x600 required"


# =====================================================================
# 4. REPORT TXT TESTS
# =====================================================================

class TestReportTXT:
    """Validate /app/report.txt."""

    def test_file_exists(self):
        assert os.path.isfile(REPORT_TXT), f"{REPORT_TXT} not found"

    def test_file_not_empty(self):
        assert os.path.getsize(REPORT_TXT) > 0, "report.txt is empty"

    def test_header_line(self):
        with open(REPORT_TXT) as f:
            content = f.read()
        assert "COVID-19 Analysis Report" in content, \
            "report.txt missing header 'COVID-19 Analysis Report'"

    def test_footer_line(self):
        with open(REPORT_TXT) as f:
            content = f.read()
        assert "End of Report" in content, \
            "report.txt missing footer 'End of Report'"

    def test_all_countries_mentioned(self):
        with open(REPORT_TXT) as f:
            content = f.read()
        for c in COUNTRIES:
            assert c in content, f"Country '{c}' not found in report.txt"

    def test_countries_in_alphabetical_order(self):
        with open(REPORT_TXT) as f:
            content = f.read()
        positions = []
        for c in sorted(COUNTRIES):
            pos = content.find(c)
            assert pos >= 0, f"Country '{c}' not found in report"
            positions.append(pos)
        assert positions == sorted(positions), \
            "Countries not in alphabetical order in report.txt"

    def test_contains_total_cases(self):
        """Report must mention total cases for each country."""
        with open(REPORT_TXT) as f:
            content = f.read()
        for c in COUNTRIES:
            expected_val = str(EXPECTED_SUMMARY[c]["total_cases"])
            assert expected_val in content, \
                f"Total cases {expected_val} for {c} not found in report"

    def test_contains_total_deaths(self):
        """Report must mention total deaths for each country."""
        with open(REPORT_TXT) as f:
            content = f.read()
        for c in COUNTRIES:
            expected_val = str(EXPECTED_SUMMARY[c]["total_deaths"])
            assert expected_val in content, \
                f"Total deaths {expected_val} for {c} not found in report"

    def test_contains_death_rate(self):
        """Report must mention death rate for each country."""
        with open(REPORT_TXT) as f:
            content = f.read()
        for c in COUNTRIES:
            expected_val = str(EXPECTED_SUMMARY[c]["death_rate"])
            assert expected_val in content, \
                f"Death rate {expected_val} for {c} not found in report"

    def test_contains_vaccination_rate(self):
        """Report must mention vaccination rate for each country."""
        with open(REPORT_TXT) as f:
            content = f.read()
        for c in COUNTRIES:
            expected_val = str(EXPECTED_SUMMARY[c]["vaccination_rate"])
            assert expected_val in content, \
                f"Vaccination rate {expected_val} for {c} not found in report"

    def test_header_before_footer(self):
        with open(REPORT_TXT) as f:
            content = f.read()
        header_pos = content.find("COVID-19 Analysis Report")
        footer_pos = content.find("End of Report")
        assert header_pos < footer_pos, \
            "Header must appear before footer in report.txt"


# =====================================================================
# 5. CROSS-FILE CONSISTENCY TESTS
# =====================================================================

class TestCrossFileConsistency:
    """Verify that summary.json and cleaned_data.csv are consistent."""

    def test_summary_countries_match_csv_countries(self):
        with open(SUMMARY_JSON) as f:
            summary = json.load(f)
        summary_countries = {e["country"] for e in summary}

        with open(CLEANED_CSV) as f:
            rows = list(csv.DictReader(f))
        csv_countries = {r["country"] for r in rows}

        assert summary_countries == csv_countries, \
            f"Country mismatch: summary={summary_countries}, csv={csv_countries}"

    def test_max_total_cases_matches_csv(self):
        """summary total_cases should equal max(total_cases) from cleaned CSV."""
        import pandas as pd
        df = pd.read_csv(CLEANED_CSV)
        with open(SUMMARY_JSON) as f:
            summary = json.load(f)
        for entry in summary:
            c = entry["country"]
            csv_max = int(df[df["country"] == c]["total_cases"].max())
            assert entry["total_cases"] == csv_max, \
                f"{c}: summary total_cases={entry['total_cases']} != csv max={csv_max}"

    def test_max_daily_cases_matches_csv(self):
        """summary max_daily_cases should equal max(new_cases) from cleaned CSV."""
        import pandas as pd
        df = pd.read_csv(CLEANED_CSV)
        with open(SUMMARY_JSON) as f:
            summary = json.load(f)
        for entry in summary:
            c = entry["country"]
            csv_max = int(df[df["country"] == c]["new_cases"].max())
            assert entry["max_daily_cases"] == csv_max, \
                f"{c}: summary max_daily_cases={entry['max_daily_cases']} != csv max={csv_max}"
