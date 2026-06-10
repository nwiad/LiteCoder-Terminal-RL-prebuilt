"""
Tests for Job Market Skills Analysis Pipeline.

Validates /app/skills_ranked.csv against the expected output derived from
the input data in /app/input.jsonl, following the processing rules in
instruction.md.

Expected data (12 unique jobs after dedup):
  J001: $145,000 → 145000  | Python, SQL, Apache Spark, AWS
  J002: £95,000  → 123500  | JavaScript, React, Node.js, CSS
  J003: USD 160000 → 160000 | Python, TensorFlow, Kubernetes, Docker
  J004: €105,000 → 115500  | Kubernetes, Docker, Terraform, AWS
  J005: $130,000 → 130000  | Python, PostgreSQL, Docker, Node.js
  J006: £72,000  → 93600   | SQL, Python, Tableau, Excel
  J007: $120,000 → 120000  | JavaScript, React, TypeScript, CSS
  J008: €130,000 → 143000  | AWS, Terraform, Kubernetes, Docker
  J009: $155,000 → 155000  | Python, SQL, TensorFlow, Apache Spark
  J010: £110,000 → 143000  | Kubernetes, Docker, AWS, Terraform
  J011: USD 125000 → 125000 | TypeScript, React, Node.js, PostgreSQL
  J012: €48,000  → 52800   | SQL, Excel, Tableau, Python
"""

import csv
import os

OUTPUT_PATH = "/app/skills_ranked.csv"

# ── Reference data ──────────────────────────────────────────────────────
# skill -> (expected_count, expected_avg_salary)
EXPECTED = {
    "Python":       (6, 122733),
    "Docker":       (5, 138300),
    "Kubernetes":   (4, 140375),
    "AWS":          (4, 136625),
    "SQL":          (4, 111600),
    "Terraform":    (3, 133833),
    "Node.js":      (3, 126167),
    "React":        (3, 122833),
    "TensorFlow":   (2, 157500),
    "Apache Spark": (2, 150000),
    "PostgreSQL":   (2, 127500),
    "TypeScript":   (2, 122500),
    "JavaScript":   (2, 121750),
    "CSS":          (2, 121750),
    "Tableau":      (2, 73200),
    "Excel":        (2, 73200),
}

SALARY_TOLERANCE = 2  # allow ±2 for rounding differences


def _load_csv():
    """Load the output CSV and return (header, rows) where rows is a list of dicts."""
    assert os.path.isfile(OUTPUT_PATH), f"Output file not found: {OUTPUT_PATH}"
    with open(OUTPUT_PATH, "r", newline="") as f:
        content = f.read()
    assert len(content.strip()) > 0, "Output file is empty"
    lines = content.strip().splitlines()
    assert len(lines) > 1, "Output file has no data rows (only header or empty)"
    reader = csv.DictReader(lines)
    rows = list(reader)
    return reader.fieldnames, rows


# ── Test: file exists and is non-empty ──────────────────────────────────
def test_output_file_exists():
    assert os.path.isfile(OUTPUT_PATH), f"Expected output at {OUTPUT_PATH}"
    size = os.path.getsize(OUTPUT_PATH)
    assert size > 50, f"Output file suspiciously small ({size} bytes)"


# ── Test: correct CSV header ────────────────────────────────────────────
def test_csv_header():
    header, _ = _load_csv()
    expected_cols = ["skill", "count", "avg_salary"]
    cleaned = [c.strip().lower() for c in header]
    assert cleaned == expected_cols, (
        f"Header mismatch. Expected {expected_cols}, got {header}"
    )


# ── Test: correct number of skills (rows) ──────────────────────────────
def test_row_count():
    _, rows = _load_csv()
    assert len(rows) == 16, (
        f"Expected 16 skill rows, got {len(rows)}. "
        "Check deduplication, skill standardization, and aggregation."
    )


# ── Test: all expected skills are present ───────────────────────────────
def test_all_skills_present():
    _, rows = _load_csv()
    found_skills = {r["skill"].strip() for r in rows}
    for skill in EXPECTED:
        assert skill in found_skills, (
            f"Missing skill '{skill}' in output. Found: {sorted(found_skills)}"
        )


