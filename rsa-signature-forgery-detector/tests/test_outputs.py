import os
import json


def test_results_file_exists():
    """Test that the results.json file exists."""
    assert os.path.exists('/app/results.json'), "results.json file not found at /app/results.json"


def test_results_file_not_empty():
    """Test that the results.json file is not empty."""
    assert os.path.getsize('/app/results.json') > 0, "results.json file is empty"


def test_results_valid_json():
    """Test that the results.json file contains valid JSON."""
    with open('/app/results.json', 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            assert False, f"results.json contains invalid JSON: {e}"


def test_results_has_required_structure():
    """Test that the results.json has the required top-level structure."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert 'results' in data, "Missing 'results' key in output"
    assert isinstance(data['results'], list), "'results' should be a list"


def test_results_count_matches_input():
    """Test that the number of results matches the number of input signatures."""
    with open('/app/signatures.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/results.json', 'r') as f:
        output_data = json.load(f)

    input_count = len(input_data['signatures'])
    output_count = len(output_data['results'])

    assert output_count == input_count, \
        f"Expected {input_count} results but got {output_count}"


def test_each_result_has_required_fields():
    """Test that each result has all required fields."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    required_fields = ['id', 'is_forged', 'confidence', 'vulnerabilities_detected', 'details']

    for i, result in enumerate(data['results']):
        for field in required_fields:
            assert field in result, \
                f"Result {i} (id: {result.get('id', 'unknown')}) missing required field '{field}'"


def test_result_ids_match_input():
    """Test that result IDs match the input signature IDs."""
    with open('/app/signatures.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/results.json', 'r') as f:
        output_data = json.load(f)

    input_ids = {sig['id'] for sig in input_data['signatures']}
    output_ids = {result['id'] for result in output_data['results']}

    assert input_ids == output_ids, \
        f"Result IDs don't match input IDs. Expected: {input_ids}, Got: {output_ids}"


def test_is_forged_is_boolean():
    """Test that is_forged field is a boolean."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    for result in data['results']:
        assert isinstance(result['is_forged'], bool), \
            f"Result {result['id']}: 'is_forged' should be boolean, got {type(result['is_forged'])}"


def test_confidence_is_valid_number():
    """Test that confidence scores are valid numbers between 0.0 and 1.0."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    for result in data['results']:
        confidence = result['confidence']
        assert isinstance(confidence, (int, float)), \
            f"Result {result['id']}: confidence should be a number, got {type(confidence)}"
        assert 0.0 <= confidence <= 1.0, \
            f"Result {result['id']}: confidence {confidence} is outside valid range [0.0, 1.0]"


def test_vulnerabilities_detected_is_list():
    """Test that vulnerabilities_detected is a list."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    for result in data['results']:
        assert isinstance(result['vulnerabilities_detected'], list), \
            f"Result {result['id']}: 'vulnerabilities_detected' should be a list"


def test_details_is_string():
    """Test that details field is a string."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    for result in data['results']:
        assert isinstance(result['details'], str), \
            f"Result {result['id']}: 'details' should be a string, got {type(result['details'])}"


def test_forged_signatures_have_vulnerabilities():
    """Test that signatures marked as forged have at least one vulnerability detected."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    for result in data['results']:
        if result['is_forged']:
            assert len(result['vulnerabilities_detected']) > 0, \
                f"Result {result['id']}: marked as forged but has no vulnerabilities detected"


def test_forged_signatures_have_positive_confidence():
    """Test that signatures marked as forged have confidence > 0."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    for result in data['results']:
        if result['is_forged']:
            assert result['confidence'] > 0.0, \
                f"Result {result['id']}: marked as forged but confidence is {result['confidence']}"


def test_valid_signatures_have_zero_confidence():
    """Test that signatures marked as valid have confidence = 0."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    for result in data['results']:
        if not result['is_forged']:
            assert result['confidence'] == 0.0, \
                f"Result {result['id']}: marked as valid but confidence is {result['confidence']} (expected 0.0)"


def test_valid_signatures_have_empty_vulnerabilities():
    """Test that signatures marked as valid have empty vulnerability list."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    for result in data['results']:
        if not result['is_forged']:
            assert len(result['vulnerabilities_detected']) == 0, \
                f"Result {result['id']}: marked as valid but has vulnerabilities: {result['vulnerabilities_detected']}"


def test_not_all_signatures_same_status():
    """Test that not all signatures have the same is_forged status (avoid hardcoded responses)."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    if len(data['results']) > 1:
        statuses = [result['is_forged'] for result in data['results']]
        # At least one should be different from the first
        assert not all(s == statuses[0] for s in statuses), \
            "All signatures have the same is_forged status - possible hardcoded response"


def test_vulnerability_types_are_strings():
    """Test that vulnerability types are strings."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    for result in data['results']:
        for vuln in result['vulnerabilities_detected']:
            assert isinstance(vuln, str), \
                f"Result {result['id']}: vulnerability should be string, got {type(vuln)}"
            assert len(vuln) > 0, \
                f"Result {result['id']}: vulnerability string is empty"


def test_details_not_empty_for_forged():
    """Test that forged signatures have non-empty details."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    for result in data['results']:
        if result['is_forged']:
            assert len(result['details'].strip()) > 0, \
                f"Result {result['id']}: marked as forged but details are empty"


def test_recognized_vulnerability_types():
    """Test that vulnerability types are from expected categories."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    # Common vulnerability types based on instruction.md requirements
    expected_categories = [
        'invalid_padding', 'mathematical_inconsistency', 'malformed_base64',
        'invalid_hash_algorithm', 'processing_error', 'bleichenbacher'
    ]

    for result in data['results']:
        for vuln in result['vulnerabilities_detected']:
            # Check if vulnerability contains any expected keyword
            vuln_lower = vuln.lower()
            has_recognized_keyword = any(
                keyword in vuln_lower for keyword in
                ['padding', 'mathematical', 'math', 'base64', 'hash', 'algorithm',
                 'error', 'bleichenbacher', 'inconsistency', 'invalid', 'malformed']
            )
            assert has_recognized_keyword, \
                f"Result {result['id']}: unrecognized vulnerability type '{vuln}'"


def test_no_duplicate_vulnerability_types():
    """Test that there are no duplicate vulnerability types in a single result."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    for result in data['results']:
        vulns = result['vulnerabilities_detected']
        unique_vulns = set(vulns)
        assert len(vulns) == len(unique_vulns), \
            f"Result {result['id']}: has duplicate vulnerabilities: {vulns}"


def test_confidence_correlates_with_vulnerability_count():
    """Test that higher confidence generally correlates with more vulnerabilities."""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    forged_results = [r for r in data['results'] if r['is_forged']]

    if len(forged_results) > 1:
        # Check that results with more vulnerabilities tend to have higher confidence
        for result in forged_results:
            vuln_count = len(result['vulnerabilities_detected'])
            confidence = result['confidence']

            # At minimum, confidence should increase with vulnerability count
            # Allow some flexibility but ensure it's not completely random
            if vuln_count >= 2:
                assert confidence >= 0.7, \
                    f"Result {result['id']}: has {vuln_count} vulnerabilities but low confidence {confidence}"
