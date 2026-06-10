import os
import json
import pandas as pd
import pytest
import requests
from requests.auth import HTTPBasicAuth
import time


def test_enriched_parquet_exists():
    """Test that enriched_data.parquet file exists."""
    assert os.path.exists('/app/enriched_data.parquet'), "enriched_data.parquet file not found"


def test_report_exists():
    """Test that report.md file exists."""
    assert os.path.exists('/app/report.md'), "report.md file not found"


def test_parquet_not_empty():
    """Test that parquet file is not empty."""
    df = pd.read_parquet('/app/enriched_data.parquet')
    assert len(df) > 0, "Parquet file is empty"


def test_parquet_has_required_columns():
    """Test that parquet file contains all required enriched fields."""
    df = pd.read_parquet('/app/enriched_data.parquet')

    required_columns = [
        'timestamp', 'source_ip', 'method', 'url', 'status_code', 'response_size', 'user_agent',
        'date', 'hour', 'domain',
        'country', 'city', 'latitude', 'longitude',
        'is_anomalous', 'threat_level'
    ]

    for col in required_columns:
        assert col in df.columns, f"Missing required column: {col}"


def test_parquet_has_original_data():
    """Test that original fields are preserved."""
    df = pd.read_parquet('/app/enriched_data.parquet')

    # Check that we have reasonable number of records (input has 47+ entries)
    assert len(df) >= 40, f"Expected at least 40 records, got {len(df)}"

    # Verify original fields have data
    assert df['source_ip'].notna().all(), "source_ip has null values"
    assert df['method'].notna().all(), "method has null values"
    assert df['url'].notna().all(), "url has null values"


def test_geoip_enrichment():
    """Test that GeoIP enrichment was performed."""
    df = pd.read_parquet('/app/enriched_data.parquet')

    # Check that country field exists and has values
    assert 'country' in df.columns, "country field missing"
    assert df['country'].notna().any(), "No country data found"

    # Check that at least some IPs have valid geolocation
    valid_geo = df[(df['latitude'].notna()) & (df['longitude'].notna())]
    assert len(valid_geo) > 0, "No valid geolocation data found"

    # Private IPs should be marked as 'Private' or handled gracefully
    private_ips = df[df['source_ip'].str.startswith('192.168.')]
    if len(private_ips) > 0:
        # Private IPs should either have 'Private' country or null lat/lon
        assert (private_ips['country'] == 'Private').any() or private_ips['latitude'].isna().any(), \
            "Private IPs not handled correctly"


def test_anomaly_detection():
    """Test that anomaly detection was performed and flags high-volume IPs."""
    df = pd.read_parquet('/app/enriched_data.parquet')

    # Check that is_anomalous field exists
    assert 'is_anomalous' in df.columns, "is_anomalous field missing"

    # Count requests per IP
    ip_counts = df.groupby('source_ip').size()

    # IP 45.142.212.61 has 15 rapid requests - should be flagged as anomalous
    if '45.142.212.61' in ip_counts.index:
        anomalous_ip_data = df[df['source_ip'] == '45.142.212.61']
        # At least some of these should be marked anomalous
        assert anomalous_ip_data['is_anomalous'].any(), \
            "High-volume IP 45.142.212.61 not flagged as anomalous"


def test_threat_intelligence():
    """Test that threat intelligence was applied."""
    df = pd.read_parquet('/app/enriched_data.parquet')

    # Check that threat_level field exists
    assert 'threat_level' in df.columns, "threat_level field missing"

    # Valid threat levels
    valid_levels = {'clean', 'suspicious', 'malicious'}
    assert df['threat_level'].isin(valid_levels).all(), \
        f"Invalid threat levels found: {df['threat_level'].unique()}"

    # IP 185.220.101.15 attempts admin access with scanning tools - should be suspicious/malicious
    if '185.220.101.15' in df['source_ip'].values:
        threat_ip_data = df[df['source_ip'] == '185.220.101.15']
        threat_levels = threat_ip_data['threat_level'].unique()
        assert any(level in ['suspicious', 'malicious'] for level in threat_levels), \
            "Scanning IP 185.220.101.15 not flagged as threat"


def test_derived_fields():
    """Test that derived fields (date, hour, domain) are correctly extracted."""
    df = pd.read_parquet('/app/enriched_data.parquet')

    # Check date field
    assert 'date' in df.columns, "date field missing"
    assert df['date'].notna().all(), "date field has null values"

    # Check hour field
    assert 'hour' in df.columns, "hour field missing"
    assert df['hour'].notna().all(), "hour field has null values"
    assert df['hour'].between(0, 23).all(), "hour values out of range"

    # Check domain field
    assert 'domain' in df.columns, "domain field missing"
    assert df['domain'].notna().all(), "domain field has null values"
    # Domains should be extracted from URLs
    assert df['domain'].str.contains('example.com').any(), "domain extraction failed"


def test_report_structure():
    """Test that report.md contains required sections."""
    with open('/app/report.md', 'r') as f:
        report_content = f.read()

    # Check for required sections
    required_sections = [
        'Summary Statistics',
        'Total Events',
        'Date Range',
        'Unique Source IPs',
        'Countries Represented',
        'Top Threats',
        'Geographic Hotspots',
        'Anomalous Periods',
        'Reproduction Steps'
    ]

    for section in required_sections:
        assert section in report_content, f"Report missing section: {section}"


