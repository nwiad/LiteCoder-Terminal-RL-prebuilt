"""
Tests for NYC SAT Demographic Analysis task.
Validates /app/output.json against expected results from the reference solution.
"""
import json
import os
import math

OUTPUT_PATH = "/app/output.json"

# ─── Expected reference values ───
EXPECTED_BEFORE = 254
EXPECTED_AFTER_CLEAN = 223
EXPECTED_AFTER_MERGE = 223

EXPECTED_BOROUGHS = {"Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"}

EXPECTED_BOROUGH_STATS = {
    "Bronx":         {"avg_sat_total": 1131.69, "avg_math": 373.77, "avg_reading": 382.54, "avg_writing": 375.38, "num_schools": 13},
    "Brooklyn":      {"avg_sat_total": 1159.80, "avg_math": 385.96, "avg_reading": 390.47, "avg_writing": 383.37, "num_schools": 76},
    "Manhattan":     {"avg_sat_total": 1236.31, "avg_math": 416.41, "avg_reading": 413.20, "avg_writing": 406.69, "num_schools": 59},
    "Queens":        {"avg_sat_total": 1190.35, "avg_math": 402.00, "avg_reading": 397.57, "avg_writing": 390.78, "num_schools": 65},
    "Staten Island": {"avg_sat_total": 1280.90, "avg_math": 423.60, "avg_reading": 432.20, "avg_writing": 425.10, "num_schools": 10},
}

EXPECTED_CORRELATIONS = {
    "White Pct":      0.5960,
    "Black Pct":     -0.5808,
    "Hispanic Pct":  -0.6045,
    "Asian Pct":      0.6453,
    "Free Lunch Pct":-0.7654,
    "ELL Pct":       -0.2781,
}

EXPECTED_TOP1 = {"DBN": "02M475", "School Name": "Stuyvesant High School", "Borough": "Manhattan", "SAT Total": 2096}
EXPECTED_BOTTOM1 = {"DBN": "02M520", "School Name": "Murry Bergtraum High School for Business Careers", "Borough": "Manhattan", "SAT Total": 1072}

EXPECTED_TOP10_DBNS = ["02M475", "15K443", "25Q525", "25Q550", "31R063", "02M449", "01M539", "30Q580", "02M416", "02M418"]
EXPECTED_BOTTOM10_DBNS = ["02M520", "10X386", "14K071", "14K477", "16K393", "16K455", "17K489", "19K409", "19K431", "19K504"]

EXPECTED_TOP10_SCORES = [2096, 1784, 1784, 1784, 1784, 1700, 1621, 1621, 1523, 1506]
EXPECTED_BOTTOM10_SCORES = [1072, 1072, 1072, 1072, 1072, 1072, 1072, 1072, 1072, 1072]

# ─── Helpers ───
def load_output():
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)

def approx(a, b, tol=0.05):
    """Check if two floats are close within absolute tolerance."""
    return abs(a - b) <= tol

# ═══════════════════════════════════════════════════════════
# 1. FILE EXISTENCE & BASIC STRUCTURE
# ═══════════════════════════════════════════════════════════

def test_output_file_exists():
    """output.json must exist."""
    assert os.path.isfile(OUTPUT_PATH), f"Output file not found at {OUTPUT_PATH}"


def test_output_is_valid_json():
    """output.json must be parseable JSON."""
    data = load_output()
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_top_level_keys():
    """All required top-level keys must be present."""
    data = load_output()
    required = {
        "total_schools_before_cleaning",
        "total_schools_after_cleaning",
        "total_schools_after_merge",
        "borough_stats",
        "correlations",
        "top_10_schools",
        "bottom_10_schools",
    }
    missing = required - set(data.keys())
    assert not missing, f"Missing top-level keys: {missing}"


# ═══════════════════════════════════════════════════════════
# 2. SCHOOL COUNTS
# ═══════════════════════════════════════════════════════════

def test_total_schools_before_cleaning():
    """Raw SAT CSV has 254 data rows."""
    data = load_output()
    assert data["total_schools_before_cleaning"] == EXPECTED_BEFORE, \
        f"Expected {EXPECTED_BEFORE}, got {data['total_schools_before_cleaning']}"


def test_total_schools_after_cleaning():
    """After removing 's' rows, 223 schools remain."""
    data = load_output()
    assert data["total_schools_after_cleaning"] == EXPECTED_AFTER_CLEAN, \
        f"Expected {EXPECTED_AFTER_CLEAN}, got {data['total_schools_after_cleaning']}"