# ── Test: no unexpected skills ──────────────────────────────────────────
def test_no_extra_skills():
    _, rows = _load_csv()
    found_skills = {r["skill"].strip() for r in rows}
    extra = found_skills - set(EXPECTED.keys())
    assert len(extra) == 0, (
        f"Unexpected skills in output: {extra}. "
        "Check skill standardization and HTML stripping."
    )


# ── Test: count values are correct for every skill ─────────────────────
def test_skill_counts():
    _, rows = _load_csv()
    for row in rows:
        skill = row["skill"].strip()
        if skill not in EXPECTED:
            continue  # caught by test_no_extra_skills
        actual_count = int(row["count"].strip())
        expected_count = EXPECTED[skill][0]
        assert actual_count == expected_count, (
            f"Count mismatch for '{skill}': expected {expected_count}, got {actual_count}"
        )


# ── Test: avg_salary values are correct (with tolerance) ───────────────
def test_avg_salaries():
    _, rows = _load_csv()
    for row in rows:
        skill = row["skill"].strip()
        if skill not in EXPECTED:
            continue
        actual_salary = int(row["avg_salary"].strip())
        expected_salary = EXPECTED[skill][1]
        assert abs(actual_salary - expected_salary) <= SALARY_TOLERANCE, (
            f"avg_salary mismatch for '{skill}': "
            f"expected {expected_salary} (±{SALARY_TOLERANCE}), got {actual_salary}"
        )


# ── Test: avg_salary values are integers (no decimals) ─────────────────
def test_avg_salary_is_integer():
    _, rows = _load_csv()
    for row in rows:
        val = row["avg_salary"].strip()
        assert "." not in val, (
            f"avg_salary should be integer, got '{val}' for skill '{row['skill']}'"
        )


# ── Test: count values are integers ────────────────────────────────────
def test_count_is_integer():
    _, rows = _load_csv()
    for row in rows:
        val = row["count"].strip()
        assert val.isdigit(), (
            f"count should be a positive integer, got '{val}' for skill '{row['skill']}'"
        )


# ── Test: primary sort order (by count descending) ─────────────────────
def test_sort_by_count_descending():
    _, rows = _load_csv()
    counts = [int(r["count"].strip()) for r in rows]
    for i in range(len(counts) - 1):
        assert counts[i] >= counts[i + 1], (
            f"Rows not sorted by count descending: "
            f"row {i} has count={counts[i]}, row {i+1} has count={counts[i+1]}"
        )


# ── Test: secondary sort (avg_salary desc within same count) ───────────
def test_sort_tiebreaker_avg_salary():
    """Within groups of the same count, avg_salary should be descending."""
    _, rows = _load_csv()
    # Group consecutive rows by count
    i = 0
    while i < len(rows):
        current_count = int(rows[i]["count"].strip())
        group_salaries = []
        while i < len(rows) and int(rows[i]["count"].strip()) == current_count:
            group_salaries.append(int(rows[i]["avg_salary"].strip()))
            i += 1
        # Within this group, salaries should be non-increasing
        for j in range(len(group_salaries) - 1):
            assert group_salaries[j] >= group_salaries[j + 1], (
                f"Tiebreaker sort violated for count={current_count}: "
                f"salary {group_salaries[j]} followed by {group_salaries[j+1]}"
            )


# ── Test: top skill is Python with count=6 ─────────────────────────────
def test_top_skill_is_python():
    """Python should be the #1 ranked skill (highest count)."""
    _, rows = _load_csv()
    assert len(rows) > 0, "No rows in output"
    top_skill = rows[0]["skill"].strip()
    top_count = int(rows[0]["count"].strip())
    assert top_skill == "Python", f"Expected top skill 'Python', got '{top_skill}'"
    assert top_count == 6, f"Expected top count 6, got {top_count}"


