"""
Tests for ALS Matrix Factorization Recommender on MovieLens 100K.
Validates all output files produced by the pipeline.
"""
import os
import json
import csv

import numpy as np
import pandas as pd

# All output files live in /app
APP_DIR = "/app"

# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_json(name):
    path = os.path.join(APP_DIR, name)
    assert os.path.isfile(path), f"{name} does not exist"
    assert os.path.getsize(path) > 0, f"{name} is empty"
    with open(path) as f:
        data = json.load(f)
    return data


def _load_csv_no_header(name):
    path = os.path.join(APP_DIR, name)
    assert os.path.isfile(path), f"{name} does not exist"
    assert os.path.getsize(path) > 0, f"{name} is empty"
    df = pd.read_csv(path, header=None, names=["user_id", "item_id", "rating"])
    return df


def _load_npy(name):
    path = os.path.join(APP_DIR, name)
    assert os.path.isfile(path), f"{name} does not exist"
    assert os.path.getsize(path) > 100, f"{name} appears too small / corrupt"
    arr = np.load(path)
    return arr


# ── 1. Train / Test CSV files ───────────────────────────────────────────────

class TestTrainTestSplit:
    """Validate train.csv and test.csv structure and content."""

    def test_train_csv_exists_and_nonempty(self):
        path = os.path.join(APP_DIR, "train.csv")
        assert os.path.isfile(path), "train.csv missing"
        assert os.path.getsize(path) > 0, "train.csv is empty"

    def test_test_csv_exists_and_nonempty(self):
        path = os.path.join(APP_DIR, "test.csv")
        assert os.path.isfile(path), "test.csv missing"
        assert os.path.getsize(path) > 0, "test.csv is empty"

    def test_train_csv_has_three_columns(self):
        df = _load_csv_no_header("train.csv")
        assert df.shape[1] == 3, f"Expected 3 columns, got {df.shape[1]}"

    def test_test_csv_has_three_columns(self):
        df = _load_csv_no_header("test.csv")
        assert df.shape[1] == 3, f"Expected 3 columns, got {df.shape[1]}"

    def test_split_ratio_approximately_80_20(self):
        """MovieLens 100K has 100000 ratings. 80/20 split."""
        train = _load_csv_no_header("train.csv")
        test = _load_csv_no_header("test.csv")
        total = len(train) + len(test)
        # Total should be 100000
        assert 99000 <= total <= 101000, (
            f"Total ratings {total} not close to 100000"
        )
        train_frac = len(train) / total
        assert 0.75 <= train_frac <= 0.85, (
            f"Train fraction {train_frac:.3f} not near 0.80"
        )

    def test_ratings_in_valid_range(self):
        """Ratings must be integers 1-5."""
        for name in ("train.csv", "test.csv"):
            df = _load_csv_no_header(name)
            assert df["rating"].between(1, 5).all(), (
                f"{name} has ratings outside [1, 5]"
            )

    def test_user_and_item_ids_positive(self):
        for name in ("train.csv", "test.csv"):
            df = _load_csv_no_header(name)
            assert (df["user_id"] > 0).all(), f"{name} has non-positive user_id"
            assert (df["item_id"] > 0).all(), f"{name} has non-positive item_id"

    def test_no_header_row_in_csv(self):
        """First row should be numeric data, not a header string."""
        for name in ("train.csv", "test.csv"):
            path = os.path.join(APP_DIR, name)
            with open(path) as f:
                first_line = f.readline().strip()
            parts = first_line.split(",")
            # All parts should be numeric
            for p in parts:
                try:
                    float(p)
                except ValueError:
                    raise AssertionError(
                        f"{name} appears to have a header row: {first_line}"
                    )


# ── 2. Model Factor Files (.npy) ────────────────────────────────────────────

