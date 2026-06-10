import os
import json
import pytest


def test_output_file_exists():
    """Test that the output file exists."""
    assert os.path.exists('/app/efficient_locations.json'), \
        "Output file /app/efficient_locations.json does not exist"


def test_output_is_valid_json():
    """Test that the output file contains valid JSON."""
    with open('/app/efficient_locations.json', 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output file is not valid JSON: {e}")


def test_output_has_required_time_periods():
    """Test that output contains all four required time periods."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    required_periods = ['morning', 'afternoon', 'evening', 'night']
    for period in required_periods:
        assert period in data, f"Missing time period: {period}"


def test_time_periods_are_lists():
    """Test that each time period contains a list."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    for period in ['morning', 'afternoon', 'evening', 'night']:
        assert isinstance(data[period], list), \
            f"Time period '{period}' should be a list, got {type(data[period])}"


def test_location_entries_have_required_fields():
    """Test that each location entry has all required fields."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    required_fields = ['location_id', 'avg_duration_minutes', 'avg_fare_per_minute',
                      'avg_passengers', 'trip_count']

    for period, locations in data.items():
        for i, location in enumerate(locations):
            for field in required_fields:
                assert field in location, \
                    f"Location {i} in '{period}' missing field: {field}"


def test_location_field_types():
    """Test that location fields have correct data types."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    for period, locations in data.items():
        for location in locations:
            assert isinstance(location['location_id'], int), \
                f"location_id should be int in '{period}'"
            assert isinstance(location['avg_duration_minutes'], (int, float)), \
                f"avg_duration_minutes should be numeric in '{period}'"
            assert isinstance(location['avg_fare_per_minute'], (int, float)), \
                f"avg_fare_per_minute should be numeric in '{period}'"
            assert isinstance(location['avg_passengers'], (int, float)), \
                f"avg_passengers should be numeric in '{period}'"
            assert isinstance(location['trip_count'], int), \
                f"trip_count should be int in '{period}'"


def test_no_more_than_10_locations_per_period():
    """Test that each time period has at most 10 locations."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    for period, locations in data.items():
        assert len(locations) <= 10, \
            f"Time period '{period}' has {len(locations)} locations, expected at most 10"


def test_positive_values():
    """Test that numeric values are positive and reasonable."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    for period, locations in data.items():
        for location in locations:
            assert location['avg_duration_minutes'] > 0, \
                f"avg_duration_minutes should be positive in '{period}'"
            assert location['avg_fare_per_minute'] > 0, \
                f"avg_fare_per_minute should be positive in '{period}'"
            assert location['avg_passengers'] > 0, \
                f"avg_passengers should be positive in '{period}'"
            assert location['trip_count'] > 0, \
                f"trip_count should be positive in '{period}'"


def test_location_ids_are_valid():
    """Test that location IDs match those in the input data."""
    # Known location IDs from taxi_data.csv: 48, 142, 161, 237
    valid_location_ids = {48, 142, 161, 237}

    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    for period, locations in data.items():
        for location in locations:
            assert location['location_id'] in valid_location_ids, \
                f"Invalid location_id {location['location_id']} in '{period}'"


def test_avg_passengers_reasonable_range():
    """Test that average passengers is within reasonable range (1-4 typical)."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    for period, locations in data.items():
        for location in locations:
            assert 0 < location['avg_passengers'] <= 6, \
                f"avg_passengers {location['avg_passengers']} out of reasonable range in '{period}'"


def test_sorted_by_efficiency():
    """Test that locations within each period are sorted by efficiency (descending).
    Since efficiency_score is not in output, we verify that the ranking makes sense
    by checking that the list is not randomly ordered."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    for period, locations in data.items():
        if len(locations) > 1:
            # Calculate a simple efficiency proxy for verification
            # Higher fare/min, lower duration, higher passengers = better
            efficiency_scores = []
            for loc in locations:
                # Simple proxy: fare_per_min * passengers / duration
                score = (loc['avg_fare_per_minute'] * loc['avg_passengers']) / loc['avg_duration_minutes']
                efficiency_scores.append(score)

            # Check that scores are generally decreasing (allowing some tolerance)
            # Not strictly enforcing because the actual formula might differ
            # But at least the first should be >= last
            if len(efficiency_scores) >= 2:
                assert efficiency_scores[0] >= efficiency_scores[-1] * 0.5, \
                    f"Locations in '{period}' don't appear to be sorted by efficiency"


def test_no_duplicate_locations_per_period():
    """Test that there are no duplicate location IDs within each time period."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    for period, locations in data.items():
        location_ids = [loc['location_id'] for loc in locations]
        assert len(location_ids) == len(set(location_ids)), \
            f"Duplicate location IDs found in '{period}'"


def test_trip_count_matches_aggregation():
    """Test that trip counts are reasonable given the input data size."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    total_trips = 0
    for period, locations in data.items():
        for location in locations:
            total_trips += location['trip_count']

    # We have 50 data rows (51 lines - 1 header)
    # Total trips across all locations should not exceed input rows
    assert total_trips <= 50, \
        f"Total trip count {total_trips} exceeds input data rows"


def test_fare_per_minute_reasonable():
    """Test that fare per minute is within reasonable range."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    for period, locations in data.items():
        for location in locations:
            # Typical NYC taxi fare per minute: $0.50 - $5.00
            assert 0.1 < location['avg_fare_per_minute'] < 10, \
                f"avg_fare_per_minute {location['avg_fare_per_minute']} out of reasonable range in '{period}'"


def test_duration_reasonable():
    """Test that average duration is within reasonable range."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    for period, locations in data.items():
        for location in locations:
            # Typical taxi trip: 5-120 minutes
            assert 1 < location['avg_duration_minutes'] < 180, \
                f"avg_duration_minutes {location['avg_duration_minutes']} out of reasonable range in '{period}'"


def test_not_empty_output():
    """Test that the output is not just empty lists."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    # At least some periods should have data
    total_locations = sum(len(locations) for locations in data.values())
    assert total_locations > 0, "Output contains no location data"


def test_morning_period_has_data():
    """Test that morning period has data (we know there are morning trips in input)."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    # From the input data, we have trips at 07:30, 08:15, 09:00, etc. (morning: 06:00-11:59)
    assert len(data['morning']) > 0, "Morning period should have at least one location"


def test_afternoon_period_has_data():
    """Test that afternoon period has data."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    # From the input data, we have trips at 13:00, 14:30, 15:45, etc. (afternoon: 12:00-17:59)
    assert len(data['afternoon']) > 0, "Afternoon period should have at least one location"


def test_evening_period_has_data():
    """Test that evening period has data."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    # From the input data, we have trips at 19:00, 20:15, 21:30, etc. (evening: 18:00-22:59)
    assert len(data['evening']) > 0, "Evening period should have at least one location"


def test_night_period_has_data():
    """Test that night period has data."""
    with open('/app/efficient_locations.json', 'r') as f:
        data = json.load(f)

    # From the input data, we have trips at 00:30, 01:45, 03:00, etc. (night: 23:00-05:59)
    assert len(data['night']) > 0, "Night period should have at least one location"
