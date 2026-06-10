import os
import subprocess
from bs4 import BeautifulSoup
import re


def test_run_analysis_script_exists():
    """Test that run_analysis.sh exists at the correct location."""
    assert os.path.exists('/app/run_analysis.sh'), "run_analysis.sh not found at /app/run_analysis.sh"


def test_run_analysis_script_executable():
    """Test that run_analysis.sh is executable."""
    assert os.access('/app/run_analysis.sh', os.X_OK), "run_analysis.sh is not executable"


def test_report_html_exists():
    """Test that report.html exists at the correct location."""
    assert os.path.exists('/app/report.html'), "report.html not found at /app/report.html"


def test_report_html_not_empty():
    """Test that report.html is not empty."""
    file_size = os.path.getsize('/app/report.html')
    assert file_size > 1000, f"report.html is too small ({file_size} bytes), likely incomplete"


def test_report_html_valid_structure():
    """Test that report.html has valid HTML structure."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')

    # Check basic HTML structure
    assert soup.find('html') is not None, "Missing <html> tag"
    assert soup.find('head') is not None, "Missing <head> tag"
    assert soup.find('body') is not None, "Missing <body> tag"
    assert soup.find('title') is not None, "Missing <title> tag"


def test_report_contains_executive_summary():
    """Test that report contains an executive summary section."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for executive summary
    assert 'executive summary' in content.lower(), "Missing executive summary section"


def test_report_contains_data_quality_assessment():
    """Test that report contains data quality assessment."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')
    text = soup.get_text().lower()

    # Check for data quality metrics
    assert 'total records' in text or 'total rows' in text or 'row count' in text, "Missing total records information"
    assert 'total columns' in text or 'column count' in text, "Missing total columns information"
    assert 'missing' in text or 'null' in text, "Missing missing values analysis"


def test_report_contains_price_analysis():
    """Test that report contains price distribution analysis."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for price-related analysis
    assert 'price' in text, "Missing price analysis"
    assert any(borough in text for borough in ['manhattan', 'brooklyn', 'queens', 'bronx', 'staten island']), \
        "Missing borough analysis"


def test_report_contains_model_metrics():
    """Test that report contains model performance metrics."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for model metrics
    assert 'r²' in text or 'r2' in text or 'r-squared' in text, "Missing R² metric"
    assert 'rmse' in text or 'root mean squared error' in text, "Missing RMSE metric"
    assert 'mae' in text or 'mean absolute error' in text, "Missing MAE metric"


def test_report_contains_feature_importance():
    """Test that report contains feature importance analysis."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for feature importance
    assert 'feature importance' in text or 'important feature' in text, "Missing feature importance section"


def test_report_contains_clustering_analysis():
    """Test that report contains neighborhood clustering analysis."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for clustering
    assert 'cluster' in text or 'segment' in text or 'group' in text, "Missing clustering analysis"
    assert 'neighborhood' in text or 'neighbourhood' in text, "Missing neighborhood analysis"


def test_report_contains_demand_forecasting():
    """Test that report contains demand forecasting section."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for demand analysis
    assert 'demand' in text or 'forecast' in text or 'availability' in text, "Missing demand forecasting section"


def test_report_contains_recommendations():
    """Test that report contains investment recommendations."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for recommendations
    assert 'recommendation' in text or 'invest' in text or 'strategy' in text, "Missing investment recommendations"


def test_report_has_visualizations():
    """Test that report contains embedded visualizations."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for base64 encoded images
    assert 'data:image/png;base64,' in content, "Missing embedded visualizations"

    # Count number of images
    image_count = content.count('data:image/png;base64,')
    assert image_count >= 2, f"Expected at least 2 visualizations, found {image_count}"


def test_report_has_tables():
    """Test that report contains data tables."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')

    # Check for tables
    tables = soup.find_all('table')
    assert len(tables) >= 3, f"Expected at least 3 tables in report, found {len(tables)}"


def test_model_metrics_are_reasonable():
    """Test that model metrics have reasonable values."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract R² value
    r2_match = re.search(r'r[²2].*?(\d+\.\d+)', content.lower())
    if r2_match:
        r2_value = float(r2_match.group(1))
        assert 0 <= r2_value <= 1, f"R² value {r2_value} is out of valid range [0, 1]"

    # Extract RMSE value (should be positive)
    rmse_match = re.search(r'rmse.*?\$?(\d+\.?\d*)', content.lower())
    if rmse_match:
        rmse_value = float(rmse_match.group(1))
        assert rmse_value > 0, f"RMSE value {rmse_value} should be positive"

    # Extract MAE value (should be positive)
    mae_match = re.search(r'mae.*?\$?(\d+\.?\d*)', content.lower())
    if mae_match:
        mae_value = float(mae_match.group(1))
        assert mae_value > 0, f"MAE value {mae_value} should be positive"


