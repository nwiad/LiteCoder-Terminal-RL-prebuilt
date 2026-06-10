"""
Tests for CPU Anomaly Detection Pipeline.

Validates /app/output.csv against the constraints in instruction.md.
Assumes the agent has already completed the task and produced the output file.
"""

import os
import csv
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

OUTPUT_PATH = "/app/output.csv"
INPUT_PATH = "/app/input.csv"

EXPECTED_COLUMNS = ["timestamp", "cpu_load", "stat_flag", "ml_flag", "consensus_flag", "rank"]
ISO8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_output():
    """Load output.csv as a pandas DataFrame with minimal type coercion."""
    assert os.path.isfile(OUTPUT_PATH), f"Output file not found: {OUTPUT_PATH}"
    df = pd.read_csv(OUTPUT_PATH)
    assert len(df) > 0, "Output CSV is empty (no data rows)"
    return df


def load_input():
    """Load input.csv for cross-validation."""
    assert os.path.isfile(INPUT_PATH), f"Input file not found: {INPUT_PATH}"
    df = pd.read_csv(INPUT_PATH)
    return df


# ---------------------------------------------------------------------------
# 1. File existence and basic structure
# ---------------------------------------------------------------------------

class TestFileExistence:
    def test_output_file_exists(self):
        assert os.path.isfile(OUTPUT_PATH), "output.csv does not exist"

    def test_output_file_not_empty(self):
        size = os.path.getsize(OUTPUT_PATH)
        assert size > 100, f"output.csv is suspiciously small ({size} bytes)"


# ---------------------------------------------------------------------------
# 2. Schema validation
# ---------------------------------------------------------------------------

class TestSchema:
    def test_exact_column_names(self):
        df = load_output()
        assert list(df.columns) == EXPECTED_COLUMNS, (
            f"Expected columns {EXPECTED_COLUMNS}, got {list(df.columns)}"
        )

    def test_column_count(self):
        df = load_output()
        assert len(df.columns) == 6, f"Expected 6 columns, got {len(df.columns)}"


# ---------------------------------------------------------------------------
# 3. Row count validation
# ---------------------------------------------------------------------------

class TestRowCount:
    def test_row_count_reasonable(self):
        """After cleaning ~20160 rows with ~200 missing, forward-fill should
        recover most. Expect between 19900 and 20160 rows."""
        df = load_output()
        assert 19900 <= len(df) <= 20160, (
            f"Row count {len(df)} outside expected range [19900, 20160]"
        )

    def test_row_count_matches_cleaned_input(self):
        """The output row count should match the input after forward-fill + dropna."""
        inp = load_input()
        inp["cpu_load"] = pd.to_numeric(inp["cpu_load"], errors="coerce")
        inp["cpu_load"] = inp["cpu_load"].ffill()
        inp.dropna(subset=["cpu_load"], inplace=True)
        expected_rows = len(inp)

        df = load_output()
        assert len(df) == expected_rows, (
            f"Output has {len(df)} rows but cleaned input has {expected_rows} rows"
        )


# ---------------------------------------------------------------------------
# 4. Data type validation
# ---------------------------------------------------------------------------

class TestDataTypes:
    def test_stat_flag_binary(self):
        df = load_output()
        unique_vals = set(df["stat_flag"].unique())
        assert unique_vals.issubset({0, 1}), (
            f"stat_flag should be 0 or 1, got unique values: {unique_vals}"
        )

    def test_ml_flag_binary(self):
        df = load_output()
        unique_vals = set(df["ml_flag"].unique())
        assert unique_vals.issubset({0, 1}), (
            f"ml_flag should be 0 or 1, got unique values: {unique_vals}"
        )

    def test_consensus_flag_binary(self):
        df = load_output()
        unique_vals = set(df["consensus_flag"].unique())
        assert unique_vals.issubset({0, 1}), (
            f"consensus_flag should be 0 or 1, got unique values: {unique_vals}"
        )

    def test_rank_values_valid(self):
        df = load_output()
        valid_ranks = set(range(0, 21))  # 0 through 20
        actual_ranks = set(df["rank"].unique())
        assert actual_ranks.issubset(valid_ranks), (
            f"rank values should be 0-20, got: {actual_ranks - valid_ranks}"
        )

    def test_cpu_load_numeric(self):
        df = load_output()
        assert pd.api.types.is_numeric_dtype(df["cpu_load"]), (
            "cpu_load column should be numeric"
        )

    def test_cpu_load_no_nan(self):
        df = load_output()
        assert df["cpu_load"].isna().sum() == 0, (
            "cpu_load should have no NaN values after cleaning"
        )

    def test_flags_are_integers(self):
        """Flags and rank must be integer-typed (not float)."""
        df = load_output()
        for col in ["stat_flag", "ml_flag", "consensus_flag", "rank"]:
            # Check that values are whole numbers
            vals = df[col].dropna()
            assert (vals == vals.astype(int)).all(), (
                f"{col} contains non-integer values"
            )


