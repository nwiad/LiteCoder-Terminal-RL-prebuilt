import os
import json
import re

def test_report_file_exists():
    """Test that the report.json file exists."""
    assert os.path.exists("/app/report.json"), "Report file /app/report.json does not exist"

def test_report_is_valid_json():
    """Test that report.json contains valid JSON."""
    with open("/app/report.json", "r") as f:
        content = f.read()
        assert len(content) > 0, "Report file is empty"
        report = json.loads(content)
        assert isinstance(report, dict), "Report must be a JSON object"

def test_report_has_required_top_level_fields():
    """Test that report has all required top-level fields."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    assert "reproducible" in report, "Report missing 'reproducible' field"
    assert "builds" in report, "Report missing 'builds' field"
    assert "comparison" in report, "Report missing 'comparison' field"

    assert isinstance(report["reproducible"], bool), "'reproducible' must be a boolean"
    assert isinstance(report["builds"], list), "'builds' must be a list"
    assert isinstance(report["comparison"], dict), "'comparison' must be an object"

def test_builds_array_has_correct_length():
    """Test that builds array contains entries for all build configs."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    # Should have 2 builds based on config.json
    assert len(report["builds"]) == 2, f"Expected 2 builds, got {len(report['builds'])}"

def test_each_build_has_required_fields():
    """Test that each build entry has all required fields."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    required_fields = ["name", "binary_path", "sha256", "size_bytes", "build_success"]

    for i, build in enumerate(report["builds"]):
        for field in required_fields:
            assert field in build, f"Build {i} missing required field '{field}'"

def test_build_names_match_config():
    """Test that build names match the configuration."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    build_names = [build["name"] for build in report["builds"]]
    assert "env1" in build_names, "Build 'env1' not found in report"
    assert "env2" in build_names, "Build 'env2' not found in report"

def test_build_success_is_boolean():
    """Test that build_success is a boolean for all builds."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    for build in report["builds"]:
        assert isinstance(build["build_success"], bool), \
            f"Build '{build['name']}' has non-boolean build_success"

def test_sha256_format_for_successful_builds():
    """Test that SHA256 hashes are valid 64-character hex strings for successful builds."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    sha256_pattern = re.compile(r'^[a-f0-9]{64}$')

    for build in report["builds"]:
        if build["build_success"]:
            assert build["sha256"] is not None, \
                f"Successful build '{build['name']}' has null sha256"
            assert isinstance(build["sha256"], str), \
                f"Build '{build['name']}' sha256 must be a string"
            assert sha256_pattern.match(build["sha256"]), \
                f"Build '{build['name']}' has invalid SHA256 format: {build['sha256']}"

def test_size_bytes_for_successful_builds():
    """Test that size_bytes is a positive integer for successful builds."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    for build in report["builds"]:
        if build["build_success"]:
            assert build["size_bytes"] is not None, \
                f"Successful build '{build['name']}' has null size_bytes"
            assert isinstance(build["size_bytes"], int), \
                f"Build '{build['name']}' size_bytes must be an integer"
            assert build["size_bytes"] > 0, \
                f"Build '{build['name']}' size_bytes must be positive"

def test_binary_path_format():
    """Test that binary paths follow the expected format."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    for build in report["builds"]:
        expected_path = f"/app/builds/{build['name']}/libsample.so"
        assert build["binary_path"] == expected_path, \
            f"Build '{build['name']}' has incorrect binary_path: {build['binary_path']}"

def test_build_directories_exist():
    """Test that build directories were actually created."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    for build in report["builds"]:
        if build["build_success"]:
            build_dir = f"/app/builds/{build['name']}"
            assert os.path.exists(build_dir), \
                f"Build directory {build_dir} does not exist"

def test_binary_files_exist_for_successful_builds():
    """Test that binary files actually exist for successful builds."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    for build in report["builds"]:
        if build["build_success"]:
            assert os.path.exists(build["binary_path"]), \
                f"Binary file {build['binary_path']} does not exist"
            assert os.path.isfile(build["binary_path"]), \
                f"Binary path {build['binary_path']} is not a file"

