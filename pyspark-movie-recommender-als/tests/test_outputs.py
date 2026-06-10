"""
Tests for PySpark Movie Recommender ALS task.
Validates output files, JSON schema, report content, CLI interface, and model quality.
"""
import os
import json
import re
import subprocess

# ─── Paths ───────────────────────────────────────────────────────────────────
OUTPUT_DIR = "/app/output"
RECOMMENDATIONS_JSON = os.path.join(OUTPUT_DIR, "recommendations.json")
REPORT_TXT = os.path.join(OUTPUT_DIR, "report.txt")
ALS_MODEL_DIR = os.path.join(OUTPUT_DIR, "als_model")
RECOMMEND_SCRIPT = "/app/recommend.py"
MOVIES_DAT = "/app/ml-1m/movies.dat"
RATINGS_DAT = "/app/ml-1m/ratings.dat"


def _load_movie_titles():
    """Load all movie titles from movies.dat."""
    titles = set()
    with open(MOVIES_DAT, "r", encoding="latin-1") as f:
        for line in f:
            parts = line.strip().split("::")
            if len(parts) >= 2:
                titles.add(parts[1])
    return titles


def _load_user_rated_movie_ids(user_id):
    """Load MovieIDs that a given user has rated."""
    rated = set()
    with open(RATINGS_DAT, "r", encoding="latin-1") as f:
        for line in f:
            parts = line.strip().split("::")
            if len(parts) >= 2 and int(parts[0]) == user_id:
                rated.add(int(parts[1]))
    return rated


def _load_all_user_ids():
    """Load all unique user IDs from ratings.dat."""
    users = set()
    with open(RATINGS_DAT, "r", encoding="latin-1") as f:
        for line in f:
            parts = line.strip().split("::")
            if len(parts) >= 1:
                users.add(int(parts[0]))
    return users


