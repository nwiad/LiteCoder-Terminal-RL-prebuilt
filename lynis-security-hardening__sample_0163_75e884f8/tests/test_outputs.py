import os
import re

def test_lynis_initial_report_exists():
    """Verify initial Lynis audit report exists and is not empty"""
    assert os.path.exists("/app/lynis_initial_report.txt"), "Initial Lynis report not found"

    with open("/app/lynis_initial_report.txt", "r") as f:
        content = f.read()

    assert len(content) > 100, "Initial report is too short or empty"
    # Verify it's actually a Lynis report
    assert "lynis" in content.lower() or "audit" in content.lower(), "File doesn't appear to be a Lynis report"


def test_recommendations_file_structure():
    """Verify recommendations.txt has proper structure with 5 recommendations"""
    assert os.path.exists("/app/recommendations.txt"), "Recommendations file not found"

    with open("/app/recommendations.txt", "r") as f:
        content = f.read()

    assert len(content) > 200, "Recommendations file is too short"

    # Check for 5 recommendations
    recommendation_count = len(re.findall(r"Recommendation #:\s*\d+", content))
    assert recommendation_count == 5, f"Expected 5 recommendations, found {recommendation_count}"

    # Verify each recommendation has required fields
    for i in range(1, 6):
        assert f"Recommendation #: {i}" in content, f"Missing Recommendation #{i}"

    # Check for required fields in the file
    assert "Test ID:" in content, "Missing Test ID field"
    assert "Category:" in content, "Missing Category field"
    assert "Description:" in content, "Missing Description field"
    assert "Suggested Action:" in content, "Missing Suggested Action field"

    # Verify test IDs are present (should have format like AUTH-9262, FILE-6310, etc.)
    test_ids = re.findall(r"Test ID:\s*([A-Z]+-\d+)", content)
    assert len(test_ids) >= 5, f"Expected at least 5 test IDs, found {len(test_ids)}"


def test_backups_directory_exists():
    """Verify backup directory exists and contains backup files"""
    assert os.path.exists("/app/backups"), "Backups directory not found"
    assert os.path.isdir("/app/backups"), "Backups path is not a directory"

    # Check that at least one backup file exists
    backup_files = os.listdir("/app/backups")
    assert len(backup_files) > 0, "No backup files found in /app/backups/"

    # Verify backup files have .backup extension
    backup_files_with_extension = [f for f in backup_files if f.endswith(".backup")]
    assert len(backup_files_with_extension) > 0, "No files with .backup extension found"


def test_lynis_final_report_exists():
    """Verify final Lynis audit report exists and is not empty"""
    assert os.path.exists("/app/lynis_final_report.txt"), "Final Lynis report not found"

    with open("/app/lynis_final_report.txt", "r") as f:
        content = f.read()

    assert len(content) > 100, "Final report is too short or empty"
    # Verify it's actually a Lynis report
    assert "lynis" in content.lower() or "audit" in content.lower(), "File doesn't appear to be a Lynis report"


def test_reports_are_different():
    """Verify initial and final reports are not identical (changes were made)"""
    with open("/app/lynis_initial_report.txt", "r") as f:
        initial_content = f.read()

    with open("/app/lynis_final_report.txt", "r") as f:
        final_content = f.read()

    # Reports should not be identical (lazy agent check)
    assert initial_content != final_content, "Initial and final reports are identical - no changes were made"


def test_improvements_summary_structure():
    """Verify improvements summary contains all required sections"""
    assert os.path.exists("/app/improvements_summary.txt"), "Improvements summary not found"

    with open("/app/improvements_summary.txt", "r") as f:
        content = f.read()

    assert len(content) > 200, "Improvements summary is too short"

    # Check for required sections
    required_sections = [
        "Initial Security",
        "Final Security",
        "Implemented Recommendations",
        "Security Score",
        "Warnings"
    ]

    for section in required_sections:
        assert section in content, f"Missing required section: {section}"

    # Verify all 5 test IDs are mentioned
    test_id_pattern = r"[A-Z]+-\d+"
    test_ids = re.findall(test_id_pattern, content)
    assert len(test_ids) >= 5, f"Expected at least 5 test IDs in summary, found {len(test_ids)}"


def test_improvements_summary_has_metrics():
    """Verify improvements summary contains actual metrics (not just N/A)"""
    with open("/app/improvements_summary.txt", "r") as f:
        content = f.read()

    # Check that at least some metrics are present (not all N/A)
    # This prevents lazy agents from just outputting placeholder text
    lines_with_numbers = [line for line in content.split('\n') if re.search(r'\d+', line)]
    assert len(lines_with_numbers) >= 3, "Summary lacks sufficient numeric metrics"


def test_all_required_files_exist():
    """Verify all 5 required output files/directories exist"""
    required_paths = [
        "/app/lynis_initial_report.txt",
        "/app/recommendations.txt",
        "/app/backups",
        "/app/lynis_final_report.txt",
        "/app/improvements_summary.txt"
    ]

    for path in required_paths:
        assert os.path.exists(path), f"Required path not found: {path}"


def test_recommendations_match_summary():
    """Verify test IDs in recommendations.txt appear in improvements_summary.txt"""
    with open("/app/recommendations.txt", "r") as f:
        recommendations_content = f.read()

    with open("/app/improvements_summary.txt", "r") as f:
        summary_content = f.read()

    # Extract test IDs from recommendations
    rec_test_ids = set(re.findall(r"Test ID:\s*([A-Z]+-\d+)", recommendations_content))

    # Extract test IDs from summary
    summary_test_ids = set(re.findall(r"Test ID:\s*([A-Z]+-\d+)", summary_content))

    # All recommendation test IDs should appear in the summary
    assert len(rec_test_ids) >= 5, "Not enough test IDs in recommendations"
    assert rec_test_ids.issubset(summary_test_ids) or len(rec_test_ids.intersection(summary_test_ids)) >= 4, \
        "Test IDs in recommendations don't match those in summary"


def test_backup_files_not_empty():
    """Verify backup files contain actual content"""
    backup_files = os.listdir("/app/backups")
    backup_files_with_extension = [f for f in backup_files if f.endswith(".backup")]

    # Check at least one backup file has content
    has_content = False
    for backup_file in backup_files_with_extension:
        file_path = os.path.join("/app/backups", backup_file)
        if os.path.getsize(file_path) > 0:
            has_content = True
            break

    assert has_content, "All backup files are empty"
