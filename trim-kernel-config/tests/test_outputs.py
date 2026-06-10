import os
import json
import re
import hashlib


def test_output_config_exists():
    """Test that output_config file exists."""
    assert os.path.exists('/app/output_config'), "Output config file /app/output_config does not exist"


def test_metadata_json_exists():
    """Test that metadata.json file exists."""
    assert os.path.exists('/app/metadata.json'), "Metadata file /app/metadata.json does not exist"


def test_output_config_not_empty():
    """Test that output_config is not empty."""
    assert os.path.getsize('/app/output_config') > 0, "Output config file is empty"


def test_output_config_valid_format():
    """Test that output_config has valid kernel config format."""
    with open('/app/output_config', 'r') as f:
        content = f.read()

    # Should not be just whitespace
    assert content.strip(), "Output config contains only whitespace"

    lines = content.strip().split('\n')

    # Check for at least some CONFIG entries
    config_lines = [line for line in lines if line.startswith('CONFIG_')]
    assert len(config_lines) > 0, "Output config has no CONFIG_ entries"

    # Validate format of CONFIG lines
    for line in config_lines:
        # Should match CONFIG_SYMBOL=value pattern
        assert re.match(r'^CONFIG_[A-Z0-9_]+=.+$', line), f"Invalid config line format: {line}"


def test_metadata_json_valid_structure():
    """Test that metadata.json has correct structure and types."""
    with open('/app/metadata.json', 'r') as f:
        metadata = json.load(f)

    # Check required fields exist
    required_fields = [
        'original_size_bytes',
        'trimmed_size_bytes',
        'original_symbol_count',
        'trimmed_symbol_count',
        'symbols_removed',
        'deterministic_hash'
    ]

    for field in required_fields:
        assert field in metadata, f"Missing required field: {field}"

    # Check types
    assert isinstance(metadata['original_size_bytes'], int), "original_size_bytes must be integer"
    assert isinstance(metadata['trimmed_size_bytes'], int), "trimmed_size_bytes must be integer"
    assert isinstance(metadata['original_symbol_count'], int), "original_symbol_count must be integer"
    assert isinstance(metadata['trimmed_symbol_count'], int), "trimmed_symbol_count must be integer"
    assert isinstance(metadata['symbols_removed'], int), "symbols_removed must be integer"
    assert isinstance(metadata['deterministic_hash'], str), "deterministic_hash must be string"

    # Check non-negative values
    assert metadata['original_size_bytes'] >= 0, "original_size_bytes must be non-negative"
    assert metadata['trimmed_size_bytes'] >= 0, "trimmed_size_bytes must be non-negative"
    assert metadata['original_symbol_count'] >= 0, "original_symbol_count must be non-negative"
    assert metadata['trimmed_symbol_count'] >= 0, "trimmed_symbol_count must be non-negative"
    assert metadata['symbols_removed'] >= 0, "symbols_removed must be non-negative"


def test_metadata_math_consistency():
    """Test that metadata calculations are consistent."""
    with open('/app/metadata.json', 'r') as f:
        metadata = json.load(f)

    # symbols_removed should equal original - trimmed
    expected_removed = metadata['original_symbol_count'] - metadata['trimmed_symbol_count']
    assert metadata['symbols_removed'] == expected_removed, \
        f"symbols_removed ({metadata['symbols_removed']}) != original - trimmed ({expected_removed})"


def test_metadata_hash_matches_output():
    """Test that deterministic_hash matches actual output_config hash."""
    with open('/app/metadata.json', 'r') as f:
        metadata = json.load(f)

    with open('/app/output_config', 'rb') as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    assert metadata['deterministic_hash'] == actual_hash, \
        f"Hash mismatch: metadata has {metadata['deterministic_hash']}, actual is {actual_hash}"


def test_metadata_hash_is_sha256():
    """Test that deterministic_hash is valid SHA256 format."""
    with open('/app/metadata.json', 'r') as f:
        metadata = json.load(f)

    hash_value = metadata['deterministic_hash']
    assert len(hash_value) == 64, f"SHA256 hash should be 64 characters, got {len(hash_value)}"
    assert re.match(r'^[a-f0-9]{64}$', hash_value), "Hash should be lowercase hex"


def test_trimming_actually_happened():
    """Test that the config was actually trimmed (not just copied)."""
    with open('/app/metadata.json', 'r') as f:
        metadata = json.load(f)

    # Should have removed at least some symbols
    assert metadata['symbols_removed'] > 0, "No symbols were removed - config was not trimmed"

    # Trimmed count should be less than original
    assert metadata['trimmed_symbol_count'] < metadata['original_symbol_count'], \
        "Trimmed symbol count should be less than original"


def test_output_preserves_essential_symbols():
    """Test that essential symbols (=y, =m) are preserved in output."""
    with open('/app/output_config', 'r') as f:
        output_content = f.read()

    # Parse output symbols
    output_symbols = {}
    for line in output_content.split('\n'):
        match = re.match(r'^(CONFIG_[A-Z0-9_]+)=(.+)$', line)
        if match:
            output_symbols[match.group(1)] = match.group(2)

    # Check that we have symbols with =y and =m values
    y_symbols = [s for s, v in output_symbols.items() if v == 'y']
    m_symbols = [s for s, v in output_symbols.items() if v == 'm']

    assert len(y_symbols) > 0, "Output should contain symbols set to 'y'"
    # m_symbols might be 0 depending on input, so we just check y_symbols


