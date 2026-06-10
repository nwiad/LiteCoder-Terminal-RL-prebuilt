"""
Tests for Reddit Market Basket Analysis task.
Validates all 4 output files: input.jsonl.gz, user_item_matrix.pkl,
association_rules.csv, and network.html.
"""

import os
import gzip
import json
import pickle
import csv
import re

# All output files live in /app
OUTPUT_DIR = "/app"


# =============================================================================
# Helper utilities
# =============================================================================

def read_gzip_jsonl(path):
    """Read a gzip-compressed JSONL file and return list of dicts."""
    records = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def read_csv_file(path):
    """Read a CSV file and return (header, rows)."""
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return header, rows


def read_html_file(path):
    """Read an HTML file and return its content as string."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# =============================================================================
# Test 1: File existence
# =============================================================================

def test_input_file_exists():
    path = os.path.join(OUTPUT_DIR, "input.jsonl.gz")
    assert os.path.isfile(path), f"Missing output file: {path}"
    assert os.path.getsize(path) > 0, f"File is empty: {path}"


def test_user_item_matrix_file_exists():
    path = os.path.join(OUTPUT_DIR, "user_item_matrix.pkl")
    assert os.path.isfile(path), f"Missing output file: {path}"
    assert os.path.getsize(path) > 0, f"File is empty: {path}"


def test_association_rules_file_exists():
    path = os.path.join(OUTPUT_DIR, "association_rules.csv")
    assert os.path.isfile(path), f"Missing output file: {path}"
    assert os.path.getsize(path) > 0, f"File is empty: {path}"


def test_network_html_file_exists():
    path = os.path.join(OUTPUT_DIR, "network.html")
    assert os.path.isfile(path), f"Missing output file: {path}"
    assert os.path.getsize(path) > 0, f"File is empty: {path}"


# =============================================================================
# Test 2: input.jsonl.gz — schema and data volume
# =============================================================================

def test_input_jsonl_is_valid_gzip():
    """File must be valid gzip-compressed JSONL."""
    path = os.path.join(OUTPUT_DIR, "input.jsonl.gz")
    try:
        records = read_gzip_jsonl(path)
    except Exception as e:
        assert False, f"Failed to read gzip JSONL: {e}"
    assert len(records) > 0, "input.jsonl.gz contains no records"


def test_input_jsonl_schema():
    """Each record must have 'author' and 'subreddit' string fields."""
    path = os.path.join(OUTPUT_DIR, "input.jsonl.gz")
    records = read_gzip_jsonl(path)
    # Check a sample of records (first 500 + last 500)
    sample = records[:500] + records[-500:] if len(records) > 1000 else records
    for i, rec in enumerate(sample):
        assert "author" in rec, f"Record {i} missing 'author' field"
        assert "subreddit" in rec, f"Record {i} missing 'subreddit' field"
        assert isinstance(rec["author"], str), f"Record {i} 'author' is not a string"
        assert isinstance(rec["subreddit"], str), f"Record {i} 'subreddit' is not a string"
        assert len(rec["author"].strip()) > 0, f"Record {i} has empty 'author'"
        assert len(rec["subreddit"].strip()) > 0, f"Record {i} has empty 'subreddit'"


def test_input_jsonl_minimum_records():
    """Must have at least 50,000 comment records."""
    path = os.path.join(OUTPUT_DIR, "input.jsonl.gz")
    records = read_gzip_jsonl(path)
    assert len(records) >= 50000, (
        f"Expected >= 50000 records, got {len(records)}"
    )


def test_input_jsonl_minimum_users():
    """Must have at least 200 unique users."""
    path = os.path.join(OUTPUT_DIR, "input.jsonl.gz")
    records = read_gzip_jsonl(path)
    users = set(r["author"] for r in records)
    assert len(users) >= 200, (
        f"Expected >= 200 unique users, got {len(users)}"
    )


def test_input_jsonl_minimum_subreddits():
    """Must have at least 30 unique subreddits."""
    path = os.path.join(OUTPUT_DIR, "input.jsonl.gz")
    records = read_gzip_jsonl(path)
    subs = set(r["subreddit"] for r in records)
    assert len(subs) >= 30, (
        f"Expected >= 30 unique subreddits, got {len(subs)}"
    )


# =============================================================================
# Test 3: user_item_matrix.pkl — valid pickle, binary DataFrame
# =============================================================================

def test_user_item_matrix_is_valid_pickle():
    """Must be a valid pickle file loadable as a pandas DataFrame."""
    import pandas as pd
    path = os.path.join(OUTPUT_DIR, "user_item_matrix.pkl")
    try:
        with open(path, "rb") as f:
            obj = pickle.load(f)
    except Exception as e:
        assert False, f"Failed to unpickle user_item_matrix.pkl: {e}"
    assert isinstance(obj, pd.DataFrame), (
        f"Expected pandas DataFrame, got {type(obj).__name__}"
    )


def test_user_item_matrix_shape():
    """Matrix must have reasonable dimensions (users x subreddits)."""
    import pandas as pd
    path = os.path.join(OUTPUT_DIR, "user_item_matrix.pkl")
    with open(path, "rb") as f:
        df = pickle.load(f)
    n_users, n_subs = df.shape
    # At least some users and subreddits after pruning
    assert n_users >= 50, f"Expected >= 50 users in matrix, got {n_users}"
    assert n_subs >= 5, f"Expected >= 5 subreddits in matrix, got {n_subs}"


def test_user_item_matrix_is_binary():
    """Matrix values must be binary (0/1 or True/False)."""
    import pandas as pd
    import numpy as np
    path = os.path.join(OUTPUT_DIR, "user_item_matrix.pkl")
    with open(path, "rb") as f:
        df = pickle.load(f)
    unique_vals = set(df.values.flatten())
    # Allow bool or int representations
    allowed = {True, False, 0, 1, 0.0, 1.0, np.True_, np.False_}
    unexpected = unique_vals - allowed
    assert len(unexpected) == 0, (
        f"Matrix contains non-binary values: {unexpected}"
    )


# =============================================================================
# Test 4: association_rules.csv — structure, columns, thresholds
# =============================================================================

def test_association_rules_csv_header():
    """CSV must have the required columns."""
    path = os.path.join(OUTPUT_DIR, "association_rules.csv")
    header, rows = read_csv_file(path)
    header_lower = [h.strip().lower() for h in header]
    required = ["antecedents", "consequents", "support", "confidence", "lift"]
    for col in required:
        assert col in header_lower, (
            f"Missing required column '{col}'. Found: {header}"
        )


def test_association_rules_csv_has_data_rows():
    """CSV must contain at least 1 rule row (beyond the header)."""
    path = os.path.join(OUTPUT_DIR, "association_rules.csv")
    header, rows = read_csv_file(path)
    assert len(rows) >= 1, (
        f"Expected at least 1 rule row, got {len(rows)}"
    )


def test_association_rules_csv_float_columns_parseable():
    """support, confidence, lift columns must be valid floats."""
    import pandas as pd
    path = os.path.join(OUTPUT_DIR, "association_rules.csv")
    df = pd.read_csv(path)
    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]
    for col in ["support", "confidence", "lift"]:
        try:
            vals = pd.to_numeric(df[col])
        except Exception as e:
            assert False, f"Column '{col}' contains non-numeric values: {e}"
        assert vals.notna().all(), f"Column '{col}' contains NaN values"


def test_association_rules_float_precision():
    """Float values must have at least 4 decimal places of precision."""
    path = os.path.join(OUTPUT_DIR, "association_rules.csv")
    header, rows = read_csv_file(path)
    header_lower = [h.strip().lower() for h in header]
    support_idx = header_lower.index("support")
    confidence_idx = header_lower.index("confidence")
    lift_idx = header_lower.index("lift")

    for row_num, row in enumerate(rows[:20]):  # Check first 20 rows
        for col_name, idx in [("support", support_idx),
                               ("confidence", confidence_idx),
                               ("lift", lift_idx)]:
            val_str = row[idx].strip().strip('"')
            # Must have a decimal point and at least 4 digits after it
            if "." in val_str:
                decimal_part = val_str.split(".")[1]
                assert len(decimal_part) >= 4, (
                    f"Row {row_num} '{col_name}' = '{val_str}' has "
                    f"only {len(decimal_part)} decimal places, need >= 4"
                )
            else:
                assert False, (
                    f"Row {row_num} '{col_name}' = '{val_str}' has no decimal point"
                )


def test_association_rules_lift_threshold():
    """All rules must have lift >= 1.5."""
    import pandas as pd
    path = os.path.join(OUTPUT_DIR, "association_rules.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    lifts = pd.to_numeric(df["lift"])
    violators = lifts[lifts < 1.5 - 1e-6]
    assert len(violators) == 0, (
        f"{len(violators)} rules have lift < 1.5. Min lift = {lifts.min():.6f}"
    )


def test_association_rules_confidence_threshold():
    """All rules must have confidence >= 0.30."""
    import pandas as pd
    path = os.path.join(OUTPUT_DIR, "association_rules.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    confs = pd.to_numeric(df["confidence"])
    violators = confs[confs < 0.30 - 1e-6]
    assert len(violators) == 0, (
        f"{len(violators)} rules have confidence < 0.30. "
        f"Min confidence = {confs.min():.6f}"
    )


def test_association_rules_antecedents_nonempty():
    """Antecedents and consequents must be non-empty strings."""
    import pandas as pd
    path = os.path.join(OUTPUT_DIR, "association_rules.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    for idx, row in df.iterrows():
        ant = str(row["antecedents"]).strip()
        con = str(row["consequents"]).strip()
        assert len(ant) > 0 and ant.lower() != "nan", (
            f"Row {idx} has empty antecedents"
        )
        assert len(con) > 0 and con.lower() != "nan", (
            f"Row {idx} has empty consequents"
        )


def test_association_rules_support_range():
    """Support values must be between 0 and 1 (exclusive)."""
    import pandas as pd
    path = os.path.join(OUTPUT_DIR, "association_rules.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    supports = pd.to_numeric(df["support"])
    assert (supports > 0).all(), "Some support values are <= 0"
    assert (supports <= 1.0).all(), "Some support values are > 1"


# =============================================================================
# Test 5: network.html — D3.js, SVG, force simulation, nodes, edges
# =============================================================================

def test_network_html_is_valid_html():
    """File must be valid HTML with basic structure."""
    path = os.path.join(OUTPUT_DIR, "network.html")
    content = read_html_file(path)
    content_lower = content.lower()
    assert "<html" in content_lower, "Missing <html> tag"
    assert "</html>" in content_lower, "Missing </html> closing tag"
    assert "<body" in content_lower, "Missing <body> tag"


def test_network_html_contains_d3_reference():
    """HTML must reference D3.js library."""
    path = os.path.join(OUTPUT_DIR, "network.html")
    content = read_html_file(path)
    # Check for D3 CDN link or inline d3 reference
    assert "d3" in content.lower(), (
        "No reference to D3.js found in network.html"
    )
    # Check for d3 script src or d3.js mention
    has_d3_cdn = bool(re.search(r'd3[./]', content, re.IGNORECASE))
    has_d3_var = "d3.select" in content or "d3.force" in content
    assert has_d3_cdn or has_d3_var, (
        "No D3.js CDN link or D3 API usage found"
    )


def test_network_html_has_force_simulation():
    """HTML must contain d3.forceSimulation for the force-directed layout."""
    path = os.path.join(OUTPUT_DIR, "network.html")
    content = read_html_file(path)
    # Allow various casings and spacing
    assert "forceSimulation" in content or "forcesimulation" in content.lower(), (
        "Missing d3.forceSimulation in network.html"
    )


def test_network_html_has_svg_or_canvas():
    """HTML must contain an SVG or canvas element for the graph."""
    path = os.path.join(OUTPUT_DIR, "network.html")
    content = read_html_file(path)
    content_lower = content.lower()
    has_svg = "<svg" in content_lower or '"svg"' in content_lower or "'svg'" in content_lower
    has_canvas = "<canvas" in content_lower or '"canvas"' in content_lower
    # Also check for D3 creating SVG dynamically via append("svg")
    has_d3_svg = 'append("svg")' in content or "append('svg')" in content
    assert has_svg or has_canvas or has_d3_svg, (
        "Missing <svg> or <canvas> element in network.html"
    )


def test_network_html_has_node_labels():
    """Nodes must have tooltips or labels showing subreddit names."""
    import pandas as pd
    path_html = os.path.join(OUTPUT_DIR, "network.html")
    path_csv = os.path.join(OUTPUT_DIR, "association_rules.csv")
    content = read_html_file(path_html)

    # Collect subreddit names from the rules CSV
    if not os.path.isfile(path_csv):
        assert False, "Cannot verify node labels: association_rules.csv missing"

    df = pd.read_csv(path_csv)
    df.columns = [c.strip().lower() for c in df.columns]
    all_subs = set()
    for _, row in df.iterrows():
        for item in str(row["antecedents"]).split(","):
            all_subs.add(item.strip())
        for item in str(row["consequents"]).split(","):
            all_subs.add(item.strip())

    # At least some subreddit names should appear in the HTML
    found = sum(1 for s in all_subs if s in content)
    assert found >= min(3, len(all_subs)), (
        f"Only {found}/{len(all_subs)} subreddit names found in HTML. "
        f"Nodes must have labels or tooltips with subreddit names."
    )


def test_network_html_has_edge_data():
    """Edges must encode support and lift (via data attributes, tooltip, or JS)."""
    path = os.path.join(OUTPUT_DIR, "network.html")
    content = read_html_file(path)
    content_lower = content.lower()
    # Check for support and lift being referenced in the HTML/JS
    has_support = "support" in content_lower
    has_lift = "lift" in content_lower
    assert has_support, (
        "No reference to 'support' found in network.html edge data"
    )
    assert has_lift, (
        "No reference to 'lift' found in network.html edge data"
    )


def test_network_html_self_contained():
    """HTML must be self-contained: CSS and JS inline (no local file refs)."""
    path = os.path.join(OUTPUT_DIR, "network.html")
    content = read_html_file(path)
    # Check that there's inline <style> or style= attributes
    has_style = "<style" in content.lower() or "style=" in content.lower()
    # Check that there's inline <script> content (not just CDN src)
    has_inline_script = bool(re.search(
        r'<script[^>]*>[\s\S]{50,}?</script>', content, re.IGNORECASE
    ))
    assert has_style, "No inline CSS found — HTML must be self-contained"
    assert has_inline_script, (
        "No substantial inline JavaScript found — HTML must be self-contained"
    )


def test_network_html_has_confidence_in_edges():
    """Edge weight should correspond to confidence."""
    path = os.path.join(OUTPUT_DIR, "network.html")
    content = read_html_file(path)
    content_lower = content.lower()
    assert "confidence" in content_lower, (
        "No reference to 'confidence' found in network.html — "
        "edge weight should correspond to confidence"
    )


# =============================================================================
# Test 6: Cross-file consistency
# =============================================================================

def test_rules_subreddits_exist_in_input():
    """Subreddits in association rules must exist in the input data."""
    path_csv = os.path.join(OUTPUT_DIR, "association_rules.csv")
    path_gz = os.path.join(OUTPUT_DIR, "input.jsonl.gz")
    if not (os.path.isfile(path_csv) and os.path.isfile(path_gz)):
        return  # Skip if files missing (caught by existence tests)

    import pandas as pd
    records = read_gzip_jsonl(path_gz)
    input_subs = set(r["subreddit"] for r in records)

    df = pd.read_csv(path_csv)
    df.columns = [c.strip().lower() for c in df.columns]
    rule_subs = set()
    for _, row in df.iterrows():
        for item in str(row["antecedents"]).split(","):
            rule_subs.add(item.strip())
        for item in str(row["consequents"]).split(","):
            rule_subs.add(item.strip())

    missing = rule_subs - input_subs
    assert len(missing) == 0, (
        f"Subreddits in rules not found in input data: {missing}"
    )