def test_total_schools_after_merge():
    """Inner join yields 223 schools."""
    data = load_output()
    assert data["total_schools_after_merge"] == EXPECTED_AFTER_MERGE, \
        f"Expected {EXPECTED_AFTER_MERGE}, got {data['total_schools_after_merge']}"


def test_cleaning_reduces_count():
    """Cleaning must remove at least some rows (there are 's' values in data)."""
    data = load_output()
    assert data["total_schools_after_cleaning"] < data["total_schools_before_cleaning"], \
        "Cleaning should reduce the school count"


# ═══════════════════════════════════════════════════════════
# 3. BOROUGH-LEVEL ANALYSIS
# ═══════════════════════════════════════════════════════════

def test_borough_stats_all_boroughs_present():
    """All 5 NYC boroughs must appear in borough_stats."""
    data = load_output()
    actual = set(data["borough_stats"].keys())
    assert actual == EXPECTED_BOROUGHS, f"Expected boroughs {EXPECTED_BOROUGHS}, got {actual}"


def test_borough_stats_num_schools():
    """Each borough must have the correct number of schools."""
    data = load_output()
    for borough, expected in EXPECTED_BOROUGH_STATS.items():
        actual_n = data["borough_stats"][borough]["num_schools"]
        assert actual_n == expected["num_schools"], \
            f"{borough}: expected num_schools={expected['num_schools']}, got {actual_n}"


def test_borough_stats_total_schools_sum():
    """Sum of num_schools across boroughs must equal total_schools_after_merge."""
    data = load_output()
    total = sum(b["num_schools"] for b in data["borough_stats"].values())
    assert total == data["total_schools_after_merge"], \
        f"Sum of borough num_schools ({total}) != total_schools_after_merge ({data['total_schools_after_merge']})"


def test_borough_stats_avg_sat_total():
    """Borough avg_sat_total values must match reference within tolerance."""
    data = load_output()
    for borough, expected in EXPECTED_BOROUGH_STATS.items():
        actual = data["borough_stats"][borough]["avg_sat_total"]
        assert approx(actual, expected["avg_sat_total"], tol=0.5), \
            f"{borough}: avg_sat_total expected ~{expected['avg_sat_total']}, got {actual}"


def test_borough_stats_avg_math():
    """Borough avg_math values must match reference within tolerance."""
    data = load_output()
    for borough, expected in EXPECTED_BOROUGH_STATS.items():
        actual = data["borough_stats"][borough]["avg_math"]
        assert approx(actual, expected["avg_math"], tol=0.5), \
            f"{borough}: avg_math expected ~{expected['avg_math']}, got {actual}"


def test_borough_stats_avg_reading():
    """Borough avg_reading values must match reference within tolerance."""
    data = load_output()
    for borough, expected in EXPECTED_BOROUGH_STATS.items():
        actual = data["borough_stats"][borough]["avg_reading"]
        assert approx(actual, expected["avg_reading"], tol=0.5), \
            f"{borough}: avg_reading expected ~{expected['avg_reading']}, got {actual}"


def test_borough_stats_avg_writing():
    """Borough avg_writing values must match reference within tolerance."""
    data = load_output()
    for borough, expected in EXPECTED_BOROUGH_STATS.items():
        actual = data["borough_stats"][borough]["avg_writing"]
        assert approx(actual, expected["avg_writing"], tol=0.5), \
            f"{borough}: avg_writing expected ~{expected['avg_writing']}, got {actual}"


def test_borough_stats_internal_consistency():
    """avg_sat_total should approximately equal avg_math + avg_reading + avg_writing."""
    data = load_output()
    for borough, stats in data["borough_stats"].items():
        component_sum = stats["avg_math"] + stats["avg_reading"] + stats["avg_writing"]
        assert approx(stats["avg_sat_total"], component_sum, tol=1.0), \
            f"{borough}: avg_sat_total ({stats['avg_sat_total']}) != sum of components ({component_sum})"


# ═══════════════════════════════════════════════════════════
# 4. CORRELATION ANALYSIS
# ═══════════════════════════════════════════════════════════

def test_correlations_all_keys_present():
    """All 6 demographic correlation keys must be present."""
    data = load_output()
    expected_keys = {"White Pct", "Black Pct", "Hispanic Pct", "Asian Pct", "Free Lunch Pct", "ELL Pct"}
    actual_keys = set(data["correlations"].keys())
    assert actual_keys == expected_keys, f"Expected keys {expected_keys}, got {actual_keys}"