# ---------------------------------------------------------------------------
# 5. Timestamp validation
# ---------------------------------------------------------------------------

class TestTimestamps:
    def test_timestamp_format(self):
        """All timestamps must match YYYY-MM-DDTHH:MM:SSZ."""
        df = load_output()
        sample = df["timestamp"].head(100)
        for ts in sample:
            assert ISO8601_PATTERN.match(str(ts)), (
                f"Timestamp '{ts}' does not match ISO 8601 format YYYY-MM-DDTHH:MM:SSZ"
            )

    def test_timestamps_sorted_ascending(self):
        df = load_output()
        timestamps = pd.to_datetime(df["timestamp"])
        assert timestamps.is_monotonic_increasing, (
            "Rows are not sorted by timestamp in ascending order"
        )

    def test_timestamp_no_duplicates_excessive(self):
        """There should be very few or no duplicate timestamps."""
        df = load_output()
        dup_count = df["timestamp"].duplicated().sum()
        assert dup_count < 10, (
            f"Found {dup_count} duplicate timestamps, expected near 0"
        )


# ---------------------------------------------------------------------------
# 6. Logical constraint validation (CORE)
# ---------------------------------------------------------------------------

class TestLogicalConstraints:
    def test_consensus_implies_both_flags(self):
        """Every row with consensus_flag==1 must have stat_flag==1 AND ml_flag==1."""
        df = load_output()
        consensus_rows = df[df["consensus_flag"] == 1]
        if len(consensus_rows) == 0:
            # At least some consensus anomalies should exist given the data
            assert False, "No consensus anomalies found — pipeline likely broken"

        bad_stat = consensus_rows[consensus_rows["stat_flag"] != 1]
        assert len(bad_stat) == 0, (
            f"{len(bad_stat)} consensus rows have stat_flag != 1"
        )
        bad_ml = consensus_rows[consensus_rows["ml_flag"] != 1]
        assert len(bad_ml) == 0, (
            f"{len(bad_ml)} consensus rows have ml_flag != 1"
        )

    def test_rank_implies_consensus(self):
        """Every row with rank > 0 must have consensus_flag == 1."""
        df = load_output()
        ranked = df[df["rank"] > 0]
        bad = ranked[ranked["consensus_flag"] != 1]
        assert len(bad) == 0, (
            f"{len(bad)} ranked rows do not have consensus_flag == 1"
        )

    def test_at_most_20_ranked(self):
        """At most 20 rows may have rank > 0."""
        df = load_output()
        ranked_count = (df["rank"] > 0).sum()
        assert ranked_count <= 20, (
            f"Found {ranked_count} ranked rows, maximum allowed is 20"
        )

    def test_at_least_one_ranked(self):
        """Given the injected anomalies, there should be at least 1 ranked row."""
        df = load_output()
        ranked_count = (df["rank"] > 0).sum()
        assert ranked_count >= 1, "No ranked anomalies found — pipeline likely broken"

    def test_ranks_are_contiguous_from_1(self):
        """Ranks should be 1, 2, 3, ..., N with no gaps."""
        df = load_output()
        ranks = sorted(df[df["rank"] > 0]["rank"].tolist())
        if len(ranks) > 0:
            expected = list(range(1, len(ranks) + 1))
            assert ranks == expected, (
                f"Ranks are not contiguous from 1: got {ranks}"
            )

    def test_non_consensus_rows_have_rank_zero(self):
        """Rows with consensus_flag==0 must have rank==0."""
        df = load_output()
        non_consensus = df[df["consensus_flag"] == 0]
        bad = non_consensus[non_consensus["rank"] != 0]
        assert len(bad) == 0, (
            f"{len(bad)} non-consensus rows have non-zero rank"
        )


