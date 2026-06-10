"""
Tests for PyTorch RNN Stock Price Prediction task.
Validates all output artifacts: CSV data, model weights, plot, and JSON report.
"""

import os
import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

# All artifacts are expected at /app/
APP_DIR = "/app"
CSV_PATH = os.path.join(APP_DIR, "aapl_30d.csv")
MODEL_PATH = os.path.join(APP_DIR, "model.pt")
PLOT_PATH = os.path.join(APP_DIR, "actual_vs_predicted.png")
REPORT_PATH = os.path.join(APP_DIR, "report.json")


# ============================================================
# Test 1: All required files exist and are non-empty
# ============================================================
class TestFileExistence:
    def test_csv_exists(self):
        assert os.path.isfile(CSV_PATH), f"Missing: {CSV_PATH}"
        assert os.path.getsize(CSV_PATH) > 100, "CSV file is too small / likely empty"

    def test_model_exists(self):
        assert os.path.isfile(MODEL_PATH), f"Missing: {MODEL_PATH}"
        assert os.path.getsize(MODEL_PATH) > 100, "Model file is too small / likely empty"

    def test_plot_exists(self):
        assert os.path.isfile(PLOT_PATH), f"Missing: {PLOT_PATH}"
        assert os.path.getsize(PLOT_PATH) > 1000, "Plot file is too small / likely a dummy"

    def test_report_exists(self):
        assert os.path.isfile(REPORT_PATH), f"Missing: {REPORT_PATH}"
        assert os.path.getsize(REPORT_PATH) > 50, "Report file is too small / likely empty"


# ============================================================
# Test 2: CSV data validation
# ============================================================
class TestCSVData:
    def _load_csv(self):
        return pd.read_csv(CSV_PATH)

    def test_csv_columns(self):
        df = self._load_csv()
        expected_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
        assert list(df.columns) == expected_cols, (
            f"Expected columns {expected_cols}, got {list(df.columns)}"
        )

    def test_csv_row_count(self):
        df = self._load_csv()
        assert len(df) == 30, f"Expected 30 data rows, got {len(df)}"

    def test_csv_start_date(self):
        df = self._load_csv()
        first_date = str(df["Date"].iloc[0]).strip()
        assert first_date == "2024-01-02", f"Start date should be 2024-01-02, got {first_date}"

    def test_csv_dates_are_business_days(self):
        df = self._load_csv()
        dates = pd.to_datetime(df["Date"])
        # Business days are Mon-Fri (dayofweek 0-4)
        for d in dates:
            assert d.dayofweek < 5, f"Date {d} is a weekend, expected business days only"

    def test_csv_dates_consecutive_business_days(self):
        df = self._load_csv()
        dates = pd.to_datetime(df["Date"])
        expected = pd.bdate_range(start="2024-01-02", periods=30)
        for actual, exp in zip(dates, expected):
            assert actual == exp, f"Date mismatch: expected {exp}, got {actual}"

    def test_csv_close_starts_near_180(self):
        df = self._load_csv()
        first_close = float(df["Close"].iloc[0])
        assert 170.0 <= first_close <= 190.0, (
            f"First Close should be near 180.0, got {first_close}"
        )

    def test_csv_prices_are_floats_2dp(self):
        df = self._load_csv()
        for col in ["Open", "High", "Low", "Close"]:
            for idx, val in enumerate(df[col]):
                fval = float(val)
                rounded = round(fval, 2)
                assert np.isclose(fval, rounded, atol=1e-9), (
                    f"Row {idx}, {col}={fval} not rounded to 2 decimal places"
                )

    def test_csv_volume_integers(self):
        df = self._load_csv()
        for idx, vol in enumerate(df["Volume"]):
            assert float(vol) == int(vol), f"Row {idx} Volume={vol} is not an integer"
            assert int(vol) > 0, f"Row {idx} Volume should be positive"

    def test_csv_volume_realistic_range(self):
        df = self._load_csv()
        volumes = df["Volume"].astype(int)
        # Volumes should be in the millions range (instruction says so)
        assert volumes.min() >= 1_000_000, (
            f"Min volume {volumes.min()} is too low, expected millions range"
        )

    def test_csv_high_low_consistency(self):
        df = self._load_csv()
        for idx in range(len(df)):
            h = float(df["High"].iloc[idx])
            l = float(df["Low"].iloc[idx])
            o = float(df["Open"].iloc[idx])
            c = float(df["Close"].iloc[idx])
            assert h >= l, f"Row {idx}: High ({h}) < Low ({l})"
            assert h >= o, f"Row {idx}: High ({h}) < Open ({o})"
            assert h >= c, f"Row {idx}: High ({h}) < Close ({c})"
            assert l <= o, f"Row {idx}: Low ({l}) > Open ({o})"
            assert l <= c, f"Row {idx}: Low ({l}) > Close ({c})"


