"""
Tests for GitHub Trending Repo Analysis task.
Validates /app/repos.db (SQLite) and /app/output.csv against the known input data.
"""

import os
import csv
import json
import sqlite3
from datetime import datetime
from collections import defaultdict

# Paths
DB_PATH = "/app/repos.db"
CSV_PATH = "/app/output.csv"
INPUT_PATH = "/app/input.json"
REFERENCE_TIME = datetime(2025, 7, 1, 0, 0, 0)

# ─── helpers ───────────────────────────────────────────────────────────────────

def _load_input():
    with open(INPUT_PATH, "r") as f:
        return json.load(f)


def _compute_expected_csv_rows(repos):
    """Recompute expected CSV output from raw input using the spec formula."""
    lang_groups = defaultdict(list)
    for repo in repos:
        lang = repo.get("language")
        if not lang:  # None, missing, or ""
            continue
        created_dt = datetime.strptime(repo["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        hours_since = (REFERENCE_TIME - created_dt).total_seconds() / 3600.0
        if hours_since <= 1.0:
            continue
        hotness = repo["stars"] / hours_since
        lang_groups[lang].append({"stars": repo["stars"], "hotness": hotness})

    results = []
    for lang, items in lang_groups.items():
        avg_hotness = sum(it["hotness"] for it in items) / len(items)
        repo_count = len(items)
        total_stars = sum(it["stars"] for it in items)
        results.append({
            "language": lang,
            "avg_hotness": round(avg_hotness, 4),
            "repo_count": repo_count,
            "total_stars": total_stars,
        })
    results.sort(key=lambda r: (-r["avg_hotness"], r["language"]))
    return results


# ─── TEST: output files exist ─────────────────────────────────────────────────

def test_db_file_exists():
    assert os.path.isfile(DB_PATH), f"SQLite database not found at {DB_PATH}"


def test_csv_file_exists():
    assert os.path.isfile(CSV_PATH), f"CSV report not found at {CSV_PATH}"


def test_db_file_not_empty():
    assert os.path.getsize(DB_PATH) > 0, "repos.db is empty (0 bytes)"


def test_csv_file_not_empty():
    assert os.path.getsize(CSV_PATH) > 0, "output.csv is empty (0 bytes)"


# ─── TEST: SQLite database structure ──────────────────────────────────────────

def test_db_has_repos_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='repos'"
    )
    tables = cur.fetchall()
    conn.close()
    assert len(tables) == 1, "Table 'repos' does not exist in repos.db"


def test_db_repos_table_columns():
    expected_cols = {"full_name", "language", "stars", "forks", "stars_today", "created_at"}
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("PRAGMA table_info(repos)")
    actual_cols = {row[1] for row in cur.fetchall()}
    conn.close()
    assert expected_cols.issubset(actual_cols), (
        f"Missing columns: {expected_cols - actual_cols}"
    )


def test_db_full_name_is_primary_key():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("PRAGMA table_info(repos)")
    rows = cur.fetchall()
    conn.close()
    pk_cols = [row[1] for row in rows if row[5] > 0]  # pk index > 0
    assert "full_name" in pk_cols, "full_name should be the PRIMARY KEY"


# ─── TEST: SQLite row count and content ───────────────────────────────────────

def test_db_row_count():
    """All 14 repos (including null/missing language) must be in the DB."""
    repos = _load_input()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT COUNT(*) FROM repos")
    count = cur.fetchone()[0]
    conn.close()
    assert count == len(repos), f"Expected {len(repos)} rows, got {count}"


def test_db_contains_all_repos():
    repos = _load_input()
    expected_names = {r["full_name"] for r in repos}
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT full_name FROM repos")
    actual_names = {row[0] for row in cur.fetchall()}
    conn.close()
    assert expected_names == actual_names, (
        f"Missing: {expected_names - actual_names}, Extra: {actual_names - expected_names}"
    )


def test_db_null_language_repos_stored():
    """Repos with null/missing/empty language must still be in the DB."""
    null_lang_names = {"some-user/unknown-tool", "anon/misc-scripts", "mystery/no-lang-repo"}
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT full_name FROM repos WHERE language IS NULL OR language = ''")
    actual = {row[0] for row in cur.fetchall()}
    conn.close()
    assert null_lang_names.issubset(actual), (
        f"Repos with null/empty language missing from DB: {null_lang_names - actual}"
    )


def test_db_spot_check_values():
    """Spot-check a known repo's values in the DB."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT stars, forks, stars_today, created_at FROM repos WHERE full_name = ?",
        ("tensorflow/tensorflow",)
    )
    row = cur.fetchone()
    conn.close()
    assert row is not None, "tensorflow/tensorflow not found in DB"
    stars, forks, stars_today, created_at = row
    assert stars == 185000, f"Expected stars=185000, got {stars}"
    assert forks == 74000, f"Expected forks=74000, got {forks}"
    assert stars_today == 320, f"Expected stars_today=320, got {stars_today}"
    assert created_at == "2015-11-07T01:19:20Z", f"Unexpected created_at: {created_at}"


# ─── TEST: CSV header ─────────────────────────────────────────────────────────

def test_csv_header():
    with open(CSV_PATH, "r") as f:
        reader = csv.reader(f)
        header = next(reader)
    expected = ["language", "avg_hotness", "repo_count", "total_stars"]
    assert header == expected, f"CSV header mismatch: expected {expected}, got {header}"


# ─── TEST: CSV row count ──────────────────────────────────────────────────────

def test_csv_row_count():
    """
    Expected languages in CSV: Python, TypeScript, Rust, C, JavaScript, Go.
    'newdev/fresh-project' (Go, 0.5h) is excluded, but golang/go remains → Go appears.
    Null/empty/missing language repos excluded.
    """
    expected = _compute_expected_csv_rows(_load_input())
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == len(expected), (
        f"Expected {len(expected)} data rows, got {len(rows)}"
    )


# ─── TEST: CSV languages present ──────────────────────────────────────────────

def test_csv_languages_present():
    """Exactly the right set of languages should appear."""
    expected = _compute_expected_csv_rows(_load_input())
    expected_langs = {r["language"] for r in expected}
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        actual_langs = {row["language"].strip() for row in reader}
    assert expected_langs == actual_langs, (
        f"Expected languages {expected_langs}, got {actual_langs}"
    )


def test_csv_excludes_null_empty_missing_languages():
    """Repos with null, empty, or missing language must NOT appear in CSV."""
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lang = row["language"].strip()
            assert lang != "", "Empty language found in CSV"
            assert lang.lower() != "null", "Literal 'null' language found in CSV"
            assert lang.lower() != "none", "Literal 'None' language found in CSV"


def test_csv_excludes_short_lived_only_language():
    """
    newdev/fresh-project (Go, 0.5h) should be excluded.
    But golang/go (Go, many hours) should keep Go in the CSV.
    Verify Go appears with repo_count=1 (not 2).
    """
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        go_rows = [r for r in reader if r["language"].strip() == "Go"]
    assert len(go_rows) == 1, "Go should appear exactly once in CSV"
    assert int(go_rows[0]["repo_count"]) == 1, (
        f"Go repo_count should be 1 (fresh-project excluded), got {go_rows[0]['repo_count']}"
    )


# ─── TEST: CSV sort order ─────────────────────────────────────────────────────

def test_csv_sort_order_descending_hotness():
    """Rows must be sorted by avg_hotness descending."""
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    hotness_values = [float(r["avg_hotness"]) for r in rows]
    for i in range(len(hotness_values) - 1):
        assert hotness_values[i] >= hotness_values[i + 1], (
            f"Sort violation at row {i}: {hotness_values[i]} < {hotness_values[i+1]}"
        )


def test_csv_first_language_is_python():
    """Python should have the highest avg_hotness given the input data."""
    expected = _compute_expected_csv_rows(_load_input())
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        first_row = next(reader)
    assert first_row["language"].strip() == expected[0]["language"], (
        f"First language should be {expected[0]['language']}, got {first_row['language']}"
    )


# ─── TEST: CSV numeric values (core correctness) ─────────────────────────────

def test_csv_avg_hotness_values():
    """Verify avg_hotness for each language matches expected computation."""
    expected = _compute_expected_csv_rows(_load_input())
    expected_map = {r["language"]: r["avg_hotness"] for r in expected}

    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lang = row["language"].strip()
            actual_val = float(row["avg_hotness"])
            assert lang in expected_map, f"Unexpected language in CSV: {lang}"
            exp_val = expected_map[lang]
            assert abs(actual_val - exp_val) < 0.0015, (
                f"{lang}: avg_hotness expected ~{exp_val}, got {actual_val}"
            )


def test_csv_repo_count_values():
    """Verify repo_count for each language."""
    expected = _compute_expected_csv_rows(_load_input())
    expected_map = {r["language"]: r["repo_count"] for r in expected}

    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lang = row["language"].strip()
            actual_count = int(row["repo_count"])
            assert lang in expected_map, f"Unexpected language: {lang}"
            assert actual_count == expected_map[lang], (
                f"{lang}: repo_count expected {expected_map[lang]}, got {actual_count}"
            )


def test_csv_total_stars_values():
    """Verify total_stars for each language."""
    expected = _compute_expected_csv_rows(_load_input())
    expected_map = {r["language"]: r["total_stars"] for r in expected}

    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lang = row["language"].strip()
            actual_stars = int(row["total_stars"])
            assert lang in expected_map, f"Unexpected language: {lang}"
            assert actual_stars == expected_map[lang], (
                f"{lang}: total_stars expected {expected_map[lang]}, got {actual_stars}"
            )


# ─── TEST: CSV formatting ────────────────────────────────────────────────────

def test_csv_avg_hotness_four_decimal_places():
    """avg_hotness must be formatted to exactly 4 decimal places."""
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = row["avg_hotness"].strip()
            assert "." in val, f"avg_hotness missing decimal point: {val}"
            decimal_part = val.split(".")[1]
            assert len(decimal_part) == 4, (
                f"avg_hotness should have 4 decimal places, got '{val}' "
                f"({len(decimal_part)} decimals)"
            )


def test_csv_repo_count_is_integer():
    """repo_count values must be valid integers (no decimals)."""
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = row["repo_count"].strip()
            assert val.isdigit(), f"repo_count is not a valid integer: '{val}'"


def test_csv_total_stars_is_integer():
    """total_stars values must be valid integers (no decimals)."""
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = row["total_stars"].strip()
            assert val.isdigit(), f"total_stars is not a valid integer: '{val}'"

# __CONTINUE_HERE_5__
