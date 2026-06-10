"""
Tests for Movie Recommender with Matrix Factorization task.
Validates /app/output.json structure, content, and /app/best_model.pt.
"""
import os
import json
import math
import pytest

# ── Paths ──────────────────────────────────────────────────────────────────
OUTPUT_JSON = "/app/output.json"
MODEL_PATH = "/app/best_model.pt"


# ── Helpers ────────────────────────────────────────────────────────────────
def load_output():
    """Load and return the output JSON, or None on failure."""
    if not os.path.isfile(OUTPUT_JSON):
        return None
    with open(OUTPUT_JSON, "r") as f:
        return json.load(f)


def _count_decimal_places(value):
    """Return the number of decimal places in a float's string representation."""
    s = str(value)
    if "." not in s:
        return 0
    # Handle scientific notation
    if "e" in s.lower():
        return -1  # can't easily count, skip
    return len(s.split(".")[1])


# ══════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE
# ══════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"

    def test_output_json_not_empty(self):
        assert os.path.getsize(OUTPUT_JSON) > 10, f"{OUTPUT_JSON} is empty or trivially small"

    def test_best_model_exists(self):
        assert os.path.isfile(MODEL_PATH), f"{MODEL_PATH} does not exist"

    def test_best_model_not_empty(self):
        assert os.path.getsize(MODEL_PATH) > 100, f"{MODEL_PATH} is trivially small"


# ══════════════════════════════════════════════════════════════════════════
# 2. JSON SCHEMA – TOP-LEVEL KEYS
# ══════════════════════════════════════════════════════════════════════════

class TestJsonTopLevelSchema:
    REQUIRED_KEYS = [
        "best_hyperparameters",
        "metrics",
        "top5_recommendations_user0",
        "num_users",
        "num_movies",
        "num_train",
        "num_val",
    ]

    def test_json_is_valid(self):
        data = load_output()
        assert data is not None, "Could not parse output.json"

    def test_all_top_level_keys_present(self):
        data = load_output()
        assert data is not None
        for key in self.REQUIRED_KEYS:
            assert key in data, f"Missing top-level key: {key}"


# ══════════════════════════════════════════════════════════════════════════
# 3. BEST HYPERPARAMETERS
# ══════════════════════════════════════════════════════════════════════════

class TestBestHyperparameters:
    def _hp(self):
        data = load_output()
        assert data is not None
        assert "best_hyperparameters" in data
        return data["best_hyperparameters"]

    def test_has_required_keys(self):
        hp = self._hp()
        for key in ["latent_dim", "weight_decay", "learning_rate", "num_epochs"]:
            assert key in hp, f"Missing hyperparameter key: {key}"

    def test_latent_dim_is_positive_int(self):
        hp = self._hp()
        assert isinstance(hp["latent_dim"], int), "latent_dim must be int"
        assert hp["latent_dim"] > 0, "latent_dim must be positive"

    def test_weight_decay_is_positive_float(self):
        hp = self._hp()
        wd = hp["weight_decay"]
        assert isinstance(wd, (int, float)), "weight_decay must be numeric"
        assert wd >= 0, "weight_decay must be non-negative"

    def test_learning_rate_is_positive_float(self):
        hp = self._hp()
        lr = hp["learning_rate"]
        assert isinstance(lr, (int, float)), "learning_rate must be numeric"
        assert lr > 0, "learning_rate must be positive"

    def test_num_epochs_at_least_20(self):
        hp = self._hp()
        assert isinstance(hp["num_epochs"], int), "num_epochs must be int"
        assert hp["num_epochs"] >= 20, "num_epochs must be >= 20 as required"


# ══════════════════════════════════════════════════════════════════════════
# 4. METRICS
# ══════════════════════════════════════════════════════════════════════════

class TestMetrics:
    def _metrics(self):
        data = load_output()
        assert data is not None
        assert "metrics" in data
        return data["metrics"]

    def test_has_required_keys(self):
        m = self._metrics()
        for key in ["val_rmse", "precision_at_10", "recall_at_10"]:
            assert key in m, f"Missing metric key: {key}"

    def test_val_rmse_is_float(self):
        m = self._metrics()
        assert isinstance(m["val_rmse"], (int, float)), "val_rmse must be numeric"

    def test_val_rmse_below_threshold(self):
        m = self._metrics()
        assert m["val_rmse"] < 1.0, f"val_rmse={m['val_rmse']} must be < 1.0"

    def test_val_rmse_is_reasonable(self):
        """RMSE should be positive and realistically above 0.5 for this dataset."""
        m = self._metrics()
        assert m["val_rmse"] > 0.0, "val_rmse must be positive"

    def test_precision_at_10_in_range(self):
        m = self._metrics()
        p = m["precision_at_10"]
        assert isinstance(p, (int, float)), "precision_at_10 must be numeric"
        assert 0.0 <= p <= 1.0, f"precision_at_10={p} must be in [0, 1]"

    def test_recall_at_10_in_range(self):
        m = self._metrics()
        r = m["recall_at_10"]
        assert isinstance(r, (int, float)), "recall_at_10 must be numeric"
        assert 0.0 <= r <= 1.0, f"recall_at_10={r} must be in [0, 1]"


