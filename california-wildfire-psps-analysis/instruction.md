## California Wildfire & Power Shut-off Analysis

Analyze relationships between California wildfire incidents, electrical transmission infrastructure, and public safety power shut-off (PSPS) events using the provided datasets. Produce cleaned data, spatial proximity analysis, temporal correlation, a visualization, and a summary report.

### Technical Requirements

- Language: Python 3
- Input files (provided):
  - `/app/data/wildfires.csv` — historical wildfire incidents
  - `/app/data/transmission_lines.csv` — electrical transmission line segments
  - `/app/data/psps_events.csv` — public safety power shut-off events
- Output files (to be created by your script):
  - `/app/output/wildfires_cleaned.csv`
  - `/app/output/psps_cleaned.csv`
  - `/app/output/spatial_join.csv`
  - `/app/output/summary_report.json`
  - `/app/output/wildfire_psps_map.png`
- The main script must be `/app/analysis.py` and be runnable via `python /app/analysis.py` with no additional arguments.

### Input Data Specifications

**wildfires.csv** columns:
| Column | Type | Description |
|---|---|---|
| fire_id | string | Unique fire identifier |
| fire_name | string | Name of the fire |
| cause | string | Cause category (e.g., "Electrical", "Lightning", "Arson", "Debris Burning", "Unknown") |
| latitude | float | Fire origin latitude |
| longitude | float | Fire origin longitude |
| start_date | string | Fire start date in format "YYYY-MM-DD" |
| end_date | string | Fire end date in format "YYYY-MM-DD" or empty string if still active |
| acres_burned | float | Total acres burned (may contain negative or null values as data errors) |
| county | string | County name |

**transmission_lines.csv** columns:
| Column | Type | Description |
|---|---|---|
| line_id | string | Unique line identifier |
| utility | string | Utility company name |
| voltage_kv | float | Line voltage in kilovolts |
| lat_start | float | Segment start latitude |
| lon_start | float | Segment start longitude |
| lat_end | float | Segment end latitude |
| lon_end | float | Segment end longitude |

**psps_events.csv** columns:
| Column | Type | Description |
|---|---|---|
| event_id | string | Unique event identifier |
| utility | string | Utility company name |
| start_datetime | string | Shut-off start in format "YYYY-MM-DD HH:MM:SS" |
| end_datetime | string | Shut-off end in format "YYYY-MM-DD HH:MM:SS" or empty string |
| latitude | float | Approximate center latitude of affected area |
| longitude | float | Approximate center longitude of affected area |
| customers_affected | int | Number of customers affected (may contain null values) |
| county | string | County name |

### Processing Requirements

**Step 1: Data Cleaning**

Wildfire cleaning (`/app/output/wildfires_cleaned.csv`):
- Remove rows where `latitude` or `longitude` is null/NaN.
- Remove rows where `acres_burned` is null/NaN or <= 0.
- Parse `start_date` into a proper date. Remove rows with unparseable dates.
- Keep all original columns. Add a column `is_utility_caused` (boolean: `True` if `cause` column value is exactly `"Electrical"`, `False` otherwise).
- Sort by `start_date` ascending, then by `fire_id` ascending.

PSPS cleaning (`/app/output/psps_cleaned.csv`):
- Remove rows where `latitude` or `longitude` is null/NaN.
- Parse `start_datetime` into a proper datetime. Remove rows with unparseable datetimes.
- Replace null `customers_affected` with 0.
- Keep all original columns. Sort by `start_datetime` ascending, then by `event_id` ascending.

**Step 2: Spatial Join**

For each fire in the cleaned wildfire data, find all transmission line segments within a 5 km buffer. The distance from a fire point (lat, lon) to a transmission line segment is defined as the minimum of:
- Haversine distance from fire point to segment start point (lat_start, lon_start)
- Haversine distance from fire point to segment end point (lat_end, lon_end)

Use Earth radius = 6371 km for Haversine calculations.

Output `/app/output/spatial_join.csv` with columns:
| Column | Description |
|---|---|
| fire_id | From wildfire data |
| fire_name | From wildfire data |
| cause | From wildfire data |
| is_utility_caused | From cleaned wildfire data |
| line_id | Matched transmission line |
| utility | From transmission line data |
| distance_km | Distance in km (rounded to 3 decimal places) |

Include one row per fire–line pair within the 5 km buffer. If a fire has no nearby lines, it is excluded. Sort by `fire_id` ascending, then `distance_km` ascending.

**Step 3: Temporal Correlation**

For each PSPS event in the cleaned PSPS data, check whether any fire in the cleaned wildfire data started within 30 days after the PSPS event's `start_datetime` (i.e., fire `start_date` >= PSPS `start_datetime` date and fire `start_date` <= PSPS `start_datetime` date + 30 days) AND is within 50 km (Haversine distance between fire point and PSPS event point).

Compute:
- `total_psps_events`: total number of cleaned PSPS events
- `psps_with_nearby_fire`: number of PSPS events that have at least one fire within the 30-day / 50-km window
- `temporal_correlation_rate`: `psps_with_nearby_fire / total_psps_events` (float, rounded to 4 decimal places; 0.0 if no PSPS events)

**Step 4: Summary Report**

Write `/app/output/summary_report.json` with this exact structure:
```json
{
  "total_fires_raw": <int>,
  "total_fires_cleaned": <int>,
  "utility_caused_fires": <int>,
  "total_psps_raw": <int>,
  "total_psps_cleaned": <int>,
  "fires_near_transmission_lines": <int>,
  "unique_fires_in_spatial_join": <int>,
  "total_psps_events": <int>,
  "psps_with_nearby_fire": <int>,
  "temporal_correlation_rate": <float>,
  "top_counties_by_utility_fires": [
    {"county": "<name>", "count": <int>},
    ...
  ]
}
```
- `total_fires_raw`: row count of original wildfires.csv (excluding header).
- `total_fires_cleaned`: row count of wildfires_cleaned.csv.
- `utility_caused_fires`: count of fires where `is_utility_caused` is True in cleaned data.
- `total_psps_raw`: row count of original psps_events.csv (excluding header).
- `total_psps_cleaned`: row count of psps_cleaned.csv.
- `fires_near_transmission_lines`: total number of rows in spatial_join.csv.
- `unique_fires_in_spatial_join`: number of distinct `fire_id` values in spatial_join.csv.
- `top_counties_by_utility_fires`: list of counties with utility-caused fires, sorted by count descending then county name ascending. Include all counties that have at least 1 utility-caused fire.

**Step 5: Visualization**

Generate `/app/output/wildfire_psps_map.png` — a scatter plot on a 2D coordinate plane (longitude on x-axis, latitude on y-axis) showing:
- Cleaned wildfire locations, colored differently for utility-caused vs. non-utility-caused fires.
- Cleaned PSPS event locations as a distinct marker.
- A legend identifying each category.
- A title containing the text "California Wildfire".

The image must be at least 800×600 pixels.
