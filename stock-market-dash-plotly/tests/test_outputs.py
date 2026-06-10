"""
Tests for Stock Market Data Visualization Dashboard.
Validates that /app/app.py creates a working Dash application with
correct components, callbacks, and data processing.
"""

import os
import sys
import json
import importlib
import numpy as np
import pytest
import requests
import time

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INPUT_JSON_PATH = "/app/input.json"
APP_PY_PATH = "/app/app.py"
TEST_DATA_PATH = "/app/test_data/input_fewer_points.json"
BASE_URL = "http://127.0.0.1:8050"


def load_input_data(path=INPUT_JSON_PATH):
    with open(path, "r") as f:
        return json.load(f)


def compute_expected_sma(closes, window=5):
    """Reference SMA: None for first (window-1) points, then arithmetic mean."""
    sma = []
    for i in range(len(closes)):
        if i < window - 1:
            sma.append(None)
        else:
            avg = sum(closes[i - window + 1 : i + 1]) / window
            sma.append(avg)
    return sma


def get_dash_app():
    """Import the Dash app module and return the app object."""
    sys.path.insert(0, "/app")
    # Prevent the app from auto-running when imported
    if "app" in sys.modules:
        mod = sys.modules["app"]
    else:
        mod = importlib.import_module("app")
    return mod


# ---------------------------------------------------------------------------
# 1. File existence
# ---------------------------------------------------------------------------

class TestFileExistence:
    def test_app_py_exists(self):
        assert os.path.isfile(APP_PY_PATH), f"{APP_PY_PATH} does not exist"

    def test_app_py_not_empty(self):
        assert os.path.getsize(APP_PY_PATH) > 100, (
            f"{APP_PY_PATH} is too small to be a valid Dash app"
        )


# ---------------------------------------------------------------------------
# 2. Module structure & Dash app object
# ---------------------------------------------------------------------------

class TestModuleStructure:
    def test_app_attribute_exists(self):
        mod = get_dash_app()
        assert hasattr(mod, "app"), "Module must expose an attribute named 'app'"

    def test_app_is_dash_instance(self):
        mod = get_dash_app()
        from dash import Dash
        assert isinstance(mod.app, Dash), "'app' must be a Dash instance"

    def test_server_attribute(self):
        mod = get_dash_app()
        from flask import Flask
        server = mod.app.server
        assert isinstance(server, Flask), "'app.server' must be a Flask instance"


# ---------------------------------------------------------------------------
# 3. Server accessibility (HTTP level)
# ---------------------------------------------------------------------------

class TestServerAccessibility:
    def test_root_endpoint_responds(self):
        """The Dash app should serve HTML at the root URL."""
        try:
            resp = requests.get(BASE_URL, timeout=10)
            assert resp.status_code == 200, (
                f"Expected 200 from {BASE_URL}, got {resp.status_code}"
            )
        except requests.ConnectionError:
            pytest.fail(f"Could not connect to {BASE_URL}. Is the server running?")

    def test_root_contains_dash_content(self):
        """The root page should contain Dash-rendered content."""
        resp = requests.get(BASE_URL, timeout=10)
        body = resp.text.lower()
        assert "dash" in body or "react" in body or "_dash" in body or "stock-selector" in body, (
            "Root page does not appear to be a Dash application"
        )


# ---------------------------------------------------------------------------
# 4. Layout components
# ---------------------------------------------------------------------------