class TestModelFactors:
    """Validate user_factors.npy and item_factors.npy."""

    def test_user_factors_exists(self):
        path = os.path.join(APP_DIR, "user_factors.npy")
        assert os.path.isfile(path), "user_factors.npy missing"

    def test_item_factors_exists(self):
        path = os.path.join(APP_DIR, "item_factors.npy")
        assert os.path.isfile(path), "item_factors.npy missing"

    def test_user_factors_is_2d_float32(self):
        U = _load_npy("user_factors.npy")
        assert U.ndim == 2, f"user_factors should be 2D, got {U.ndim}D"
        assert U.dtype == np.float32, f"Expected float32, got {U.dtype}"

    def test_item_factors_is_2d_float32(self):
        V = _load_npy("item_factors.npy")
        assert V.ndim == 2, f"item_factors should be 2D, got {V.ndim}D"
        assert V.dtype == np.float32, f"Expected float32, got {V.dtype}"

    def test_factors_rank_matches(self):
        """Both factor matrices must share the same latent rank."""
        U = _load_npy("user_factors.npy")
        V = _load_npy("item_factors.npy")
        assert U.shape[1] == V.shape[1], (
            f"Rank mismatch: user_factors rank={U.shape[1]}, "
            f"item_factors rank={V.shape[1]}"
        )

    def test_rank_within_search_range(self):
        """Rank should be in the 20-100 range per instruction."""
        U = _load_npy("user_factors.npy")
        rank = U.shape[1]
        assert 20 <= rank <= 100, f"Rank {rank} outside allowed range [20, 100]"

    def test_user_factors_shape_reasonable(self):
        """MovieLens 100K has 943 users."""
        U = _load_npy("user_factors.npy")
        n_users = U.shape[0]
        assert 900 <= n_users <= 1000, (
            f"n_users={n_users} not in expected range for MovieLens 100K"
        )

    def test_item_factors_shape_reasonable(self):
        """MovieLens 100K has 1682 items."""
        V = _load_npy("item_factors.npy")
        n_items = V.shape[0]
        assert 1600 <= n_items <= 1800, (
            f"n_items={n_items} not in expected range for MovieLens 100K"
        )

    def test_factors_not_all_zeros(self):
        """A trained model should have non-trivial factor values."""
        U = _load_npy("user_factors.npy")
        V = _load_npy("item_factors.npy")
        assert np.abs(U).sum() > 0, "user_factors is all zeros"
        assert np.abs(V).sum() > 0, "item_factors is all zeros"

    def test_factors_no_nan_or_inf(self):
        U = _load_npy("user_factors.npy")
        V = _load_npy("item_factors.npy")
        assert np.isfinite(U).all(), "user_factors contains NaN or Inf"
        assert np.isfinite(V).all(), "item_factors contains NaN or Inf"


# ── 3. metrics.json ─────────────────────────────────────────────────────────

REQUIRED_METRIC_KEYS = {
    "baseline_knn_rmse",
    "als_rmse",
    "training_time_seconds",
    "prediction_latency_ms",
    "peak_ram_mb",
    "als_rank",
    "als_reg",
    "als_iterations",
}


