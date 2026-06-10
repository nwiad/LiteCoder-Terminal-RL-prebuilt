"""
Tests for Insider Trading Email Detection Pipeline.

Validates all output files produced by the pipeline:
- 500 .eml files in /app/data/raw/
- labels.csv with 200 labeled entries
- emails.csv with 500 parsed rows
- model.joblib saved model
- metrics.json with valid evaluation metrics
- top_suspicious.csv with top 100 ranked emails
- summary.md with required sections
- run.sh exists and is executable
"""

import os
import csv
import json
import glob
import email
import re

import pandas as pd
import numpy as np


# ── Paths ──────────────────────────────────────────────────────────────────────

RAW_DIR = "/app/data/raw"
LABELS_PATH = "/app/data/labels.csv"
EMAILS_CSV = "/app/data/processed/emails.csv"
MODEL_PATH = "/app/data/model_output/model.joblib"
METRICS_PATH = "/app/data/reports/metrics.json"
TOP_SUSPICIOUS_PATH = "/app/data/reports/top_suspicious.csv"
SUMMARY_PATH = "/app/data/reports/summary.md"
RUN_SH_PATH = "/app/run.sh"


# ── Helper ─────────────────────────────────────────────────────────────────────

def _read_csv_safe(path):
    """Read a CSV, return a DataFrame or None if missing/empty."""
    if not os.path.isfile(path):
        return None
    df = pd.read_csv(path)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 1. Directory structure & run.sh
# ══════════════════════════════════════════════════════════════════════════════

class TestDirectoryAndRunScript:

    def test_run_sh_exists(self):
        assert os.path.isfile(RUN_SH_PATH), "run.sh must exist at /app/run.sh"

    def test_run_sh_is_executable(self):
        assert os.access(RUN_SH_PATH, os.X_OK), "run.sh must be executable"

    def test_run_sh_is_bash(self):
        with open(RUN_SH_PATH, "r") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!"), "run.sh should have a shebang line"
        assert "bash" in first_line or "sh" in first_line, \
            "run.sh shebang should reference bash or sh"

    def test_required_directories_exist(self):
        for d in [RAW_DIR, "/app/data/processed",
                  "/app/data/model_output", "/app/data/reports"]:
            assert os.path.isdir(d), f"Directory {d} must exist"


# ══════════════════════════════════════════════════════════════════════════════
# 2. Synthetic .eml data generation
# ══════════════════════════════════════════════════════════════════════════════

class TestEmlGeneration:

    def test_eml_file_count(self):
        eml_files = glob.glob(os.path.join(RAW_DIR, "*.eml"))
        assert len(eml_files) == 500, \
            f"Expected 500 .eml files, found {len(eml_files)}"

    def test_eml_naming_convention(self):
        """Files should be named email_001.eml through email_500.eml."""
        for i in range(1, 501):
            fname = f"email_{i:03d}.eml"
            fpath = os.path.join(RAW_DIR, fname)
            assert os.path.isfile(fpath), f"Missing expected file: {fname}"

    def test_eml_is_valid_rfc2822(self):
        """Spot-check a sample of .eml files for required headers."""
        required_headers = {"From", "To", "Date", "Subject"}
        sample_indices = [1, 50, 100, 250, 500]
        for i in sample_indices:
            fpath = os.path.join(RAW_DIR, f"email_{i:03d}.eml")
            with open(fpath, "r", encoding="utf-8") as f:
                msg = email.message_from_string(f.read())
            present = set(msg.keys())
            for hdr in required_headers:
                assert hdr in present, \
                    f"email_{i:03d}.eml missing header: {hdr}"

    def test_eml_has_body(self):
        """Spot-check that emails have non-empty bodies."""
        for i in [1, 100, 300, 500]:
            fpath = os.path.join(RAW_DIR, f"email_{i:03d}.eml")
            with open(fpath, "r", encoding="utf-8") as f:
                msg = email.message_from_string(f.read())
            if msg.is_multipart():
                body = ""
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        body = payload.decode("utf-8", errors="replace") if payload else ""
                        break
            else:
                payload = msg.get_payload(decode=True)
                body = payload.decode("utf-8", errors="replace") if payload else ""
            assert len(body.strip()) > 0, \
                f"email_{i:03d}.eml has an empty body"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Labels CSV
# ══════════════════════════════════════════════════════════════════════════════