class TestLayoutComponents:
    """Verify the Dash layout contains required components with correct IDs."""

    def _flatten_children(self, component):
        """Recursively collect all components from the layout tree."""
        found = []
        found.append(component)
        children = getattr(component, "children", None)
        if children is None:
            return found
        if isinstance(children, (list, tuple)):
            for child in children:
                if hasattr(child, "children") or hasattr(child, "id"):
                    found.extend(self._flatten_children(child))
        elif hasattr(children, "children") or hasattr(children, "id"):
            found.extend(self._flatten_children(children))
        return found

    def _find_component_by_id(self, target_id):
        mod = get_dash_app()
        layout = mod.app.layout
        # If layout is callable (Dash 2.x+), call it
        if callable(layout):
            layout = layout()
        all_components = self._flatten_children(layout)
        for comp in all_components:
            if getattr(comp, "id", None) == target_id:
                return comp
        return None

    def test_stock_selector_exists(self):
        comp = self._find_component_by_id("stock-selector")
        assert comp is not None, "Layout must contain a component with id='stock-selector'"

    def test_stock_selector_is_dropdown(self):
        from dash import dcc
        comp = self._find_component_by_id("stock-selector")
        assert isinstance(comp, dcc.Dropdown), (
            f"stock-selector must be a dcc.Dropdown, got {type(comp).__name__}"
        )

    def test_price_chart_exists(self):
        comp = self._find_component_by_id("price-chart")
        assert comp is not None, "Layout must contain a component with id='price-chart'"

    def test_price_chart_is_graph(self):
        from dash import dcc
        comp = self._find_component_by_id("price-chart")
        assert isinstance(comp, dcc.Graph), (
            f"price-chart must be a dcc.Graph, got {type(comp).__name__}"
        )

    def test_volume_chart_exists(self):
        comp = self._find_component_by_id("volume-chart")
        assert comp is not None, "Layout must contain a component with id='volume-chart'"

    def test_volume_chart_is_graph(self):
        from dash import dcc
        comp = self._find_component_by_id("volume-chart")
        assert isinstance(comp, dcc.Graph), (
            f"volume-chart must be a dcc.Graph, got {type(comp).__name__}"
        )


# ---------------------------------------------------------------------------
# 5. Dropdown options and default value
# ---------------------------------------------------------------------------

class TestDropdownOptions:
    def _get_dropdown(self):
        mod = get_dash_app()
        layout = mod.app.layout
        if callable(layout):
            layout = layout()
        # Use the flatten helper from TestLayoutComponents
        helper = TestLayoutComponents()
        return helper._find_component_by_id("stock-selector")

    def test_dropdown_has_all_tickers(self):
        data = load_input_data()
        expected_tickers = sorted(data.keys())
        dropdown = self._get_dropdown()
        assert dropdown is not None, "stock-selector not found"
        options = dropdown.options
        # Options can be list of dicts or list of strings
        if options and isinstance(options[0], dict):
            option_values = sorted([o["value"] for o in options])
        else:
            option_values = sorted(options)
        assert option_values == expected_tickers, (
            f"Dropdown options {option_values} != expected tickers {expected_tickers}"
        )

    def test_dropdown_default_is_first_alphabetically(self):
        data = load_input_data()
        expected_default = sorted(data.keys())[0]
        dropdown = self._get_dropdown()
        assert dropdown is not None, "stock-selector not found"
        assert dropdown.value == expected_default, (
            f"Default value should be '{expected_default}', got '{dropdown.value}'"
        )


# ---------------------------------------------------------------------------
# 6. Callback data validation via Dash HTTP API
# ---------------------------------------------------------------------------

def _dash_update_component(ticker):
    """
    Call the Dash server's _dash-update-component endpoint to trigger
    the callback and retrieve the resulting figure JSON for both charts.
    """
    payload = {
        "output": "..price-chart.figure...volume-chart.figure..",
        "outputs": [
            {"id": "price-chart", "property": "figure"},
            {"id": "volume-chart", "property": "figure"},
        ],
        "inputs": [
            {"id": "stock-selector", "property": "value", "value": ticker}
        ],
        "changedPropIds": ["stock-selector.value"],
    }
    resp = requests.post(
        f"{BASE_URL}/_dash-update-component",
        json=payload,
        timeout=15,
    )
    assert resp.status_code == 200, (
        f"Callback request failed with status {resp.status_code}: {resp.text[:300]}"
    )
    result = resp.json()
    # Dash returns {"response": {"price-chart": {"figure": ...}, ...}} or
    # {"multi": true, "response": {...}}
    response_data = result.get("response", result)
    return response_data