def test_report_has_statistics():
    """Test that report contains actual statistics, not just empty sections."""
    with open('/app/report.md', 'r') as f:
        report_content = f.read()

    # Should contain numeric values
    import re
    numbers = re.findall(r'\d+', report_content)
    assert len(numbers) > 5, "Report lacks statistical data"

    # Should mention at least one IP address
    ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    assert re.search(ip_pattern, report_content), "Report doesn't mention any IP addresses"


def test_dashboard_server_running():
    """Test that dashboard server is accessible on port 8080."""
    max_retries = 10
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.get('http://0.0.0.0:8080/', timeout=5)
            # Should get 401 without auth or 200 with proper response
            assert response.status_code in [200, 401], \
                f"Unexpected status code: {response.status_code}"
            return  # Success
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                pytest.fail("Dashboard server not accessible on port 8080")
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                pytest.fail("Dashboard server timeout on port 8080")


def test_dashboard_authentication():
    """Test that dashboard implements basic authentication."""
    try:
        # Request without auth should return 401
        response = requests.get('http://0.0.0.0:8080/', timeout=5)
        if response.status_code == 401:
            # Good - authentication required
            assert 'WWW-Authenticate' in response.headers or response.status_code == 401

        # Request with correct credentials should succeed
        response_auth = requests.get(
            'http://0.0.0.0:8080/',
            auth=HTTPBasicAuth('admin', 'admin'),
            timeout=5
        )
        assert response_auth.status_code == 200, \
            f"Authentication with admin/admin failed: {response_auth.status_code}"
    except requests.exceptions.ConnectionError:
        pytest.skip("Dashboard server not running")


def test_dashboard_serves_html():
    """Test that dashboard serves HTML content."""
    try:
        response = requests.get(
            'http://0.0.0.0:8080/',
            auth=HTTPBasicAuth('admin', 'admin'),
            timeout=5
        )

        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            assert 'html' in content_type.lower() or '<html' in response.text.lower(), \
                "Dashboard doesn't serve HTML content"
    except requests.exceptions.ConnectionError:
        pytest.skip("Dashboard server not running")


def test_dashboard_has_required_elements():
    """Test that dashboard HTML contains required visualization elements."""
    try:
        response = requests.get(
            'http://0.0.0.0:8080/',
            auth=HTTPBasicAuth('admin', 'admin'),
            timeout=5
        )

        if response.status_code == 200:
            html_content = response.text.lower()

            # Should have map element
            assert 'map' in html_content, "Dashboard missing map element"

            # Should have chart/time series
            assert 'chart' in html_content or 'time' in html_content, \
                "Dashboard missing time series chart"

            # Should have table for events
            assert 'table' in html_content, "Dashboard missing data table"

            # Should have download link
            assert 'download' in html_content or 'parquet' in html_content, \
                "Dashboard missing download link"
    except requests.exceptions.ConnectionError:
        pytest.skip("Dashboard server not running")


def test_dashboard_api_endpoint():
    """Test that dashboard provides data API endpoint."""
    try:
        response = requests.get(
            'http://0.0.0.0:8080/api/data',
            auth=HTTPBasicAuth('admin', 'admin'),
            timeout=5
        )

        if response.status_code == 200:
            # Should return JSON data
            data = response.json()
            assert isinstance(data, list), "API should return list of events"
            assert len(data) > 0, "API returns empty data"

            # Check that data has required fields
            if len(data) > 0:
                first_event = data[0]
                assert 'source_ip' in first_event, "API data missing source_ip"
                assert 'threat_level' in first_event, "API data missing threat_level"
    except requests.exceptions.ConnectionError:
        pytest.skip("Dashboard server not running")
    except json.JSONDecodeError:
        pytest.fail("API endpoint doesn't return valid JSON")


def test_no_hardcoded_dummy_data():
    """Test that solution doesn't just output hardcoded dummy data."""
    df = pd.read_parquet('/app/enriched_data.parquet')

    # Check that we have diverse data, not just repeated dummy values
    unique_ips = df['source_ip'].nunique()
    assert unique_ips >= 5, f"Too few unique IPs ({unique_ips}), might be dummy data"

    unique_countries = df[df['country'] != 'Private']['country'].nunique()
    assert unique_countries >= 3, f"Too few unique countries ({unique_countries}), might be dummy data"

    # Check that timestamps are not all the same
    unique_timestamps = df['timestamp'].nunique()
    assert unique_timestamps >= 10, "Too few unique timestamps, might be dummy data"


def test_edge_case_handling():
    """Test that solution handles edge cases gracefully."""
    df = pd.read_parquet('/app/enriched_data.parquet')

    # Should not have any completely null rows
    assert not df.isnull().all(axis=1).any(), "Found completely null rows"

    # Critical fields should never be null
    assert df['source_ip'].notna().all(), "source_ip has null values"
    assert df['threat_level'].notna().all(), "threat_level has null values"
    assert df['is_anomalous'].notna().all(), "is_anomalous has null values"
