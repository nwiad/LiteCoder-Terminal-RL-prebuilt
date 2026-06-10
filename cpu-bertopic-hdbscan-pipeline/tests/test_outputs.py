"""
Tests for CPU-Optimized BERTopic HDBSCAN Pipeline.

Validates the four key outputs:
  1. /app/data/abstracts.json   — synthetic dataset
  2. /app/output/results.json   — training results
  3. /app/output/model/         — saved BERTopic model
  4. /app/output/prediction.json — prediction demo output
"""
import json
import os
import pathlib

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ABSTRACTS_PATH = "/app/data/abstracts.json"
RESULTS_PATH = "/app/output/results.json"
MODEL_DIR = "/app/output/model"
PREDICTION_PATH = "/app/output/prediction.json"

PREDICTION_INPUT_TEXT = (
    "Deep reinforcement learning has shown remarkable success in game playing "
    "and robotic control tasks, combining neural network function approximation "
    "with temporal difference learning methods."
)

# ===========================================================================
# Helper loaders (return None on failure so individual tests can report clearly)
# ===========================================================================

def _load_json(path):
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        data = json.load(f)
    return data


# ===========================================================================
# 1. abstracts.json — Synthetic Dataset Tests
# ===========================================================================

class TestAbstracts:
    """Validate /app/data/abstracts.json"""

    def test_file_exists(self):
        assert os.path.isfile(ABSTRACTS_PATH), "abstracts.json does not exist"

    def test_is_valid_json_list(self):
        data = _load_json(ABSTRACTS_PATH)
        assert isinstance(data, list), "abstracts.json root must be a JSON array"

    def test_exactly_200_abstracts(self):
        data = _load_json(ABSTRACTS_PATH)
        assert len(data) == 200, f"Expected 200 abstracts, got {len(data)}"

    def test_required_fields_present(self):
        data = _load_json(ABSTRACTS_PATH)
        required = {"id", "title", "abstract", "domain"}
        for i, item in enumerate(data):
            missing = required - set(item.keys())
            assert not missing, f"Abstract {i} missing fields: {missing}"

    def test_id_field_is_int(self):
        data = _load_json(ABSTRACTS_PATH)
        for item in data:
            assert isinstance(item["id"], int), f"id must be int, got {type(item['id'])}"

    def test_title_and_abstract_are_nonempty_strings(self):
        data = _load_json(ABSTRACTS_PATH)
        for i, item in enumerate(data):
            assert isinstance(item["title"], str) and len(item["title"].strip()) > 0, \
                f"Abstract {i}: title must be a non-empty string"
            assert isinstance(item["abstract"], str) and len(item["abstract"].strip()) > 0, \
                f"Abstract {i}: abstract must be a non-empty string"

    def test_domain_is_nonempty_string(self):
        data = _load_json(ABSTRACTS_PATH)
        for i, item in enumerate(data):
            assert isinstance(item["domain"], str) and len(item["domain"].strip()) > 0, \
                f"Abstract {i}: domain must be a non-empty string"

    def test_at_least_5_distinct_domains(self):
        data = _load_json(ABSTRACTS_PATH)
        domains = {item["domain"] for item in data}
        assert len(domains) >= 5, f"Expected >=5 domains, got {len(domains)}: {domains}"

    def test_abstract_word_count_in_range(self):
        """Each abstract should be 40-120 words (with small tolerance)."""
        data = _load_json(ABSTRACTS_PATH)
        violations = []
        for i, item in enumerate(data):
            wc = len(item["abstract"].split())
            # Allow slight tolerance: 30-150 to not penalize minor variance
            if wc < 30 or wc > 150:
                violations.append((i, wc))
        assert len(violations) == 0, (
            f"{len(violations)} abstracts outside 30-150 word range: "
            f"{violations[:5]}{'...' if len(violations) > 5 else ''}"
        )

    def test_ids_cover_0_to_199(self):
        data = _load_json(ABSTRACTS_PATH)
        ids = sorted(item["id"] for item in data)
        assert ids == list(range(200)), "IDs must be 0..199 (each appearing once)"


# ===========================================================================
# 2. results.json — Training Results Tests
# ===========================================================================

