"""
Tests for Zero-shot Topic Modeling with BERTopic pipeline.

Validates the 4 output artifacts:
  /app/documents.json
  /app/topic_assignments.json
  /app/metrics.json
  /app/saved_model/
"""

import os
import json
import numpy as np

BASE_DIR = "/app"

DOCUMENTS_PATH = os.path.join(BASE_DIR, "documents.json")
ASSIGNMENTS_PATH = os.path.join(BASE_DIR, "topic_assignments.json")
METRICS_PATH = os.path.join(BASE_DIR, "metrics.json")
MODEL_DIR = os.path.join(BASE_DIR, "saved_model")

EXPECTED_CANDIDATE_LABELS = [
    "Sports",
    "Medicine & Health",
    "Computer Graphics",
    "Gun Policy & Politics",
    "Religion & Christianity",
]

# The 20 Newsgroups test subset with these 5 categories has a known doc count.
# It is approximately 3000+ documents. We use a generous range to allow for
# minor sklearn version differences but catch dummy/empty outputs.
MIN_EXPECTED_DOCS = 2500
MAX_EXPECTED_DOCS = 4500


# ============================================================
# Helper: safe JSON loading
# ============================================================

def _load_json(path):
    """Load and return parsed JSON from path. Raises AssertionError on failure."""
    assert os.path.isfile(path), f"Output file not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert len(content.strip()) > 0, f"Output file is empty: {path}"
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON in {path}: {e}")


# ============================================================
# 1. documents.json
# ============================================================

class TestDocuments:
    """Validate /app/documents.json"""

    def test_file_exists(self):
        assert os.path.isfile(DOCUMENTS_PATH), "documents.json not found"

    def test_is_json_array(self):
        data = _load_json(DOCUMENTS_PATH)
        assert isinstance(data, list), "documents.json must be a JSON array"

    def test_array_of_strings(self):
        data = _load_json(DOCUMENTS_PATH)
        assert len(data) > 0, "documents.json must not be empty"
        for i, doc in enumerate(data):
            assert isinstance(doc, str), (
                f"documents.json[{i}] must be a string, got {type(doc).__name__}"
            )

    def test_document_count_in_range(self):
        """20 Newsgroups test subset with 5 categories should have ~3000+ docs."""
        data = _load_json(DOCUMENTS_PATH)
        assert MIN_EXPECTED_DOCS <= len(data) <= MAX_EXPECTED_DOCS, (
            f"Expected {MIN_EXPECTED_DOCS}-{MAX_EXPECTED_DOCS} documents, got {len(data)}"
        )

    def test_documents_have_content(self):
        """At least 90% of documents should be non-trivial (>10 chars)."""
        data = _load_json(DOCUMENTS_PATH)
        non_trivial = sum(1 for d in data if len(d.strip()) > 10)
        ratio = non_trivial / len(data)
        assert ratio >= 0.5, (
            f"Only {ratio:.1%} of documents have >10 chars; expected >=50%"
        )


# ============================================================
# 2. topic_assignments.json
# ============================================================

