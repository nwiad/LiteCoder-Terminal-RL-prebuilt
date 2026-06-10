import os
import json
import pytest


def test_output_file_exists():
    """Test that the output JSON file exists."""
    assert os.path.exists('/app/medal_analysis.json'), "Output file /app/medal_analysis.json does not exist"


def test_output_file_not_empty():
    """Test that the output file is not empty."""
    assert os.path.getsize('/app/medal_analysis.json') > 0, "Output file is empty"


def test_output_is_valid_json():
    """Test that the output file contains valid JSON."""
    with open('/app/medal_analysis.json', 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output file is not valid JSON: {e}")


def test_output_has_required_keys():
    """Test that the output JSON has all required top-level keys."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    required_keys = ['total_medals', 'medals_by_sport', 'top_countries', 'medals_by_year']
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"


def test_total_medals_structure():
    """Test that total_medals has correct structure with country codes and medal counts."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    total_medals = data['total_medals']
    assert isinstance(total_medals, dict), "total_medals should be a dictionary"
    assert len(total_medals) > 0, "total_medals should not be empty"

    # Check structure for each country
    for country, medals in total_medals.items():
        assert isinstance(country, str), f"Country code should be string, got {type(country)}"
        assert country.isupper(), f"Country code {country} should be uppercase"
        assert len(country) == 3, f"Country code {country} should be 3 letters"

        assert isinstance(medals, dict), f"Medals for {country} should be a dictionary"
        assert 'Gold' in medals, f"Missing 'Gold' key for {country}"
        assert 'Silver' in medals, f"Missing 'Silver' key for {country}"
        assert 'Bronze' in medals, f"Missing 'Bronze' key for {country}"
        assert 'Total' in medals, f"Missing 'Total' key for {country}"

        # Check that all values are integers
        for medal_type, count in medals.items():
            assert isinstance(count, int), f"{medal_type} count for {country} should be integer, got {type(count)}"
            assert count >= 0, f"{medal_type} count for {country} should be non-negative"


def test_total_medals_total_calculation():
    """Test that Total equals sum of Gold, Silver, and Bronze for each country."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    total_medals = data['total_medals']
    for country, medals in total_medals.items():
        expected_total = medals['Gold'] + medals['Silver'] + medals['Bronze']
        assert medals['Total'] == expected_total, \
            f"Total for {country} ({medals['Total']}) doesn't match sum of medals ({expected_total})"


def test_medals_by_sport_structure():
    """Test that medals_by_sport has correct structure."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    medals_by_sport = data['medals_by_sport']
    assert isinstance(medals_by_sport, dict), "medals_by_sport should be a dictionary"
    assert len(medals_by_sport) > 0, "medals_by_sport should not be empty"

    for sport, medals in medals_by_sport.items():
        assert isinstance(sport, str), f"Sport name should be string, got {type(sport)}"
        assert len(sport) > 0, f"Sport name should not be empty"

        assert isinstance(medals, dict), f"Medals for {sport} should be a dictionary"
        assert 'Gold' in medals, f"Missing 'Gold' key for {sport}"
        assert 'Silver' in medals, f"Missing 'Silver' key for {sport}"
        assert 'Bronze' in medals, f"Missing 'Bronze' key for {sport}"

        for medal_type, count in medals.items():
            assert isinstance(count, int), f"{medal_type} count for {sport} should be integer"
            assert count >= 0, f"{medal_type} count for {sport} should be non-negative"


def test_top_countries_structure():
    """Test that top_countries is a list with correct structure."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    top_countries = data['top_countries']
    assert isinstance(top_countries, list), "top_countries should be a list"
    assert len(top_countries) > 0, "top_countries should not be empty"
    assert len(top_countries) <= 10, "top_countries should have at most 10 entries"

    for entry in top_countries:
        assert isinstance(entry, dict), "Each top_countries entry should be a dictionary"
        assert 'country' in entry, "Missing 'country' key in top_countries entry"
        assert 'total' in entry, "Missing 'total' key in top_countries entry"

        assert isinstance(entry['country'], str), "Country should be string"
        assert entry['country'].isupper(), f"Country code {entry['country']} should be uppercase"
        assert isinstance(entry['total'], int), "Total should be integer"
        assert entry['total'] > 0, "Total should be positive"


def test_top_countries_sorted_descending():
    """Test that top_countries is sorted by total in descending order."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    top_countries = data['top_countries']
    totals = [entry['total'] for entry in top_countries]

    assert totals == sorted(totals, reverse=True), \
        "top_countries should be sorted by total in descending order"


def test_top_countries_matches_total_medals():
    """Test that top_countries totals match the Total field in total_medals."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    top_countries = data['top_countries']
    total_medals = data['total_medals']

    for entry in top_countries:
        country = entry['country']
        assert country in total_medals, f"Country {country} in top_countries not found in total_medals"
        assert entry['total'] == total_medals[country]['Total'], \
            f"Total mismatch for {country}: {entry['total']} vs {total_medals[country]['Total']}"


def test_medals_by_year_structure():
    """Test that medals_by_year has correct structure."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    medals_by_year = data['medals_by_year']
    assert isinstance(medals_by_year, dict), "medals_by_year should be a dictionary"
    assert len(medals_by_year) > 0, "medals_by_year should not be empty"

    for year, medals in medals_by_year.items():
        assert isinstance(year, str), f"Year should be string, got {type(year)}"
        assert year.isdigit(), f"Year {year} should be numeric"

        assert isinstance(medals, dict), f"Medals for {year} should be a dictionary"
        assert 'Gold' in medals, f"Missing 'Gold' key for year {year}"
        assert 'Silver' in medals, f"Missing 'Silver' key for year {year}"
        assert 'Bronze' in medals, f"Missing 'Bronze' key for year {year}"

        for medal_type, count in medals.items():
            assert isinstance(count, int), f"{medal_type} count for {year} should be integer"
            assert count >= 0, f"{medal_type} count for {year} should be non-negative"


def test_data_consistency_total_count():
    """Test that total medal counts are consistent across different sections."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    # Sum all medals from total_medals
    total_from_countries = sum(
        country_data['Total']
        for country_data in data['total_medals'].values()
    )

    # Sum all medals from medals_by_sport
    total_from_sports = sum(
        sport_data['Gold'] + sport_data['Silver'] + sport_data['Bronze']
        for sport_data in data['medals_by_sport'].values()
    )

    # Sum all medals from medals_by_year
    total_from_years = sum(
        year_data['Gold'] + year_data['Silver'] + year_data['Bronze']
        for year_data in data['medals_by_year'].values()
    )

    assert total_from_countries == total_from_sports, \
        f"Total medals mismatch: countries ({total_from_countries}) vs sports ({total_from_sports})"
    assert total_from_countries == total_from_years, \
        f"Total medals mismatch: countries ({total_from_countries}) vs years ({total_from_years})"


def test_expected_countries_present():
    """Test that expected countries from input data are present."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    total_medals = data['total_medals']

    # Based on the input CSV, these countries should be present
    expected_countries = ['USA', 'CHN', 'GBR', 'JAM', 'AUS', 'RUS', 'JPN', 'BRA', 'KEN', 'GRE', 'CUB']

    for country in expected_countries:
        assert country in total_medals, f"Expected country {country} not found in total_medals"


def test_usa_has_most_medals():
    """Test that USA has the highest medal count (based on input data)."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    top_countries = data['top_countries']
    assert len(top_countries) > 0, "top_countries should not be empty"
    assert top_countries[0]['country'] == 'USA', "USA should be the top country by medal count"


def test_expected_sports_present():
    """Test that expected sports from input data are present."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    medals_by_sport = data['medals_by_sport']

    # Based on the input CSV, these sports should be present
    expected_sports = ['Swimming', 'Athletics', 'Diving', 'Gymnastics', 'Cycling', 'Judo', 'Basketball', 'Football', 'Boxing', 'Weightlifting']

    for sport in expected_sports:
        assert sport in medals_by_sport, f"Expected sport {sport} not found in medals_by_sport"


def test_expected_years_present():
    """Test that expected years from input data are present."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    medals_by_year = data['medals_by_year']

    # Based on the input CSV, these years should be present
    expected_years = ['2000', '2004', '2008', '2012', '2016', '2020']

    for year in expected_years:
        assert year in medals_by_year, f"Expected year {year} not found in medals_by_year"


def test_no_invalid_medal_types():
    """Test that only valid medal types (Gold, Silver, Bronze) are present."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    valid_medal_types = {'Gold', 'Silver', 'Bronze', 'Total'}

    # Check total_medals
    for country, medals in data['total_medals'].items():
        for medal_type in medals.keys():
            assert medal_type in valid_medal_types, \
                f"Invalid medal type '{medal_type}' found in total_medals for {country}"

    # Check medals_by_sport
    valid_sport_medal_types = {'Gold', 'Silver', 'Bronze'}
    for sport, medals in data['medals_by_sport'].items():
        for medal_type in medals.keys():
            assert medal_type in valid_sport_medal_types, \
                f"Invalid medal type '{medal_type}' found in medals_by_sport for {sport}"

    # Check medals_by_year
    for year, medals in data['medals_by_year'].items():
        for medal_type in medals.keys():
            assert medal_type in valid_sport_medal_types, \
                f"Invalid medal type '{medal_type}' found in medals_by_year for {year}"


def test_not_just_hardcoded_dummy_data():
    """Test that the output is not just hardcoded dummy data."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    # Check that we have reasonable data diversity
    assert len(data['total_medals']) >= 10, "Should have at least 10 countries"
    assert len(data['medals_by_sport']) >= 8, "Should have at least 8 sports"
    assert len(data['medals_by_year']) >= 5, "Should have at least 5 years"

    # Check that USA has a reasonable number of medals (not just 1 or 0)
    assert 'USA' in data['total_medals'], "USA should be in total_medals"
    assert data['total_medals']['USA']['Total'] >= 10, "USA should have at least 10 medals based on input data"


def test_swimming_has_multiple_medals():
    """Test that Swimming sport has multiple medals (based on input data)."""
    with open('/app/medal_analysis.json', 'r') as f:
        data = json.load(f)

    medals_by_sport = data['medals_by_sport']
    assert 'Swimming' in medals_by_sport, "Swimming should be in medals_by_sport"

    swimming_total = (medals_by_sport['Swimming']['Gold'] +
                     medals_by_sport['Swimming']['Silver'] +
                     medals_by_sport['Swimming']['Bronze'])
    assert swimming_total >= 10, "Swimming should have at least 10 medals based on input data"
