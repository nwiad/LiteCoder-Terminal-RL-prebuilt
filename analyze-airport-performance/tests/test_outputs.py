import os
import json
import pytest
import numpy as np
import pandas as pd


def test_output_file_exists():
    """Test that the output JSON file exists."""
    assert os.path.exists('/app/analysis_results.json'), "Output file /app/analysis_results.json does not exist"


def test_output_file_not_empty():
    """Test that the output file is not empty."""
    assert os.path.getsize('/app/analysis_results.json') > 0, "Output file is empty"


def test_valid_json_format():
    """Test that the output is valid JSON."""
    with open('/app/analysis_results.json', 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON format: {e}")
    assert isinstance(data, dict), "Output should be a JSON object (dict)"


def load_output():
    """Helper function to load the output JSON."""
    with open('/app/analysis_results.json', 'r') as f:
        return json.load(f)


def load_input_data():
    """Helper function to load the input CSV."""
    return pd.read_csv('/app/airports_data.csv')


def test_required_top_level_keys():
    """Test that all required top-level keys are present."""
    data = load_output()
    required_keys = [
        'top_airports_by_passengers',
        'top_airports_by_movements',
        'delay_statistics',
        'yearly_trends'
    ]
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"


def test_top_airports_by_passengers_structure():
    """Test the structure of top_airports_by_passengers."""
    data = load_output()
    top_passengers = data['top_airports_by_passengers']

    assert isinstance(top_passengers, list), "top_airports_by_passengers should be a list"
    assert len(top_passengers) <= 10, "Should have at most 10 airports"
    assert len(top_passengers) > 0, "Should have at least 1 airport"

    for airport in top_passengers:
        assert 'airport_code' in airport, "Missing airport_code"
        assert 'airport_name' in airport, "Missing airport_name"
        assert 'total_passengers' in airport, "Missing total_passengers"
        assert isinstance(airport['total_passengers'], int), "total_passengers should be an integer"
        assert airport['total_passengers'] > 0, "total_passengers should be positive"


def test_top_airports_by_passengers_correctness():
    """Test that top airports by passengers are correctly calculated and sorted."""
    data = load_output()
    df = load_input_data()

    # Calculate expected top 10
    expected = df.groupby(['airport_code', 'airport_name'])['passengers'].sum().reset_index()
    expected = expected.sort_values('passengers', ascending=False).head(10)

    top_passengers = data['top_airports_by_passengers']

    # Check that results are sorted in descending order
    totals = [airport['total_passengers'] for airport in top_passengers]
    assert totals == sorted(totals, reverse=True), "Airports should be sorted by total_passengers in descending order"

    # Verify top airport matches expected
    assert top_passengers[0]['airport_code'] == expected.iloc[0]['airport_code'], "Top airport by passengers is incorrect"
    assert top_passengers[0]['total_passengers'] == int(expected.iloc[0]['passengers']), "Top airport passenger count is incorrect"


def test_top_airports_by_movements_structure():
    """Test the structure of top_airports_by_movements."""
    data = load_output()
    top_movements = data['top_airports_by_movements']

    assert isinstance(top_movements, list), "top_airports_by_movements should be a list"
    assert len(top_movements) <= 10, "Should have at most 10 airports"
    assert len(top_movements) > 0, "Should have at least 1 airport"

    for airport in top_movements:
        assert 'airport_code' in airport, "Missing airport_code"
        assert 'airport_name' in airport, "Missing airport_name"
        assert 'total_movements' in airport, "Missing total_movements"
        assert isinstance(airport['total_movements'], int), "total_movements should be an integer"
        assert airport['total_movements'] > 0, "total_movements should be positive"


def test_top_airports_by_movements_correctness():
    """Test that top airports by movements are correctly calculated and sorted."""
    data = load_output()
    df = load_input_data()

    # Calculate expected top 10
    expected = df.groupby(['airport_code', 'airport_name'])['aircraft_movements'].sum().reset_index()
    expected = expected.sort_values('aircraft_movements', ascending=False).head(10)

    top_movements = data['top_airports_by_movements']

    # Check that results are sorted in descending order
    totals = [airport['total_movements'] for airport in top_movements]
    assert totals == sorted(totals, reverse=True), "Airports should be sorted by total_movements in descending order"

    # Verify top airport matches expected
    assert top_movements[0]['airport_code'] == expected.iloc[0]['airport_code'], "Top airport by movements is incorrect"
    assert top_movements[0]['total_movements'] == int(expected.iloc[0]['aircraft_movements']), "Top airport movement count is incorrect"


def test_delay_statistics_structure():
    """Test the structure of delay_statistics."""
    data = load_output()
    delay_stats = data['delay_statistics']

    assert isinstance(delay_stats, dict), "delay_statistics should be a dict"
    assert 'airports_with_highest_avg_delay' in delay_stats, "Missing airports_with_highest_avg_delay"
    assert 'overall_avg_delay' in delay_stats, "Missing overall_avg_delay"

    highest_delays = delay_stats['airports_with_highest_avg_delay']
    assert isinstance(highest_delays, list), "airports_with_highest_avg_delay should be a list"
    assert len(highest_delays) <= 5, "Should have at most 5 airports"
    assert len(highest_delays) > 0, "Should have at least 1 airport"

    for airport in highest_delays:
        assert 'airport_code' in airport, "Missing airport_code"
        assert 'airport_name' in airport, "Missing airport_name"
        assert 'avg_delay_minutes' in airport, "Missing avg_delay_minutes"
        assert isinstance(airport['avg_delay_minutes'], (int, float)), "avg_delay_minutes should be numeric"
        assert airport['avg_delay_minutes'] > 0, "avg_delay_minutes should be positive"

    overall_avg = delay_stats['overall_avg_delay']
    assert isinstance(overall_avg, (int, float)), "overall_avg_delay should be numeric"
    assert overall_avg > 0, "overall_avg_delay should be positive"


def test_delay_statistics_correctness():
    """Test that delay statistics are correctly calculated."""
    data = load_output()
    df = load_input_data()

    # Convert delay column to numeric, handling missing values
    df['avg_delay_minutes'] = pd.to_numeric(df['avg_delay_minutes'], errors='coerce')
    df_with_delay = df[df['avg_delay_minutes'].notna()]

    # Calculate expected top 5 airports with highest average delay
    expected = df_with_delay.groupby(['airport_code', 'airport_name'])['avg_delay_minutes'].mean().reset_index()
    expected = expected.sort_values('avg_delay_minutes', ascending=False).head(5)

    highest_delays = data['delay_statistics']['airports_with_highest_avg_delay']

    # Check that results are sorted in descending order
    delays = [airport['avg_delay_minutes'] for airport in highest_delays]
    assert delays == sorted(delays, reverse=True), "Airports should be sorted by avg_delay_minutes in descending order"

    # Verify top airport with highest delay
    assert highest_delays[0]['airport_code'] == expected.iloc[0]['airport_code'], "Top airport by delay is incorrect"
    assert np.isclose(highest_delays[0]['avg_delay_minutes'], expected.iloc[0]['avg_delay_minutes'], atol=0.01), "Top airport delay value is incorrect"

    # Verify overall average delay
    expected_overall = df_with_delay['avg_delay_minutes'].mean()
    assert np.isclose(data['delay_statistics']['overall_avg_delay'], expected_overall, atol=0.01), "Overall average delay is incorrect"


def test_delay_statistics_excludes_missing_values():
    """Test that missing delay values are properly excluded from calculations."""
    data = load_output()
    df = load_input_data()

    # Check that airports with all missing delays are not in top 5
    df['avg_delay_minutes'] = pd.to_numeric(df['avg_delay_minutes'], errors='coerce')
    airports_with_all_missing = df.groupby('airport_code')['avg_delay_minutes'].apply(lambda x: x.isna().all())
    airports_with_all_missing = airports_with_all_missing[airports_with_all_missing].index.tolist()

    highest_delays = data['delay_statistics']['airports_with_highest_avg_delay']
    result_codes = [airport['airport_code'] for airport in highest_delays]

    for code in airports_with_all_missing:
        assert code not in result_codes, f"Airport {code} with all missing delays should not be in results"


def test_yearly_trends_structure():
    """Test the structure of yearly_trends."""
    data = load_output()
    yearly_trends = data['yearly_trends']

    assert isinstance(yearly_trends, dict), "yearly_trends should be a dict"
    assert len(yearly_trends) > 0, "yearly_trends should not be empty"

    for year, stats in yearly_trends.items():
        assert year.isdigit(), f"Year key '{year}' should be a string representation of a number"
        assert isinstance(stats, dict), f"Stats for year {year} should be a dict"
        assert 'total_passengers' in stats, f"Missing total_passengers for year {year}"
        assert 'total_movements' in stats, f"Missing total_movements for year {year}"
        assert 'avg_delay' in stats, f"Missing avg_delay for year {year}"

        assert isinstance(stats['total_passengers'], int), f"total_passengers for year {year} should be an integer"
        assert isinstance(stats['total_movements'], int), f"total_movements for year {year} should be an integer"
        assert isinstance(stats['avg_delay'], (int, float)), f"avg_delay for year {year} should be numeric"

        assert stats['total_passengers'] > 0, f"total_passengers for year {year} should be positive"
        assert stats['total_movements'] > 0, f"total_movements for year {year} should be positive"


def test_yearly_trends_correctness():
    """Test that yearly trends are correctly calculated."""
    data = load_output()
    df = load_input_data()

    df['avg_delay_minutes'] = pd.to_numeric(df['avg_delay_minutes'], errors='coerce')

    yearly_trends = data['yearly_trends']

    for year in df['year'].unique():
        year_str = str(year)
        assert year_str in yearly_trends, f"Missing year {year} in yearly_trends"

        year_data = df[df['year'] == year]
        year_data_with_delay = year_data[year_data['avg_delay_minutes'].notna()]

        expected_passengers = int(year_data['passengers'].sum())
        expected_movements = int(year_data['aircraft_movements'].sum())
        expected_delay = year_data_with_delay['avg_delay_minutes'].mean()

        assert yearly_trends[year_str]['total_passengers'] == expected_passengers, f"Incorrect total_passengers for year {year}"
        assert yearly_trends[year_str]['total_movements'] == expected_movements, f"Incorrect total_movements for year {year}"
        assert np.isclose(yearly_trends[year_str]['avg_delay'], expected_delay, atol=0.01), f"Incorrect avg_delay for year {year}"


def test_float_precision():
    """Test that float values are rounded to 2 decimal places."""
    data = load_output()

    # Check delay statistics
    overall_avg = data['delay_statistics']['overall_avg_delay']
    assert len(str(overall_avg).split('.')[-1]) <= 2, "overall_avg_delay should be rounded to 2 decimal places"

    for airport in data['delay_statistics']['airports_with_highest_avg_delay']:
        delay = airport['avg_delay_minutes']
        assert len(str(delay).split('.')[-1]) <= 2, f"avg_delay_minutes for {airport['airport_code']} should be rounded to 2 decimal places"

    # Check yearly trends
    for year, stats in data['yearly_trends'].items():
        delay = stats['avg_delay']
        assert len(str(delay).split('.')[-1]) <= 2, f"avg_delay for year {year} should be rounded to 2 decimal places"


def test_no_hardcoded_dummy_data():
    """Test that the output is not hardcoded or dummy data."""
    data = load_output()
    df = load_input_data()

    # Verify that the total passengers across all top airports is reasonable
    total_passengers_in_top = sum(airport['total_passengers'] for airport in data['top_airports_by_passengers'])
    total_passengers_in_data = df['passengers'].sum()

    # Top 10 should represent a significant portion of total traffic
    assert total_passengers_in_top > 0, "Total passengers in top airports should be positive"
    assert total_passengers_in_top <= total_passengers_in_data, "Total passengers in top airports cannot exceed total in dataset"

    # Verify that airport codes are from the actual dataset
    actual_codes = set(df['airport_code'].unique())
    result_codes = set(airport['airport_code'] for airport in data['top_airports_by_passengers'])
    assert result_codes.issubset(actual_codes), "Airport codes in results should be from the input dataset"


def test_data_types_consistency():
    """Test that data types are consistent throughout the output."""
    data = load_output()

    # All passenger and movement counts should be integers
    for airport in data['top_airports_by_passengers']:
        assert isinstance(airport['total_passengers'], int), "total_passengers must be integer"

    for airport in data['top_airports_by_movements']:
        assert isinstance(airport['total_movements'], int), "total_movements must be integer"

    # All delay values should be floats or ints
    for airport in data['delay_statistics']['airports_with_highest_avg_delay']:
        assert isinstance(airport['avg_delay_minutes'], (int, float)), "avg_delay_minutes must be numeric"

    assert isinstance(data['delay_statistics']['overall_avg_delay'], (int, float)), "overall_avg_delay must be numeric"

    for year, stats in data['yearly_trends'].items():
        assert isinstance(stats['total_passengers'], int), "total_passengers must be integer"
        assert isinstance(stats['total_movements'], int), "total_movements must be integer"
        assert isinstance(stats['avg_delay'], (int, float)), "avg_delay must be numeric"


def test_airport_names_match_codes():
    """Test that airport names correctly match their codes."""
    data = load_output()
    df = load_input_data()

    # Create a mapping of airport codes to names from input data
    code_to_name = df.groupby('airport_code')['airport_name'].first().to_dict()

    # Check top airports by passengers
    for airport in data['top_airports_by_passengers']:
        code = airport['airport_code']
        name = airport['airport_name']
        assert code in code_to_name, f"Airport code {code} not found in input data"
        assert name == code_to_name[code], f"Airport name mismatch for code {code}"

    # Check top airports by movements
    for airport in data['top_airports_by_movements']:
        code = airport['airport_code']
        name = airport['airport_name']
        assert code in code_to_name, f"Airport code {code} not found in input data"
        assert name == code_to_name[code], f"Airport name mismatch for code {code}"

    # Check delay statistics
    for airport in data['delay_statistics']['airports_with_highest_avg_delay']:
        code = airport['airport_code']
        name = airport['airport_name']
        assert code in code_to_name, f"Airport code {code} not found in input data"
        assert name == code_to_name[code], f"Airport name mismatch for code {code}"