def test_report_not_hardcoded():
    """Test that report contains actual data, not just placeholders."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check that report doesn't contain obvious placeholders
    assert 'todo' not in text, "Report contains TODO placeholders"
    assert 'placeholder' not in text, "Report contains placeholder text"
    assert 'xxx' not in text, "Report contains XXX placeholders"

    # Check for actual numeric values in tables
    soup = BeautifulSoup(content, 'html.parser')
    tables = soup.find_all('table')

    has_numeric_data = False
    for table in tables:
        table_text = table.get_text()
        # Look for numbers with decimals or dollar signs
        if re.search(r'\d+\.\d+|\$\d+', table_text):
            has_numeric_data = True
            break

    assert has_numeric_data, "Report tables don't contain actual numeric data"


def test_clustering_has_multiple_segments():
    """Test that clustering analysis identifies multiple segments."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for multiple segments/clusters
    segment_count = text.count('segment') + text.count('cluster')
    assert segment_count >= 3, f"Expected multiple segments/clusters, found only {segment_count} mentions"


def test_report_contains_borough_names():
    """Test that report mentions actual NYC boroughs."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for at least 3 NYC boroughs
    boroughs = ['manhattan', 'brooklyn', 'queens', 'bronx', 'staten island']
    found_boroughs = [b for b in boroughs if b in text]

    assert len(found_boroughs) >= 3, f"Expected at least 3 NYC boroughs, found only {found_boroughs}"


def test_report_contains_room_types():
    """Test that report analyzes different room types."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for room type analysis
    assert 'room type' in text or 'room_type' in text, "Missing room type analysis"

    # Check for specific room types
    room_types_found = sum([
        'entire home' in text or 'entire apt' in text,
        'private room' in text,
        'shared room' in text
    ])

    assert room_types_found >= 2, "Report should analyze multiple room types"


def test_report_has_styling():
    """Test that report has CSS styling."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for CSS
    assert '<style>' in content or 'style=' in content, "Report missing CSS styling"


def test_data_cleaning_documented():
    """Test that data cleaning steps are documented."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for data cleaning documentation
    assert 'clean' in text or 'outlier' in text or 'missing' in text, "Missing data cleaning documentation"


def test_report_contains_availability_analysis():
    """Test that report analyzes availability patterns."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for availability analysis
    assert 'availability' in text, "Missing availability analysis"


def test_report_contains_review_analysis():
    """Test that report analyzes review data."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check for review analysis
    assert 'review' in text, "Missing review analysis"


def test_report_not_just_empty_template():
    """Test that report is not just an empty template with no analysis."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')

    # Get all text content
    text = soup.get_text()

    # Remove whitespace and count actual content
    text_content = ''.join(text.split())

    # Report should have substantial content (at least 3000 characters of actual text)
    assert len(text_content) > 3000, f"Report content too short ({len(text_content)} chars), likely just a template"


def test_report_has_numeric_metrics():
    """Test that report contains actual numeric metrics, not just text."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Count numeric values (integers and decimals)
    numeric_matches = re.findall(r'\b\d+\.?\d*\b', content)

    # Should have many numeric values throughout the report
    assert len(numeric_matches) > 50, f"Expected many numeric values in report, found only {len(numeric_matches)}"


def test_investment_recommendations_specific():
    """Test that investment recommendations are specific, not generic."""
    with open('/app/report.html', 'r', encoding='utf-8') as f:
        content = f.read()

    text = content.lower()

    # Check that recommendations section exists
    assert 'recommendation' in text, "Missing recommendations section"

    # Check for specific elements (borough names, prices, etc.)
    has_specifics = any([
        re.search(r'\$\d+', content),  # Dollar amounts
        any(b in text for b in ['manhattan', 'brooklyn', 'queens', 'bronx']),  # Borough names
        re.search(r'\d+%', content),  # Percentages
    ])

    assert has_specifics, "Recommendations should contain specific data (prices, boroughs, percentages)"
