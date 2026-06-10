"""
Tests for Network Traffic Simulator with Synthetic Attack Detection.
Validates the four output files produced by the agent's solution.
"""

import os
import json
import re
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths – the task WORKDIR is /app, outputs land there
# ---------------------------------------------------------------------------
APP_DIR = "/app"
TRAFFIC_CSV = os.path.join(APP_DIR, "traffic_data.csv")
RESULTS_CSV = os.path.join(APP_DIR, "detection_results.csv")
REPORT_JSON = os.path.join(APP_DIR, "security_report.json")
TIMELINE_PNG = os.path.join(APP_DIR, "attack_timeline.png")
CONFIG_JSON = os.path.join(APP_DIR, "config.json")

# Load config once for reference values
def _load_config():
    assert os.path.isfile(CONFIG_JSON), f"Config file missing: {CONFIG_JSON}"
    with open(CONFIG_JSON, "r") as f:
        return json.load(f)

CFG = _load_config()
NUM_RECORDS = CFG["num_records"]          # 10000
ATTACK_RATIO = CFG["attack_ratio"]        # 0.15
ATTACK_TYPES = CFG["attack_types"]        # ["dos", "port_scan", "data_exfiltration"]
DURATION_SEC = CFG["duration_seconds"]    # 3600

# ===================================================================
# 1. traffic_data.csv tests
# ===================================================================