class TestLabelsCSV:

    def test_labels_file_exists(self):
        assert os.path.isfile(LABELS_PATH), "labels.csv must exist"

    def test_labels_columns(self):
        df = _read_csv_safe(LABELS_PATH)
        assert df is not None, "labels.csv could not be read"
        cols = [c.strip().lower() for c in df.columns]
        assert "id" in cols, "labels.csv must have 'id' column"
        assert "label" in cols, "labels.csv must have 'label' column"

    def test_labels_row_count(self):
        df = _read_csv_safe(LABELS_PATH)
        assert df is not None
        assert len(df) == 200, \
            f"labels.csv must have exactly 200 rows, found {len(df)}"

    def test_labels_values_binary(self):
        df = _read_csv_safe(LABELS_PATH)
        assert df is not None
        unique_labels = set(df["label"].unique())
        assert unique_labels.issubset({0, 1}), \
            f"Labels must be 0 or 1, found: {unique_labels}"

    def test_labels_have_both_classes(self):
        df = _read_csv_safe(LABELS_PATH)
        assert df is not None
        assert 0 in df["label"].values, "labels.csv must contain class 0"
        assert 1 in df["label"].values, "labels.csv must contain class 1"

    def test_labels_ids_match_eml_files(self):
        """Every id in labels.csv should correspond to an existing .eml file."""
        df = _read_csv_safe(LABELS_PATH)
        assert df is not None
        for eid in df["id"]:
            fpath = os.path.join(RAW_DIR, f"{eid}.eml")
            assert os.path.isfile(fpath), \
                f"labels.csv references {eid} but {fpath} does not exist"

    def test_labels_suspicious_proportion(self):
        """Roughly 10% of the 500 emails are suspicious; among 200 labeled,
        we expect a meaningful number of positives (at least 10)."""
        df = _read_csv_safe(LABELS_PATH)
        assert df is not None
        n_pos = (df["label"] == 1).sum()
        assert n_pos >= 10, \
            f"Expected at least 10 suspicious labels, found {n_pos}"


# ══════════════════════════════════════════════════════════════════════════════
# 4. Parsed emails CSV
# ══════════════════════════════════════════════════════════════════════════════

class TestEmailsCSV:

    def test_emails_csv_exists(self):
        assert os.path.isfile(EMAILS_CSV), "emails.csv must exist"

    def test_emails_csv_columns(self):
        df = _read_csv_safe(EMAILS_CSV)
        assert df is not None
        required = {"id", "date", "from", "to", "subject", "body"}
        actual = {c.strip().lower() for c in df.columns}
        missing = required - actual
        assert not missing, f"emails.csv missing columns: {missing}"

    def test_emails_csv_row_count(self):
        df = _read_csv_safe(EMAILS_CSV)
        assert df is not None
        assert len(df) == 500, \
            f"emails.csv must have 500 rows, found {len(df)}"

    def test_emails_csv_ids_unique(self):
        df = _read_csv_safe(EMAILS_CSV)
        assert df is not None
        assert df["id"].nunique() == 500, "emails.csv ids must be unique"

    def test_emails_csv_no_empty_bodies(self):
        """Spot-check that bodies are not all empty."""
        df = _read_csv_safe(EMAILS_CSV)
        assert df is not None
        non_empty = df["body"].dropna().apply(lambda x: len(str(x).strip()) > 0)
        assert non_empty.sum() >= 450, \
            "Most emails should have non-empty bodies"


# ══════════════════════════════════════════════════════════════════════════════
# 5. Model artifact
# ══════════════════════════════════════════════════════════════════════════════

class TestModelArtifact:

    def test_model_file_exists(self):
        assert os.path.isfile(MODEL_PATH), \
            "model.joblib must exist at /app/data/model_output/model.joblib"

    def test_model_file_not_empty(self):
        assert os.path.getsize(MODEL_PATH) > 100, \
            "model.joblib appears to be empty or trivially small"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Metrics JSON
# ══════════════════════════════════════════════════════════════════════════════