class TestMetrics:
    """Validate metrics.json structure and values."""

    def test_metrics_file_exists(self):
        path = os.path.join(APP_DIR, "metrics.json")
        assert os.path.isfile(path), "metrics.json missing"

    def test_metrics_is_valid_json(self):
        _load_json("metrics.json")

    def test_metrics_has_all_required_keys(self):
        m = _load_json("metrics.json")
        missing = REQUIRED_METRIC_KEYS - set(m.keys())
        assert not missing, f"Missing keys in metrics.json: {missing}"

    def test_baseline_knn_rmse_is_positive_float(self):
        m = _load_json("metrics.json")
        val = m["baseline_knn_rmse"]
        assert isinstance(val, (int, float)), "baseline_knn_rmse must be numeric"
        assert val > 0, "baseline_knn_rmse must be positive"

    def test_als_rmse_is_positive_float(self):
        m = _load_json("metrics.json")
        val = m["als_rmse"]
        assert isinstance(val, (int, float)), "als_rmse must be numeric"
        assert val > 0, "als_rmse must be positive"

    def test_als_beats_baseline(self):
        """Core requirement: ALS RMSE must be strictly less than k-NN RMSE."""
        m = _load_json("metrics.json")
        als = m["als_rmse"]
        knn = m["baseline_knn_rmse"]
        assert als < knn, (
            f"ALS RMSE ({als}) must be strictly less than "
            f"k-NN baseline RMSE ({knn})"
        )

    def test_rmse_values_in_reasonable_range(self):
        """For MovieLens 100K, RMSE should be roughly 0.8 - 1.5."""
        m = _load_json("metrics.json")
        for key in ("baseline_knn_rmse", "als_rmse"):
            val = m[key]
            assert 0.5 <= val <= 2.0, (
                f"{key}={val} outside plausible range [0.5, 2.0]"
            )

    def test_training_time_within_limit(self):
        m = _load_json("metrics.json")
        val = m["training_time_seconds"]
        assert isinstance(val, (int, float)), "training_time_seconds must be numeric"
        assert val > 0, "training_time_seconds must be positive"
        assert val <= 300, f"Training time {val}s exceeds 300s limit"

    def test_prediction_latency_within_limit(self):
        m = _load_json("metrics.json")
        val = m["prediction_latency_ms"]
        assert isinstance(val, (int, float)), "prediction_latency_ms must be numeric"
        assert val > 0, "prediction_latency_ms must be positive"
        assert val <= 5, f"Prediction latency {val}ms exceeds 5ms limit"

    def test_peak_ram_within_limit(self):
        m = _load_json("metrics.json")
        val = m["peak_ram_mb"]
        assert isinstance(val, (int, float)), "peak_ram_mb must be numeric"
        assert val > 0, "peak_ram_mb must be positive"
        assert val < 2048, f"Peak RAM {val}MB exceeds 2048MB limit"

    def test_als_rank_is_int_in_range(self):
        m = _load_json("metrics.json")
        val = m["als_rank"]
        assert isinstance(val, int), f"als_rank must be int, got {type(val)}"
        assert 20 <= val <= 100, f"als_rank={val} outside [20, 100]"

    def test_als_reg_is_float_in_range(self):
        m = _load_json("metrics.json")
        val = m["als_reg"]
        assert isinstance(val, (int, float)), "als_reg must be numeric"
        assert 0.01 <= val <= 1.0, f"als_reg={val} outside [0.01, 1.0]"

    def test_als_iterations_is_int_in_range(self):
        m = _load_json("metrics.json")
        val = m["als_iterations"]
        assert isinstance(val, int), f"als_iterations must be int, got {type(val)}"
        assert 10 <= val <= 30, f"als_iterations={val} outside [10, 30]"

    def test_float_values_rounded_to_4_decimals(self):
        """All float values should be rounded to 4 decimal places."""
        m = _load_json("metrics.json")
        float_keys = [
            "baseline_knn_rmse", "als_rmse", "training_time_seconds",
            "prediction_latency_ms", "peak_ram_mb", "als_reg",
        ]
        for key in float_keys:
            val = m[key]
            if isinstance(val, float):
                rounded = round(val, 4)
                assert abs(val - rounded) < 1e-9, (
                    f"{key}={val} not rounded to 4 decimal places"
                )

    def test_rank_matches_npy_factors(self):
        """als_rank in metrics must match the actual factor matrix rank."""
        m = _load_json("metrics.json")
        U = _load_npy("user_factors.npy")
        assert m["als_rank"] == U.shape[1], (
            f"metrics als_rank={m['als_rank']} != "
            f"user_factors rank={U.shape[1]}"
        )


# ── 4. recommendations.json ─────────────────────────────────────────────────