class TestResults:
    """Validate /app/output/results.json"""

    def test_file_exists(self):
        assert os.path.isfile(RESULTS_PATH), "results.json does not exist"

    def test_is_valid_json_object(self):
        data = _load_json(RESULTS_PATH)
        assert isinstance(data, dict), "results.json root must be a JSON object"

    def test_required_top_level_keys(self):
        data = _load_json(RESULTS_PATH)
        required = {"num_topics", "topics", "topic_assignments", "outlier_count"}
        missing = required - set(data.keys())
        assert not missing, f"results.json missing keys: {missing}"

    def test_num_topics_at_least_3(self):
        data = _load_json(RESULTS_PATH)
        nt = data["num_topics"]
        assert isinstance(nt, int), f"num_topics must be int, got {type(nt)}"
        assert nt >= 3, f"Must discover >=3 non-outlier topics, got {nt}"

    def test_topics_is_list_with_entries(self):
        data = _load_json(RESULTS_PATH)
        topics = data["topics"]
        assert isinstance(topics, list), "topics must be a list"
        assert len(topics) >= 3, f"Expected >=3 topic entries, got {len(topics)}"

    def test_topic_entry_schema(self):
        data = _load_json(RESULTS_PATH)
        required_keys = {"topic_id", "count", "top_words", "representative_doc_ids"}
        for i, t in enumerate(data["topics"]):
            missing = required_keys - set(t.keys())
            assert not missing, f"Topic entry {i} missing keys: {missing}"
            assert isinstance(t["topic_id"], int), f"topic_id must be int in entry {i}"
            assert isinstance(t["count"], int) and t["count"] > 0, \
                f"count must be positive int in entry {i}"
            assert isinstance(t["top_words"], list), f"top_words must be list in entry {i}"
            assert isinstance(t["representative_doc_ids"], list), \
                f"representative_doc_ids must be list in entry {i}"

    def test_non_outlier_topics_have_top_words(self):
        """Each non-outlier topic must have at least 1 top word (instruction says 5)."""
        data = _load_json(RESULTS_PATH)
        for t in data["topics"]:
            if t["topic_id"] >= 0:
                assert len(t["top_words"]) >= 1, \
                    f"Topic {t['topic_id']} has no top_words"
                for w in t["top_words"]:
                    assert isinstance(w, str) and len(w.strip()) > 0, \
                        f"Topic {t['topic_id']}: top_words must be non-empty strings"

    def test_representative_doc_ids_valid(self):
        """representative_doc_ids should be ints in [0, 199] with at most 3 entries."""
        data = _load_json(RESULTS_PATH)
        for t in data["topics"]:
            ids = t["representative_doc_ids"]
            assert len(ids) <= 10, \
                f"Topic {t['topic_id']}: too many representative_doc_ids ({len(ids)})"
            for did in ids:
                assert isinstance(did, int) and 0 <= did <= 199, \
                    f"Topic {t['topic_id']}: invalid doc id {did}"

    def test_topic_assignments_length_200(self):
        data = _load_json(RESULTS_PATH)
        ta = data["topic_assignments"]
        assert isinstance(ta, list), "topic_assignments must be a list"
        assert len(ta) == 200, f"topic_assignments length must be 200, got {len(ta)}"

    def test_topic_assignments_are_ints(self):
        data = _load_json(RESULTS_PATH)
        for i, t in enumerate(data["topic_assignments"]):
            assert isinstance(t, int), f"topic_assignments[{i}] must be int, got {type(t)}"

    def test_topic_assignments_reference_known_topics(self):
        """Every assignment must reference a topic_id that exists in the topics list."""
        data = _load_json(RESULTS_PATH)
        known_ids = {t["topic_id"] for t in data["topics"]}
        for i, t in enumerate(data["topic_assignments"]):
            assert t in known_ids, \
                f"topic_assignments[{i}]={t} not in known topic ids {known_ids}"

    def test_outlier_count_is_nonneg_int(self):
        data = _load_json(RESULTS_PATH)
        oc = data["outlier_count"]
        assert isinstance(oc, int) and oc >= 0, \
            f"outlier_count must be non-negative int, got {oc}"

    def test_outlier_count_matches_assignments(self):
        """outlier_count should equal the number of -1 entries in topic_assignments."""
        data = _load_json(RESULTS_PATH)
        actual = sum(1 for t in data["topic_assignments"] if t == -1)
        assert data["outlier_count"] == actual, \
            f"outlier_count={data['outlier_count']} but found {actual} assignments of -1"

    def test_num_topics_matches_topic_entries(self):
        """num_topics should equal the count of topic entries with topic_id >= 0."""
        data = _load_json(RESULTS_PATH)
        non_outlier = [t for t in data["topics"] if t["topic_id"] >= 0]
        assert data["num_topics"] == len(non_outlier), (
            f"num_topics={data['num_topics']} but found {len(non_outlier)} "
            f"non-outlier topic entries"
        )

    def test_topic_counts_sum_to_200(self):
        """Sum of all topic counts should equal 200 (total documents)."""
        data = _load_json(RESULTS_PATH)
        total = sum(t["count"] for t in data["topics"])
        assert total == 200, f"Topic counts sum to {total}, expected 200"


# ===========================================================================
# 3. Model Directory Tests
# ===========================================================================