class TestTopicAssignments:
    """Validate /app/topic_assignments.json"""

    def test_file_exists(self):
        assert os.path.isfile(ASSIGNMENTS_PATH), "topic_assignments.json not found"

    def test_is_json_array(self):
        data = _load_json(ASSIGNMENTS_PATH)
        assert isinstance(data, list), "topic_assignments.json must be a JSON array"

    def test_not_empty(self):
        data = _load_json(ASSIGNMENTS_PATH)
        assert len(data) > 0, "topic_assignments.json must not be empty"

    def test_entry_schema(self):
        """Each entry must have doc_index (int), topic_id (int), topic_label (str)."""
        data = _load_json(ASSIGNMENTS_PATH)
        required_keys = {"doc_index", "topic_id", "topic_label"}
        for i, entry in enumerate(data):
            assert isinstance(entry, dict), (
                f"Entry {i} must be an object, got {type(entry).__name__}"
            )
            missing = required_keys - set(entry.keys())
            assert not missing, f"Entry {i} missing keys: {missing}"
            assert isinstance(entry["doc_index"], int), (
                f"Entry {i}: doc_index must be int"
            )
            assert isinstance(entry["topic_id"], int), (
                f"Entry {i}: topic_id must be int"
            )
            assert isinstance(entry["topic_label"], str), (
                f"Entry {i}: topic_label must be str"
            )

    def test_doc_indices_sequential(self):
        """doc_index values should be 0..N-1 covering every document."""
        data = _load_json(ASSIGNMENTS_PATH)
        indices = sorted(entry["doc_index"] for entry in data)
        expected = list(range(len(data)))
        assert indices == expected, (
            "doc_index values must be sequential 0..N-1 with no gaps or duplicates"
        )

    def test_count_matches_documents(self):
        """Number of assignments must equal number of documents."""
        docs = _load_json(DOCUMENTS_PATH)
        assignments = _load_json(ASSIGNMENTS_PATH)
        assert len(assignments) == len(docs), (
            f"topic_assignments has {len(assignments)} entries but "
            f"documents has {len(docs)} entries"
        )

    def test_topic_ids_include_valid_values(self):
        """topic_id should be -1 (outlier) or a non-negative integer."""
        data = _load_json(ASSIGNMENTS_PATH)
        for i, entry in enumerate(data):
            tid = entry["topic_id"]
            assert tid >= -1, f"Entry {i}: topic_id {tid} is invalid (must be >= -1)"

    def test_topic_labels_non_empty(self):
        """All topic labels must be non-empty strings."""
        data = _load_json(ASSIGNMENTS_PATH)
        for i, entry in enumerate(data):
            label = entry["topic_label"].strip()
            assert len(label) > 0, f"Entry {i}: topic_label is empty"

    def test_outlier_label_consistency(self):
        """Documents with topic_id == -1 should have 'Outlier' as label."""
        data = _load_json(ASSIGNMENTS_PATH)
        for i, entry in enumerate(data):
            if entry["topic_id"] == -1:
                assert entry["topic_label"] == "Outlier", (
                    f"Entry {i}: topic_id is -1 but label is '{entry['topic_label']}', "
                    f"expected 'Outlier'"
                )

    def test_has_multiple_distinct_topics(self):
        """The model should discover more than 1 topic (excluding outliers)."""
        data = _load_json(ASSIGNMENTS_PATH)
        non_outlier_ids = set(e["topic_id"] for e in data if e["topic_id"] != -1)
        assert len(non_outlier_ids) >= 2, (
            f"Expected at least 2 distinct non-outlier topics, got {len(non_outlier_ids)}"
        )


# ============================================================
# 3. metrics.json
# ============================================================

