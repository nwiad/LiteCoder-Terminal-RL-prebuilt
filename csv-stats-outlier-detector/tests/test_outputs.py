import os
import json
import pytest


def test_output_file_exists():
    """Test that output.json file exists."""
    assert os.path.exists('/app/output.json'), "output.json file not found at /app/output.json"


def test_output_is_valid_json():
    """Test that output.json contains valid JSON."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)
    assert isinstance(data, dict), "Output must be a JSON object"


def test_output_has_columns_key():
    """Test that output has 'columns' key."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)
    assert 'columns' in data, "Output must have 'columns' key"
    assert isinstance(data['columns'], dict), "'columns' must be a dictionary"


def test_numeric_columns_detected():
    """Test that numeric columns are detected and non-numeric are skipped."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    columns = data['columns']

    # Should have numeric columns: age, salary, score
    assert len(columns) >= 1, "At least one numeric column should be detected"

    # Should NOT have non-numeric columns like 'name' or 'category'
    assert 'name' not in columns, "Non-numeric column 'name' should be skipped"
    assert 'category' not in columns, "Non-numeric column 'category' should be skipped"


def test_column_statistics_structure():
    """Test that each column has required statistics fields."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    columns = data['columns']
    assert len(columns) > 0, "Should have at least one numeric column"

    for col_name, col_data in columns.items():
        # Check required fields
        assert 'count' in col_data, f"Column '{col_name}' missing 'count'"
        assert 'mean' in col_data, f"Column '{col_name}' missing 'mean'"
        assert 'median' in col_data, f"Column '{col_name}' missing 'median'"
        assert 'std' in col_data, f"Column '{col_name}' missing 'std'"
        assert 'outliers' in col_data, f"Column '{col_name}' missing 'outliers'"

        # Check types
        assert isinstance(col_data['count'], int), f"Column '{col_name}' count must be integer"
        assert isinstance(col_data['mean'], (int, float)), f"Column '{col_name}' mean must be numeric"
        assert isinstance(col_data['median'], (int, float)), f"Column '{col_name}' median must be numeric"
        assert isinstance(col_data['std'], (int, float)), f"Column '{col_name}' std must be numeric"
        assert isinstance(col_data['outliers'], list), f"Column '{col_name}' outliers must be a list"


def test_outlier_structure():
    """Test that outliers have correct structure."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    columns = data['columns']

    for col_name, col_data in columns.items():
        outliers = col_data['outliers']

        # Each outlier must have row_index, value, score
        for outlier in outliers:
            assert 'row_index' in outlier, f"Outlier in '{col_name}' missing 'row_index'"
            assert 'value' in outlier, f"Outlier in '{col_name}' missing 'value'"
            assert 'score' in outlier, f"Outlier in '{col_name}' missing 'score'"

            assert isinstance(outlier['row_index'], int), f"row_index must be integer"
            assert isinstance(outlier['value'], (int, float)), f"value must be numeric"
            assert isinstance(outlier['score'], (int, float)), f"score must be numeric"
            assert outlier['score'] >= 0, f"Z-score must be non-negative (absolute value)"


def test_outliers_sorted_by_score():
    """Test that outliers are sorted by score in descending order."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    columns = data['columns']

    for col_name, col_data in columns.items():
        outliers = col_data['outliers']

        if len(outliers) > 1:
            scores = [o['score'] for o in outliers]
            # Check descending order
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i+1], f"Outliers in '{col_name}' not sorted by score descending"


def test_max_five_outliers():
    """Test that at most 5 outliers are reported per column."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    columns = data['columns']

    for col_name, col_data in columns.items():
        outliers = col_data['outliers']
        assert len(outliers) <= 5, f"Column '{col_name}' has more than 5 outliers"


def test_statistics_are_reasonable():
    """Test that statistics are reasonable (not NaN, not infinity)."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    columns = data['columns']

    for col_name, col_data in columns.items():
        # Check for valid numbers
        assert col_data['count'] > 0, f"Column '{col_name}' count must be positive"
        assert not (col_data['mean'] != col_data['mean']), f"Column '{col_name}' mean is NaN"
        assert not (col_data['median'] != col_data['median']), f"Column '{col_name}' median is NaN"
        assert not (col_data['std'] != col_data['std']), f"Column '{col_name}' std is NaN"
        assert col_data['std'] >= 0, f"Column '{col_name}' std must be non-negative"