# ---------------------------------------------------------------------------
# 7. Statistical anomaly detector validation
# ---------------------------------------------------------------------------

class TestStatisticalDetector:
    def test_stat_flag_count_reasonable(self):
        """With Z-score threshold 3.0, expect a small fraction of rows flagged.
        The data has ~35 spikes + ~25 dips injected. Stat flags should be
        in a reasonable range (at least 10, at most 500)."""
        df = load_output()
        stat_count = df["stat_flag"].sum()
        assert 10 <= stat_count <= 500, (
            f"stat_flag count {stat_count} outside expected range [10, 500]"
        )

    def test_stat_flagged_rows_have_extreme_cpu_load(self):
        """Rows flagged by stat detector should have cpu_load far from the mean.
        Verify that flagged rows' cpu_load deviates significantly from the
        overall mean (at least 2 std devs as a loose check)."""
        df = load_output()
        mean_load = df["cpu_load"].mean()
        std_load = df["cpu_load"].std()

        flagged = df[df["stat_flag"] == 1]
        if len(flagged) == 0:
            assert False, "No statistical anomalies detected"

        # Every flagged row should be at least 2 std devs from mean
        # (using 2.0 as a loose bound; the actual threshold is 3.0)
        for _, row in flagged.iterrows():
            z = abs(row["cpu_load"] - mean_load) / std_load
            assert z > 2.0, (
                f"stat_flag=1 row at {row['timestamp']} has z-score {z:.2f} < 2.0"
            )

    def test_normal_rows_not_extreme(self):
        """Spot-check: rows with stat_flag=0 should generally not have |z| > 3.5.
        Allow a tiny tolerance for edge cases."""
        df = load_output()
        mean_load = df["cpu_load"].mean()
        std_load = df["cpu_load"].std()

        normal = df[df["stat_flag"] == 0]
        # Check that the vast majority of normal rows are within bounds
        extreme_normal = 0
        for _, row in normal.sample(min(500, len(normal)), random_state=42).iterrows():
            z = abs(row["cpu_load"] - mean_load) / std_load
            if z > 3.5:
                extreme_normal += 1
        assert extreme_normal == 0, (
            f"{extreme_normal} normal rows have |z| > 3.5 — stat detector may be wrong"
        )


# ---------------------------------------------------------------------------
# 8. ML anomaly detector validation
# ---------------------------------------------------------------------------

class TestMLDetector:
    def test_ml_flag_count_near_one_percent(self):
        """Isolation Forest with contamination=0.01 should flag ~1% of rows.
        Allow range 0.5% to 2.0% for implementation variance."""
        df = load_output()
        ml_count = df["ml_flag"].sum()
        total = len(df)
        pct = ml_count / total * 100
        assert 0.5 <= pct <= 2.0, (
            f"ML flag rate {pct:.2f}% outside expected range [0.5%, 2.0%] "
            f"(contamination=0.01 should give ~1%)"
        )

    def test_ml_flagged_rows_have_unusual_cpu_load(self):
        """ML-flagged rows should generally have cpu_load that differs from
        the median more than the average row."""
        df = load_output()
        median_load = df["cpu_load"].median()
        flagged = df[df["ml_flag"] == 1]
        normal = df[df["ml_flag"] == 0]

        if len(flagged) == 0:
            assert False, "No ML anomalies detected"

        avg_dev_flagged = (flagged["cpu_load"] - median_load).abs().mean()
        avg_dev_normal = (normal["cpu_load"] - median_load).abs().mean()

        # Flagged rows should deviate more on average
        assert avg_dev_flagged > avg_dev_normal, (
            f"ML-flagged rows avg deviation ({avg_dev_flagged:.3f}) not greater "
            f"than normal rows ({avg_dev_normal:.3f})"
        )


# ---------------------------------------------------------------------------
# 9. Consensus and ranking validation
# ---------------------------------------------------------------------------