class TestMetricsJSON:

    def test_metrics_file_exists(self):
        assert os.path.isfile(METRICS_PATH), "metrics.json must exist"

    def test_metrics_valid_json(self):
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), "metrics.json must be a JSON object"

    def test_metrics_required_keys(self):
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        required = {"accuracy", "precision", "recall", "f1_score", "roc_auc"}
        actual = set(data.keys())
        missing = required - actual
        assert not missing, f"metrics.json missing keys: {missing}"

    def test_metrics_values_are_floats_in_range(self):
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        for key in ["accuracy", "precision", "recall", "f1_score", "roc_auc"]:
            val = data[key]
            assert isinstance(val, (int, float)), \
                f"metrics['{key}'] must be numeric, got {type(val)}"
            assert 0.0 <= float(val) <= 1.0, \
                f"metrics['{key}'] = {val} is out of [0, 1] range"

    def test_metrics_not_all_zero(self):
        """Guard against a dummy pipeline that outputs all zeros."""
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        values = [data[k] for k in ["accuracy", "precision", "recall",
                                     "f1_score", "roc_auc"]]
        assert sum(values) > 0.5, \
            "Metrics are suspiciously low — pipeline may not be working"

    def test_metrics_not_all_identical(self):
        """Guard against hardcoded dummy values."""
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        values = [data[k] for k in ["accuracy", "precision", "recall",
                                     "f1_score", "roc_auc"]]
        assert len(set(round(v, 6) for v in values)) > 1, \
            "All metric values are identical — likely hardcoded"


# ══════════════════════════════════════════════════════════════════════════════
# 7. Top suspicious CSV
# ══════════════════════════════════════════════════════════════════════════════

class TestTopSuspiciousCSV:

    def test_top_suspicious_exists(self):
        assert os.path.isfile(TOP_SUSPICIOUS_PATH), \
            "top_suspicious.csv must exist"

    def test_top_suspicious_columns(self):
        df = _read_csv_safe(TOP_SUSPICIOUS_PATH)
        assert df is not None
        required = {"rank", "id", "from", "to", "subject", "score"}
        actual = {c.strip().lower() for c in df.columns}
        missing = required - actual
        assert not missing, \
            f"top_suspicious.csv missing columns: {missing}"

    def test_top_suspicious_row_count(self):
        df = _read_csv_safe(TOP_SUSPICIOUS_PATH)
        assert df is not None
        assert len(df) == 100, \
            f"top_suspicious.csv must have exactly 100 rows, found {len(df)}"

    def test_top_suspicious_rank_1_indexed(self):
        df = _read_csv_safe(TOP_SUSPICIOUS_PATH)
        assert df is not None
        ranks = df["rank"].tolist()
        assert ranks[0] == 1, "Rank must start at 1"
        assert ranks[-1] == 100, "Rank must end at 100"

    def test_top_suspicious_rank_sequential(self):
        df = _read_csv_safe(TOP_SUSPICIOUS_PATH)
        assert df is not None
        expected = list(range(1, 101))
        assert df["rank"].tolist() == expected, \
            "Ranks must be sequential 1..100"

    def test_top_suspicious_scores_in_range(self):
        df = _read_csv_safe(TOP_SUSPICIOUS_PATH)
        assert df is not None
        assert df["score"].between(0.0, 1.0).all(), \
            "All scores must be between 0 and 1"

    def test_top_suspicious_scores_descending(self):
        df = _read_csv_safe(TOP_SUSPICIOUS_PATH)
        assert df is not None
        scores = df["score"].tolist()
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1] - 1e-9, \
                f"Scores must be descending; violation at rank {i+1}"

    def test_top_suspicious_ids_are_valid(self):
        """All ids in top_suspicious.csv must exist in emails.csv."""
        top_df = _read_csv_safe(TOP_SUSPICIOUS_PATH)
        emails_df = _read_csv_safe(EMAILS_CSV)
        assert top_df is not None and emails_df is not None
        valid_ids = set(emails_df["id"].values)
        for eid in top_df["id"]:
            assert eid in valid_ids, \
                f"top_suspicious.csv id '{eid}' not found in emails.csv"

    def test_top_suspicious_ids_unique(self):
        df = _read_csv_safe(TOP_SUSPICIOUS_PATH)
        assert df is not None
        assert df["id"].nunique() == 100, \
            "top_suspicious.csv ids must be unique"

    def test_top_suspicious_scores_not_all_same(self):
        """Guard against dummy constant scores."""
        df = _read_csv_safe(TOP_SUSPICIOUS_PATH)
        assert df is not None
        assert df["score"].nunique() > 1, \
            "All scores are identical — model may not be working"


