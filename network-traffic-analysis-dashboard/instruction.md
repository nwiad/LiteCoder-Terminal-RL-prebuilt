## Task: Network Traffic Analysis and Visualization Pipeline

Process network traffic logs to detect anomalies, enrich with geolocation data, identify threats, and create an interactive web dashboard for security analysis.

### Technical Requirements

- **Language:** Python 3.x
- **Input:** `/app/network_logs.jsonl` (JSON Lines format, one event per line)
- **Output:**
  - `/app/enriched_data.parquet` (processed dataset)
  - `/app/report.md` (analysis summary)
  - Web dashboard served on `http://0.0.0.0:8080`

### Input Specification

The input file `/app/network_logs.jsonl` contains one JSON object per line with the following fields:

```json
{
  "timestamp": "2024-01-15T14:23:45Z",
  "source_ip": "192.168.1.100",
  "method": "GET",
  "url": "https://example.com/api/data",
  "status_code": 200,
  "response_size": 1024,
  "user_agent": "Mozilla/5.0..."
}
```

### Processing Requirements

1. **Data Cleaning:**
   - Parse ISO 8601 timestamps into datetime objects
   - Normalize URLs (extract domain, path, query parameters)
   - Remove records with malformed JSON or missing required fields
   - Add derived columns: date, hour, domain

2. **GeoIP Enrichment:**
   - Add country, city, latitude, longitude for each source IP
   - Use a GeoIP lookup library (e.g., geoip2, ip2geotools)
   - Handle private/invalid IPs gracefully

3. **Anomaly Detection:**
   - Calculate per-source-IP request rates
   - Flag IPs with request rates exceeding 3 standard deviations from the mean
   - Add `is_anomalous` boolean field to dataset

4. **Threat Intelligence:**
   - Check source IPs and domains against threat indicators
   - Add `threat_level` field: "clean", "suspicious", or "malicious"
   - Document threat sources used in report

5. **Data Persistence:**
   - Save enriched dataset to `/app/enriched_data.parquet`
   - Partition by date if dataset spans multiple days
   - Include all original and derived fields

### Dashboard Requirements

Create a web dashboard accessible at `http://0.0.0.0:8080` with:

1. **World Map:** Plot traffic sources by geolocation with markers sized by request volume
2. **Time Series Chart:** Show request volume over time with anomalies highlighted
3. **Data Table:** Filterable table showing suspicious events with columns: timestamp, source_ip, country, url, threat_level, is_anomalous
4. **Download Links:** Allow users to download the enriched Parquet file

Technical specifications:
- Use Python web framework (Flask, FastAPI, or http.server)
- Serve static HTML/CSS/JS files
- Use JavaScript visualization library (e.g., Leaflet for maps, Chart.js for time series)
- Implement basic authentication (username: admin, password: admin)
- Enable gzip compression for static assets

### Report Requirements

Generate `/app/report.md` containing:

1. **Summary Statistics:** Total events, date range, unique source IPs, countries represented
2. **Top Threats:** List of top 10 suspicious IPs with their threat levels and request counts
3. **Geographic Hotspots:** Countries with highest traffic volume
4. **Anomalous Periods:** Time windows with unusual activity spikes
5. **Reproduction Steps:** Command to run the complete pipeline

### Deliverables

1. Python script(s) implementing the complete pipeline
2. `/app/enriched_data.parquet` with all enriched fields
3. `/app/report.md` with analysis findings
4. Web dashboard files (HTML/CSS/JS)
5. Single executable script that runs the entire workflow and starts the dashboard server

### Edge Cases

- Handle missing or null fields in input data
- Gracefully handle GeoIP lookup failures
- Handle IPs that cannot be geolocated (private ranges, invalid IPs)
- Ensure dashboard works with empty or minimal datasets