class TestTrafficData:
    """Validate /app/traffic_data.csv"""

    def _load(self):
        assert os.path.isfile(TRAFFIC_CSV), f"Missing: {TRAFFIC_CSV}"
        df = pd.read_csv(TRAFFIC_CSV)
        assert len(df) > 0, "traffic_data.csv is empty"
        return df

    def test_file_exists_and_not_empty(self):
        assert os.path.isfile(TRAFFIC_CSV), f"Missing: {TRAFFIC_CSV}"
        assert os.path.getsize(TRAFFIC_CSV) > 100, "traffic_data.csv appears too small"

    def test_row_count(self):
        df = self._load()
        assert len(df) == NUM_RECORDS, (
            f"Expected {NUM_RECORDS} rows, got {len(df)}"
        )

    def test_required_columns(self):
        df = self._load()
        required = {
            "timestamp", "src_ip", "dst_ip", "src_port", "dst_port",
            "protocol", "bytes_sent", "bytes_received", "packets",
            "duration_ms", "label",
        }
        missing = required - set(df.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_label_values(self):
        df = self._load()
        valid_labels = {"normal"} | set(ATTACK_TYPES)
        actual = set(df["label"].unique())
        invalid = actual - valid_labels
        assert not invalid, f"Invalid labels found: {invalid}"

    def test_all_attack_types_present(self):
        df = self._load()
        for atype in ATTACK_TYPES:
            count = (df["label"] == atype).sum()
            assert count >= 1, f"Attack type '{atype}' not found in data"

    def test_attack_ratio_within_tolerance(self):
        df = self._load()
        actual_ratio = (df["label"] != "normal").sum() / len(df)
        assert abs(actual_ratio - ATTACK_RATIO) <= 0.02, (
            f"Attack ratio {actual_ratio:.4f} not within ±2% of {ATTACK_RATIO}"
        )

    def test_protocol_values(self):
        df = self._load()
        valid_protocols = {"TCP", "UDP", "ICMP"}
        actual = set(df["protocol"].unique())
        invalid = actual - valid_protocols
        assert not invalid, f"Invalid protocols: {invalid}"

    def test_port_ranges(self):
        df = self._load()
        assert (df["src_port"] >= 1).all() and (df["src_port"] <= 65535).all(), \
            "src_port out of range [1, 65535]"
        assert (df["dst_port"] >= 1).all() and (df["dst_port"] <= 65535).all(), \
            "dst_port out of range [1, 65535]"

    def test_bytes_non_negative(self):
        df = self._load()
        assert (df["bytes_sent"] >= 0).all(), "bytes_sent has negative values"
        assert (df["bytes_received"] >= 0).all(), "bytes_received has negative values"

    def test_packets_positive(self):
        df = self._load()
        assert (df["packets"] >= 1).all(), "packets must be >= 1"

    def test_duration_ms_non_negative(self):
        df = self._load()
        assert (df["duration_ms"] >= 0).all(), "duration_ms has negative values"

    def test_ip_format(self):
        """Spot-check that IPs look like valid IPv4 addresses."""
        df = self._load()
        ipv4_re = re.compile(
            r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
        )
        sample = df.sample(min(200, len(df)), random_state=0)
        for col in ("src_ip", "dst_ip"):
            for val in sample[col]:
                assert ipv4_re.match(str(val)), f"Invalid IPv4 in {col}: {val}"

    def test_timestamps_sorted_ascending(self):
        df = self._load()
        ts = pd.to_datetime(df["timestamp"])
        assert ts.is_monotonic_increasing, "Timestamps are not sorted ascending"

    def test_timestamps_within_duration(self):
        df = self._load()
        ts = pd.to_datetime(df["timestamp"])
        t0 = ts.iloc[0]
        t_last = ts.iloc[-1]
        span_seconds = (t_last - t0).total_seconds()
        assert span_seconds <= DURATION_SEC, (
            f"Timestamp span {span_seconds:.1f}s exceeds duration {DURATION_SEC}s"
        )


# ===================================================================
# 2. detection_results.csv tests
# ===================================================================

class TestDetectionResults:
    """Validate /app/detection_results.csv"""

    def _load(self):
        assert os.path.isfile(RESULTS_CSV), f"Missing: {RESULTS_CSV}"
        df = pd.read_csv(RESULTS_CSV)
        assert len(df) > 0, "detection_results.csv is empty"
        return df

    def test_file_exists_and_not_empty(self):
        assert os.path.isfile(RESULTS_CSV), f"Missing: {RESULTS_CSV}"
        assert os.path.getsize(RESULTS_CSV) > 100, "detection_results.csv appears too small"

    def test_row_count(self):
        df = self._load()
        assert len(df) == NUM_RECORDS, (
            f"Expected {NUM_RECORDS} rows, got {len(df)}"
        )

    def test_required_columns(self):
        df = self._load()
        required = {
            "record_index", "true_label", "anomaly_score",
            "is_anomaly", "predicted_attack_type",
        }
        missing = required - set(df.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_record_index_sequential(self):
        df = self._load()
        expected = list(range(NUM_RECORDS))
        assert list(df["record_index"]) == expected, (
            "record_index should be 0-based sequential integers"
        )

    def test_true_label_values(self):
        df = self._load()
        valid = {"normal"} | set(ATTACK_TYPES)
        actual = set(df["true_label"].unique())
        invalid = actual - valid
        assert not invalid, f"Invalid true_label values: {invalid}"

    def test_anomaly_score_is_numeric(self):
        df = self._load()
        scores = pd.to_numeric(df["anomaly_score"], errors="coerce")
        assert scores.notna().all(), "anomaly_score contains non-numeric values"

    def test_is_anomaly_boolean_values(self):
        df = self._load()
        col = df["is_anomaly"].astype(str).str.strip().str.lower()
        valid = {"true", "false"}
        actual = set(col.unique())
        invalid = actual - valid
        assert not invalid, f"is_anomaly has invalid values: {invalid}"

    def test_predicted_attack_type_values(self):
        df = self._load()
        valid = {"normal"} | set(ATTACK_TYPES)
        actual = set(df["predicted_attack_type"].unique())
        invalid = actual - valid
        assert not invalid, f"Invalid predicted_attack_type: {invalid}"

    def test_true_labels_match_traffic_data(self):
        """true_label in results must match label in traffic_data row-by-row."""
        assert os.path.isfile(TRAFFIC_CSV), f"Missing: {TRAFFIC_CSV}"
        assert os.path.isfile(RESULTS_CSV), f"Missing: {RESULTS_CSV}"
        df_traffic = pd.read_csv(TRAFFIC_CSV)
        df_results = pd.read_csv(RESULTS_CSV)
        if len(df_traffic) == len(df_results):
            mismatches = (df_traffic["label"] != df_results["true_label"]).sum()
            assert mismatches == 0, (
                f"{mismatches} rows have mismatched true_label vs traffic label"
            )

    def test_anomaly_scores_higher_means_more_anomalous(self):
        """On average, attack records should have higher anomaly scores than normal."""
        df = self._load()
        scores = pd.to_numeric(df["anomaly_score"], errors="coerce")
        assert os.path.isfile(TRAFFIC_CSV)
        df_traffic = pd.read_csv(TRAFFIC_CSV)
        if len(df) == len(df_traffic):
            normal_mask = df_traffic["label"] == "normal"
            attack_mask = ~normal_mask
            if normal_mask.sum() > 0 and attack_mask.sum() > 0:
                mean_normal = scores[normal_mask].mean()
                mean_attack = scores[attack_mask].mean()
                assert mean_attack > mean_normal, (
                    f"Attack mean score ({mean_attack:.4f}) should be > "
                    f"normal mean score ({mean_normal:.4f})"
                )


# ===================================================================
# 3. security_report.json tests
# ===================================================================

class TestSecurityReport:
    """Validate /app/security_report.json"""

    def _load(self):
        assert os.path.isfile(REPORT_JSON), f"Missing: {REPORT_JSON}"
        with open(REPORT_JSON, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), "Report root must be a JSON object"
        return data

    def test_file_exists_and_valid_json(self):
        assert os.path.isfile(REPORT_JSON), f"Missing: {REPORT_JSON}"
        assert os.path.getsize(REPORT_JSON) > 10, "security_report.json too small"
        with open(REPORT_JSON, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_top_level_keys(self):
        data = self._load()
        required_keys = {"summary", "attack_breakdown", "classification_metrics", "timeline"}
        missing = required_keys - set(data.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    # --- summary section ---
    def test_summary_keys(self):
        data = self._load()
        summary = data.get("summary", {})
        required = {
            "total_records", "total_attacks", "total_normal",
            "attack_ratio", "detection_rate", "false_positive_rate",
        }
        missing = required - set(summary.keys())
        assert not missing, f"Missing summary keys: {missing}"

    def test_summary_total_records(self):
        data = self._load()
        assert data["summary"]["total_records"] == NUM_RECORDS

    def test_summary_counts_add_up(self):
        data = self._load()
        s = data["summary"]
        assert s["total_attacks"] + s["total_normal"] == s["total_records"], (
            "total_attacks + total_normal must equal total_records"
        )

    def test_summary_attack_ratio_reasonable(self):
        data = self._load()
        ratio = data["summary"]["attack_ratio"]
        assert 0.0 <= ratio <= 1.0, f"attack_ratio {ratio} out of [0,1]"
        assert abs(ratio - ATTACK_RATIO) <= 0.02, (
            f"Reported attack_ratio {ratio} not within ±2% of config {ATTACK_RATIO}"
        )

    def test_summary_detection_rate_range(self):
        data = self._load()
        dr = data["summary"]["detection_rate"]
        assert 0.0 <= dr <= 1.0, f"detection_rate {dr} out of [0,1]"

    def test_summary_false_positive_rate_range(self):
        data = self._load()
        fpr = data["summary"]["false_positive_rate"]
        assert 0.0 <= fpr <= 1.0, f"false_positive_rate {fpr} out of [0,1]"

    # --- attack_breakdown section ---
    def test_attack_breakdown_all_types_present(self):
        data = self._load()
        breakdown = data.get("attack_breakdown", {})
        for atype in ATTACK_TYPES:
            assert atype in breakdown, (
                f"attack_breakdown missing entry for '{atype}'"
            )

    def test_attack_breakdown_structure(self):
        data = self._load()
        breakdown = data.get("attack_breakdown", {})
        for atype in ATTACK_TYPES:
            if atype in breakdown:
                entry = breakdown[atype]
                assert "count" in entry, f"'{atype}' missing 'count'"
                assert "detected" in entry, f"'{atype}' missing 'detected'"
                assert isinstance(entry["count"], int), f"'{atype}' count not int"
                assert isinstance(entry["detected"], int), f"'{atype}' detected not int"
                assert entry["detected"] <= entry["count"], (
                    f"'{atype}' detected ({entry['detected']}) > count ({entry['count']})"
                )

    def test_attack_breakdown_counts_sum(self):
        """Sum of all attack type counts should equal total_attacks."""
        data = self._load()
        breakdown = data.get("attack_breakdown", {})
        s = data.get("summary", {})
        total_from_breakdown = sum(
            breakdown[atype]["count"]
            for atype in ATTACK_TYPES
            if atype in breakdown
        )
        assert total_from_breakdown == s.get("total_attacks", -1), (
            f"Breakdown sum {total_from_breakdown} != total_attacks {s.get('total_attacks')}"
        )

    # --- classification_metrics section ---
    def test_classification_metrics_keys(self):
        data = self._load()
        metrics = data.get("classification_metrics", {})
        required = {"accuracy", "precision_macro", "recall_macro", "f1_macro"}
        missing = required - set(metrics.keys())
        assert not missing, f"Missing classification_metrics keys: {missing}"

    def test_classification_metrics_ranges(self):
        data = self._load()
        metrics = data.get("classification_metrics", {})
        for key in ("accuracy", "precision_macro", "recall_macro", "f1_macro"):
            if key in metrics:
                val = metrics[key]
                assert 0.0 <= val <= 1.0, f"{key} = {val} out of [0,1]"

    def test_classification_accuracy_reasonable(self):
        """A proper RF classifier on this data should achieve > 50% accuracy."""
        data = self._load()
        metrics = data.get("classification_metrics", {})
        acc = metrics.get("accuracy", 0)
        assert acc > 0.5, f"Accuracy {acc} is suspiciously low (< 0.5)"

    # --- timeline section ---
    def test_timeline_keys(self):
        data = self._load()
        timeline = data.get("timeline", {})
        required = {"start_time", "end_time", "peak_attack_window"}
        missing = required - set(timeline.keys())
        assert not missing, f"Missing timeline keys: {missing}"

    def test_timeline_iso8601_format(self):
        data = self._load()
        timeline = data.get("timeline", {})
        for key in ("start_time", "end_time"):
            val = timeline.get(key, "")
            try:
                pd.Timestamp(val)
            except Exception:
                assert False, f"timeline.{key} = '{val}' is not valid ISO 8601"

    def test_timeline_start_before_end(self):
        data = self._load()
        timeline = data.get("timeline", {})
        try:
            start = pd.Timestamp(timeline["start_time"])
            end = pd.Timestamp(timeline["end_time"])
            assert start <= end, "start_time must be <= end_time"
        except (KeyError, ValueError):
            pass  # other tests catch missing/invalid keys

    def test_peak_attack_window_format(self):
        """peak_attack_window should contain two ISO timestamps separated by ' / '."""
        data = self._load()
        timeline = data.get("timeline", {})
        paw = timeline.get("peak_attack_window", "")
        assert "/" in paw, "peak_attack_window must contain '/'"
        parts = paw.split("/")
        assert len(parts) == 2, f"Expected 2 parts around '/', got {len(parts)}"
        for part in parts:
            part = part.strip()
            try:
                pd.Timestamp(part)
            except Exception:
                assert False, f"Cannot parse '{part}' as ISO 8601 timestamp"

    def test_peak_attack_window_is_60_seconds(self):
        data = self._load()
        timeline = data.get("timeline", {})
        paw = timeline.get("peak_attack_window", "")
        if "/" in paw:
            parts = paw.split("/")
            if len(parts) == 2:
                try:
                    t_start = pd.Timestamp(parts[0].strip())
                    t_end = pd.Timestamp(parts[1].strip())
                    diff = (t_end - t_start).total_seconds()
                    assert np.isclose(diff, 60.0, atol=1.0), (
                        f"Peak window span is {diff}s, expected ~60s"
                    )
                except (ValueError, TypeError):
                    pass  # format test catches this


# ===================================================================
# 4. attack_timeline.png tests
# ===================================================================

class TestAttackTimeline:
    """Validate /app/attack_timeline.png"""

    def test_file_exists(self):
        assert os.path.isfile(TIMELINE_PNG), f"Missing: {TIMELINE_PNG}"

    def test_file_not_trivially_small(self):
        assert os.path.isfile(TIMELINE_PNG), f"Missing: {TIMELINE_PNG}"
        size = os.path.getsize(TIMELINE_PNG)
        assert size > 1000, f"attack_timeline.png is only {size} bytes — too small"

    def test_valid_png_signature(self):
        """Check the PNG magic bytes."""
        assert os.path.isfile(TIMELINE_PNG), f"Missing: {TIMELINE_PNG}"
        with open(TIMELINE_PNG, "rb") as f:
            header = f.read(8)
        png_sig = b"\x89PNG\r\n\x1a\n"
        assert header == png_sig, "File does not have valid PNG signature"

    def test_png_dimensions_minimum(self):
        """PNG must be at least 800x600 pixels."""
        from PIL import Image
        assert os.path.isfile(TIMELINE_PNG), f"Missing: {TIMELINE_PNG}"
        img = Image.open(TIMELINE_PNG)
        w, h = img.size
        assert w >= 800, f"Image width {w} < 800"
        assert h >= 600, f"Image height {h} < 600"
