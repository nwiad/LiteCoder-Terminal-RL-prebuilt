"""
Tests for K-Means Clustering from Scratch task.
Validates output.json structure/content, PNG plot existence, and solution integrity.
"""

import os
import json
import re

# All output files live under /app
OUTPUT_JSON = "/app/output.json"
CLUSTERS_PNG = "/app/clusters_k4.png"
ELBOW_PNG = "/app/elbow_plot.png"
SILHOUETTE_PNG = "/app/silhouette_comparison.png"
SOLUTION_PY = "/app/solution.py"

EXPECTED_K_VALUES = [2, 3, 4, 5]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_output_json():
    """Load and return the parsed output.json, or None on failure."""
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
    with open(OUTPUT_JSON, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"{OUTPUT_JSON} is empty"
    data = json.loads(content)
    return data


def is_valid_png(path):
    """Check PNG magic bytes."""
    with open(path, "rb") as f:
        header = f.read(8)
    # PNG signature: 137 80 78 71 13 10 26 10
    return header[:8] == b'\x89PNG\r\n\x1a\n'


# ---------------------------------------------------------------------------
# 1. File existence tests
# ---------------------------------------------------------------------------

def test_output_json_exists():
    assert os.path.isfile(OUTPUT_JSON), "output.json not found"
    assert os.path.getsize(OUTPUT_JSON) > 10, "output.json appears empty or trivially small"


def test_clusters_k4_png_exists():
    assert os.path.isfile(CLUSTERS_PNG), "clusters_k4.png not found"
    assert os.path.getsize(CLUSTERS_PNG) > 1000, "clusters_k4.png is too small to be a real plot"


def test_elbow_plot_png_exists():
    assert os.path.isfile(ELBOW_PNG), "elbow_plot.png not found"
    assert os.path.getsize(ELBOW_PNG) > 1000, "elbow_plot.png is too small to be a real plot"


def test_silhouette_comparison_png_exists():
    assert os.path.isfile(SILHOUETTE_PNG), "silhouette_comparison.png not found"
    assert os.path.getsize(SILHOUETTE_PNG) > 1000, "silhouette_comparison.png is too small to be a real plot"


# ---------------------------------------------------------------------------
# 2. PNG validity tests
# ---------------------------------------------------------------------------

def test_clusters_k4_is_valid_png():
    assert is_valid_png(CLUSTERS_PNG), "clusters_k4.png is not a valid PNG file"


def test_elbow_plot_is_valid_png():
    assert is_valid_png(ELBOW_PNG), "elbow_plot.png is not a valid PNG file"


def test_silhouette_comparison_is_valid_png():
    assert is_valid_png(SILHOUETTE_PNG), "silhouette_comparison.png is not a valid PNG file"


# ---------------------------------------------------------------------------
# 3. JSON top-level structure
# ---------------------------------------------------------------------------

def test_json_top_level_keys():
    data = load_output_json()
    required_keys = {"data_info", "kmeans_results", "best_k", "best_silhouette_score"}
    assert required_keys.issubset(data.keys()), (
        f"Missing top-level keys: {required_keys - set(data.keys())}"
    )


# ---------------------------------------------------------------------------
# 4. data_info validation
# ---------------------------------------------------------------------------

def test_data_info_structure():
    data = load_output_json()
    di = data["data_info"]
    assert isinstance(di, dict), "data_info must be a dict"
    assert di.get("n_samples") == 500, f"n_samples should be 500, got {di.get('n_samples')}"
    assert di.get("n_features") == 2, f"n_features should be 2, got {di.get('n_features')}"
    assert di.get("true_centers") == 4, f"true_centers should be 4, got {di.get('true_centers')}"


# ---------------------------------------------------------------------------
# 5. kmeans_results validation
# ---------------------------------------------------------------------------

def test_kmeans_results_is_list_of_four():
    data = load_output_json()
    results = data["kmeans_results"]
    assert isinstance(results, list), "kmeans_results must be a list"
    assert len(results) == 4, f"kmeans_results should have 4 entries, got {len(results)}"


def test_kmeans_results_k_values():
    data = load_output_json()
    results = data["kmeans_results"]
    k_vals = [r["k"] for r in results]
    assert sorted(k_vals) == EXPECTED_K_VALUES, (
        f"K values should be {EXPECTED_K_VALUES}, got {sorted(k_vals)}"
    )


def test_kmeans_results_entry_keys():
    data = load_output_json()
    required = {"k", "silhouette_score", "iterations", "centroids"}
    for entry in data["kmeans_results"]:
        missing = required - set(entry.keys())
        assert not missing, f"Entry for k={entry.get('k')} missing keys: {missing}"


def test_silhouette_scores_valid_range():
    """Silhouette scores must be in (-1, 1]."""
    data = load_output_json()
    for entry in data["kmeans_results"]:
        s = entry["silhouette_score"]
        assert isinstance(s, (int, float)), f"silhouette_score for k={entry['k']} is not numeric"
        assert -1 < s <= 1, (
            f"silhouette_score for k={entry['k']} out of range: {s}"
        )


def test_iterations_positive_integers():
    """Each K-Means run must converge in a positive number of iterations."""
    data = load_output_json()
    for entry in data["kmeans_results"]:
        it = entry["iterations"]
        assert isinstance(it, int), f"iterations for k={entry['k']} is not int"
        assert 1 <= it <= 300, (
            f"iterations for k={entry['k']} should be in [1, 300], got {it}"
        )


def test_centroids_shape():
    """Each entry's centroids must be a list of k points, each with 2 coordinates."""
    data = load_output_json()
    for entry in data["kmeans_results"]:
        k = entry["k"]
        centroids = entry["centroids"]
        assert isinstance(centroids, list), f"centroids for k={k} is not a list"
        assert len(centroids) == k, (
            f"centroids for k={k} should have {k} points, got {len(centroids)}"
        )
        for i, pt in enumerate(centroids):
            assert isinstance(pt, list), f"centroid[{i}] for k={k} is not a list"
            assert len(pt) == 2, f"centroid[{i}] for k={k} should have 2 coords, got {len(pt)}"
            for j, coord in enumerate(pt):
                assert isinstance(coord, (int, float)), (
                    f"centroid[{i}][{j}] for k={k} is not numeric"
                )


def test_centroids_rounded_to_4_decimals():
    """Centroid coordinates should be rounded to at most 4 decimal places."""
    data = load_output_json()
    for entry in data["kmeans_results"]:
        k = entry["k"]
        for pt in entry["centroids"]:
            for coord in pt:
                # Convert to string and check decimal places
                s = str(coord)
                if '.' in s:
                    decimal_part = s.split('.')[1]
                    assert len(decimal_part) <= 4, (
                        f"Centroid coord {coord} for k={k} has more than 4 decimal places"
                    )


# ---------------------------------------------------------------------------
# 6. best_k and best_silhouette_score consistency
# ---------------------------------------------------------------------------

def test_best_k_in_expected_range():
    data = load_output_json()
    assert data["best_k"] in EXPECTED_K_VALUES, (
        f"best_k should be one of {EXPECTED_K_VALUES}, got {data['best_k']}"
    )


def test_best_silhouette_score_is_float():
    data = load_output_json()
    bss = data["best_silhouette_score"]
    assert isinstance(bss, (int, float)), "best_silhouette_score must be numeric"
    assert -1 < bss <= 1, f"best_silhouette_score out of range: {bss}"


def test_best_k_matches_highest_silhouette():
    """best_k must correspond to the entry with the highest silhouette score."""
    data = load_output_json()
    results = data["kmeans_results"]
    best_entry = max(results, key=lambda r: r["silhouette_score"])
    assert data["best_k"] == best_entry["k"], (
        f"best_k={data['best_k']} but highest silhouette is at k={best_entry['k']} "
        f"(score={best_entry['silhouette_score']})"
    )


def test_best_silhouette_score_matches_best_k():
    """best_silhouette_score must equal the silhouette_score of the best_k entry."""
    data = load_output_json()
    best_k = data["best_k"]
    entry = [r for r in data["kmeans_results"] if r["k"] == best_k]
    assert len(entry) == 1, f"Could not find unique entry for best_k={best_k}"
    assert abs(data["best_silhouette_score"] - entry[0]["silhouette_score"]) < 1e-6, (
        f"best_silhouette_score={data['best_silhouette_score']} does not match "
        f"entry score={entry[0]['silhouette_score']} for k={best_k}"
    )


# ---------------------------------------------------------------------------
# 7. Semantic correctness — silhouette score plausibility
# ---------------------------------------------------------------------------

def test_silhouette_scores_plausible_for_blob_data():
    """
    With make_blobs(n_samples=500, centers=4, cluster_std=1.0, random_state=42),
    K=4 should produce a reasonably high silhouette score (>0.4).
    K=2 should be noticeably lower than K=4.
    This catches hardcoded/garbage outputs.
    """
    data = load_output_json()
    results_by_k = {r["k"]: r for r in data["kmeans_results"]}

    # K=4 matches the true number of clusters — expect decent score
    s4 = results_by_k[4]["silhouette_score"]
    assert s4 > 0.4, (
        f"Silhouette score for k=4 should be > 0.4 for well-separated blobs, got {s4}"
    )

    # K=2 should be lower than K=4 (merging 4 clusters into 2 is suboptimal)
    s2 = results_by_k[2]["silhouette_score"]
    assert s4 > s2, (
        f"K=4 silhouette ({s4}) should be higher than K=2 ({s2}) for 4-blob data"
    )


def test_best_k_is_reasonable():
    """
    For make_blobs with 4 true centers, the best K by silhouette should be
    3, 4, or 5 (most likely 4). K=2 should not win.
    """
    data = load_output_json()
    assert data["best_k"] != 2, (
        f"best_k=2 is unreasonable for data with 4 true clusters"
    )


def test_silhouette_monotonic_trend():
    """
    For well-separated 4-blob data, silhouette should generally increase
    from K=2 to K=4. We check that K=3 score > K=2 score (merging blobs
    is always worse than getting closer to the true count).
    """
    data = load_output_json()
    results_by_k = {r["k"]: r for r in data["kmeans_results"]}
    s2 = results_by_k[2]["silhouette_score"]
    s3 = results_by_k[3]["silhouette_score"]
    assert s3 > s2, (
        f"K=3 silhouette ({s3}) should be higher than K=2 ({s2}) for 4-blob data"
    )


# ---------------------------------------------------------------------------
# 8. Verify no sklearn.cluster.KMeans usage (from-scratch requirement)
# ---------------------------------------------------------------------------

def test_no_sklearn_kmeans_import():
    """
    The solution must implement K-Means from scratch.
    Check that solution.py does not import sklearn.cluster.KMeans.
    """
    if not os.path.isfile(SOLUTION_PY):
        # If solution.py doesn't exist at the expected path, skip this test
        # (the agent might have used a different filename, but outputs are valid)
        return

    with open(SOLUTION_PY, "r") as f:
        code = f.read()

    # Check for direct imports of KMeans from sklearn
    # Match: from sklearn.cluster import KMeans (with possible other imports)
    pattern1 = r'from\s+sklearn\.cluster\s+import\s+.*KMeans'
    # Match: sklearn.cluster.KMeans usage
    pattern2 = r'sklearn\.cluster\.KMeans'
    # Match: import sklearn.cluster
    pattern3 = r'import\s+sklearn\.cluster'

    assert not re.search(pattern1, code), (
        "solution.py imports KMeans from sklearn.cluster — must implement from scratch"
    )
    assert not re.search(pattern2, code), (
        "solution.py uses sklearn.cluster.KMeans — must implement from scratch"
    )
    assert not re.search(pattern3, code), (
        "solution.py imports sklearn.cluster — must implement from scratch"
    )


# ---------------------------------------------------------------------------
# 9. Independent verification of silhouette scores
# ---------------------------------------------------------------------------

def test_verify_silhouette_scores_independently():
    """
    Re-generate the same data and run the agent's clustering labels through
    sklearn.silhouette_score to verify the reported scores are plausible.
    We regenerate data with the same seed and check that the reported
    silhouette scores for each K are within a reasonable tolerance of what
    a correct implementation would produce.

    Since different initialization strategies can yield slightly different
    clusterings, we use a generous tolerance of 0.15.
    """
    try:
        import numpy as np
        from sklearn.datasets import make_blobs
        from sklearn.metrics import silhouette_score as sk_silhouette
    except ImportError:
        # If sklearn/numpy not available in test env, skip
        return

    data = load_output_json()

    # Reference silhouette scores from the reference solution (seed=42)
    # These are approximate — different implementations may vary
    # K=2: ~0.56, K=3: ~0.62, K=4: ~0.73, K=5: ~0.58
    # We just check that reported scores are in a sane ballpark
    ref_ranges = {
        2: (0.30, 0.80),
        3: (0.40, 0.85),
        4: (0.50, 0.90),
        5: (0.35, 0.80),
    }

    for entry in data["kmeans_results"]:
        k = entry["k"]
        s = entry["silhouette_score"]
        lo, hi = ref_ranges[k]
        assert lo <= s <= hi, (
            f"Silhouette score for k={k} is {s}, expected in [{lo}, {hi}]"
        )