class TestMetrics:
    """Validate /app/metrics.json"""

    def test_file_exists(self):
        assert os.path.isfile(METRICS_PATH), "metrics.json not found"

    def test_is_json_object(self):
        data = _load_json(METRICS_PATH)
        assert isinstance(data, dict), "metrics.json must be a JSON object"

    def test_required_keys_present(self):
        data = _load_json(METRICS_PATH)
        required = {
            "total_documents", "num_topics", "outlier_count",
            "outlier_ratio", "topic_distribution", "candidate_labels",
        }
        missing = required - set(data.keys())
        assert not missing, f"metrics.json missing keys: {missing}"

    def test_total_documents_type_and_range(self):
        data = _load_json(METRICS_PATH)
        td = data["total_documents"]
        assert isinstance(td, int), f"total_documents must be int, got {type(td).__name__}"
        assert MIN_EXPECTED_DOCS <= td <= MAX_EXPECTED_DOCS, (
            f"total_documents={td} outside expected range [{MIN_EXPECTED_DOCS}, {MAX_EXPECTED_DOCS}]"
        )

    def test_total_documents_matches_documents_json(self):
        docs = _load_json(DOCUMENTS_PATH)
        metrics = _load_json(METRICS_PATH)
        assert metrics["total_documents"] == len(docs), (
            f"metrics.total_documents ({metrics['total_documents']}) != "
            f"len(documents.json) ({len(docs)})"
        )

    def test_num_topics_positive(self):
        data = _load_json(METRICS_PATH)
        nt = data["num_topics"]
        assert isinstance(nt, int), f"num_topics must be int, got {type(nt).__name__}"
        assert nt > 0, f"num_topics must be > 0, got {nt}"

    def test_num_topics_reasonable(self):
        """With 5 candidate labels, num_topics should be between 1 and 20."""
        data = _load_json(METRICS_PATH)
        nt = data["num_topics"]
        assert 1 <= nt <= 20, (
            f"num_topics={nt} seems unreasonable for 5 candidate labels"
        )

    def test_outlier_count_type_and_range(self):
        data = _load_json(METRICS_PATH)
        oc = data["outlier_count"]
        assert isinstance(oc, int), f"outlier_count must be int, got {type(oc).__name__}"
        assert 0 <= oc <= data["total_documents"], (
            f"outlier_count={oc} out of range [0, {data['total_documents']}]"
        )

    def test_outlier_ratio_type_and_range(self):
        data = _load_json(METRICS_PATH)
        oratio = data["outlier_ratio"]
        assert isinstance(oratio, (int, float)), (
            f"outlier_ratio must be numeric, got {type(oratio).__name__}"
        )
        assert 0.0 <= oratio <= 1.0, (
            f"outlier_ratio={oratio} must be between 0.0 and 1.0"
        )

    def test_outlier_ratio_consistency(self):
        """outlier_ratio should equal outlier_count / total_documents (within tolerance)."""
        data = _load_json(METRICS_PATH)
        expected = data["outlier_count"] / data["total_documents"]
        assert np.isclose(data["outlier_ratio"], expected, atol=1e-3), (
            f"outlier_ratio={data['outlier_ratio']} != "
            f"outlier_count/total_documents={expected:.4f}"
        )

    def test_candidate_labels_exact(self):
        data = _load_json(METRICS_PATH)
        cl = data["candidate_labels"]
        assert isinstance(cl, list), "candidate_labels must be a list"
        assert cl == EXPECTED_CANDIDATE_LABELS, (
            f"candidate_labels mismatch.\n"
            f"  Expected: {EXPECTED_CANDIDATE_LABELS}\n"
            f"  Got:      {cl}"
        )

    def test_topic_distribution_is_dict(self):
        data = _load_json(METRICS_PATH)
        td = data["topic_distribution"]
        assert isinstance(td, dict), (
            f"topic_distribution must be an object, got {type(td).__name__}"
        )

    def test_topic_distribution_values_are_positive_ints(self):
        data = _load_json(METRICS_PATH)
        td = data["topic_distribution"]
        for label, count in td.items():
            assert isinstance(count, int), (
                f"topic_distribution['{label}'] must be int, got {type(count).__name__}"
            )
            assert count > 0, (
                f"topic_distribution['{label}'] = {count}, expected > 0"
            )

    def test_topic_distribution_sum_equals_total(self):
        """Sum of all topic_distribution values must equal total_documents."""
        data = _load_json(METRICS_PATH)
        dist_sum = sum(data["topic_distribution"].values())
        assert dist_sum == data["total_documents"], (
            f"sum(topic_distribution) = {dist_sum} != "
            f"total_documents = {data['total_documents']}"
        )

    def test_topic_distribution_has_outlier_key_if_outliers_exist(self):
        """If outlier_count > 0, topic_distribution must have an 'Outlier' key."""
        data = _load_json(METRICS_PATH)
        if data["outlier_count"] > 0:
            assert "Outlier" in data["topic_distribution"], (
                "outlier_count > 0 but 'Outlier' key missing from topic_distribution"
            )
            assert data["topic_distribution"]["Outlier"] == data["outlier_count"], (
                f"topic_distribution['Outlier'] = {data['topic_distribution']['Outlier']} "
                f"!= outlier_count = {data['outlier_count']}"
            )

    def test_num_topics_matches_distribution_keys(self):
        """num_topics should match the number of non-Outlier keys in topic_distribution."""
        data = _load_json(METRICS_PATH)
        non_outlier_keys = [k for k in data["topic_distribution"] if k != "Outlier"]
        assert data["num_topics"] == len(non_outlier_keys), (
            f"num_topics={data['num_topics']} but topic_distribution has "
            f"{len(non_outlier_keys)} non-Outlier keys: {non_outlier_keys}"
        )


# ============================================================
# 4. saved_model/ directory
# ============================================================