# ══════════════════════════════════════════════════════════════════════════════
# 8. Summary report
# ══════════════════════════════════════════════════════════════════════════════

class TestSummaryReport:

    def test_summary_exists(self):
        assert os.path.isfile(SUMMARY_PATH), "summary.md must exist"

    def test_summary_not_empty(self):
        with open(SUMMARY_PATH, "r") as f:
            content = f.read()
        assert len(content.strip()) > 100, \
            "summary.md is too short to be a real report"

    def test_summary_has_methodology_section(self):
        with open(SUMMARY_PATH, "r") as f:
            content = f.read().lower()
        assert "methodology" in content, \
            "summary.md must contain a 'Methodology' section"

    def test_summary_has_evaluation_metrics_section(self):
        with open(SUMMARY_PATH, "r") as f:
            content = f.read().lower()
        # Check for key metric terms in the report
        assert "precision" in content, \
            "summary.md must mention precision"
        assert "recall" in content, \
            "summary.md must mention recall"
        assert "f1" in content, \
            "summary.md must mention F1"
        assert "roc" in content or "auc" in content, \
            "summary.md must mention ROC-AUC"

    def test_summary_has_top5_section(self):
        with open(SUMMARY_PATH, "r") as f:
            content = f.read().lower()
        assert "top" in content and "suspicious" in content, \
            "summary.md must contain a 'Top ... Suspicious Emails' section"

    def test_summary_contains_email_ids(self):
        """The top-5 section should reference actual email ids."""
        with open(SUMMARY_PATH, "r") as f:
            content = f.read()
        # Look for patterns like email_NNN
        ids_found = re.findall(r"email_\d{3}", content)
        assert len(ids_found) >= 5, \
            f"summary.md should list at least 5 email ids, found {len(ids_found)}"

    def test_summary_contains_numeric_scores(self):
        """The report should contain numeric metric values (floats like 0.xxxx)."""
        with open(SUMMARY_PATH, "r") as f:
            content = f.read()
        floats_found = re.findall(r"0\.\d{2,}", content)
        assert len(floats_found) >= 4, \
            "summary.md should contain at least 4 numeric metric values"


# ══════════════════════════════════════════════════════════════════════════════
# 9. Cross-file consistency checks
# ══════════════════════════════════════════════════════════════════════════════

class TestCrossFileConsistency:

    def test_labels_ids_subset_of_emails(self):
        """All labeled ids must appear in emails.csv."""
        labels_df = _read_csv_safe(LABELS_PATH)
        emails_df = _read_csv_safe(EMAILS_CSV)
        if labels_df is None or emails_df is None:
            assert False, "Cannot read labels.csv or emails.csv"
        label_ids = set(labels_df["id"].values)
        email_ids = set(emails_df["id"].values)
        missing = label_ids - email_ids
        assert not missing, \
            f"labels.csv ids not in emails.csv: {missing}"

    def test_top_suspicious_subjects_match_emails(self):
        """Subjects in top_suspicious.csv should match emails.csv."""
        top_df = _read_csv_safe(TOP_SUSPICIOUS_PATH)
        emails_df = _read_csv_safe(EMAILS_CSV)
        if top_df is None or emails_df is None:
            assert False, "Cannot read required CSVs"
        email_subjects = dict(zip(emails_df["id"], emails_df["subject"]))
        # Spot-check first 5
        for _, row in top_df.head(5).iterrows():
            eid = row["id"]
            if eid in email_subjects:
                assert str(row["subject"]).strip() == str(email_subjects[eid]).strip(), \
                    f"Subject mismatch for {eid}"

    def test_metrics_json_matches_summary(self):
        """Metric values in metrics.json should appear in summary.md."""
        if not os.path.isfile(METRICS_PATH) or not os.path.isfile(SUMMARY_PATH):
            assert False, "metrics.json or summary.md missing"
        with open(METRICS_PATH, "r") as f:
            metrics = json.load(f)
        with open(SUMMARY_PATH, "r") as f:
            summary = f.read()
        # At least precision and recall values should appear in the summary
        for key in ["precision", "recall"]:
            val_str = f"{metrics[key]:.4f}"
            # Also try fewer decimals for flexibility
            val_str_2 = f"{metrics[key]:.2f}"
            assert val_str in summary or val_str_2 in summary, \
                f"metrics.json {key}={metrics[key]} not found in summary.md"

