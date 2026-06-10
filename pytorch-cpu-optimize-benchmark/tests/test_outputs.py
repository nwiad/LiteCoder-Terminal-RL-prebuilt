"""
Tests for PyTorch CPU Optimization Benchmark task.

Validates /app/benchmark_report.json against the specification in instruction.md.
Assumes the agent has already run the task and produced the output file.
"""

import json
import os
import math

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPORT_PATH = "/app/benchmark_report.json"
SCRIPT_PATH = "/app/optimize_benchmark.py"

REQUIRED_TECHNIQUES = {"baseline", "torchscript", "quantized", "combined"}
REQUIRED_METRICS = {"avg_latency_ms", "throughput_samples_per_sec", "accuracy", "model_size_bytes"}
VALID_TECHNIQUE_NAMES = REQUIRED_TECHNIQUES  # for summary fields


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_report():
    """Load and return the parsed JSON report. Raises on missing/invalid file."""
    assert os.path.isfile(REPORT_PATH), (
        f"Report file not found at {REPORT_PATH}"
    )
    with open(REPORT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"Report file at {REPORT_PATH} is empty"
    report = json.loads(content)  # will raise JSONDecodeError if invalid
    return report


# ===========================================================================
# 1. FILE EXISTENCE
# ===========================================================================

def test_script_exists():
    """The optimization benchmark script must exist."""
    assert os.path.isfile(SCRIPT_PATH), (
        f"Script not found at {SCRIPT_PATH}"
    )

def test_report_file_exists():
    """The benchmark report JSON must exist."""
    assert os.path.isfile(REPORT_PATH), (
        f"Report file not found at {REPORT_PATH}"
    )


# ===========================================================================
# 2. JSON VALIDITY AND TOP-LEVEL STRUCTURE
# ===========================================================================

def test_report_is_valid_json():
    """Report must be parseable JSON."""
    load_report()  # raises on failure

def test_report_has_results_key():
    report = load_report()
    assert "results" in report, "Report missing top-level 'results' key"
    assert isinstance(report["results"], dict), "'results' must be a dict"

def test_report_has_summary_key():
    report = load_report()
    assert "summary" in report, "Report missing top-level 'summary' key"
    assert isinstance(report["summary"], dict), "'summary' must be a dict"


# ===========================================================================
# 3. ALL FOUR TECHNIQUES PRESENT
# ===========================================================================

def test_all_techniques_present():
    """All four optimization technique keys must exist under 'results'."""
    report = load_report()
    results = report["results"]
    for tech in REQUIRED_TECHNIQUES:
        assert tech in results, f"Missing technique '{tech}' in results"


# ===========================================================================
# 4. METRIC SCHEMA PER TECHNIQUE
# ===========================================================================

def test_each_technique_has_all_metrics():
    """Each technique must report all four required metrics."""
    report = load_report()
    results = report["results"]
    for tech in REQUIRED_TECHNIQUES:
        if tech not in results:
            continue  # caught by test_all_techniques_present
        entry = results[tech]
        assert isinstance(entry, dict), f"results['{tech}'] must be a dict"
        for metric in REQUIRED_METRICS:
            assert metric in entry, (
                f"Technique '{tech}' missing metric '{metric}'"
            )


# ===========================================================================
# 5. NUMERIC VALUE CONSTRAINTS
# ===========================================================================

def test_all_metrics_are_numeric():
    """Every metric value must be a number (int or float)."""
    report = load_report()
    results = report["results"]
    for tech in REQUIRED_TECHNIQUES:
        if tech not in results:
            continue
        entry = results[tech]
        for metric in REQUIRED_METRICS:
            if metric not in entry:
                continue
            val = entry[metric]
            assert isinstance(val, (int, float)), (
                f"results['{tech}']['{metric}'] = {val!r} is not numeric"
            )

def test_all_metrics_positive():
    """All metric values must be strictly positive (> 0)."""
    report = load_report()
    results = report["results"]
    for tech in REQUIRED_TECHNIQUES:
        if tech not in results:
            continue
        entry = results[tech]
        for metric in REQUIRED_METRICS:
            if metric not in entry:
                continue
            val = entry[metric]
            if not isinstance(val, (int, float)):
                continue
            assert val > 0, (
                f"results['{tech}']['{metric}'] = {val} is not positive"
            )
            # Also reject NaN / Inf
            assert not math.isnan(val) and not math.isinf(val), (
                f"results['{tech}']['{metric}'] = {val} is NaN or Inf"
            )

def test_accuracy_in_range():
    """Accuracy must be between 0.0 and 1.0 inclusive for every technique."""
    report = load_report()
    results = report["results"]
    for tech in REQUIRED_TECHNIQUES:
        if tech not in results:
            continue
        entry = results[tech]
        acc = entry.get("accuracy")
        if acc is None:
            continue
        assert isinstance(acc, (int, float)), (
            f"results['{tech}']['accuracy'] is not numeric"
        )
        assert 0.0 <= acc <= 1.0, (
            f"results['{tech}']['accuracy'] = {acc} not in [0.0, 1.0]"
        )

def test_model_size_bytes_is_integer_like():
    """model_size_bytes should be a positive integer (or integer-valued float)."""
    report = load_report()
    results = report["results"]
    for tech in REQUIRED_TECHNIQUES:
        if tech not in results:
            continue
        entry = results[tech]
        size = entry.get("model_size_bytes")
        if size is None:
            continue
        # Accept int or float that is whole number
        assert isinstance(size, (int, float)), (
            f"results['{tech}']['model_size_bytes'] is not numeric"
        )
        assert size > 0, (
            f"results['{tech}']['model_size_bytes'] must be positive"
        )
        if isinstance(size, float):
            assert size == int(size), (
                f"results['{tech}']['model_size_bytes'] = {size} is not integer-valued"
            )


# ===========================================================================
# 6. QUANTIZED MODEL SIZE < BASELINE MODEL SIZE
# ===========================================================================

def test_quantized_smaller_than_baseline():
    """INT8 quantization must reduce model size compared to baseline."""
    report = load_report()
    results = report["results"]
    baseline_size = results.get("baseline", {}).get("model_size_bytes")
    quantized_size = results.get("quantized", {}).get("model_size_bytes")
    if baseline_size is None or quantized_size is None:
        return  # caught by other tests
    assert quantized_size < baseline_size, (
        f"Quantized model size ({quantized_size}) must be strictly less than "
        f"baseline model size ({baseline_size})"
    )


# ===========================================================================
# 7. SUMMARY FIELD VALIDATION
# ===========================================================================

def test_summary_has_required_fields():
    """Summary must contain fastest_technique, smallest_model_technique, num_test_samples."""
    report = load_report()
    summary = report.get("summary", {})
    assert "fastest_technique" in summary, "summary missing 'fastest_technique'"
    assert "smallest_model_technique" in summary, "summary missing 'smallest_model_technique'"
    assert "num_test_samples" in summary, "summary missing 'num_test_samples'"

def test_summary_technique_names_valid():
    """Summary technique names must be one of the four valid technique names."""
    report = load_report()
    summary = report.get("summary", {})
    fastest = summary.get("fastest_technique")
    smallest = summary.get("smallest_model_technique")
    if fastest is not None:
        assert fastest in VALID_TECHNIQUE_NAMES, (
            f"fastest_technique '{fastest}' not in {VALID_TECHNIQUE_NAMES}"
        )
    if smallest is not None:
        assert smallest in VALID_TECHNIQUE_NAMES, (
            f"smallest_model_technique '{smallest}' not in {VALID_TECHNIQUE_NAMES}"
        )

def test_num_test_samples_at_least_200():
    """num_test_samples must be >= 200."""
    report = load_report()
    summary = report.get("summary", {})
    n = summary.get("num_test_samples")
    if n is None:
        return  # caught by test_summary_has_required_fields
    assert isinstance(n, int), f"num_test_samples must be an integer, got {type(n)}"
    assert n >= 200, f"num_test_samples = {n}, must be >= 200"


# ===========================================================================
# 8. FASTEST TECHNIQUE CONSISTENCY
# ===========================================================================

def test_fastest_technique_is_correct():
    """fastest_technique must match the technique with the lowest avg_latency_ms."""
    report = load_report()
    results = report["results"]
    summary = report.get("summary", {})
    claimed_fastest = summary.get("fastest_technique")
    if claimed_fastest is None:
        return

    # Gather latencies for all present techniques
    latencies = {}
    for tech in REQUIRED_TECHNIQUES:
        entry = results.get(tech, {})
        lat = entry.get("avg_latency_ms")
        if lat is not None and isinstance(lat, (int, float)):
            latencies[tech] = lat

    if not latencies:
        return  # caught by other tests

    actual_fastest = min(latencies, key=latencies.get)
    min_latency = latencies[actual_fastest]

    # Allow tie-breaking: claimed is valid if its latency equals the minimum
    claimed_latency = latencies.get(claimed_fastest)
    assert claimed_latency is not None, (
        f"fastest_technique '{claimed_fastest}' has no avg_latency_ms"
    )
    # Use relative tolerance for float comparison
    assert math.isclose(claimed_latency, min_latency, rel_tol=1e-6), (
        f"fastest_technique is '{claimed_fastest}' (latency={claimed_latency:.4f}ms) "
        f"but '{actual_fastest}' has lower latency ({min_latency:.4f}ms)"
    )


# ===========================================================================
# 9. SMALLEST MODEL TECHNIQUE CONSISTENCY
# ===========================================================================

def test_smallest_model_technique_is_correct():
    """smallest_model_technique must match the technique with the smallest model_size_bytes."""
    report = load_report()
    results = report["results"]
    summary = report.get("summary", {})
    claimed_smallest = summary.get("smallest_model_technique")
    if claimed_smallest is None:
        return

    sizes = {}
    for tech in REQUIRED_TECHNIQUES:
        entry = results.get(tech, {})
        s = entry.get("model_size_bytes")
        if s is not None and isinstance(s, (int, float)):
            sizes[tech] = s

    if not sizes:
        return

    actual_smallest = min(sizes, key=sizes.get)
    min_size = sizes[actual_smallest]

    claimed_size = sizes.get(claimed_smallest)
    assert claimed_size is not None, (
        f"smallest_model_technique '{claimed_smallest}' has no model_size_bytes"
    )
    assert claimed_size <= min_size, (
        f"smallest_model_technique is '{claimed_smallest}' (size={claimed_size}) "
        f"but '{actual_smallest}' has smaller size ({min_size})"
    )


# ===========================================================================
# 10. LATENCY / THROUGHPUT SANITY CHECK
# ===========================================================================

def test_throughput_latency_sanity():
    """
    Throughput and latency should be inversely related within each technique.
    Higher throughput should correspond to lower latency (rough sanity check).
    We verify that throughput * avg_latency_ms is in a reasonable range,
    meaning they are not independently fabricated random numbers.
    """
    report = load_report()
    results = report["results"]

    for tech in REQUIRED_TECHNIQUES:
        entry = results.get(tech, {})
        lat = entry.get("avg_latency_ms")
        thr = entry.get("throughput_samples_per_sec")
        if lat is None or thr is None:
            continue
        if not isinstance(lat, (int, float)) or not isinstance(thr, (int, float)):
            continue
        if lat <= 0 or thr <= 0:
            continue

        # throughput = num_samples / (latency_sec)
        # So throughput * latency_ms / 1000 ≈ num_samples
        # num_samples should be >= 200 and likely < 100000
        implied_samples = thr * (lat / 1000.0)
        assert 1 < implied_samples < 1_000_000, (
            f"Technique '{tech}': throughput ({thr}) * latency ({lat}ms) "
            f"implies {implied_samples:.1f} samples, which is unreasonable"
        )


# ===========================================================================
# 11. MODEL SIZE REASONABLENESS
# ===========================================================================

def test_model_sizes_reasonable():
    """
    Model sizes should be in a reasonable range for a small sentiment model.
    A tiny embedding + linear model should be between ~1KB and ~100MB.
    """
    report = load_report()
    results = report["results"]

    for tech in REQUIRED_TECHNIQUES:
        entry = results.get(tech, {})
        size = entry.get("model_size_bytes")
        if size is None or not isinstance(size, (int, float)):
            continue
        # At minimum a few hundred bytes, at most 100MB
        assert 100 < size < 100_000_000, (
            f"Technique '{tech}': model_size_bytes = {size} is outside "
            f"reasonable range (100, 100_000_000)"
        )