class TestRecommendations:
    """Validate recommendations.json structure and content."""

    def test_recommendations_file_exists(self):
        path = os.path.join(APP_DIR, "recommendations.json")
        assert os.path.isfile(path), "recommendations.json missing"

    def test_recommendations_is_valid_json(self):
        _load_json("recommendations.json")

    def test_recommendations_has_users_1_through_5(self):
        recs = _load_json("recommendations.json")
        for uid in ["1", "2", "3", "4", "5"]:
            assert uid in recs, f"User {uid} missing from recommendations.json"

    def test_each_user_has_exactly_10_recommendations(self):
        recs = _load_json("recommendations.json")
        for uid in ["1", "2", "3", "4", "5"]:
            items = recs[uid]
            assert isinstance(items, list), (
                f"User {uid} recommendations must be a list"
            )
            assert len(items) == 10, (
                f"User {uid} has {len(items)} recommendations, expected 10"
            )

    def test_recommended_items_are_integers(self):
        recs = _load_json("recommendations.json")
        for uid in ["1", "2", "3", "4", "5"]:
            for item in recs[uid]:
                assert isinstance(item, int), (
                    f"User {uid}: item {item} is not an integer"
                )

    def test_recommended_items_are_positive(self):
        recs = _load_json("recommendations.json")
        for uid in ["1", "2", "3", "4", "5"]:
            for item in recs[uid]:
                assert item > 0, (
                    f"User {uid}: item_id {item} must be positive"
                )

    def test_no_duplicate_recommendations_per_user(self):
        recs = _load_json("recommendations.json")
        for uid in ["1", "2", "3", "4", "5"]:
            items = recs[uid]
            assert len(items) == len(set(items)), (
                f"User {uid} has duplicate items in recommendations"
            )

    def test_recommended_items_within_movielens_range(self):
        """MovieLens 100K item IDs are in [1, 1682]."""
        recs = _load_json("recommendations.json")
        for uid in ["1", "2", "3", "4", "5"]:
            for item in recs[uid]:
                assert 1 <= item <= 1682, (
                    f"User {uid}: item_id {item} outside MovieLens range [1, 1682]"
                )

    def test_recommendations_exclude_training_items(self):
        """Recommended items must NOT be in the user's training set."""
        recs = _load_json("recommendations.json")
        train = _load_csv_no_header("train.csv")
        for uid_str in ["1", "2", "3", "4", "5"]:
            uid = int(uid_str)
            trained_items = set(
                train[train["user_id"] == uid]["item_id"].values
            )
            rec_items = set(recs[uid_str])
            overlap = rec_items & trained_items
            assert len(overlap) == 0, (
                f"User {uid}: recommended items {overlap} "
                f"were already in training set"
            )


# ── 5. Cross-file consistency checks ────────────────────────────────────────

class TestCrossFileConsistency:
    """Validate consistency across output files."""

    def test_npy_dimensions_consistent_with_data(self):
        """Factor matrix dimensions should match the number of unique
        users/items across train + test."""
        train = _load_csv_no_header("train.csv")
        test = _load_csv_no_header("test.csv")
        all_users = set(train["user_id"]) | set(test["user_id"])
        all_items = set(train["item_id"]) | set(test["item_id"])
        U = _load_npy("user_factors.npy")
        V = _load_npy("item_factors.npy")
        # Allow some tolerance — mapping may include only train users
        assert U.shape[0] >= len(set(train["user_id"])), (
            f"user_factors rows {U.shape[0]} < unique train users "
            f"{len(set(train['user_id']))}"
        )
        assert V.shape[0] >= len(set(train["item_id"])), (
            f"item_factors rows {V.shape[0]} < unique train items "
            f"{len(set(train['item_id']))}"
        )

    def test_model_produces_plausible_predictions(self):
        """Spot-check: dot product of user/item factors should produce
        values roughly in the rating range [1, 5] for most pairs."""
        U = _load_npy("user_factors.npy")
        V = _load_npy("item_factors.npy")
        # Sample 100 random user-item pairs
        rng = np.random.RandomState(42)
        u_idx = rng.randint(0, U.shape[0], size=100)
        i_idx = rng.randint(0, V.shape[0], size=100)
        preds = np.array([np.dot(U[u], V[i]) for u, i in zip(u_idx, i_idx)])
        # Most predictions should be in a reasonable range
        in_range = np.sum((preds >= 0) & (preds <= 7))
        assert in_range >= 80, (
            f"Only {in_range}/100 sampled predictions in [0, 7] — "
            f"model factors seem broken"
        )