# ============================================================
# Test 3: Model state_dict validation
# ============================================================
class TestModel:
    def _load_state_dict(self):
        return torch.load(MODEL_PATH, map_location="cpu", weights_only=True)

    def test_model_loadable(self):
        sd = self._load_state_dict()
        assert isinstance(sd, dict), "state_dict should be a dictionary"
        assert len(sd) > 0, "state_dict is empty"

    def test_model_has_rnn_keys(self):
        sd = self._load_state_dict()
        key_str = " ".join(sd.keys())
        # Must contain 'rnn' layer keys (not lstm, not gru)
        assert "rnn" in key_str.lower(), (
            f"Model keys {list(sd.keys())} do not contain 'rnn' — wrong architecture?"
        )
        # Should NOT be an LSTM or GRU
        assert "lstm" not in key_str.lower(), "Model uses LSTM instead of RNN"
        assert "gru" not in key_str.lower(), "Model uses GRU instead of RNN"

    def test_model_hidden_size_16(self):
        sd = self._load_state_dict()
        # RNN weight_hh has shape (hidden_size, hidden_size)
        hh_key = [k for k in sd.keys() if "weight_hh" in k]
        assert len(hh_key) > 0, "No weight_hh found in state_dict"
        hh_shape = sd[hh_key[0]].shape
        assert hh_shape[0] == 16, f"hidden_size should be 16, got {hh_shape[0]}"
        assert hh_shape[1] == 16, f"weight_hh shape mismatch: {hh_shape}"

    def test_model_input_size_1(self):
        sd = self._load_state_dict()
        ih_key = [k for k in sd.keys() if "weight_ih" in k]
        assert len(ih_key) > 0, "No weight_ih found in state_dict"
        ih_shape = sd[ih_key[0]].shape
        # weight_ih shape: (hidden_size, input_size)
        assert ih_shape[1] == 1, f"input_size should be 1, got {ih_shape[1]}"

    def test_model_fc_output_layer(self):
        sd = self._load_state_dict()
        fc_keys = [k for k in sd.keys() if "fc" in k.lower() or "linear" in k.lower() or "out" in k.lower()]
        # Find a weight key that maps 16 -> 1
        found = False
        for k in sd.keys():
            shape = sd[k].shape
            if len(shape) == 2 and shape[0] == 1 and shape[1] == 16:
                found = True
                break
        assert found, (
            f"No linear layer mapping 16->1 found. Keys: {list(sd.keys())}"
        )


# ============================================================
# Test 4: Report JSON validation
# ============================================================
class TestReport:
    def _load_report(self):
        with open(REPORT_PATH, "r") as f:
            return json.load(f)

    def test_report_is_valid_json(self):
        report = self._load_report()
        assert isinstance(report, dict), "Report should be a JSON object"

    def test_report_top_level_keys(self):
        report = self._load_report()
        for key in ["model", "metrics", "data"]:
            assert key in report, f"Missing top-level key: '{key}'"

    def test_report_model_section(self):
        report = self._load_report()
        model = report["model"]
        assert model["type"] == "RNN", f"model.type should be 'RNN', got '{model.get('type')}'"
        assert model["hidden_size"] == 16, f"model.hidden_size should be 16"
        assert model["num_layers"] == 1, f"model.num_layers should be 1"
        assert model["nonlinearity"] == "tanh", f"model.nonlinearity should be 'tanh'"
        assert model["lookback"] == 5, f"model.lookback should be 5"
        assert isinstance(model["epochs"], int), "model.epochs should be int"
        assert model["epochs"] >= 100, f"model.epochs should be >= 100, got {model['epochs']}"
        assert isinstance(model["learning_rate"], (int, float)), "model.learning_rate should be numeric"
        assert model["learning_rate"] > 0, "model.learning_rate should be positive"
        assert model["optimizer"] == "Adam", f"model.optimizer should be 'Adam'"
        assert model["loss_function"] == "MSE", f"model.loss_function should be 'MSE'"

    def test_report_metrics_section(self):
        report = self._load_report()
        metrics = report["metrics"]
        assert "rnn" in metrics, "Missing metrics.rnn"
        assert "naive_baseline" in metrics, "Missing metrics.naive_baseline"

        for name in ["rnn", "naive_baseline"]:
            section = metrics[name]
            assert "mae" in section, f"Missing metrics.{name}.mae"
            assert "rmse" in section, f"Missing metrics.{name}.rmse"
            mae = section["mae"]
            rmse = section["rmse"]
            assert isinstance(mae, (int, float)), f"metrics.{name}.mae should be numeric"
            assert isinstance(rmse, (int, float)), f"metrics.{name}.rmse should be numeric"
            assert mae >= 0, f"metrics.{name}.mae should be non-negative"
            assert rmse >= 0, f"metrics.{name}.rmse should be non-negative"
            # Sanity: metrics shouldn't be astronomically large for stock ~180
            assert mae < 200, f"metrics.{name}.mae={mae} is unreasonably large"
            assert rmse < 200, f"metrics.{name}.rmse={rmse} is unreasonably large"

    def test_report_metrics_rounded_to_4dp(self):
        report = self._load_report()
        metrics = report["metrics"]
        for name in ["rnn", "naive_baseline"]:
            for metric_key in ["mae", "rmse"]:
                val = metrics[name][metric_key]
                rounded = round(val, 4)
                assert np.isclose(val, rounded, atol=1e-9), (
                    f"metrics.{name}.{metric_key}={val} not rounded to 4dp"
                )

    def test_report_rmse_ge_mae(self):
        """RMSE should always be >= MAE for the same predictions."""
        report = self._load_report()
        metrics = report["metrics"]
        for name in ["rnn", "naive_baseline"]:
            mae = metrics[name]["mae"]
            rmse = metrics[name]["rmse"]
            assert rmse >= mae - 1e-4, (
                f"metrics.{name}: RMSE ({rmse}) should be >= MAE ({mae})"
            )