def test_binary_files_are_not_empty():
    """Test that binary files are not empty (prevent dummy files)."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    for build in report["builds"]:
        if build["build_success"]:
            file_size = os.path.getsize(build["binary_path"])
            assert file_size > 0, \
                f"Binary file {build['binary_path']} is empty"
            # Shared libraries should be at least a few KB
            assert file_size >= 100, \
                f"Binary file {build['binary_path']} is suspiciously small ({file_size} bytes)"

def test_reported_size_matches_actual_file_size():
    """Test that reported size_bytes matches actual file size."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    for build in report["builds"]:
        if build["build_success"]:
            actual_size = os.path.getsize(build["binary_path"])
            reported_size = build["size_bytes"]
            assert actual_size == reported_size, \
                f"Build '{build['name']}' reported size {reported_size} doesn't match actual size {actual_size}"

def test_comparison_has_required_fields():
    """Test that comparison object has all required fields."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    comparison = report["comparison"]
    assert "all_hashes_match" in comparison, "Comparison missing 'all_hashes_match' field"
    assert "all_sizes_match" in comparison, "Comparison missing 'all_sizes_match' field"
    assert "differences" in comparison, "Comparison missing 'differences' field"

    assert isinstance(comparison["all_hashes_match"], bool), "'all_hashes_match' must be boolean"
    assert isinstance(comparison["all_sizes_match"], bool), "'all_sizes_match' must be boolean"
    assert isinstance(comparison["differences"], list), "'differences' must be a list"

def test_reproducibility_logic_when_hashes_match():
    """Test that reproducible=true when all builds succeed and hashes match."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    all_builds_succeeded = all(build["build_success"] for build in report["builds"])

    if all_builds_succeeded:
        hashes = [build["sha256"] for build in report["builds"]]
        all_hashes_same = len(set(hashes)) == 1

        if all_hashes_same:
            assert report["reproducible"] == True, \
                "reproducible should be true when all builds succeed and hashes match"
            assert report["comparison"]["all_hashes_match"] == True, \
                "all_hashes_match should be true when hashes match"
            assert len(report["comparison"]["differences"]) == 0, \
                "differences should be empty when hashes match"

def test_reproducibility_logic_when_hashes_differ():
    """Test that reproducible=false when hashes don't match."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    all_builds_succeeded = all(build["build_success"] for build in report["builds"])

    if all_builds_succeeded:
        hashes = [build["sha256"] for build in report["builds"]]
        all_hashes_same = len(set(hashes)) == 1

        if not all_hashes_same:
            assert report["reproducible"] == False, \
                "reproducible should be false when hashes don't match"
            assert report["comparison"]["all_hashes_match"] == False, \
                "all_hashes_match should be false when hashes don't match"
            assert len(report["comparison"]["differences"]) > 0, \
                "differences should list mismatched builds"

def test_reproducibility_false_when_build_fails():
    """Test that reproducible=false if any build fails."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    any_build_failed = any(not build["build_success"] for build in report["builds"])

    if any_build_failed:
        assert report["reproducible"] == False, \
            "reproducible should be false when any build fails"

def test_all_sizes_match_logic():
    """Test that all_sizes_match is accurate."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    successful_builds = [b for b in report["builds"] if b["build_success"]]

    if len(successful_builds) >= 2:
        sizes = [build["size_bytes"] for build in successful_builds]
        all_sizes_same = len(set(sizes)) == 1

        assert report["comparison"]["all_sizes_match"] == all_sizes_same, \
            f"all_sizes_match should be {all_sizes_same} based on actual sizes"

def test_sha256_hashes_are_not_dummy_values():
    """Test that SHA256 hashes are not obviously fake/hardcoded values."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    # Common dummy hashes to reject
    dummy_hashes = [
        "0" * 64,
        "1" * 64,
        "a" * 64,
        "f" * 64,
        "abc123" + "0" * 58,
        "deadbeef" + "0" * 56
    ]

    for build in report["builds"]:
        if build["build_success"] and build["sha256"]:
            assert build["sha256"] not in dummy_hashes, \
                f"Build '{build['name']}' has suspicious dummy hash: {build['sha256']}"

def test_differences_array_content():
    """Test that differences array contains correct build names when hashes don't match."""
    with open("/app/report.json", "r") as f:
        report = json.load(f)

    if not report["comparison"]["all_hashes_match"]:
        # differences should contain names of builds that differ
        assert isinstance(report["comparison"]["differences"], list), \
            "differences must be a list"

        # All entries in differences should be valid build names
        build_names = [build["name"] for build in report["builds"]]
        for diff_name in report["comparison"]["differences"]:
            assert diff_name in build_names, \
                f"differences contains invalid build name: {diff_name}"
