import os
import csv


def test_output_file_exists():
    """Test that the sales report CSV file exists."""
    assert os.path.exists('/app/sales_report.csv'), "Output file /app/sales_report.csv does not exist"


def test_output_file_not_empty():
    """Test that the output file is not empty."""
    assert os.path.getsize('/app/sales_report.csv') > 0, "Output file is empty"


def test_csv_structure():
    """Test that the CSV has correct structure with proper headers."""
    with open('/app/sales_report.csv', 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        assert headers is not None, "CSV has no headers"
        assert len(headers) == 2, f"Expected 2 columns, got {len(headers)}"
        assert 'metric_name' in headers, "Missing 'metric_name' column"
        assert 'metric_value' in headers, "Missing 'metric_value' column"


def test_correct_number_of_metrics():
    """Test that exactly 5 metrics are present."""
    with open('/app/sales_report.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        assert len(rows) == 5, f"Expected exactly 5 metrics, got {len(rows)}"


def test_metric_names_and_order():
    """Test that all required metrics are present in the correct order."""
    expected_metrics = [
        'total_revenue',
        'average_order_value',
        'total_transactions',
        'top_region_by_revenue',
        'top_category_by_revenue'
    ]

    with open('/app/sales_report.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        actual_metrics = [row['metric_name'] for row in rows]

        assert actual_metrics == expected_metrics, \
            f"Metrics not in correct order. Expected {expected_metrics}, got {actual_metrics}"


def test_total_transactions_is_10000():
    """Test that total_transactions equals exactly 10,000."""
    with open('/app/sales_report.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        transactions_row = next((row for row in rows if row['metric_name'] == 'total_transactions'), None)
        assert transactions_row is not None, "total_transactions metric not found"

        transactions = float(transactions_row['metric_value'])
        assert transactions == 10000, f"Expected 10,000 transactions, got {transactions}"


def test_numeric_metrics_are_valid():
    """Test that numeric metrics have valid values (not zero, not negative)."""
    with open('/app/sales_report.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        # Check total_revenue
        revenue_row = next((row for row in rows if row['metric_name'] == 'total_revenue'), None)
        assert revenue_row is not None, "total_revenue metric not found"
        total_revenue = float(revenue_row['metric_value'])
        assert total_revenue > 0, f"total_revenue should be positive, got {total_revenue}"
        assert total_revenue > 100000, f"total_revenue seems too low for 10,000 transactions: {total_revenue}"

        # Check average_order_value
        avg_row = next((row for row in rows if row['metric_name'] == 'average_order_value'), None)
        assert avg_row is not None, "average_order_value metric not found"
        avg_value = float(avg_row['metric_value'])
        assert avg_value > 0, f"average_order_value should be positive, got {avg_value}"
        assert avg_value >= 10, f"average_order_value seems too low (min unit_price is 10): {avg_value}"
        assert avg_value <= 5000, f"average_order_value seems too high (max is 10 * 500): {avg_value}"


def test_revenue_calculation_consistency():
    """Test that total_revenue = average_order_value × total_transactions (within rounding tolerance)."""
    with open('/app/sales_report.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        revenue_row = next((row for row in rows if row['metric_name'] == 'total_revenue'), None)
        avg_row = next((row for row in rows if row['metric_name'] == 'average_order_value'), None)
        transactions_row = next((row for row in rows if row['metric_name'] == 'total_transactions'), None)

        total_revenue = float(revenue_row['metric_value'])
        avg_value = float(avg_row['metric_value'])
        transactions = float(transactions_row['metric_value'])

        expected_revenue = avg_value * transactions

        # Allow for rounding differences (within 1% tolerance)
        tolerance = total_revenue * 0.01
        assert abs(total_revenue - expected_revenue) <= tolerance, \
            f"Revenue calculation inconsistent: {total_revenue} != {avg_value} × {transactions} = {expected_revenue}"


def test_top_region_is_valid():
    """Test that top_region_by_revenue is one of the valid regions."""
    valid_regions = ["North", "South", "East", "West"]

    with open('/app/sales_report.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        region_row = next((row for row in rows if row['metric_name'] == 'top_region_by_revenue'), None)
        assert region_row is not None, "top_region_by_revenue metric not found"

        top_region = region_row['metric_value']
        assert top_region in valid_regions, \
            f"Invalid region '{top_region}'. Must be one of {valid_regions}"


def test_top_category_is_valid():
    """Test that top_category_by_revenue is one of the valid categories."""
    valid_categories = ["Electronics", "Clothing", "Home", "Books", "Sports"]

    with open('/app/sales_report.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        category_row = next((row for row in rows if row['metric_name'] == 'top_category_by_revenue'), None)
        assert category_row is not None, "top_category_by_revenue metric not found"

        top_category = category_row['metric_value']
        assert top_category in valid_categories, \
            f"Invalid category '{top_category}'. Must be one of {valid_categories}"


def test_no_dummy_or_placeholder_values():
    """Test that metrics don't contain obvious dummy/placeholder values."""
    dummy_values = ['test', 'dummy', 'placeholder', 'n/a', 'null', 'none', '0', '0.0', '0.00']

    with open('/app/sales_report.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        for row in rows:
            value = row['metric_value'].lower().strip()
            assert value not in dummy_values, \
                f"Metric '{row['metric_name']}' contains dummy value: '{row['metric_value']}'"


def test_numeric_precision():
    """Test that numeric values are formatted with appropriate precision (2 decimal places)."""
    with open('/app/sales_report.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        numeric_metrics = ['total_revenue', 'average_order_value']

        for row in rows:
            if row['metric_name'] in numeric_metrics:
                value_str = row['metric_value']

                # Check if it's a valid number
                try:
                    float(value_str)
                except ValueError:
                    assert False, f"Metric '{row['metric_name']}' has non-numeric value: '{value_str}'"

                # Check decimal places (should have at most 2)
                if '.' in value_str:
                    decimal_part = value_str.split('.')[1]
                    assert len(decimal_part) <= 2, \
                        f"Metric '{row['metric_name']}' has more than 2 decimal places: '{value_str}'"