def test_output_is_deterministic():
    """Test that output appears to be deterministically sorted."""
    with open('/app/output_config', 'r') as f:
        lines = f.readlines()

    # Extract CONFIG lines
    config_lines = [line.strip() for line in lines if line.strip().startswith('CONFIG_')]

    # Extract symbol names
    symbols = []
    for line in config_lines:
        match = re.match(r'^(CONFIG_[A-Z0-9_]+)=', line)
        if match:
            symbols.append(match.group(1))

    # Check if sorted alphabetically
    assert symbols == sorted(symbols), "CONFIG symbols should be sorted alphabetically for determinism"


def test_no_disabled_symbols_in_output():
    """Test that output doesn't contain explicitly disabled symbols (=n)."""
    with open('/app/output_config', 'r') as f:
        content = f.read()

    # Check for =n patterns (these should be trimmed)
    for line in content.split('\n'):
        if line.startswith('CONFIG_'):
            assert not line.endswith('=n'), f"Output should not contain disabled symbols: {line}"


def test_no_comment_only_disabled_symbols():
    """Test that output doesn't contain comment-style disabled symbols."""
    with open('/app/output_config', 'r') as f:
        content = f.read()

    # Check for "# CONFIG_XXX is not set" patterns (these should be trimmed)
    for line in content.split('\n'):
        assert not re.match(r'^# CONFIG_[A-Z0-9_]+ is not set$', line), \
            f"Output should not contain comment-style disabled symbols: {line}"


def test_output_symbol_count_matches_metadata():
    """Test that actual symbol count in output matches metadata."""
    with open('/app/output_config', 'r') as f:
        content = f.read()

    # Count CONFIG symbols in output
    actual_count = 0
    for line in content.split('\n'):
        if re.match(r'^CONFIG_[A-Z0-9_]+=.+$', line):
            actual_count += 1

    with open('/app/metadata.json', 'r') as f:
        metadata = json.load(f)

    assert actual_count == metadata['trimmed_symbol_count'], \
        f"Actual symbol count ({actual_count}) doesn't match metadata ({metadata['trimmed_symbol_count']})"


def test_output_file_size_matches_metadata():
    """Test that actual output file size matches metadata."""
    actual_size = os.path.getsize('/app/output_config')

    with open('/app/metadata.json', 'r') as f:
        metadata = json.load(f)

    assert actual_size == metadata['trimmed_size_bytes'], \
        f"Actual file size ({actual_size}) doesn't match metadata ({metadata['trimmed_size_bytes']})"


def test_input_file_size_matches_metadata():
    """Test that input file size matches metadata."""
    actual_size = os.path.getsize('/app/input_config')

    with open('/app/metadata.json', 'r') as f:
        metadata = json.load(f)

    assert actual_size == metadata['original_size_bytes'], \
        f"Input file size ({actual_size}) doesn't match metadata ({metadata['original_size_bytes']})"


def test_no_hardcoded_dummy_output():
    """Test that output is not a hardcoded dummy file."""
    with open('/app/output_config', 'r') as f:
        content = f.read()

    # Check it's not suspiciously small
    assert len(content) > 50, "Output file is suspiciously small"

    # Check it's not just a placeholder
    assert 'TODO' not in content.upper(), "Output contains TODO placeholder"
    assert 'DUMMY' not in content.upper(), "Output contains DUMMY placeholder"
    assert 'PLACEHOLDER' not in content.upper(), "Output contains PLACEHOLDER"


def test_output_contains_valid_config_values():
    """Test that output contains valid kernel config values."""
    with open('/app/output_config', 'r') as f:
        content = f.read()

    valid_values_found = False

    for line in content.split('\n'):
        match = re.match(r'^CONFIG_[A-Z0-9_]+=(.+)$', line)
        if match:
            value = match.group(1)
            # Check for valid value types: y, m, n, quoted strings, or numbers
            if value in ['y', 'm', 'n'] or \
               (value.startswith('"') and value.endswith('"')) or \
               value.isdigit():
                valid_values_found = True
                break

    assert valid_values_found, "Output should contain at least one valid config value"


def test_trimmed_size_reasonable():
    """Test that trimmed size is reasonable (not 0, not same as original)."""
    with open('/app/metadata.json', 'r') as f:
        metadata = json.load(f)

    assert metadata['trimmed_size_bytes'] > 0, "Trimmed size should be greater than 0"
    assert metadata['trimmed_size_bytes'] < metadata['original_size_bytes'], \
        "Trimmed size should be less than original size"


def test_original_symbol_count_reasonable():
    """Test that original symbol count is reasonable based on input."""
    with open('/app/input_config', 'r') as f:
        content = f.read()

    # Count actual CONFIG symbols in input
    actual_count = 0
    for line in content.split('\n'):
        if re.match(r'^CONFIG_[A-Z0-9_]+=.+$', line):
            actual_count += 1

    with open('/app/metadata.json', 'r') as f:
        metadata = json.load(f)

    assert metadata['original_symbol_count'] == actual_count, \
        f"Original symbol count in metadata ({metadata['original_symbol_count']}) doesn't match actual ({actual_count})"
