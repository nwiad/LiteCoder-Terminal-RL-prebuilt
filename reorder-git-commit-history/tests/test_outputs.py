import os
import json
import subprocess
import re

def run_git_command(cmd, cwd='/app/repo'):
    """Execute a git command and return output."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def test_report_file_exists():
    """Test that the report file exists."""
    assert os.path.exists('/app/reorder_report.json'), "Report file /app/reorder_report.json does not exist"

def test_report_is_valid_json():
    """Test that the report is valid JSON."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)
    assert isinstance(data, dict), "Report must be a JSON object"

def test_report_has_required_keys():
    """Test that the report has all required top-level keys."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    assert 'original_order' in data, "Report missing 'original_order' key"
    assert 'new_order' in data, "Report missing 'new_order' key"
    assert 'verification' in data, "Report missing 'verification' key"

def test_original_order_structure():
    """Test that original_order has correct structure."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    original_order = data['original_order']
    assert isinstance(original_order, list), "original_order must be a list"
    assert len(original_order) > 0, "original_order cannot be empty"

    for commit in original_order:
        assert 'hash' in commit, "Each commit must have 'hash' field"
        assert 'message' in commit, "Each commit must have 'message' field"
        assert 'type' in commit, "Each commit must have 'type' field"
        assert commit['type'] in ['bugfix', 'feature'], f"Invalid type: {commit['type']}"

def test_new_order_structure():
    """Test that new_order has correct structure."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    new_order = data['new_order']
    assert isinstance(new_order, list), "new_order must be a list"
    assert len(new_order) > 0, "new_order cannot be empty"

    for commit in new_order:
        assert 'hash' in commit, "Each commit must have 'hash' field"
        assert 'message' in commit, "Each commit must have 'message' field"
        assert 'type' in commit, "Each commit must have 'type' field"
        assert commit['type'] in ['bugfix', 'feature'], f"Invalid type: {commit['type']}"

def test_commit_hashes_are_full_sha1():
    """Test that all commit hashes are full 40-character SHA-1 hashes."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    sha1_pattern = re.compile(r'^[0-9a-f]{40}$')

    for commit in data['original_order']:
        assert sha1_pattern.match(commit['hash']), f"Invalid SHA-1 hash: {commit['hash']}"

    for commit in data['new_order']:
        assert sha1_pattern.match(commit['hash']), f"Invalid SHA-1 hash: {commit['hash']}"

def test_same_number_of_commits():
    """Test that original_order and new_order have the same number of commits."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    assert len(data['original_order']) == len(data['new_order']), \
        "original_order and new_order must have the same number of commits"

def test_commit_classification():
    """Test that commits are correctly classified as bugfix or feature."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    bugfix_keywords = ['fix', 'bug', 'patch', 'repair', 'correct']
    feature_keywords = ['add', 'feature', 'implement', 'new']

    for commit in data['original_order']:
        message_lower = commit['message'].lower()

        # Check if classification matches message content
        has_bugfix_keyword = any(kw in message_lower for kw in bugfix_keywords)
        has_feature_keyword = any(kw in message_lower for kw in feature_keywords)

        if has_bugfix_keyword:
            assert commit['type'] == 'bugfix', \
                f"Commit '{commit['message']}' should be classified as bugfix"
        elif has_feature_keyword:
            assert commit['type'] == 'feature', \
                f"Commit '{commit['message']}' should be classified as feature"

def test_bugfixes_before_features():
    """Test that all bugfix commits come before all feature commits in new_order."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    new_order = data['new_order']

    # Find the last bugfix index and first feature index
    last_bugfix_idx = -1
    first_feature_idx = len(new_order)

    for idx, commit in enumerate(new_order):
        if commit['type'] == 'bugfix':
            last_bugfix_idx = idx
        elif commit['type'] == 'feature' and first_feature_idx == len(new_order):
            first_feature_idx = idx

    # If both types exist, bugfixes must come before features
    if last_bugfix_idx >= 0 and first_feature_idx < len(new_order):
        assert last_bugfix_idx < first_feature_idx, \
            "All bugfix commits must come before all feature commits"

def test_relative_order_preserved():
    """Test that relative order within each category is preserved."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    # Extract bugfixes and features from original order
    original_bugfixes = [c['message'] for c in data['original_order'] if c['type'] == 'bugfix']
    original_features = [c['message'] for c in data['original_order'] if c['type'] == 'feature']

    # Extract bugfixes and features from new order
    new_bugfixes = [c['message'] for c in data['new_order'] if c['type'] == 'bugfix']
    new_features = [c['message'] for c in data['new_order'] if c['type'] == 'feature']

    # Check that relative order is preserved
    assert original_bugfixes == new_bugfixes, \
        "Relative order of bugfix commits must be preserved"
    assert original_features == new_features, \
        "Relative order of feature commits must be preserved"

