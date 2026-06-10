## Task: Analyze Yelp Dataset for Business Insights

You are a data scientist analyzing Yelp business data to identify top-rated businesses and trends across categories and cities.

**Technical Requirements:**
- Language: Python 3.x
- Input: `/app/business.json` (Yelp business dataset in JSON format)
- Output: `/app/insights.csv` (summary statistics and insights)

**Input Specification:**

The input file `/app/business.json` contains one JSON object per line (JSON Lines format) with the following fields:
- `business_id` (string): Unique business identifier
- `name` (string): Business name
- `city` (string): City location
- `state` (string): State code
- `stars` (float): Average rating (0.0 to 5.0)
- `review_count` (integer): Number of reviews
- `categories` (string): Comma-separated list of business categories (may be null)

**Output Specification:**

Generate `/app/insights.csv` with the following columns:
- `category` (string): Business category name
- `city` (string): City name
- `avg_rating` (float): Average star rating for this category-city combination
- `business_count` (integer): Number of businesses in this category-city combination
- `top_business_name` (string): Name of the highest-rated business in this group

**Requirements:**

1. Load and parse the JSON Lines format from `/app/business.json`
2. Filter businesses with ratings of 4.5 stars or higher
3. Handle missing or null categories by excluding those records
4. Split comma-separated categories into individual category entries
5. Group data by category and city combinations
6. Calculate average ratings and count businesses for each group
7. Identify the top-rated business name in each group
8. Sort output by average rating (descending), then by business count (descending)
9. Export results to `/app/insights.csv` in CSV format with headers

**Data Handling:**
- Exclude businesses with null or empty categories
- Trim whitespace from category names after splitting
- Handle businesses that appear in multiple categories appropriately