# ── Test: second skill is Docker with count=5 ──────────────────────────
def test_second_skill_is_docker():
    _, rows = _load_csv()
    assert len(rows) > 1, "Not enough rows"
    second_skill = rows[1]["skill"].strip()
    second_count = int(rows[1]["count"].strip())
    assert second_skill == "Docker", f"Expected 2nd skill 'Docker', got '{second_skill}'"
    assert second_count == 5, f"Expected 2nd count 5, got {second_count}"


# ── Test: deduplication was applied (12 unique jobs) ────────────────────
def test_deduplication_applied():
    """
    If dedup was NOT applied, Python would have count > 6 because
    J001 and J005 appear twice each in the input.
    """
    _, rows = _load_csv()
    skill_counts = {r["skill"].strip(): int(r["count"].strip()) for r in rows}
    python_count = skill_counts.get("Python", 0)
    assert python_count == 6, (
        f"Python count is {python_count}, expected 6. "
        "Deduplication may not have been applied correctly."
    )
    docker_count = skill_counts.get("Docker", 0)
    assert docker_count == 5, (
        f"Docker count is {docker_count}, expected 5. "
        "Deduplication may not have been applied correctly."
    )


# ── Test: HTML stripping was applied ────────────────────────────────────
def test_no_html_in_skills():
    """Skill names should not contain any HTML tags."""
    _, rows = _load_csv()
    import re
    for row in rows:
        skill = row["skill"].strip()
        assert not re.search(r"<[^>]+>", skill), (
            f"HTML tag found in skill name: '{skill}'"
        )


# ── Test: currency conversion correctness (spot-check EUR) ─────────────
def test_eur_conversion():
    """
    Tableau appears only in J006 (£72000→93600) and J012 (€48000→52800).
    avg = (93600+52800)/2 = 73200
    This validates both GBP and EUR conversion.
    """
    _, rows = _load_csv()
    skill_data = {r["skill"].strip(): int(r["avg_salary"].strip()) for r in rows}
    tableau_salary = skill_data.get("Tableau", 0)
    assert abs(tableau_salary - 73200) <= SALARY_TOLERANCE, (
        f"Tableau avg_salary={tableau_salary}, expected 73200. "
        "Check currency conversion (GBP=1.30, EUR=1.10)."
    )


# ── Test: GBP conversion correctness ───────────────────────────────────
def test_gbp_conversion():
    """
    JavaScript appears in J002 (£95000→123500) and J007 ($120000→120000).
    avg = (123500+120000)/2 = 121750
    """
    _, rows = _load_csv()
    skill_data = {r["skill"].strip(): int(r["avg_salary"].strip()) for r in rows}
    js_salary = skill_data.get("JavaScript", 0)
    assert abs(js_salary - 121750) <= SALARY_TOLERANCE, (
        f"JavaScript avg_salary={js_salary}, expected 121750. "
        "Check GBP conversion (£95000 * 1.30 = 123500)."
    )


# ── Test: skill standardization (postgres → PostgreSQL) ────────────────
def test_skill_standardization():
    """
    'postgres' in input should become 'PostgreSQL' in output.
    'kubernetes' should become 'Kubernetes', etc.
    """
    _, rows = _load_csv()
    found_skills = {r["skill"].strip() for r in rows}
    # These raw forms should NOT appear
    raw_forms = {"postgres", "Postgres", "POSTGRES", "sql", "python",
                 "javascript", "node.js", "kubernetes", "typescript",
                 "tensorflow", "apache spark", "tableau", "docker",
                 "react", "aws", "terraform", "excel", "css"}
    for raw in raw_forms:
        assert raw not in found_skills, (
            f"Raw/unstandardized skill '{raw}' found in output. "
            "Skill names should be canonicalized."
        )
    # Canonical forms SHOULD appear
    canonical = {"PostgreSQL", "SQL", "Python", "JavaScript", "Node.js",
                 "Kubernetes", "TypeScript", "TensorFlow", "Apache Spark",
                 "Tableau", "Docker", "React", "AWS", "Terraform", "Excel", "CSS"}
    for c in canonical:
        assert c in found_skills, f"Canonical skill '{c}' missing from output"