class TestModelDirectory:
    """Validate /app/output/model/ exists and is non-trivial."""

    def test_model_dir_exists(self):
        assert os.path.isdir(MODEL_DIR), f"Model directory not found: {MODEL_DIR}"

    def test_model_dir_not_empty(self):
        assert os.path.isdir(MODEL_DIR), f"Model directory not found: {MODEL_DIR}"
        contents = os.listdir(MODEL_DIR)
        assert len(contents) > 0, "Model directory is empty"

    def test_model_dir_has_meaningful_size(self):
        """Model directory should contain files with real data (not just empty stubs)."""
        assert os.path.isdir(MODEL_DIR), f"Model directory not found: {MODEL_DIR}"
        total_size = 0
        for root, dirs, files in os.walk(MODEL_DIR):
            for f in files:
                total_size += os.path.getsize(os.path.join(root, f))
        # A real BERTopic model save should be at least a few KB
        assert total_size > 1000, (
            f"Model directory total size is only {total_size} bytes — "
            f"expected a real saved model"
        )


# ===========================================================================
# 4. prediction.json — Prediction Demo Tests
# ===========================================================================

class TestPrediction:
    """Validate /app/output/prediction.json"""

    def test_file_exists(self):
        assert os.path.isfile(PREDICTION_PATH), "prediction.json does not exist"

    def test_is_valid_json_object(self):
        data = _load_json(PREDICTION_PATH)
        assert isinstance(data, dict), "prediction.json root must be a JSON object"

    def test_required_keys(self):
        data = _load_json(PREDICTION_PATH)
        required = {"input_text", "predicted_topic", "topic_words", "all_topic_probabilities"}
        missing = required - set(data.keys())
        assert not missing, f"prediction.json missing keys: {missing}"

    def test_input_text_matches(self):
        """The input_text field must match the hard-coded sentence from the instruction."""
        data = _load_json(PREDICTION_PATH)
        actual = data["input_text"].strip()
        expected = PREDICTION_INPUT_TEXT.strip()
        assert actual == expected, (
            f"input_text mismatch.\n  Expected: {expected!r}\n  Got: {actual!r}"
        )

    def test_predicted_topic_is_int(self):
        data = _load_json(PREDICTION_PATH)
        pt = data["predicted_topic"]
        assert isinstance(pt, int), f"predicted_topic must be int, got {type(pt)}"

    def test_topic_words_is_list_of_strings(self):
        data = _load_json(PREDICTION_PATH)
        tw = data["topic_words"]
        assert isinstance(tw, list), f"topic_words must be a list, got {type(tw)}"
        for i, w in enumerate(tw):
            assert isinstance(w, str), f"topic_words[{i}] must be str, got {type(w)}"

    def test_topic_words_nonempty_if_non_outlier(self):
        """If predicted topic >= 0, there should be at least 1 topic word."""
        data = _load_json(PREDICTION_PATH)
        if data["predicted_topic"] >= 0:
            assert len(data["topic_words"]) >= 1, \
                "Non-outlier predicted topic should have at least 1 topic word"

    def test_all_topic_probabilities_is_dict(self):
        data = _load_json(PREDICTION_PATH)
        atp = data["all_topic_probabilities"]
        assert isinstance(atp, dict), \
            f"all_topic_probabilities must be a dict, got {type(atp)}"

    def test_all_topic_probabilities_values_are_floats(self):
        """If probabilities are provided, values must be numeric in [0, 1]."""
        data = _load_json(PREDICTION_PATH)
        atp = data["all_topic_probabilities"]
        if len(atp) > 0:
            for k, v in atp.items():
                assert isinstance(k, str), \
                    f"Probability key must be string, got {type(k)}"
                assert isinstance(v, (int, float)), \
                    f"Probability for topic {k} must be numeric, got {type(v)}"
                assert 0.0 <= float(v) <= 1.0 + 1e-6, \
                    f"Probability for topic {k}={v} outside [0, 1]"


# ===========================================================================
# 5. Cross-file Consistency Tests
# ===========================================================================

class TestCrossFileConsistency:
    """Validate consistency between output files."""

    def test_prediction_topic_exists_in_results(self):
        """The predicted topic should be one of the topics in results.json."""
        pred = _load_json(PREDICTION_PATH)
        results = _load_json(RESULTS_PATH)
        known_ids = {t["topic_id"] for t in results["topics"]}
        pt = pred["predicted_topic"]
        assert pt in known_ids, \
            f"predicted_topic={pt} not found in results topics {known_ids}"

    def test_results_doc_ids_reference_valid_abstracts(self):
        """representative_doc_ids in results should be valid abstract indices."""
        abstracts = _load_json(ABSTRACTS_PATH)
        results = _load_json(RESULTS_PATH)
        valid_ids = {item["id"] for item in abstracts}
        for t in results["topics"]:
            for did in t["representative_doc_ids"]:
                assert did in valid_ids, \
                    f"Topic {t['topic_id']}: doc id {did} not in abstracts"
