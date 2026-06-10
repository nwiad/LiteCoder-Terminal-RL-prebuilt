import os
import json
import sqlite3
import hashlib
from datetime import datetime

def test_database_exists():
    """Test that the SQLite database file exists"""
    assert os.path.exists('/app/crawled_data.db'), "Database file /app/crawled_data.db does not exist"

def test_stats_file_exists():
    """Test that the stats JSON file exists"""
    assert os.path.exists('/app/stats.json'), "Stats file /app/stats.json does not exist"

def test_database_not_empty():
    """Test that the database file is not empty"""
    size = os.path.getsize('/app/crawled_data.db')
    assert size > 0, "Database file is empty"

def test_stats_file_not_empty():
    """Test that the stats file is not empty"""
    size = os.path.getsize('/app/stats.json')
    assert size > 0, "Stats file is empty"

def test_database_schema():
    """Test that the database has the correct schema"""
    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    # Check if pages table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pages'")
    result = cursor.fetchone()
    assert result is not None, "Table 'pages' does not exist"

    # Check table schema
    cursor.execute("PRAGMA table_info(pages)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]

    required_columns = ['url', 'domain', 'content_hash', 'title', 'content', 'crawled_at', 'status_code']
    for col in required_columns:
        assert col in column_names, f"Required column '{col}' is missing from pages table"

    conn.close()

def test_database_has_data():
    """Test that the database contains crawled pages"""
    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM pages")
    count = cursor.fetchone()[0]

    conn.close()

    assert count > 0, "Database contains no crawled pages"

def test_stats_json_structure():
    """Test that stats.json has the correct structure"""
    with open('/app/stats.json', 'r') as f:
        stats = json.load(f)

    required_keys = ['total_pages_crawled', 'pages_per_domain', 'duplicates_skipped', 'errors', 'crawl_duration_seconds']
    for key in required_keys:
        assert key in stats, f"Required key '{key}' is missing from stats.json"

def test_stats_total_pages_crawled():
    """Test that total_pages_crawled is a positive integer"""
    with open('/app/stats.json', 'r') as f:
        stats = json.load(f)

    assert isinstance(stats['total_pages_crawled'], int), "total_pages_crawled must be an integer"
    assert stats['total_pages_crawled'] > 0, "total_pages_crawled must be greater than 0"

def test_stats_pages_per_domain():
    """Test that pages_per_domain is a dictionary with valid data"""
    with open('/app/stats.json', 'r') as f:
        stats = json.load(f)

    assert isinstance(stats['pages_per_domain'], dict), "pages_per_domain must be a dictionary"
    assert len(stats['pages_per_domain']) > 0, "pages_per_domain must not be empty"

    for domain, count in stats['pages_per_domain'].items():
        assert isinstance(domain, str), f"Domain key must be a string, got {type(domain)}"
        assert isinstance(count, int), f"Page count for domain {domain} must be an integer"
        assert count > 0, f"Page count for domain {domain} must be greater than 0"

def test_stats_duplicates_skipped():
    """Test that duplicates_skipped is a non-negative integer"""
    with open('/app/stats.json', 'r') as f:
        stats = json.load(f)

    assert isinstance(stats['duplicates_skipped'], int), "duplicates_skipped must be an integer"
    assert stats['duplicates_skipped'] >= 0, "duplicates_skipped must be non-negative"

def test_stats_errors():
    """Test that errors is a non-negative integer"""
    with open('/app/stats.json', 'r') as f:
        stats = json.load(f)

    assert isinstance(stats['errors'], int), "errors must be an integer"
    assert stats['errors'] >= 0, "errors must be non-negative"

def test_stats_crawl_duration():
    """Test that crawl_duration_seconds is a positive number"""
    with open('/app/stats.json', 'r') as f:
        stats = json.load(f)

    assert isinstance(stats['crawl_duration_seconds'], (int, float)), "crawl_duration_seconds must be a number"
    assert stats['crawl_duration_seconds'] > 0, "crawl_duration_seconds must be greater than 0"

def test_database_url_uniqueness():
    """Test that all URLs in the database are unique (PRIMARY KEY constraint)"""
    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT url, COUNT(*) as cnt FROM pages GROUP BY url HAVING cnt > 1")
    duplicates = cursor.fetchall()

    conn.close()

    assert len(duplicates) == 0, f"Found duplicate URLs in database: {duplicates}"

def test_database_content_hash_format():
    """Test that content_hash values are valid SHA256 hashes"""
    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT content_hash FROM pages LIMIT 10")
    hashes = cursor.fetchall()

    conn.close()

    for (hash_value,) in hashes:
        assert hash_value is not None, "content_hash should not be NULL"
        assert len(hash_value) == 64, f"SHA256 hash should be 64 characters, got {len(hash_value)}"
        assert all(c in '0123456789abcdef' for c in hash_value.lower()), "content_hash should be a valid hex string"

def test_database_status_codes():
    """Test that status_code values are valid HTTP status codes"""
    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT status_code FROM pages")
    status_codes = cursor.fetchall()

    conn.close()

    for (status_code,) in status_codes:
        assert status_code is not None, "status_code should not be NULL"
        assert isinstance(status_code, int), "status_code must be an integer"
        assert 100 <= status_code < 600, f"status_code {status_code} is not a valid HTTP status code"

def test_database_domains_extracted():
    """Test that domain field is properly extracted from URLs"""
    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT url, domain FROM pages LIMIT 10")
    rows = cursor.fetchall()

    conn.close()

    for url, domain in rows:
        assert domain is not None and domain != "", f"Domain should not be empty for URL {url}"
        assert domain in url, f"Domain '{domain}' should be part of URL '{url}'"

def test_database_timestamps():
    """Test that crawled_at timestamps are valid"""
    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT crawled_at FROM pages LIMIT 10")
    timestamps = cursor.fetchall()

    conn.close()

    for (timestamp,) in timestamps:
        assert timestamp is not None, "crawled_at should not be NULL"
        # Try to parse as ISO format timestamp
        try:
            datetime.fromisoformat(timestamp)
        except:
            assert False, f"crawled_at '{timestamp}' is not a valid ISO format timestamp"

def test_stats_consistency_with_database():
    """Test that stats.json total_pages_crawled matches database row count"""
    with open('/app/stats.json', 'r') as f:
        stats = json.load(f)

    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM pages")
    db_count = cursor.fetchone()[0]

    conn.close()

    assert stats['total_pages_crawled'] == db_count, \
        f"total_pages_crawled ({stats['total_pages_crawled']}) does not match database row count ({db_count})"

def test_stats_pages_per_domain_consistency():
    """Test that pages_per_domain in stats matches actual database counts"""
    with open('/app/stats.json', 'r') as f:
        stats = json.load(f)

    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT domain, COUNT(*) FROM pages GROUP BY domain")
    db_domain_counts = dict(cursor.fetchall())

    conn.close()

    # Check that all domains in stats exist in database
    for domain, count in stats['pages_per_domain'].items():
        assert domain in db_domain_counts, f"Domain '{domain}' in stats not found in database"
        assert count == db_domain_counts[domain], \
            f"Domain '{domain}' count mismatch: stats={count}, database={db_domain_counts[domain]}"

def test_max_pages_per_domain_respected():
    """Test that max_pages_per_domain limit is respected"""
    # Read config to get the limit
    with open('/app/config.json', 'r') as f:
        config = json.load(f)

    max_pages = config['max_pages_per_domain']

    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT domain, COUNT(*) as cnt FROM pages GROUP BY domain")
    domain_counts = cursor.fetchall()

    conn.close()

    for domain, count in domain_counts:
        assert count <= max_pages, \
            f"Domain '{domain}' has {count} pages, exceeding max_pages_per_domain limit of {max_pages}"

def test_database_content_not_empty():
    """Test that crawled pages have non-empty content"""
    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT url, content FROM pages LIMIT 10")
    rows = cursor.fetchall()

    conn.close()

    assert len(rows) > 0, "No pages found in database"

    for url, content in rows:
        # Content should exist (can be empty string for some pages, but not NULL)
        assert content is not None, f"Content is NULL for URL {url}"

def test_content_hash_matches_content():
    """Test that content_hash actually matches the SHA256 of the content"""
    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT content, content_hash FROM pages LIMIT 5")
    rows = cursor.fetchall()

    conn.close()

    for content, stored_hash in rows:
        computed_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        assert computed_hash == stored_hash, \
            f"Content hash mismatch: computed={computed_hash}, stored={stored_hash}"

def test_no_hardcoded_dummy_data():
    """Test that the solution doesn't just insert hardcoded dummy data"""
    conn = sqlite3.connect('/app/crawled_data.db')
    cursor = conn.cursor()

    # Check for variety in data
    cursor.execute("SELECT COUNT(DISTINCT domain) FROM pages")
    distinct_domains = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT content_hash) FROM pages")
    distinct_hashes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pages")
    total_pages = cursor.fetchone()[0]

    conn.close()

    # If there are multiple pages, there should be some variety
    if total_pages > 1:
        assert distinct_hashes > 1 or distinct_domains > 1, \
            "All pages have identical content and domain - likely hardcoded dummy data"