# ══════════════════════════════════════════════════════════════════════════
# 5. TOP-5 RECOMMENDATIONS FOR USER 0
# ══════════════════════════════════════════════════════════════════════════

class TestTop5Recommendations:
    def _top5(self):
        data = load_output()
        assert data is not None
        assert "top5_recommendations_user0" in data
        return data["top5_recommendations_user0"]

    def test_exactly_5_entries(self):
        top5 = self._top5()
        assert isinstance(top5, list), "top5_recommendations_user0 must be a list"
        assert len(top5) == 5, f"Expected exactly 5 recommendations, got {len(top5)}"

    def test_each_entry_has_required_keys(self):
        top5 = self._top5()
        for i, entry in enumerate(top5):
            assert isinstance(entry, dict), f"Entry {i} must be a dict"
            for key in ["movie_id", "title", "predicted_rating"]:
                assert key in entry, f"Entry {i} missing key: {key}"

    def test_movie_ids_are_positive_ints(self):
        top5 = self._top5()
        for i, entry in enumerate(top5):
            mid = entry["movie_id"]
            assert isinstance(mid, int), f"Entry {i}: movie_id must be int, got {type(mid)}"
            assert mid > 0, f"Entry {i}: movie_id must be positive (original ML ID)"

    def test_movie_ids_in_valid_range(self):
        """MovieLens-100K movie IDs range from 1 to 1682."""
        top5 = self._top5()
        for i, entry in enumerate(top5):
            mid = entry["movie_id"]
            assert 1 <= mid <= 1682, f"Entry {i}: movie_id={mid} outside MovieLens-100K range [1,1682]"

    def test_titles_are_nonempty_strings(self):
        top5 = self._top5()
        for i, entry in enumerate(top5):
            title = entry["title"]
            assert isinstance(title, str), f"Entry {i}: title must be string"
            assert len(title.strip()) > 0, f"Entry {i}: title must not be empty"

    def test_predicted_ratings_are_numeric(self):
        top5 = self._top5()
        for i, entry in enumerate(top5):
            pr = entry["predicted_rating"]
            assert isinstance(pr, (int, float)), f"Entry {i}: predicted_rating must be numeric"

    def test_sorted_descending_by_predicted_rating(self):
        top5 = self._top5()
        ratings = [entry["predicted_rating"] for entry in top5]
        for i in range(len(ratings) - 1):
            assert ratings[i] >= ratings[i + 1], (
                f"top5 not sorted descending: index {i} ({ratings[i]}) < index {i+1} ({ratings[i+1]})"
            )

    def test_no_duplicate_movie_ids(self):
        top5 = self._top5()
        ids = [entry["movie_id"] for entry in top5]
        assert len(ids) == len(set(ids)), "Duplicate movie_ids in top-5 recommendations"


# ══════════════════════════════════════════════════════════════════════════
# 6. DATASET STATISTICS
# ══════════════════════════════════════════════════════════════════════════

class TestDatasetStatistics:
    """MovieLens-100K has 943 users, 1682 movies, 100000 ratings."""

    def _data(self):
        data = load_output()
        assert data is not None
        return data

    def test_num_users(self):
        d = self._data()
        assert isinstance(d["num_users"], int), "num_users must be int"
        assert d["num_users"] == 943, f"Expected 943 users, got {d['num_users']}"

    def test_num_movies(self):
        d = self._data()
        assert isinstance(d["num_movies"], int), "num_movies must be int"
        assert d["num_movies"] == 1682, f"Expected 1682 movies, got {d['num_movies']}"

    def test_num_train(self):
        d = self._data()
        assert isinstance(d["num_train"], int), "num_train must be int"
        assert d["num_train"] == 80000, f"Expected 80000 train samples (80% of 100K), got {d['num_train']}"

    def test_num_val(self):
        d = self._data()
        assert isinstance(d["num_val"], int), "num_val must be int"
        assert d["num_val"] == 20000, f"Expected 20000 val samples (20% of 100K), got {d['num_val']}"

    def test_train_val_sum(self):
        d = self._data()
        total = d["num_train"] + d["num_val"]
        assert total == 100000, f"train + val should be 100000, got {total}"