def test_correlations_values():
    """Correlation values must match reference within tolerance."""
    data = load_output()
    for col, expected_r in EXPECTED_CORRELATIONS.items():
        actual_r = data["correlations"][col]
        assert approx(actual_r, expected_r, tol=0.01), \
            f"{col}: correlation expected ~{expected_r}, got {actual_r}"


def test_correlations_signs():
    """Correlation signs must be correct (positive for White/Asian, negative for others)."""
    data = load_output()
    assert data["correlations"]["White Pct"] > 0, "White Pct correlation should be positive"
    assert data["correlations"]["Asian Pct"] > 0, "Asian Pct correlation should be positive"
    assert data["correlations"]["Black Pct"] < 0, "Black Pct correlation should be negative"
    assert data["correlations"]["Hispanic Pct"] < 0, "Hispanic Pct correlation should be negative"
    assert data["correlations"]["Free Lunch Pct"] < 0, "Free Lunch Pct correlation should be negative"
    assert data["correlations"]["ELL Pct"] < 0, "ELL Pct correlation should be negative"


def test_correlations_range():
    """All correlations must be in [-1, 1]."""
    data = load_output()
    for col, val in data["correlations"].items():
        assert -1.0 <= val <= 1.0, f"{col}: correlation {val} out of [-1, 1] range"


def test_correlations_strongest_negative():
    """Free Lunch Pct should have the strongest negative correlation."""
    data = load_output()
    corrs = data["correlations"]
    free_lunch = corrs["Free Lunch Pct"]
    for col in ["Black Pct", "Hispanic Pct", "ELL Pct"]:
        assert free_lunch < corrs[col], \
            f"Free Lunch Pct ({free_lunch}) should be more negative than {col} ({corrs[col]})"


# ═══════════════════════════════════════════════════════════
# 5. TOP 10 SCHOOLS
# ═══════════════════════════════════════════════════════════

def test_top_10_length():
    """top_10_schools must contain exactly 10 entries."""
    data = load_output()
    assert len(data["top_10_schools"]) == 10, \
        f"Expected 10 top schools, got {len(data['top_10_schools'])}"


def test_top_10_required_fields():
    """Each top school entry must have DBN, School Name, Borough, SAT Total."""
    data = load_output()
    required = {"DBN", "School Name", "Borough", "SAT Total"}
    for i, school in enumerate(data["top_10_schools"]):
        missing = required - set(school.keys())
        assert not missing, f"top_10_schools[{i}] missing keys: {missing}"


def test_top_10_first_school():
    """The #1 school must be Stuyvesant with SAT Total 2096."""
    data = load_output()
    top1 = data["top_10_schools"][0]
    assert top1["DBN"] == EXPECTED_TOP1["DBN"], \
        f"Top school DBN: expected {EXPECTED_TOP1['DBN']}, got {top1['DBN']}"
    assert top1["SAT Total"] == EXPECTED_TOP1["SAT Total"], \
        f"Top school SAT Total: expected {EXPECTED_TOP1['SAT Total']}, got {top1['SAT Total']}"


def test_top_10_descending_order():
    """top_10_schools must be sorted descending by SAT Total."""
    data = load_output()
    scores = [s["SAT Total"] for s in data["top_10_schools"]]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], \
            f"top_10_schools not descending at index {i}: {scores[i]} < {scores[i+1]}"


def test_top_10_dbns():
    """Top 10 DBNs must match expected list (order matters for tiebreaking)."""
    data = load_output()
    actual_dbns = [s["DBN"] for s in data["top_10_schools"]]
    assert actual_dbns == EXPECTED_TOP10_DBNS, \
        f"Top 10 DBNs mismatch.\nExpected: {EXPECTED_TOP10_DBNS}\nGot:      {actual_dbns}"


def test_top_10_scores():
    """Top 10 SAT Total scores must match expected values."""
    data = load_output()
    actual_scores = [s["SAT Total"] for s in data["top_10_schools"]]
    assert actual_scores == EXPECTED_TOP10_SCORES, \
        f"Top 10 scores mismatch.\nExpected: {EXPECTED_TOP10_SCORES}\nGot:      {actual_scores}"


# ═══════════════════════════════════════════════════════════
# 6. BOTTOM 10 SCHOOLS
# ═══════════════════════════════════════════════════════════

