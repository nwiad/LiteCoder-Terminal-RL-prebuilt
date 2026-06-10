import os
import json
import pytest


def test_results_json_exists():
    """Test that results.json file exists"""
    assert os.path.exists('/app/results.json'), "results.json file not found at /app/results.json"


def test_model_pth_exists():
    """Test that model.pth file exists"""
    assert os.path.exists('/app/model.pth'), "model.pth file not found at /app/model.pth"


def test_results_json_valid_format():
    """Test that results.json is valid JSON and not empty"""
    with open('/app/results.json', 'r') as f:
        content = f.read().strip()
        assert len(content) > 0, "results.json is empty"
        data = json.loads(content)
        assert isinstance(data, dict), "results.json must contain a JSON object"


def test_results_has_required_keys():
    """Test that results.json has the required top-level keys"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert 'model_performance' in data, "Missing 'model_performance' key in results.json"
    assert 'sample_recommendations' in data, "Missing 'sample_recommendations' key in results.json"


def test_model_performance_structure():
    """Test that model_performance has correct structure and valid metrics"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    perf = data['model_performance']
    assert isinstance(perf, dict), "model_performance must be a dictionary"

    # Check required keys
    assert 'rmse' in perf, "Missing 'rmse' in model_performance"
    assert 'mae' in perf, "Missing 'mae' in model_performance"

    # Check types
    assert isinstance(perf['rmse'], (int, float)), "rmse must be a number"
    assert isinstance(perf['mae'], (int, float)), "mae must be a number"

    # Check values are positive
    assert perf['rmse'] > 0, "rmse must be positive"
    assert perf['mae'] > 0, "mae must be positive"

    # Sanity check: RMSE and MAE should be reasonable for 1-5 rating scale
    # A completely random model would have RMSE ~1.4, MAE ~1.1
    # A trained model should be better than random
    assert perf['rmse'] < 5.0, f"rmse too high ({perf['rmse']}), model likely not trained"
    assert perf['mae'] < 5.0, f"mae too high ({perf['mae']}), model likely not trained"

    # Check that metrics are not suspiciously perfect (hardcoded)
    assert perf['rmse'] > 0.1, "rmse suspiciously low, might be hardcoded"
    assert perf['mae'] > 0.1, "mae suspiciously low, might be hardcoded"


def test_sample_recommendations_structure():
    """Test that sample_recommendations has correct structure"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    recs = data['sample_recommendations']
    assert isinstance(recs, dict), "sample_recommendations must be a dictionary"

    # Check that user_id 1 exists (as required by instruction)
    assert '1' in recs, "sample_recommendations must contain user_id '1'"

    # Check that recommendations for user 1 is a list
    user_1_recs = recs['1']
    assert isinstance(user_1_recs, list), "Recommendations for user 1 must be a list"

    # Check that there are exactly 5 recommendations (top 5 as specified)
    assert len(user_1_recs) == 5, f"Expected 5 recommendations for user 1, got {len(user_1_recs)}"

    # Check that all recommendations are integers (item IDs)
    for item_id in user_1_recs:
        assert isinstance(item_id, int), f"Item ID {item_id} must be an integer"
        assert item_id > 0, f"Item ID {item_id} must be positive"


def test_recommendations_are_not_hardcoded():
    """Test that recommendations are not trivially hardcoded (e.g., [1,2,3,4,5])"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    user_1_recs = data['sample_recommendations']['1']

    # Check that recommendations are not just sequential numbers starting from 1
    assert user_1_recs != [1, 2, 3, 4, 5], "Recommendations appear to be hardcoded as [1,2,3,4,5]"

    # Check that recommendations are unique (no duplicates)
    assert len(user_1_recs) == len(set(user_1_recs)), "Recommendations contain duplicates"


def test_recommendations_are_valid_item_ids():
    """Test that recommended items are valid item IDs from the dataset"""
    # Load the dataset to get valid item IDs
    valid_items = set()
    with open('/app/ml-100k/u.data', 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            item_id = int(parts[1])
            valid_items.add(item_id)

    # Check recommendations
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    user_1_recs = data['sample_recommendations']['1']

    for item_id in user_1_recs:
        assert item_id in valid_items, f"Recommended item {item_id} is not in the dataset"


def test_recommendations_exclude_rated_items():
    """Test that recommendations don't include items user 1 has already rated"""
    # Get items rated by user 1
    user_1_rated = set()
    with open('/app/ml-100k/u.data', 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            user_id = int(parts[0])
            item_id = int(parts[1])
            if user_id == 1:
                user_1_rated.add(item_id)

    # Check recommendations
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    user_1_recs = data['sample_recommendations']['1']

    for item_id in user_1_recs:
        assert item_id not in user_1_rated, f"Recommended item {item_id} was already rated by user 1"


def test_model_file_not_empty():
    """Test that model.pth is not empty"""
    file_size = os.path.getsize('/app/model.pth')
    assert file_size > 1000, f"model.pth is too small ({file_size} bytes), likely not a valid model"


def test_json_output_format():
    """Test that JSON output is properly formatted (not minified or malformed)"""
    with open('/app/results.json', 'r') as f:
        content = f.read()

    # Check that it's not a single line (should be indented)
    lines = content.strip().split('\n')
    assert len(lines) > 5, "JSON output appears to be minified or malformed"

    # Verify it can be parsed
    data = json.loads(content)
    assert data is not None


def test_metrics_relationship():
    """Test that RMSE >= MAE (mathematical property)"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    perf = data['model_performance']
    # RMSE should always be >= MAE due to squaring
    assert perf['rmse'] >= perf['mae'], f"RMSE ({perf['rmse']}) should be >= MAE ({perf['mae']})"
