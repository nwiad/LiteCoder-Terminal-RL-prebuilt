## Olympic Medal Analytics Data Pipeline

Build a data processing pipeline that analyzes Olympic medal data and generates statistical insights on medal distribution patterns.

**Technical Requirements:**
- Python 3.x
- Input: CSV file at `/app/olympic_medals.csv`
- Output: JSON file at `/app/medal_analysis.json`

**Input Format:**

The input CSV file contains Olympic medal records with the following columns:
- `Year` (integer): Olympic year (e.g., 2000, 2004, 2008, 2012, 2016, 2020)
- `Country` (string): Three-letter country code (e.g., "USA", "CHN", "GBR")
- `Sport` (string): Sport name (e.g., "Athletics", "Swimming", "Gymnastics")
- `Medal` (string): Medal type - one of "Gold", "Silver", or "Bronze"
- `Athlete` (string): Athlete name

Example input rows:
```
Year,Country,Sport,Medal,Athlete
2020,USA,Swimming,Gold,Caeleb Dressel
2020,CHN,Diving,Gold,Quan Hongchan
2016,JAM,Athletics,Gold,Usain Bolt
```

**Output Format:**

Generate a JSON file with the following structure:

```json
{
  "total_medals": {
    "Country_Code": {"Gold": int, "Silver": int, "Bronze": int, "Total": int}
  },
  "medals_by_sport": {
    "Sport_Name": {"Gold": int, "Silver": int, "Bronze": int}
  },
  "top_countries": [
    {"country": "Country_Code", "total": int}
  ],
  "medals_by_year": {
    "Year": {"Gold": int, "Silver": int, "Bronze": int}
  }
}
```

**Requirements:**

1. Read the CSV file from `/app/olympic_medals.csv`
2. Calculate total medal counts per country (Gold, Silver, Bronze, and Total)
3. Calculate medal counts by sport across all years
4. Identify top 10 countries by total medal count (sorted descending)
5. Calculate medal distribution by year
6. Write results to `/app/medal_analysis.json`

**Data Processing:**

- Handle missing or empty values by skipping those records
- Country codes should be uppercase
- Medal types must be exactly "Gold", "Silver", or "Bronze" (case-sensitive)
- All numeric counts should be integers