def test_bottom_10_length():
    """bottom_10_schools must contain exactly 10 entries."""
    data = load_output()
    assert len(data["bottom_10_schools"]) == 10, \
        f"Expected 10 bottom schools, got {len(data['bottom_10_schools'])}"


def test_bottom_10_required_fields():
    """Each bottom school entry must have DBN, School Name, Borough, SAT Total."""
    data = load_output()
    required = {"DBN", "School Name", "Borough", "SAT Total"}
    for i, school in enumerate(data["bottom_10_schools"]):
        missing = required - set(school.keys())
        assert not missing, f"bottom_10_schools[{i}] missing keys: {missing}"


def test_bottom_10_first_school():
    """The lowest-ranked school must match expected."""
    data = load_output()
    bot1 = data["bottom_10_schools"][0]
    assert bot1["DBN"] == EXPECTED_BOTTOM1["DBN"], \
        f"Bottom school DBN: expected {EXPECTED_BOTTOM1['DBN']}, got {bot1['DBN']}"
    assert bot1["SAT Total"] == EXPECTED_BOTTOM1["SAT Total"], \
        f"Bottom school SAT Total: expected {EXPECTED_BOTTOM1['SAT Total']}, got {bot1['SAT Total']}"


def test_bottom_10_ascending_order():
    """bottom_10_schools must be sorted ascending by SAT Total."""
    data = load_output()
    scores = [s["SAT Total"] for s in data["bottom_10_schools"]]
    for i in range(len(scores) - 1):
        assert scores[i] <= scores[i + 1], \
            f"bottom_10_schools not ascending at index {i}: {scores[i]} > {scores[i+1]}"


def test_bottom_10_dbns():
    """Bottom 10 DBNs must match expected list (order matters for tiebreaking)."""
    data = load_output()
    actual_dbns = [s["DBN"] for s in data["bottom_10_schools"]]
    assert actual_dbns == EXPECTED_BOTTOM10_DBNS, \
        f"Bottom 10 DBNs mismatch.\nExpected: {EXPECTED_BOTTOM10_DBNS}\nGot:      {actual_dbns}"


def test_bottom_10_scores():
    """Bottom 10 SAT Total scores must match expected values."""
    data = load_output()
    actual_scores = [s["SAT Total"] for s in data["bottom_10_schools"]]
    assert actual_scores == EXPECTED_BOTTOM10_SCORES, \
        f"Bottom 10 scores mismatch.\nExpected: {EXPECTED_BOTTOM10_SCORES}\nGot:      {actual_scores}"


# ═══════════════════════════════════════════════════════════
# 7. CROSS-SECTION CONSISTENCY CHECKS
# ═══════════════════════════════════════════════════════════

def test_top_bottom_no_overlap():
    """Top 10 and bottom 10 should have no overlapping schools."""
    data = load_output()
    top_dbns = {s["DBN"] for s in data["top_10_schools"]}
    bot_dbns = {s["DBN"] for s in data["bottom_10_schools"]}
    overlap = top_dbns & bot_dbns
    assert not overlap, f"Schools appear in both top and bottom 10: {overlap}"


def test_top_scores_above_bottom_scores():
    """Lowest score in top 10 must be >= highest score in bottom 10."""
    data = load_output()
    min_top = min(s["SAT Total"] for s in data["top_10_schools"])
    max_bot = max(s["SAT Total"] for s in data["bottom_10_schools"])
    assert min_top >= max_bot, \
        f"Top 10 min ({min_top}) should be >= bottom 10 max ({max_bot})"


def test_sat_total_is_integer():
    """SAT Total in top/bottom schools should be integers (sum of 3 integer means)."""
    data = load_output()
    for label, schools in [("top_10_schools", data["top_10_schools"]),
                           ("bottom_10_schools", data["bottom_10_schools"])]:
        for i, s in enumerate(schools):
            val = s["SAT Total"]
            assert isinstance(val, int) or (isinstance(val, float) and val == int(val)), \
                f"{label}[{i}] SAT Total should be integer, got {val} ({type(val).__name__})"


def test_borough_values_in_schools():
    """Borough values in top/bottom schools must be valid NYC boroughs."""
    data = load_output()
    for label in ["top_10_schools", "bottom_10_schools"]:
        for i, s in enumerate(data[label]):
            assert s["Borough"] in EXPECTED_BOROUGHS, \
                f"{label}[{i}] has invalid borough: {s['Borough']}"
