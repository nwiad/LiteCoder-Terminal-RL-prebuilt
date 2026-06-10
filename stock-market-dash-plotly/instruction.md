## Stock Market Data Visualization Dashboard

Build a stock market data visualization dashboard using Python and Plotly Dash that reads stock data from a local JSON file and displays interactive charts via a web application.

### Technical Requirements

- Language: Python 3
- Framework: Plotly Dash
- Input file: `/app/input.json`
- The Dash application must be defined in `/app/app.py`
- The Dash app server must be accessible on `http://127.0.0.1:8050` when started

### Input Format

`/app/input.json` contains a JSON object where each key is a stock ticker symbol. Each ticker maps to an array of daily records sorted by date ascending. Example:

```json
{
  "AAPL": [
    {
      "date": "2024-01-02",
      "open": 185.50,
      "high": 187.20,
      "low": 184.80,
      "close": 186.90,
      "volume": 45000000
    },
    {
      "date": "2024-01-03",
      "open": 186.90,
      "high": 188.00,
      "low": 185.50,
      "close": 185.80,
      "volume": 42000000
    }
  ],
  "GOOGL": [
    {
      "date": "2024-01-02",
      "open": 140.10,
      "high": 141.50,
      "low": 139.80,
      "close": 141.20,
      "volume": 22000000
    }
  ]
}
```

Each record always contains the fields: `date` (string, YYYY-MM-DD), `open`, `high`, `low`, `close` (floats), and `volume` (integer).

### Dashboard Requirements

1. **Stock Selector**: A `dcc.Dropdown` component with `id="stock-selector"` that lists all ticker symbols from the input data. The dropdown's `options` must include every ticker present in `/app/input.json`. The first ticker (alphabetically) should be selected by default.

2. **Price Chart**: A `dcc.Graph` component with `id="price-chart"` that displays the closing price over time (date on x-axis, close price on y-axis) for the currently selected stock.

3. **Volume Chart**: A `dcc.Graph` component with `id="volume-chart"` that displays a bar chart of daily trading volume (date on x-axis, volume on y-axis) for the currently selected stock.

4. **Moving Average**: The price chart must also include a 5-day simple moving average (SMA) line overlaid on the closing price data. The SMA is calculated as the arithmetic mean of the most recent 5 closing prices. For the first 4 data points where fewer than 5 values are available, no SMA value should be plotted (i.e., those points should be absent or null).

5. **Callbacks**: Selecting a different stock from the dropdown must update both the price chart and the volume chart to reflect the newly selected stock's data.

### Application Entry Point

`/app/app.py` must expose:
- A Dash application instance named `app`
- The underlying Flask server accessible as `app.server`
- Running `python /app/app.py` must start the server on host `0.0.0.0`, port `8050`, with `debug=False`