class TestSavedModel:
    """Validate /app/saved_model/ directory exists and contains model files."""

    def test_directory_exists(self):
        assert os.path.isdir(MODEL_DIR), f"Model directory not found: {MODEL_DIR}"

    def test_directory_not_empty(self):
        assert os.path.isdir(MODEL_DIR), f"Model directory not found: {MODEL_DIR}"
        contents = os.listdir(MODEL_DIR)
        assert len(contents) > 0, "saved_model/ directory is empty"

    def test_has_model_files(self):
        """The directory should contain at least one recognizable model artifact."""
        assert os.path.isdir(MODEL_DIR), f"Model directory not found: {MODEL_DIR}"
        contents = os.listdir(MODEL_DIR)
        # BERTopic saves various files depending on serialization method:
        # safetensors: topic_embeddings.safetensors, ctfidf.safetensors, etc.
        # pytorch: pytorch_model.bin or similar
        # pickle: bertopic_model.pkl or similar
        # Also common: topics.json, config.json, etc.
        # We just check there's at least one non-trivial file
        has_model_file = False
        for item in contents:
            full_path = os.path.join(MODEL_DIR, item)
            if os.path.isfile(full_path):
                size = os.path.getsize(full_path)
                if size > 100:  # non-trivial file
                    has_model_file = True
                    break
            elif os.path.isdir(full_path):
                # Could be a subdirectory with model files
                has_model_file = True
                break
        assert has_model_file, (
            f"saved_model/ has no recognizable model files. Contents: {contents}"
        )


# ============================================================
# 5. Cross-file consistency
# ============================================================

class TestCrossFileConsistency:
    """Validate consistency across all output files."""

    def test_assignments_length_matches_metrics(self):
        """len(topic_assignments) must equal metrics.total_documents."""
        assignments = _load_json(ASSIGNMENTS_PATH)
        metrics = _load_json(METRICS_PATH)
        assert len(assignments) == metrics["total_documents"], (
            f"len(topic_assignments)={len(assignments)} != "
            f"metrics.total_documents={metrics['total_documents']}"
        )

    def test_assignment_topic_ids_match_metrics(self):
        """Non-outlier topic count from assignments should match num_topics in metrics."""
        assignments = _load_json(ASSIGNMENTS_PATH)
        metrics = _load_json(METRICS_PATH)
        unique_non_outlier = set(
            e["topic_id"] for e in assignments if e["topic_id"] != -1
        )
        assert len(unique_non_outlier) == metrics["num_topics"], (
            f"Unique non-outlier topic IDs in assignments: {len(unique_non_outlier)} "
            f"!= metrics.num_topics: {metrics['num_topics']}"
        )

    def test_outlier_count_matches_assignments(self):
        """Count of topic_id==-1 in assignments should match metrics.outlier_count."""
        assignments = _load_json(ASSIGNMENTS_PATH)
        metrics = _load_json(METRICS_PATH)
        outliers_in_assignments = sum(
            1 for e in assignments if e["topic_id"] == -1
        )
        assert outliers_in_assignments == metrics["outlier_count"], (
            f"Outliers in assignments: {outliers_in_assignments} != "
            f"metrics.outlier_count: {metrics['outlier_count']}"
        )

    def test_topic_labels_in_assignments_match_distribution(self):
        """Labels used in assignments should appear in topic_distribution."""
        assignments = _load_json(ASSIGNMENTS_PATH)
        metrics = _load_json(METRICS_PATH)
        labels_in_assignments = set(e["topic_label"] for e in assignments)
        dist_keys = set(metrics["topic_distribution"].keys())
        assert labels_in_assignments == dist_keys, (
            f"Labels in assignments: {labels_in_assignments} != "
            f"topic_distribution keys: {dist_keys}"
        )

    def test_distribution_counts_match_assignments(self):
        """Each label's count in topic_distribution should match actual count in assignments."""
        assignments = _load_json(ASSIGNMENTS_PATH)
        metrics = _load_json(METRICS_PATH)
        # Count labels from assignments
        label_counts = {}
        for e in assignments:
            lbl = e["topic_label"]
            label_counts[lbl] = label_counts.get(lbl, 0) + 1
        for label, expected_count in metrics["topic_distribution"].items():
            actual = label_counts.get(label, 0)
            assert actual == expected_count, (
                f"topic_distribution['{label}']={expected_count} but "
                f"assignments has {actual} docs with that label"
            )