class TestConsensusAndRanking:
    def test_consensus_count_reasonable(self):
        """Consensus anomalies (both detectors agree) should exist but be fewer
        than either individual detector's count."""
        df = load_output()
        consensus_count = df["consensus_flag"].sum()
        stat_count = df["stat_flag"].sum()
        ml_count = df["ml_flag"].sum()

        assert consensus_count > 0, "No consensus anomalies found"
        assert consensus_count <= stat_count, (
            f"Consensus count ({consensus_count}) > stat count ({stat_count})"
        )
        assert consensus_count <= ml_count, (
            f"Consensus count ({consensus_count}) > ml count ({ml_count})"
        )

    def test_ranked_rows_ordered_by_severity(self):
        """Ranked rows (rank 1..N) should be ordered by decreasing anomaly
        severity. Rank 1 should have the most extreme cpu_load deviation."""
        df = load_output()
        ranked = df[df["rank"] > 0].copy()
        if len(ranked) < 2:
            return  # Not enough to check ordering

        mean_load = df["cpu_load"].mean()
        std_load = df["cpu_load"].std()

        ranked["abs_z"] = ((ranked["cpu_load"] - mean_load) / std_load).abs()
        ranked_sorted = ranked.sort_values("rank")

        # Verify that abs_z is non-increasing as rank increases
        abs_z_values = ranked_sorted["abs_z"].tolist()
        for i in range(len(abs_z_values) - 1):
            assert abs_z_values[i] >= abs_z_values[i + 1] - 0.01, (
                f"Rank {i+1} has |z|={abs_z_values[i]:.3f} but rank {i+2} "
                f"has |z|={abs_z_values[i+1]:.3f} — not in descending order"
            )

    def test_rank_1_is_most_anomalous(self):
        """The row with rank=1 should have the highest absolute z-score
        among all consensus anomalies."""
        df = load_output()
        mean_load = df["cpu_load"].mean()
        std_load = df["cpu_load"].std()

        consensus = df[df["consensus_flag"] == 1].copy()
        if len(consensus) == 0:
            return

        consensus["abs_z"] = ((consensus["cpu_load"] - mean_load) / std_load).abs()
        max_z_row = consensus.loc[consensus["abs_z"].idxmax()]
        rank1_rows = df[df["rank"] == 1]

        assert len(rank1_rows) == 1, (
            f"Expected exactly 1 row with rank=1, found {len(rank1_rows)}"
        )
        rank1_z = abs(rank1_rows.iloc[0]["cpu_load"] - mean_load) / std_load
        # Allow small tolerance for float precision
        assert np.isclose(rank1_z, max_z_row["abs_z"], atol=0.1), (
            f"Rank 1 |z|={rank1_z:.3f} != max consensus |z|={max_z_row['abs_z']:.3f}"
        )

    def test_each_rank_unique(self):
        """Each rank value 1..N should appear exactly once."""
        df = load_output()
        ranked = df[df["rank"] > 0]
        rank_counts = ranked["rank"].value_counts()
        duplicates = rank_counts[rank_counts > 1]
        assert len(duplicates) == 0, (
            f"Duplicate rank values found: {duplicates.to_dict()}"
        )


# ---------------------------------------------------------------------------
# 10. Data cleaning validation
# ---------------------------------------------------------------------------

class TestDataCleaning:
    def test_cpu_load_all_positive_or_zero(self):
        """After cleaning, cpu_load should be >= 0."""
        df = load_output()
        neg = df[df["cpu_load"] < 0]
        assert len(neg) == 0, (
            f"{len(neg)} rows have negative cpu_load after cleaning"
        )

    def test_output_timestamps_subset_of_input(self):
        """All output timestamps should come from the input data."""
        df = load_output()
        inp = load_input()
        output_ts = set(df["timestamp"].tolist())
        input_ts = set(inp["timestamp"].tolist())
        extra = output_ts - input_ts
        assert len(extra) == 0, (
            f"{len(extra)} output timestamps not found in input"
        )

    def test_missing_values_handled(self):
        """The input has ~200 missing cpu_load values. The output should have
        fewer rows than the input only if leading NaNs couldn't be forward-filled.
        The output should never have more rows than the input."""
        df = load_output()
        inp = load_input()
        assert len(df) <= len(inp), (
            f"Output has {len(df)} rows but input only has {len(inp)} rows"
        )