# ══════════════════════════════════════════════════════════════════════════
# 7. FLOAT PRECISION (4 decimal places)
# ══════════════════════════════════════════════════════════════════════════

class TestFloatPrecision:
    """All float values must be rounded to 4 decimal places."""

    def _check_decimal_places(self, value, name, max_places=4):
        """Check that a float has at most max_places decimal digits."""
        s = str(value)
        if "e" in s.lower():
            # Scientific notation — acceptable for very small values like 1e-05
            return
        if "." in s:
            decimal_part = s.split(".")[1]
            assert len(decimal_part) <= max_places, (
                f"{name}={value} has {len(decimal_part)} decimal places, expected <= {max_places}"
            )

    def test_metrics_precision(self):
        data = load_output()
        assert data is not None
        m = data["metrics"]
        self._check_decimal_places(m["val_rmse"], "val_rmse")
        self._check_decimal_places(m["precision_at_10"], "precision_at_10")
        self._check_decimal_places(m["recall_at_10"], "recall_at_10")

    def test_top5_predicted_rating_precision(self):
        data = load_output()
        assert data is not None
        for i, entry in enumerate(data["top5_recommendations_user0"]):
            self._check_decimal_places(
                entry["predicted_rating"],
                f"top5[{i}].predicted_rating",
            )


# ══════════════════════════════════════════════════════════════════════════
# 8. MODEL FILE LOADABILITY
# ══════════════════════════════════════════════════════════════════════════

class TestModelFile:
    def test_model_loadable_with_torch(self):
        """best_model.pt must be loadable via torch.load()."""
        import torch
        assert os.path.isfile(MODEL_PATH), f"{MODEL_PATH} not found"
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
        assert isinstance(state_dict, dict), "Model file should contain a state dict (dict)"
        assert len(state_dict) > 0, "State dict is empty"

    def test_model_has_expected_keys(self):
        """The MF model should have user/item embeddings and biases."""
        import torch
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
        key_str = " ".join(state_dict.keys()).lower()
        # Must contain embedding weights for users and movies/items
        has_user_emb = any("user" in k.lower() and "emb" in k.lower() for k in state_dict)
        has_movie_emb = any(
            ("movie" in k.lower() or "item" in k.lower()) and "emb" in k.lower()
            for k in state_dict
        )
        assert has_user_emb, f"State dict missing user embedding. Keys: {list(state_dict.keys())}"
        assert has_movie_emb, f"State dict missing movie/item embedding. Keys: {list(state_dict.keys())}"

    def test_model_embedding_dimensions(self):
        """Embedding dimensions should match num_users/num_movies from output."""
        import torch
        data = load_output()
        assert data is not None
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)

        # Find user embedding tensor
        user_emb_key = None
        movie_emb_key = None
        for k in state_dict:
            kl = k.lower()
            if "user" in kl and "emb" in kl and "bias" not in kl:
                user_emb_key = k
            if ("movie" in kl or "item" in kl) and "emb" in kl and "bias" not in kl:
                movie_emb_key = k

        if user_emb_key:
            shape = state_dict[user_emb_key].shape
            assert shape[0] == data["num_users"], (
                f"User embedding rows={shape[0]} != num_users={data['num_users']}"
            )
        if movie_emb_key:
            shape = state_dict[movie_emb_key].shape
            assert shape[0] == data["num_movies"], (
                f"Movie embedding rows={shape[0]} != num_movies={data['num_movies']}"
            )


# ══════════════════════════════════════════════════════════════════════════
# 9. CROSS-FIELD CONSISTENCY
# ══════════════════════════════════════════════════════════════════════════

class TestCrossFieldConsistency:
    def test_latent_dim_matches_model(self):
        """The latent_dim in hyperparameters should match the embedding width in the model."""
        import torch
        data = load_output()
        assert data is not None
        ld = data["best_hyperparameters"]["latent_dim"]
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
        for k in state_dict:
            kl = k.lower()
            if "user" in kl and "emb" in kl and "bias" not in kl:
                emb_dim = state_dict[k].shape[1]
                assert emb_dim == ld, (
                    f"Embedding dim={emb_dim} != reported latent_dim={ld}"
                )
                break
