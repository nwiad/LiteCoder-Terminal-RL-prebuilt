## Distributed Web Crawler with Rate Limiting

Build a distributed web crawler that crawls multiple domains concurrently while respecting rate limits and avoiding duplicate content.

**Technical Requirements:**
- Python 3.8+
- Input: `/app/config.json` - crawler configuration
- Output: `/app/crawled_data.db` - SQLite database with crawled content
- Output: `/app/stats.json` - crawling statistics

**Input Specification:**

`/app/config.json` structure:
```json
{
  "seed_urls": ["http://example.com", "http://test.com"],
  "max_pages_per_domain": 50,
  "rate_limit_delay": 1.0,
  "max_concurrent_requests": 10,
  "respect_robots_txt": true,
  "user_agent": "CustomCrawler/1.0"
}
```

**Output Specification:**

`/app/crawled_data.db` - SQLite database with table `pages`:
- `url` (TEXT, PRIMARY KEY) - crawled URL
- `domain` (TEXT) - extracted domain
- `content_hash` (TEXT) - SHA256 hash of content
- `title` (TEXT) - page title
- `content` (TEXT) - extracted text content
- `crawled_at` (TIMESTAMP) - crawl timestamp
- `status_code` (INTEGER) - HTTP status code

`/app/stats.json` structure:
```json
{
  "total_pages_crawled": 100,
  "pages_per_domain": {"example.com": 50, "test.com": 50},
  "duplicates_skipped": 5,
  "errors": 2,
  "crawl_duration_seconds": 120.5
}
```

**Functional Requirements:**

1. **URL Queue Management**: Implement a queue system for managing URLs to crawl (can use in-memory queue or Redis if available)

2. **Rate Limiting**: Enforce per-domain rate limiting based on `rate_limit_delay` from config

3. **Robots.txt Compliance**: Parse and respect robots.txt rules when `respect_robots_txt` is true

4. **Content Deduplication**: Skip URLs already crawled and detect duplicate content using SHA256 hashing

5. **Concurrent Crawling**: Support concurrent requests up to `max_concurrent_requests` limit

6. **Content Extraction**: Extract page title and text content from HTML

7. **Error Handling**: Handle network errors, timeouts, and invalid responses gracefully; continue crawling other URLs

8. **Statistics Tracking**: Track crawling metrics and write to `/app/stats.json` upon completion

**Edge Cases:**
- Handle redirects (follow and record final URL)
- Skip non-HTML content types
- Handle malformed HTML gracefully
- Respect `max_pages_per_domain` limit per domain
- Handle connection timeouts and retries
