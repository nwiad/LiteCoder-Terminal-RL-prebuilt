## Crypto Market Dashboard

Build a Flask web application that reads Bitcoin-USDT market ticker data from a local JSON file and serves a dashboard displaying the latest price, 24-hour price change percentage, and 24-hour trading volume.

### Technical Requirements

- Language: Python 3
- Framework: Flask
- Main application file: `/app/app.py`
- Input data file: `/app/input.json`
- The Flask app must bind to `0.0.0.0` on port `8080`

### Input Specification

`/app/input.json` contains an array of ticker snapshot objects, sorted by timestamp ascending. Each object has the following fields:

```json
[
  {
    "timestamp": "2025-01-15T10:00:00Z",
    "symbol": "BTCUSDT",
    "price": "43250.50",
    "price_24h_ago": "42800.00",
    "volume_24h": "18523.456"
  },
  {
    "timestamp": "2025-01-15T10:00:30Z",
    "symbol": "BTCUSDT",
    "price": "43300.75",
    "price_24h_ago": "42850.10",
    "volume_24h": "18600.123"
  }
]
```

All numeric values are provided as strings. The last entry in the array represents the most recent (current) ticker data.

### Endpoints

#### `GET /`

Returns an HTML page (Content-Type: `text/html`) that displays:

- The current Bitcoin price (from the last entry's `price` field)
- The 24-hour price change percentage, calculated as: `((price - price_24h_ago) / price_24h_ago) * 100`, rounded to 2 decimal places
- The 24-hour trading volume (from the last entry's `volume_24h` field)

The HTML response body must contain these exact substrings (with actual computed values substituted):

- `id="price"` — an element whose text content is the current price (e.g., `43300.75`)
- `id="change"` — an element whose text content is the 24h change percentage (e.g., `1.05`)
- `id="volume"` — an element whose text content is the 24h volume (e.g., `18600.123`)

#### `GET /data`

Returns a JSON response (Content-Type: `application/json`) with the following exact structure, derived from the last entry in the input array:

```json
{
  "symbol": "BTCUSDT",
  "price": 43300.75,
  "change_pct": 1.05,
  "volume_24h": 18600.123
}
```

- `price`: float, the current price
- `change_pct`: float, the 24h change percentage rounded to 2 decimal places
- `volume_24h`: float, the 24h trading volume
- `symbol`: string, copied from the input entry

### Edge Cases

- If `/app/input.json` is missing or contains an empty array `[]`, both endpoints must return HTTP status code `503` (Service Unavailable).
- If any required field (`price`, `price_24h_ago`, `volume_24h`, `symbol`) is missing from the last entry, both endpoints must return HTTP status code `503`.

### Running

The application must be runnable via:

```
cd /app && python3 app.py
```

It should start and listen on port 8080 immediately, ready to serve requests.