# ============================================================
# Test 5: Report data section validation
# ============================================================
class TestReportData:
    def _load_report(self):
        with open(REPORT_PATH, "r") as f:
            return json.load(f)

    def test_report_data_total_samples(self):
        report = self._load_report()
        assert report["data"]["total_samples"] == 30, (
            f"data.total_samples should be 30, got {report['data']['total_samples']}"
        )

    def test_report_data_test_size(self):
        report = self._load_report()
        assert report["data"]["test_size"] == 5, (
            f"data.test_size should be 5, got {report['data']['test_size']}"
        )

    def test_report_data_train_size_positive(self):
        report = self._load_report()
        train_size = report["data"]["train_size"]
        assert isinstance(train_size, int), "data.train_size should be int"
        assert train_size > 0, "data.train_size should be positive"
        # With 30 data points, 5-day lookback, and 5 test samples,
        # train_size should be reasonable (around 19-20)
        assert train_size >= 10, f"data.train_size={train_size} seems too small"
        assert train_size <= 25, f"data.train_size={train_size} seems too large"

    def test_report_data_start_date(self):
        report = self._load_report()
        assert report["data"]["start_date"] == "2024-01-02", (
            f"data.start_date should be '2024-01-02', got '{report['data']['start_date']}'"
        )

    def test_report_data_end_date_valid(self):
        report = self._load_report()
        end_date = report["data"]["end_date"]
        # End date should be a valid date string
        end_dt = pd.to_datetime(end_date)
        # Should be after start date
        assert end_dt > pd.to_datetime("2024-01-02"), "end_date should be after start_date"
        # Should be a business day
        assert end_dt.dayofweek < 5, f"end_date {end_date} is a weekend"

    def test_report_data_end_date_matches_csv(self):
        """End date in report should match the last date in the CSV."""
        report = self._load_report()
        df = pd.read_csv(CSV_PATH)
        csv_last_date = str(df["Date"].iloc[-1]).strip()
        report_end_date = str(report["data"]["end_date"]).strip()
        assert csv_last_date == report_end_date, (
            f"Report end_date '{report_end_date}' doesn't match CSV last date '{csv_last_date}'"
        )


# ============================================================
# Test 6: Plot file validation
# ============================================================
class TestPlot:
    def test_plot_is_valid_png(self):
        """Check PNG magic bytes."""
        with open(PLOT_PATH, "rb") as f:
            header = f.read(8)
        png_magic = b'\x89PNG\r\n\x1a\n'
        assert header == png_magic, "Plot file is not a valid PNG"

    def test_plot_reasonable_size(self):
        """A real matplotlib plot should be at least a few KB."""
        size = os.path.getsize(PLOT_PATH)
        assert size > 5000, f"Plot is only {size} bytes — likely a dummy or corrupt file"


# ============================================================
# Test 7: Cross-artifact consistency
# ============================================================
class TestCrossArtifactConsistency:
    def test_csv_line_count_matches_instruction(self):
        """CSV should have exactly 31 lines (1 header + 30 data rows)."""
        with open(CSV_PATH, "r") as f:
            lines = f.readlines()
        # Filter out empty trailing lines
        lines = [l for l in lines if l.strip()]
        assert len(lines) == 31, (
            f"CSV should have 31 lines (1 header + 30 rows), got {len(lines)}"
        )

    def test_model_weights_are_trained(self):
        """Verify model weights are not all zeros (i.e., model was actually trained)."""
        sd = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        all_zero = True
        for k, v in sd.items():
            if torch.any(v != 0):
                all_zero = False
                break
        assert not all_zero, "All model weights are zero — model was not trained"

    def test_model_num_layers_1(self):
        """Verify num_layers=1 by checking only one set of RNN weight matrices."""
        sd = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        # With num_layers=1, keys should have l0 but not l1
        hh_keys = [k for k in sd.keys() if "weight_hh" in k]
        assert len(hh_keys) == 1, (
            f"Expected 1 RNN layer (1 weight_hh), found {len(hh_keys)}: {hh_keys}"
        )