def _extract_figure(response_data, component_id):
    """Extract figure dict from Dash callback response for a given component."""
    if component_id in response_data:
        fig = response_data[component_id]
        if isinstance(fig, dict) and "figure" in fig:
            return fig["figure"]
        return fig
    pytest.fail(f"Component '{component_id}' not found in callback response")


def _find_sma_trace_in_figure(price_fig, closes):
    """
    Identify the SMA trace from a price figure by excluding the close-price trace.
    Returns the first trace whose non-None y-values do NOT exactly match closes.
    """
    traces = price_fig.get("data", [])
    for t in traces:
        y_vals = t.get("y", [])
        y_numeric = [v for v in y_vals if v is not None]
        # Skip the close price trace (exact match on all non-None values)
        if len(y_numeric) == len(closes):
            if all(np.isclose(a, b, atol=0.001) for a, b in zip(y_numeric, closes)):
                continue
        # Must have some data to be a valid SMA trace
        if len(y_vals) > 0:
            return t
    return None


class TestCallbackRegistered:
    def test_callback_exists(self):
        """At least one callback must be registered on the app."""
        mod = get_dash_app()
        app = mod.app
        assert len(app.callback_map) > 0, "No callbacks registered on the Dash app"


# ---------------------------------------------------------------------------
# 7. Price chart data validation
# ---------------------------------------------------------------------------

class TestPriceChart:
    """Validate the price chart shows correct closing prices and SMA."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_input_data()
        self.ticker = sorted(self.data.keys())[0]  # AAPL
        self.response = _dash_update_component(self.ticker)
        self.price_fig = _extract_figure(self.response, "price-chart")

    def test_price_chart_has_traces(self):
        traces = self.price_fig.get("data", [])
        assert len(traces) >= 2, (
            f"Price chart should have at least 2 traces (close + SMA), got {len(traces)}"
        )

    def test_closing_price_values(self):
        """The first trace should contain the closing prices."""
        traces = self.price_fig.get("data", [])
        records = self.data[self.ticker]
        expected_closes = [r["close"] for r in records]
        # Find the trace with closing price data (first trace or by name)
        close_trace = None
        for t in traces:
            y_vals = t.get("y", [])
            # Filter out None values for comparison
            y_numeric = [v for v in y_vals if v is not None]
            if len(y_numeric) == len(expected_closes):
                if all(np.isclose(a, b, atol=0.01) for a, b in zip(y_numeric, expected_closes)):
                    close_trace = t
                    break
        assert close_trace is not None, (
            f"Could not find a trace with correct closing prices for {self.ticker}"
        )

    def test_closing_price_dates(self):
        """X-axis should contain the correct dates."""
        traces = self.price_fig.get("data", [])
        records = self.data[self.ticker]
        expected_dates = [r["date"] for r in records]
        # Check at least one trace has matching dates
        found = False
        for t in traces:
            x_vals = [str(v).split("T")[0] if v else v for v in t.get("x", [])]
            if len(x_vals) >= len(expected_dates):
                if x_vals[:len(expected_dates)] == expected_dates:
                    found = True
                    break
        assert found, "No trace found with correct date values on x-axis"


# ---------------------------------------------------------------------------
# 8. SMA validation
# ---------------------------------------------------------------------------

class TestSMA:
    """Validate the 5-day simple moving average calculation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_input_data()
        self.ticker = sorted(self.data.keys())[0]  # AAPL (10 points)
        self.response = _dash_update_component(self.ticker)
        self.price_fig = _extract_figure(self.response, "price-chart")
        self.records = self.data[self.ticker]
        self.closes = [r["close"] for r in self.records]
        self.expected_sma = compute_expected_sma(self.closes, window=5)

    def _find_sma_trace(self):
        """Find the SMA trace among the price chart traces."""
        return _find_sma_trace_in_figure(self.price_fig, self.closes)

    def test_sma_trace_exists(self):
        sma_trace = self._find_sma_trace()
        assert sma_trace is not None, "Could not find SMA trace in price chart"

    def test_sma_first_four_are_null(self):
        """First 4 SMA values should be None/null (not enough data for window=5)."""
        sma_trace = self._find_sma_trace()
        assert sma_trace is not None, "SMA trace not found"
        y_vals = sma_trace.get("y", [])
        for i in range(min(4, len(y_vals))):
            assert y_vals[i] is None, (
                f"SMA value at index {i} should be None, got {y_vals[i]}"
            )

    def test_sma_computed_values_correct(self):
        """SMA values from index 4 onward should match expected arithmetic mean."""
        sma_trace = self._find_sma_trace()
        assert sma_trace is not None, "SMA trace not found"
        y_vals = sma_trace.get("y", [])
        # Check the non-None expected values
        for i in range(4, len(self.expected_sma)):
            assert i < len(y_vals), f"SMA trace missing value at index {i}"
            assert y_vals[i] is not None, f"SMA at index {i} should not be None"
            assert np.isclose(y_vals[i], self.expected_sma[i], atol=0.01), (
                f"SMA at index {i}: expected {self.expected_sma[i]:.4f}, got {y_vals[i]}"
            )

    def test_sma_specific_value_spot_check(self):
        """Spot-check: SMA at index 4 = mean of closes[0:5]."""
        sma_trace = self._find_sma_trace()
        assert sma_trace is not None, "SMA trace not found"
        y_vals = sma_trace.get("y", [])
        expected_val = sum(self.closes[0:5]) / 5.0
        assert len(y_vals) > 4, "SMA trace has fewer than 5 values"
        assert np.isclose(y_vals[4], expected_val, atol=0.01), (
            f"SMA[4] should be {expected_val:.4f}, got {y_vals[4]}"
        )