def test_rounding_precision():
    """Test that values are rounded to 1 decimal place."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    columns = data['columns']

    for col_name, col_data in columns.items():
        # Check statistics rounding
        mean_str = str(col_data['mean'])
        median_str = str(col_data['median'])
        std_str = str(col_data['std'])

        # If there's a decimal point, should have at most 1 decimal place
        if '.' in mean_str:
            decimals = len(mean_str.split('.')[1])
            assert decimals <= 1, f"Column '{col_name}' mean has more than 1 decimal place"

        if '.' in median_str:
            decimals = len(median_str.split('.')[1])
            assert decimals <= 1, f"Column '{col_name}' median has more than 1 decimal place"

        if '.' in std_str:
            decimals = len(std_str.split('.')[1])
            assert decimals <= 1, f"Column '{col_name}' std has more than 1 decimal place"

        # Check outlier rounding
        for outlier in col_data['outliers']:
            value_str = str(outlier['value'])
            score_str = str(outlier['score'])

            if '.' in value_str:
                decimals = len(value_str.split('.')[1])
                assert decimals <= 1, f"Outlier value in '{col_name}' has more than 1 decimal place"

            if '.' in score_str:
                decimals = len(score_str.split('.')[1])
                assert decimals <= 1, f"Outlier score in '{col_name}' has more than 1 decimal place"


def test_row_indices_are_valid():
    """Test that row indices are valid (0-based, within data range)."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    columns = data['columns']

    for col_name, col_data in columns.items():
        count = col_data['count']

        for outlier in col_data['outliers']:
            row_idx = outlier['row_index']
            # Row index should be non-negative and reasonable
            assert row_idx >= 0, f"Row index must be non-negative"
            # Should be within reasonable range (less than 1 million rows for sanity)
            assert row_idx < 1000000, f"Row index seems unreasonably large"


def test_not_empty_output():
    """Test that output is not just an empty structure."""
    with open('/app/output.json', 'r') as f:
        content = f.read().strip()

    # Should not be empty
    assert len(content) > 0, "Output file is empty"

    # Should not be just '{}'
    data = json.loads(content)
    assert data != {}, "Output is empty JSON object"
    assert data.get('columns') != {}, "Columns object is empty"


def test_statistics_consistency():
    """Test that statistics are internally consistent."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    columns = data['columns']

    for col_name, col_data in columns.items():
        count = col_data['count']
        mean = col_data['mean']
        median = col_data['median']
        std = col_data['std']

        # If count is 1, std should be 0
        if count == 1:
            assert std == 0.0, f"Column '{col_name}' with count=1 should have std=0"

        # Mean and median should be reasonable relative to each other
        # (not testing exact relationship, just sanity check)
        # Both should exist and be numbers
        assert isinstance(mean, (int, float)), f"Mean must be numeric"
        assert isinstance(median, (int, float)), f"Median must be numeric"


def test_z_score_calculation():
    """Test that Z-scores are calculated correctly (spot check)."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    columns = data['columns']

    for col_name, col_data in columns.items():
        mean = col_data['mean']
        std = col_data['std']

        for outlier in col_data['outliers']:
            value = outlier['value']
            score = outlier['score']

            # Calculate expected Z-score
            if std == 0:
                expected_z = 0.0
            else:
                expected_z = abs((value - mean) / std)

            # Allow small rounding differences (0.15 tolerance for rounding)
            assert abs(score - round(expected_z, 1)) < 0.15, \
                f"Z-score mismatch in '{col_name}': expected ~{round(expected_z, 1)}, got {score}"


def test_no_duplicate_row_indices():
    """Test that there are no duplicate row indices in outliers (same row reported twice)."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    columns = data['columns']

    for col_name, col_data in columns.items():
        outliers = col_data['outliers']
        row_indices = [o['row_index'] for o in outliers]

        # Check for duplicates
        assert len(row_indices) == len(set(row_indices)), \
            f"Column '{col_name}' has duplicate row indices in outliers"
