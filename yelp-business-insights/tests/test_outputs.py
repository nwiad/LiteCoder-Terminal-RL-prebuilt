import os
import csv
import pandas as pd
import json

def test_output_file_exists():
    """Test that the output file exists."""
    assert os.path.exists('/app/insights.csv'), "Output file /app/insights.csv does not exist"

def test_output_file_not_empty():
    """Test that the output file is not empty."""
    assert os.path.getsize('/app/insights.csv') > 0, "Output file is empty"

def test_csv_headers():
    """Test that CSV has correct headers."""
    with open('/app/insights.csv', 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        expected_headers = ['category', 'city', 'avg_rating', 'business_count', 'top_business_name']
        assert headers == expected_headers, f"Headers mismatch. Expected {expected_headers}, got {headers}"

def test_csv_structure():
    """Test that CSV can be parsed and has the correct columns."""
    df = pd.read_csv('/app/insights.csv')
    expected_columns = ['category', 'city', 'avg_rating', 'business_count', 'top_business_name']
    assert list(df.columns) == expected_columns, f"Column mismatch. Expected {expected_columns}, got {list(df.columns)}"
    assert len(df) > 0, "CSV has no data rows"

def test_only_high_rated_businesses():
    """Test that only businesses with stars >= 4.5 are included."""
    # Load input data to verify filtering
    businesses = []
    with open('/app/business.json', 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                businesses.append(json.loads(line))

    # Get all business names from output
    df = pd.read_csv('/app/insights.csv')
    output_business_names = set(df['top_business_name'].unique())

    # Check that no business with stars < 4.5 appears in output
    for business in businesses:
        if business['stars'] < 4.5:
            assert business['name'] not in output_business_names, \
                f"Business '{business['name']}' with {business['stars']} stars should not appear (< 4.5)"

def test_null_empty_categories_excluded():
    """Test that businesses with null or empty categories are excluded."""
    df = pd.read_csv('/app/insights.csv')
    output_business_names = set(df['top_business_name'].unique())

    # b14 has null categories, b17 has empty categories - neither should appear
    assert 'No Category Place' not in output_business_names, "Business with null categories should be excluded"
    assert 'Empty Categories' not in output_business_names, "Business with empty categories should be excluded"

def test_category_splitting():
    """Test that multi-category businesses appear in multiple rows."""
    df = pd.read_csv('/app/insights.csv')

    # "The Golden Spoon" has categories: "Restaurants, Italian, Fine Dining"
    # It should appear in multiple category-city combinations
    golden_spoon_rows = df[df['top_business_name'] == 'The Golden Spoon']

    # Check that it appears in at least one row (could be top business in multiple categories)
    assert len(golden_spoon_rows) >= 1, "Multi-category business should appear in output"

    # Verify categories are properly split (check for "Restaurants", "Italian", "Fine Dining" in Las Vegas)
    restaurants_lv = df[(df['category'] == 'Restaurants') & (df['city'] == 'Las Vegas')]
    italian_lv = df[(df['category'] == 'Italian') & (df['city'] == 'Las Vegas')]
    fine_dining_lv = df[(df['category'] == 'Fine Dining') & (df['city'] == 'Las Vegas')]

    assert len(restaurants_lv) > 0, "Category 'Restaurants' should exist for Las Vegas"
    assert len(italian_lv) > 0, "Category 'Italian' should exist for Las Vegas"
    assert len(fine_dining_lv) > 0, "Category 'Fine Dining' should exist for Las Vegas"

def test_grouping_by_category_city():
    """Test that data is correctly grouped by category and city."""
    df = pd.read_csv('/app/insights.csv')

    # Each row should represent a unique (category, city) combination
    grouped = df.groupby(['category', 'city']).size()
    assert all(grouped == 1), "Each (category, city) combination should appear exactly once"

def test_average_rating_calculation():
    """Test that average ratings are calculated correctly."""
    # Load input data
    businesses = []
    with open('/app/business.json', 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                business = json.loads(line)
                if business['stars'] >= 4.5 and business.get('categories'):
                    businesses.append(business)

    df = pd.read_csv('/app/insights.csv')

    # Manually calculate for "Italian" in "Las Vegas"
    # b1 (The Golden Spoon): 4.5, b5 (Bella Pasta): 4.7
    italian_lv = df[(df['category'] == 'Italian') & (df['city'] == 'Las Vegas')]
    if len(italian_lv) > 0:
        expected_avg = (4.5 + 4.7) / 2
        actual_avg = italian_lv.iloc[0]['avg_rating']
        assert abs(actual_avg - expected_avg) < 0.01, \
            f"Average rating for Italian in Las Vegas should be {expected_avg}, got {actual_avg}"

def test_business_count_accuracy():
    """Test that business counts are accurate."""
    df = pd.read_csv('/app/insights.csv')

    # Check "Italian" in "Las Vegas" - should have 2 businesses (b1, b5)
    italian_lv = df[(df['category'] == 'Italian') & (df['city'] == 'Las Vegas')]
    if len(italian_lv) > 0:
        assert italian_lv.iloc[0]['business_count'] == 2, \
            "Italian in Las Vegas should have 2 businesses"

    # Check "Restaurants" in "Tucson" - should have 2 businesses (b9, b15)
    restaurants_tucson = df[(df['category'] == 'Restaurants') & (df['city'] == 'Tucson')]
    if len(restaurants_tucson) > 0:
        assert restaurants_tucson.iloc[0]['business_count'] == 2, \
            "Restaurants in Tucson should have 2 businesses"

def test_top_business_selection():
    """Test that the top business is the highest-rated in each group."""
    df = pd.read_csv('/app/insights.csv')

    # For "Spas" in "Las Vegas", only b7 (Zen Spa & Wellness) with 5.0 stars
    spas_lv = df[(df['category'] == 'Spas') & (df['city'] == 'Las Vegas')]
    if len(spas_lv) > 0:
        assert spas_lv.iloc[0]['top_business_name'] == 'Zen Spa & Wellness', \
            "Top business for Spas in Las Vegas should be Zen Spa & Wellness"

    # For "Italian" in "Las Vegas", b5 (Bella Pasta) has 4.7 stars, b1 (The Golden Spoon) has 4.5
    # Top should be Bella Pasta
    italian_lv = df[(df['category'] == 'Italian') & (df['city'] == 'Las Vegas')]
    if len(italian_lv) > 0:
        assert italian_lv.iloc[0]['top_business_name'] == 'Bella Pasta', \
            "Top business for Italian in Las Vegas should be Bella Pasta (4.7 > 4.5)"

def test_sorting_by_avg_rating():
    """Test that output is sorted by avg_rating descending."""
    df = pd.read_csv('/app/insights.csv')

    # Check that avg_rating is in descending order (allowing for ties)
    avg_ratings = df['avg_rating'].tolist()
    for i in range(len(avg_ratings) - 1):
        assert avg_ratings[i] >= avg_ratings[i + 1], \
            f"Rows should be sorted by avg_rating descending. Row {i} has {avg_ratings[i]}, row {i+1} has {avg_ratings[i+1]}"

def test_sorting_by_business_count_within_same_rating():
    """Test that within same avg_rating, rows are sorted by business_count descending."""
    df = pd.read_csv('/app/insights.csv')

    # Group by avg_rating and check business_count ordering within each group
    for rating in df['avg_rating'].unique():
        same_rating_rows = df[df['avg_rating'] == rating]
        if len(same_rating_rows) > 1:
            business_counts = same_rating_rows['business_count'].tolist()
            for i in range(len(business_counts) - 1):
                assert business_counts[i] >= business_counts[i + 1], \
                    f"Within avg_rating={rating}, business_count should be descending"

def test_data_types():
    """Test that columns have correct data types."""
    df = pd.read_csv('/app/insights.csv')

    assert df['category'].dtype == 'object', "category should be string"
    assert df['city'].dtype == 'object', "city should be string"
    assert pd.api.types.is_numeric_dtype(df['avg_rating']), "avg_rating should be numeric"
    assert pd.api.types.is_integer_dtype(df['business_count']), "business_count should be integer"
    assert df['top_business_name'].dtype == 'object', "top_business_name should be string"

def test_no_missing_values():
    """Test that there are no missing values in the output."""
    df = pd.read_csv('/app/insights.csv')
    assert not df.isnull().any().any(), "Output should not contain any missing values"

def test_avg_rating_range():
    """Test that average ratings are within valid range (4.5 to 5.0)."""
    df = pd.read_csv('/app/insights.csv')

    # Since we only include businesses with stars >= 4.5, avg should be >= 4.5
    assert df['avg_rating'].min() >= 4.5, "Average rating should be at least 4.5"
    assert df['avg_rating'].max() <= 5.0, "Average rating should not exceed 5.0"

def test_business_count_positive():
    """Test that business counts are positive integers."""
    df = pd.read_csv('/app/insights.csv')
    assert (df['business_count'] > 0).all(), "All business counts should be positive"

def test_no_duplicate_category_city_combinations():
    """Test that there are no duplicate (category, city) combinations."""
    df = pd.read_csv('/app/insights.csv')
    duplicates = df.duplicated(subset=['category', 'city'])
    assert not duplicates.any(), "There should be no duplicate (category, city) combinations"

def test_whitespace_trimming():
    """Test that category names have no leading/trailing whitespace."""
    df = pd.read_csv('/app/insights.csv')

    for category in df['category']:
        assert category == category.strip(), f"Category '{category}' has untrimmed whitespace"