# ---------------------------------------------------------------------------
# 9. Volume chart validation
# ---------------------------------------------------------------------------

class TestVolumeChart:
    """Validate the volume bar chart data."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_input_data()
        self.ticker = sorted(self.data.keys())[0]  # AAPL
        self.response = _dash_update_component(self.ticker)
        self.volume_fig = _extract_figure(self.response, "volume-chart")
        self.records = self.data[self.ticker]

    def test_volume_chart_has_trace(self):
        traces = self.volume_fig.get("data", [])
        assert len(traces) >= 1, "Volume chart should have at least 1 trace"

    def test_volume_chart_is_bar(self):
        """Volume chart should use bar chart type."""
        traces = self.volume_fig.get("data", [])
        bar_found = False
        for t in traces:
            if t.get("type", "").lower() == "bar":
                bar_found = True
                break
        assert bar_found, (
            f"Volume chart should contain a bar trace, got types: "
            f"{[t.get('type') for t in traces]}"
        )

    def test_volume_values_correct(self):
        """Volume values should match the input data."""
        traces = self.volume_fig.get("data", [])
        expected_volumes = [r["volume"] for r in self.records]
        found = False
        for t in traces:
            y_vals = t.get("y", [])
            if len(y_vals) == len(expected_volumes):
                if all(
                    np.isclose(float(a), float(b), rtol=1e-6)
                    for a, b in zip(y_vals, expected_volumes)
                ):
                    found = True
                    break
        assert found, "Volume chart y-values do not match expected volumes"

    def test_volume_dates_correct(self):
        """Volume chart x-axis should have correct dates."""
        traces = self.volume_fig.get("data", [])
        expected_dates = [r["date"] for r in self.records]
        found = False
        for t in traces:
            x_vals = [str(v).split("T")[0] if v else v for v in t.get("x", [])]
            if x_vals == expected_dates:
                found = True
                break
        assert found, "Volume chart x-values do not match expected dates"


# ---------------------------------------------------------------------------
# 10. Callback updates for different tickers
# ---------------------------------------------------------------------------

class TestTickerSwitching:
    """Verify that selecting a different ticker updates both charts."""

    def test_different_ticker_returns_different_data(self):
        """Selecting MSFT should return MSFT data, not AAPL data."""
        data = load_input_data()
        tickers = sorted(data.keys())
        assert len(tickers) >= 2, "Need at least 2 tickers to test switching"

        ticker_a = tickers[0]
        ticker_b = tickers[-1]

        resp_a = _dash_update_component(ticker_a)
        resp_b = _dash_update_component(ticker_b)

        price_a = _extract_figure(resp_a, "price-chart")
        price_b = _extract_figure(resp_b, "price-chart")

        # The close prices should differ between tickers
        closes_a = [r["close"] for r in data[ticker_a]]
        closes_b = [r["close"] for r in data[ticker_b]]
        assert closes_a != closes_b, "Test data tickers should have different prices"

        # Verify ticker_b's price chart has ticker_b's data
        traces_b = price_b.get("data", [])
        found = False
        for t in traces_b:
            y_vals = t.get("y", [])
            y_numeric = [v for v in y_vals if v is not None]
            if len(y_numeric) == len(closes_b):
                if all(np.isclose(a, b, atol=0.01) for a, b in zip(y_numeric, closes_b)):
                    found = True
                    break
        assert found, (
            f"After selecting {ticker_b}, price chart should show {ticker_b}'s closing prices"
        )

    def test_volume_updates_on_ticker_switch(self):
        """Volume chart should update when ticker changes."""
        data = load_input_data()
        tickers = sorted(data.keys())
        ticker_b = tickers[-1]

        resp_b = _dash_update_component(ticker_b)
        vol_fig = _extract_figure(resp_b, "volume-chart")

        expected_volumes = [r["volume"] for r in data[ticker_b]]
        traces = vol_fig.get("data", [])
        found = False
        for t in traces:
            y_vals = t.get("y", [])
            if len(y_vals) == len(expected_volumes):
                if all(
                    np.isclose(float(a), float(b), rtol=1e-6)
                    for a, b in zip(y_vals, expected_volumes)
                ):
                    found = True
                    break
        assert found, (
            f"After selecting {ticker_b}, volume chart should show {ticker_b}'s volumes"
        )

    def test_all_tickers_produce_valid_figures(self):
        """Every ticker in the input should produce non-empty figures."""
        data = load_input_data()
        for ticker in sorted(data.keys()):
            resp = _dash_update_component(ticker)
            price_fig = _extract_figure(resp, "price-chart")
            vol_fig = _extract_figure(resp, "volume-chart")
            assert len(price_fig.get("data", [])) >= 1, (
                f"Price chart for {ticker} has no traces"
            )
            assert len(vol_fig.get("data", [])) >= 1, (
                f"Volume chart for {ticker} has no traces"
            )


# ---------------------------------------------------------------------------
# 11. SMA edge case: second ticker (GOOGL) also correct
# ---------------------------------------------------------------------------

class TestSMASecondTicker:
    """Cross-check SMA on a different ticker to catch hardcoded values."""

    def test_sma_for_googl(self):
        data = load_input_data()
        tickers = sorted(data.keys())
        # Pick second ticker (GOOGL)
        ticker = tickers[1] if len(tickers) > 1 else tickers[0]
        records = data[ticker]
        closes = [r["close"] for r in records]
        expected_sma = compute_expected_sma(closes, window=5)

        resp = _dash_update_component(ticker)
        price_fig = _extract_figure(resp, "price-chart")

        # Find the SMA trace (not the close price trace)
        sma_trace = _find_sma_trace_in_figure(price_fig, closes)

        assert sma_trace is not None, f"SMA trace not found for {ticker}"
        y_vals = sma_trace.get("y", [])

        # Verify non-None SMA values
        for i in range(4, min(len(expected_sma), len(y_vals))):
            assert y_vals[i] is not None, f"SMA[{i}] for {ticker} should not be None"
            assert np.isclose(y_vals[i], expected_sma[i], atol=0.01), (
                f"SMA[{i}] for {ticker}: expected {expected_sma[i]:.4f}, got {y_vals[i]}"
            )