def test_verification_structure():
    """Test that verification object has correct structure."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    verification = data['verification']
    assert isinstance(verification, dict), "verification must be an object"

    assert 'final_state_matches' in verification, "verification missing 'final_state_matches'"
    assert 'backup_branch' in verification, "verification missing 'backup_branch'"
    assert 'reordered_branch' in verification, "verification missing 'reordered_branch'"

    assert isinstance(verification['final_state_matches'], bool), \
        "final_state_matches must be a boolean"
    assert verification['backup_branch'] == 'backup-original', \
        "backup_branch must be 'backup-original'"
    assert verification['reordered_branch'] == 'reordered-history', \
        "reordered_branch must be 'reordered-history'"

def test_final_state_matches():
    """Test that final_state_matches is true."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    assert data['verification']['final_state_matches'] is True, \
        "Final state must match original HEAD state"

def test_backup_branch_exists():
    """Test that backup-original branch exists and points to original HEAD."""
    stdout, stderr, code = run_git_command('git rev-parse backup-original')
    assert code == 0, "backup-original branch does not exist"
    assert len(stdout) == 40, "backup-original branch hash is invalid"

def test_reordered_branch_exists():
    """Test that reordered-history branch exists."""
    stdout, stderr, code = run_git_command('git rev-parse reordered-history')
    assert code == 0, "reordered-history branch does not exist"
    assert len(stdout) == 40, "reordered-history branch hash is invalid"

def test_branches_have_same_tree():
    """Test that backup-original and reordered-history have identical tree states."""
    # Get tree hash for backup-original
    backup_tree, _, code1 = run_git_command('git rev-parse backup-original^{tree}')
    assert code1 == 0, "Failed to get tree hash for backup-original"

    # Get tree hash for reordered-history
    reordered_tree, _, code2 = run_git_command('git rev-parse reordered-history^{tree}')
    assert code2 == 0, "Failed to get tree hash for reordered-history"

    assert backup_tree == reordered_tree, \
        "Tree states of backup-original and reordered-history must be identical"

def test_reordered_branch_commit_count():
    """Test that reordered-history has the correct number of commits."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    # Count commits in reordered-history (excluding initial commit)
    stdout, _, code = run_git_command('git rev-list --count reordered-history')
    assert code == 0, "Failed to count commits in reordered-history"

    commit_count = int(stdout)
    expected_count = len(data['new_order']) + 1  # +1 for initial commit

    assert commit_count == expected_count, \
        f"reordered-history should have {expected_count} commits, found {commit_count}"

def test_not_empty_or_dummy_data():
    """Test against lazy solutions with empty or hardcoded dummy data."""
    with open('/app/reorder_report.json', 'r') as f:
        content = f.read()
        data = json.loads(content)

    # Check file is not trivially small
    assert len(content) > 100, "Report file is suspiciously small"

    # Check that we have actual commits
    assert len(data['original_order']) >= 4, "Expected at least 4 commits in original_order"
    assert len(data['new_order']) >= 4, "Expected at least 4 commits in new_order"

    # Check that hashes are not dummy values
    for commit in data['original_order']:
        assert commit['hash'] != '0' * 40, "Commit hash appears to be dummy data"
        assert commit['hash'] != 'abc1234', "Commit hash appears to be dummy data"
        assert commit['message'] != '', "Commit message is empty"

    for commit in data['new_order']:
        assert commit['hash'] != '0' * 40, "Commit hash appears to be dummy data"
        assert commit['hash'] != 'ghi9012', "Commit hash appears to be dummy data"
        assert commit['message'] != '', "Commit message is empty"

def test_actual_reordering_occurred():
    """Test that actual reordering occurred (not just copying original order)."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    original_order = data['original_order']
    new_order = data['new_order']

    # Check if there are both bugfixes and features
    has_bugfix = any(c['type'] == 'bugfix' for c in original_order)
    has_feature = any(c['type'] == 'feature' for c in original_order)

    if has_bugfix and has_feature:
        # Extract message sequences
        original_messages = [c['message'] for c in original_order]
        new_messages = [c['message'] for c in new_order]

        # If there are interleaved commits, order should change
        original_types = [c['type'] for c in original_order]
        new_types = [c['type'] for c in new_order]

        # Check if original had interleaved types
        is_interleaved = False
        for i in range(len(original_types) - 1):
            if original_types[i] != original_types[i + 1]:
                is_interleaved = True
                break

        if is_interleaved:
            # Order should have changed
            assert original_messages != new_messages, \
                "Commits were interleaved but order did not change"

def test_commit_messages_preserved():
    """Test that all commit messages are preserved between original and new order."""
    with open('/app/reorder_report.json', 'r') as f:
        data = json.load(f)

    original_messages = sorted([c['message'] for c in data['original_order']])
    new_messages = sorted([c['message'] for c in data['new_order']])

    assert original_messages == new_messages, \
        "Commit messages must be preserved (same set of commits)"