# ═══════════════════════════════════════════════════════════════════════════════
# 1. OUTPUT FILE EXISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    def test_recommendations_json_exists(self):
        assert os.path.isfile(RECOMMENDATIONS_JSON), (
            f"Missing output file: {RECOMMENDATIONS_JSON}"
        )

    def test_report_txt_exists(self):
        assert os.path.isfile(REPORT_TXT), (
            f"Missing output file: {REPORT_TXT}"
        )

    def test_als_model_dir_exists(self):
        assert os.path.isdir(ALS_MODEL_DIR), (
            f"Missing saved model directory: {ALS_MODEL_DIR}"
        )

    def test_als_model_not_empty(self):
        """Model directory should contain actual model artifacts."""
        assert os.path.isdir(ALS_MODEL_DIR), f"Missing: {ALS_MODEL_DIR}"
        contents = os.listdir(ALS_MODEL_DIR)
        assert len(contents) > 0, "ALS model directory is empty"

    def test_recommend_script_exists(self):
        assert os.path.isfile(RECOMMEND_SCRIPT), (
            f"Missing CLI script: {RECOMMEND_SCRIPT}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. RECOMMENDATIONS.JSON VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecommendationsJson:
    def _load(self):
        assert os.path.isfile(RECOMMENDATIONS_JSON), "File missing"
        with open(RECOMMENDATIONS_JSON, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "recommendations.json is empty"
        return json.loads(content)

    def test_valid_json(self):
        """File must be parseable JSON."""
        self._load()

    def test_top_level_keys(self):
        data = self._load()
        for key in ("user_id", "recommendations", "count"):
            assert key in data, f"Missing top-level key: '{key}'"

    def test_user_id_is_123(self):
        data = self._load()
        assert data["user_id"] == 123, (
            f"Expected user_id=123, got {data['user_id']}"
        )

    def test_count_equals_5(self):
        data = self._load()
        assert data["count"] == 5, f"Expected count=5, got {data['count']}"

    def test_count_matches_list_length(self):
        data = self._load()
        assert data["count"] == len(data["recommendations"]), (
            f"count ({data['count']}) != len(recommendations) "
            f"({len(data['recommendations'])})"
        )

    def test_recommendation_item_schema(self):
        """Each recommendation must have movie_title (str) and predicted_rating (float)."""
        data = self._load()
        for i, rec in enumerate(data["recommendations"]):
            assert "movie_title" in rec, f"Item {i} missing 'movie_title'"
            assert "predicted_rating" in rec, f"Item {i} missing 'predicted_rating'"
            assert isinstance(rec["movie_title"], str), (
                f"Item {i}: movie_title should be str, got {type(rec['movie_title'])}"
            )
            assert isinstance(rec["predicted_rating"], (int, float)), (
                f"Item {i}: predicted_rating should be numeric, got {type(rec['predicted_rating'])}"
            )

    def test_predicted_ratings_4_decimal_places(self):
        """Predicted ratings must be rounded to at most 4 decimal places."""
        data = self._load()
        for i, rec in enumerate(data["recommendations"]):
            rating = rec["predicted_rating"]
            rating_str = str(rating)
            if "." in rating_str:
                decimals = len(rating_str.split(".")[1])
                assert decimals <= 4, (
                    f"Item {i}: predicted_rating has {decimals} decimals (max 4)"
                )

    def test_sorted_descending_by_predicted_rating(self):
        """Recommendations must be sorted by predicted_rating descending."""
        data = self._load()
        ratings = [r["predicted_rating"] for r in data["recommendations"]]
        for i in range(len(ratings) - 1):
            assert ratings[i] >= ratings[i + 1], (
                f"Not sorted descending: index {i} ({ratings[i]}) < index {i+1} ({ratings[i+1]})"
            )

    def test_movie_titles_are_from_dataset(self):
        """Recommended movie titles must exist in movies.dat."""
        data = self._load()
        all_titles = _load_movie_titles()
        for rec in data["recommendations"]:
            assert rec["movie_title"] in all_titles, (
                f"Movie title '{rec['movie_title']}' not found in movies.dat"
            )

    def test_recommended_movies_not_already_rated(self):
        """Recommended movies should NOT be ones user 123 already rated."""
        data = self._load()
        # Build a set of titles that user 123 rated
        rated_ids = _load_user_rated_movie_ids(123)
        # Map MovieID -> Title from movies.dat
        id_to_title = {}
        with open(MOVIES_DAT, "r", encoding="latin-1") as f:
            for line in f:
                parts = line.strip().split("::")
                if len(parts) >= 2:
                    id_to_title[int(parts[0])] = parts[1]
        rated_titles = {id_to_title[mid] for mid in rated_ids if mid in id_to_title}
        for rec in data["recommendations"]:
            assert rec["movie_title"] not in rated_titles, (
                f"Movie '{rec['movie_title']}' was already rated by user 123"
            )

    def test_predicted_ratings_in_reasonable_range(self):
        """Predicted ratings should be in a plausible range (0-6)."""
        data = self._load()
        for rec in data["recommendations"]:
            r = rec["predicted_rating"]
            assert 0.0 <= r <= 6.0, (
                f"Predicted rating {r} out of plausible range [0, 6]"
            )

    def test_no_duplicate_movie_titles(self):
        """No duplicate movie titles in recommendations."""
        data = self._load()
        titles = [r["movie_title"] for r in data["recommendations"]]
        assert len(titles) == len(set(titles)), "Duplicate movie titles found"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. REPORT.TXT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestReportTxt:
    def _load(self):
        assert os.path.isfile(REPORT_TXT), "report.txt missing"
        with open(REPORT_TXT, "r") as f:
            content = f.read()
        assert len(content.strip()) > 0, "report.txt is empty"
        return content

    def test_contains_rmse_line(self):
        """Report must contain a line matching 'RMSE: <value>'."""
        content = self._load()
        match = re.search(r"RMSE:\s*([\d.]+)", content)
        assert match is not None, "No 'RMSE: <value>' line found in report.txt"

    def test_rmse_below_threshold(self):
        """RMSE value must be below 1.0."""
        content = self._load()
        match = re.search(r"RMSE:\s*([\d.]+)", content)
        assert match is not None, "No RMSE line found"
        rmse = float(match.group(1))
        assert rmse < 1.0, f"RMSE {rmse} is not below 1.0"

    def test_rmse_is_positive(self):
        """RMSE should be a positive number."""
        content = self._load()
        match = re.search(r"RMSE:\s*([\d.]+)", content)
        assert match is not None, "No RMSE line found"
        rmse = float(match.group(1))
        assert rmse > 0.0, f"RMSE {rmse} should be positive"

    def test_contains_als_parameters(self):
        """Report must mention ALS model parameters: rank, regParam, maxIter."""
        content = self._load().lower()
        assert "rank" in content, "Report missing ALS parameter: rank"
        assert "regparam" in content or "reg_param" in content or "reg param" in content, (
            "Report missing ALS parameter: regParam"
        )
        assert "maxiter" in content or "max_iter" in content or "max iter" in content, (
            "Report missing ALS parameter: maxIter"
        )

    def test_contains_cleaning_summary(self):
        """Report must contain a summary of data-cleaning steps."""
        content = self._load().lower()
        # Should mention cleaning-related concepts
        has_cleaning = any(kw in content for kw in [
            "clean", "dedup", "duplicate", "null", "missing", "initial", "removed"
        ])
        assert has_cleaning, "Report missing data-cleaning summary"

    def test_contains_recommendations_for_user_123(self):
        """Report must list top-5 recommendations for user 123."""
        content = self._load()
        assert "123" in content, "Report does not mention user 123"
        # Should contain at least some movie titles
        all_titles = _load_movie_titles()
        found = sum(1 for t in all_titles if t in content)
        assert found >= 1, "Report does not list any movie titles from the dataset"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CLI INTERFACE (recommend.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCLIInterface:
    """Test the recommend.py CLI script."""

    def _run_cli(self, args, timeout=300):
        """Run recommend.py with given args, return (stdout, returncode)."""
        cmd = ["python3", RECOMMEND_SCRIPT] + [str(a) for a in args]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.returncode

    def test_valid_user_exit_code_0(self):
        """CLI should exit 0 for a valid user."""
        if not os.path.isfile(RECOMMEND_SCRIPT):
            assert False, "recommend.py not found"
        if not os.path.isdir(ALS_MODEL_DIR):
            assert False, "ALS model not saved; CLI cannot run"
        stdout, rc = self._run_cli([1, 5])
        assert rc == 0, f"Expected exit code 0 for valid user, got {rc}"

    def test_valid_user_returns_json(self):
        """CLI output for valid user must be valid JSON."""
        if not os.path.isfile(RECOMMEND_SCRIPT) or not os.path.isdir(ALS_MODEL_DIR):
            assert False, "Prerequisites missing"
        stdout, rc = self._run_cli([1, 5])
        assert rc == 0, f"Exit code {rc}"
        # Extract last JSON object from stdout (skip Spark log noise)
        data = _extract_json_from_output(stdout)
        assert data is not None, f"Could not parse JSON from CLI output"

    def test_valid_user_json_schema(self):
        """CLI JSON output must have user_id, recommendations, count."""
        if not os.path.isfile(RECOMMEND_SCRIPT) or not os.path.isdir(ALS_MODEL_DIR):
            assert False, "Prerequisites missing"
        stdout, rc = self._run_cli([1, 5])
        data = _extract_json_from_output(stdout)
        assert data is not None, "No JSON in output"
        assert "user_id" in data, "Missing 'user_id'"
        assert "recommendations" in data, "Missing 'recommendations'"
        assert "count" in data, "Missing 'count'"
        assert data["user_id"] == 1
        assert data["count"] == len(data["recommendations"])

    def test_valid_user_recommendation_items(self):
        """Each CLI recommendation item must have movie_title and predicted_rating."""
        if not os.path.isfile(RECOMMEND_SCRIPT) or not os.path.isdir(ALS_MODEL_DIR):
            assert False, "Prerequisites missing"
        stdout, rc = self._run_cli([1, 3])
        data = _extract_json_from_output(stdout)
        assert data is not None, "No JSON in output"
        for i, rec in enumerate(data["recommendations"]):
            assert "movie_title" in rec, f"Item {i} missing movie_title"
            assert "predicted_rating" in rec, f"Item {i} missing predicted_rating"

    def test_invalid_user_exit_code_1(self):
        """CLI should exit 1 for a non-existent user."""
        if not os.path.isfile(RECOMMEND_SCRIPT) or not os.path.isdir(ALS_MODEL_DIR):
            assert False, "Prerequisites missing"
        stdout, rc = self._run_cli([999999])
        assert rc == 1, f"Expected exit code 1 for invalid user, got {rc}"

    def test_invalid_user_error_message(self):
        """CLI should output error JSON for non-existent user."""
        if not os.path.isfile(RECOMMEND_SCRIPT) or not os.path.isdir(ALS_MODEL_DIR):
            assert False, "Prerequisites missing"
        stdout, rc = self._run_cli([999999])
        data = _extract_json_from_output(stdout)
        assert data is not None, "No JSON in error output"
        assert "error" in data, "Error JSON missing 'error' key"
        assert "999999" in data["error"], (
            f"Error message should mention user ID 999999, got: {data['error']}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CROSS-VALIDATION: JSON vs REPORT CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossConsistency:
    """Verify that recommendations.json and report.txt are consistent."""

    def test_rmse_consistent_between_json_and_report(self):
        """RMSE in report should be a valid positive number below 1.0."""
        if not os.path.isfile(REPORT_TXT):
            assert False, "report.txt missing"
        with open(REPORT_TXT, "r") as f:
            content = f.read()
        match = re.search(r"RMSE:\s*([\d.]+)", content)
        assert match is not None
        rmse = float(match.group(1))
        assert 0.0 < rmse < 1.0, f"RMSE {rmse} not in valid range (0, 1)"

    def test_report_mentions_same_movies_as_json(self):
        """At least some movie titles from recommendations.json should appear in report."""
        if not os.path.isfile(RECOMMENDATIONS_JSON) or not os.path.isfile(REPORT_TXT):
            assert False, "Output files missing"
        with open(RECOMMENDATIONS_JSON, "r") as f:
            data = json.load(f)
        with open(REPORT_TXT, "r") as f:
            report = f.read()
        json_titles = [r["movie_title"] for r in data["recommendations"]]
        found = sum(1 for t in json_titles if t in report)
        assert found >= 1, (
            "None of the movie titles from recommendations.json appear in report.txt"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Extract JSON from potentially noisy CLI output
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_json_from_output(stdout):
    """
    Try to extract a JSON object from stdout that may contain Spark log lines.
    Tries the full string first, then scans for the last '{' ... '}' block.
    """
    # Try full string first
    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to find the last JSON object in the output
    # (Spark may print log lines before the JSON)
    brace_depth = 0
    start = None
    end = None
    for i in range(len(stdout) - 1, -1, -1):
        if stdout[i] == '}':
            if brace_depth == 0:
                end = i
            brace_depth += 1
        elif stdout[i] == '{':
            brace_depth -= 1
            if brace_depth == 0:
                start = i
                break

    if start is not None and end is not None:
        try:
            return json.loads(stdout[start:end + 1])
        except (json.JSONDecodeError, ValueError):
            pass

    return None
