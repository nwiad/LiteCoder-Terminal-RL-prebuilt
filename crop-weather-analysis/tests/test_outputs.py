import os
import json
import pytest


def test_output_file_exists():
    """Test that the output file exists"""
    assert os.path.exists('/app/crop_recommendations.json'), "Output file /app/crop_recommendations.json does not exist"


def test_output_file_not_empty():
    """Test that the output file is not empty"""
    assert os.path.getsize('/app/crop_recommendations.json') > 0, "Output file is empty"


def test_output_is_valid_json():
    """Test that the output file contains valid JSON"""
    with open('/app/crop_recommendations.json', 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output file is not valid JSON: {e}")

    assert isinstance(data, dict), "Output JSON must be a dictionary"


def test_output_has_required_top_level_keys():
    """Test that output has 'stations' and 'summary' keys"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    assert 'stations' in data, "Output must contain 'stations' key"
    assert 'summary' in data, "Output must contain 'summary' key"


def test_stations_is_list():
    """Test that 'stations' is a list"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['stations'], list), "'stations' must be a list"
    assert len(data['stations']) > 0, "'stations' list cannot be empty"


def test_station_structure():
    """Test that each station has the required structure"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    for station in data['stations']:
        assert isinstance(station, dict), "Each station must be a dictionary"
        assert 'station_id' in station, "Station must have 'station_id'"
        assert 'recommended_crops' in station, "Station must have 'recommended_crops'"
        assert isinstance(station['station_id'], str), "'station_id' must be a string"
        assert isinstance(station['recommended_crops'], list), "'recommended_crops' must be a list"


def test_crop_recommendation_structure():
    """Test that each crop recommendation has the required fields"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    for station in data['stations']:
        for crop in station['recommended_crops']:
            assert isinstance(crop, dict), "Each crop recommendation must be a dictionary"

            # Check required fields
            assert 'crop_name' in crop, "Crop must have 'crop_name'"
            assert 'suitability_score' in crop, "Crop must have 'suitability_score'"
            assert 'optimal_planting_months' in crop, "Crop must have 'optimal_planting_months'"
            assert 'growing_conditions' in crop, "Crop must have 'growing_conditions'"

            # Check field types
            assert isinstance(crop['crop_name'], str), "'crop_name' must be a string"
            assert isinstance(crop['suitability_score'], (int, float)), "'suitability_score' must be a number"
            assert isinstance(crop['optimal_planting_months'], list), "'optimal_planting_months' must be a list"
            assert isinstance(crop['growing_conditions'], dict), "'growing_conditions' must be a dictionary"


def test_suitability_score_range():
    """Test that suitability scores are within valid range (0-100)"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    for station in data['stations']:
        for crop in station['recommended_crops']:
            score = crop['suitability_score']
            assert 0 <= score <= 100, f"Suitability score {score} for {crop['crop_name']} must be between 0 and 100"


def test_growing_conditions_structure():
    """Test that growing_conditions has the required structure"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    for station in data['stations']:
        for crop in station['recommended_crops']:
            conditions = crop['growing_conditions']

            assert 'avg_temperature_range' in conditions, "growing_conditions must have 'avg_temperature_range'"
            assert 'avg_precipitation' in conditions, "growing_conditions must have 'avg_precipitation'"

            # Check temperature range
            temp_range = conditions['avg_temperature_range']
            assert isinstance(temp_range, list), "'avg_temperature_range' must be a list"
            assert len(temp_range) == 2, "'avg_temperature_range' must have exactly 2 elements"
            assert all(isinstance(t, (int, float)) for t in temp_range), "Temperature values must be numbers"
            assert temp_range[0] <= temp_range[1], "Temperature range must be [min, max]"

            # Check precipitation
            precip = conditions['avg_precipitation']
            assert isinstance(precip, (int, float)), "'avg_precipitation' must be a number"
            assert precip >= 0, "'avg_precipitation' must be non-negative"


def test_optimal_planting_months_valid():
    """Test that optimal_planting_months contains valid month names"""
    valid_months = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December']

    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    for station in data['stations']:
        for crop in station['recommended_crops']:
            months = crop['optimal_planting_months']
            for month in months:
                assert isinstance(month, str), "Month names must be strings"
                assert month in valid_months, f"Invalid month name: {month}"


def test_required_crops_present():
    """Test that all required crops are analyzed (Wheat, Corn, Rice, Soybeans)"""
    required_crops = {'Wheat', 'Corn', 'Rice', 'Soybeans'}

    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    for station in data['stations']:
        crop_names = {crop['crop_name'] for crop in station['recommended_crops']}
        assert required_crops.issubset(crop_names), f"Station {station['station_id']} missing required crops. Found: {crop_names}, Required: {required_crops}"


def test_summary_structure():
    """Test that summary has the required structure"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    summary = data['summary']

    assert 'total_stations_analyzed' in summary, "Summary must have 'total_stations_analyzed'"
    assert 'date_range' in summary, "Summary must have 'date_range'"

    assert isinstance(summary['total_stations_analyzed'], int), "'total_stations_analyzed' must be an integer"
    assert summary['total_stations_analyzed'] > 0, "'total_stations_analyzed' must be positive"

    date_range = summary['date_range']
    assert isinstance(date_range, dict), "'date_range' must be a dictionary"
    assert 'start' in date_range, "'date_range' must have 'start'"
    assert 'end' in date_range, "'date_range' must have 'end'"


def test_date_range_format():
    """Test that date_range dates are in YYYY-MM-DD format"""
    import re
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    date_range = data['summary']['date_range']

    assert date_pattern.match(date_range['start']), f"Start date '{date_range['start']}' must be in YYYY-MM-DD format"
    assert date_pattern.match(date_range['end']), f"End date '{date_range['end']}' must be in YYYY-MM-DD format"
    assert date_range['start'] <= date_range['end'], "Start date must be before or equal to end date"


def test_total_stations_matches_data():
    """Test that total_stations_analyzed matches the number of stations in the output"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    expected_count = len(data['stations'])
    actual_count = data['summary']['total_stations_analyzed']

    assert actual_count == expected_count, f"total_stations_analyzed ({actual_count}) does not match number of stations ({expected_count})"


def test_station_ids_are_unique():
    """Test that station IDs are unique"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    station_ids = [station['station_id'] for station in data['stations']]
    assert len(station_ids) == len(set(station_ids)), "Station IDs must be unique"


def test_crops_sorted_by_suitability():
    """Test that crops are sorted by suitability score in descending order"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    for station in data['stations']:
        scores = [crop['suitability_score'] for crop in station['recommended_crops']]
        assert scores == sorted(scores, reverse=True), f"Crops for station {station['station_id']} are not sorted by suitability score"


def test_temperature_range_reasonable():
    """Test that temperature ranges are within reasonable bounds"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    for station in data['stations']:
        for crop in station['recommended_crops']:
            temp_range = crop['growing_conditions']['avg_temperature_range']
            assert -50 <= temp_range[0] <= 60, f"Minimum temperature {temp_range[0]} is outside reasonable range (-50 to 60°C)"
            assert -50 <= temp_range[1] <= 60, f"Maximum temperature {temp_range[1]} is outside reasonable range (-50 to 60°C)"


def test_not_all_empty_planting_months():
    """Test that at least some crops have optimal planting months (not all empty)"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    has_planting_months = False
    for station in data['stations']:
        for crop in station['recommended_crops']:
            if len(crop['optimal_planting_months']) > 0:
                has_planting_months = True
                break
        if has_planting_months:
            break

    assert has_planting_months, "At least some crops should have optimal planting months"


def test_not_hardcoded_dummy_data():
    """Test that the output is not just hardcoded dummy data"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    # Check that we have multiple stations (input has STATION_A, STATION_B, STATION_C)
    assert len(data['stations']) >= 2, "Output should contain multiple stations"

    # Check that suitability scores vary (not all the same)
    all_scores = []
    for station in data['stations']:
        for crop in station['recommended_crops']:
            all_scores.append(crop['suitability_score'])

    unique_scores = set(all_scores)
    assert len(unique_scores) > 1, "Suitability scores should vary, not all be the same value"

    # Check that precipitation values vary
    all_precip = []
    for station in data['stations']:
        for crop in station['recommended_crops']:
            all_precip.append(crop['growing_conditions']['avg_precipitation'])

    unique_precip = set(all_precip)
    assert len(unique_precip) > 1, "Precipitation values should vary, not all be the same"


def test_date_range_matches_input_data():
    """Test that date range is reasonable (2023 data)"""
    with open('/app/crop_recommendations.json', 'r') as f:
        data = json.load(f)

    date_range = data['summary']['date_range']

    # Input data is from 2023
    assert date_range['start'].startswith('2023'), "Start date should be from 2023"
    assert date_range['end'].startswith('2023'), "End date should be from 2023"
