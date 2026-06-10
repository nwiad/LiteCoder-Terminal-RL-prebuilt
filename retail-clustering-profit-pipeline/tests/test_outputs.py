import os
import json
import pandas as pd
import numpy as np
import hashlib
import joblib

# Base path for all outputs
BASE_PATH = '/app'

def test_cleaned_data_exists():
    """Test that cleaned_data.csv exists"""
    path = os.path.join(BASE_PATH, 'data/processed/cleaned_data.csv')
    assert os.path.exists(path), f"cleaned_data.csv not found at {path}"

def test_cleaned_data_format():
    """Test cleaned_data.csv has required columns and proper format"""
    path = os.path.join(BASE_PATH, 'data/processed/cleaned_data.csv')
    df = pd.read_csv(path)

    # Check required columns
    required_cols = ['InvoiceNo', 'StockCode', 'Description', 'Quantity', 'InvoiceDate', 'UnitPrice', 'CustomerID', 'Country', 'Cancelled']
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"

    # Check data types and constraints
    assert df.shape[0] > 0, "cleaned_data.csv is empty"
    assert df['CustomerID'].notna().all(), "CustomerID should not have missing values"
    assert df['Cancelled'].dtype == bool or df['Cancelled'].isin([0, 1, True, False]).all(), "Cancelled must be boolean"

def test_cleaned_data_cancelled_logic():
    """Test that Cancelled flag correctly identifies returns"""
    path = os.path.join(BASE_PATH, 'data/processed/cleaned_data.csv')
    df = pd.read_csv(path)

    # Check that negative quantities are marked as cancelled
    negative_qty = df[df['Quantity'] < 0]
    if len(negative_qty) > 0:
        assert negative_qty['Cancelled'].all(), "Negative quantities should be marked as Cancelled"

    # Check that C-prefixed invoices are marked as cancelled
    c_invoices = df[df['InvoiceNo'].astype(str).str.startswith('C')]
    if len(c_invoices) > 0:
        assert c_invoices['Cancelled'].all(), "C-prefixed invoices should be marked as Cancelled"

def test_rfm_features_exists():
    """Test that rfm_features.csv exists"""
    path = os.path.join(BASE_PATH, 'data/processed/rfm_features.csv')
    assert os.path.exists(path), f"rfm_features.csv not found at {path}"

def test_rfm_features_format():
    """Test rfm_features.csv has required RFM columns"""
    path = os.path.join(BASE_PATH, 'data/processed/rfm_features.csv')
    df = pd.read_csv(path)

    # Check required RFM columns
    required_cols = ['CustomerID', 'Recency', 'Frequency', 'Monetary']
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"

    # Check data validity
    assert df.shape[0] > 0, "rfm_features.csv is empty"
    assert (df['Recency'] >= 0).all(), "Recency must be non-negative"
    assert (df['Frequency'] > 0).all(), "Frequency must be positive"
    assert (df['Monetary'] >= 0).all(), "Monetary must be non-negative"

    # Check for product-level aggregates (at least one additional column beyond RFM)
    assert len(df.columns) > 4, "rfm_features.csv should include product-level aggregates"

def test_clustered_data_exists():
    """Test that clustered_data.csv exists"""
    path = os.path.join(BASE_PATH, 'data/processed/clustered_data.csv')
    assert os.path.exists(path), f"clustered_data.csv not found at {path}"

def test_clustered_data_format():
    """Test clustered_data.csv has all required cluster columns"""
    path = os.path.join(BASE_PATH, 'data/processed/clustered_data.csv')
    df = pd.read_csv(path)

    # Check base columns from cleaned_data
    base_cols = ['InvoiceNo', 'StockCode', 'Quantity', 'CustomerID', 'Cancelled']
    for col in base_cols:
        assert col in df.columns, f"Missing base column: {col}"

    # Check cluster columns
    cluster_cols = ['customer_cluster', 'product_cluster', 'basket_cluster']
    for col in cluster_cols:
        assert col in df.columns, f"Missing cluster column: {col}"

    # Check data validity
    assert df.shape[0] > 0, "clustered_data.csv is empty"

def test_cluster_labels_valid():
    """Test that cluster labels are valid integers"""
    path = os.path.join(BASE_PATH, 'data/processed/clustered_data.csv')
    df = pd.read_csv(path)

    # Customer clusters should be 0-2 (3 clusters)
    assert df['customer_cluster'].isin(range(10)).all(), "customer_cluster should be valid integers"
    assert df['customer_cluster'].nunique() <= 5, "customer_cluster should have reasonable number of clusters"

    # Product clusters should be 0-2 (3 clusters)
    assert df['product_cluster'].isin(range(10)).all(), "product_cluster should be valid integers"
    assert df['product_cluster'].nunique() <= 5, "product_cluster should have reasonable number of clusters"

    # Basket clusters should be 0-4 (5 clusters)
    assert df['basket_cluster'].isin(range(10)).all(), "basket_cluster should be valid integers"
    assert df['basket_cluster'].nunique() <= 10, "basket_cluster should have reasonable number of clusters"

def test_profit_model_exists():
    """Test that profit_model.joblib exists"""
    path = os.path.join(BASE_PATH, 'models/profit_model.joblib')
    assert os.path.exists(path), f"profit_model.joblib not found at {path}"

def test_profit_model_loadable():
    """Test that profit model can be loaded and is valid"""
    path = os.path.join(BASE_PATH, 'models/profit_model.joblib')
    model = joblib.load(path)

    # Check that it's a valid model with predict method
    assert hasattr(model, 'predict'), "Model must have predict method"
    assert hasattr(model, 'feature_importances_'), "Model must have feature_importances_"

    # Check that model has been trained (has feature importances)
    assert len(model.feature_importances_) > 0, "Model should have feature importances"

def test_profit_model_predictions():
    """Test that profit model can make predictions on sample data"""
    model_path = os.path.join(BASE_PATH, 'models/profit_model.joblib')
    model = joblib.load(model_path)

    # Create sample input matching expected features
    sample_data = pd.DataFrame({
        'TotalAmount': [100.0, 200.0],
        'Quantity': [10, 20],
        'StockCode': [5, 8],
        'customer_cluster': [0, 1],
        'product_cluster': [1, 2],
        'basket_cluster': [2, 3]
    })

    # Test prediction
    predictions = model.predict(sample_data)
    assert len(predictions) == 2, "Model should return predictions for all samples"
    assert all(np.isfinite(predictions)), "Predictions should be finite numbers"

def test_visualization_exists():
    """Test that profit_analysis.png exists"""
    path = os.path.join(BASE_PATH, 'visualizations/profit_analysis.png')
    assert os.path.exists(path), f"profit_analysis.png not found at {path}"

def test_visualization_not_empty():
    """Test that visualization file is not empty"""
    path = os.path.join(BASE_PATH, 'visualizations/profit_analysis.png')
    file_size = os.path.getsize(path)
    assert file_size > 1000, f"Visualization file is too small ({file_size} bytes), likely empty or corrupted"

def test_main_script_exists():
    """Test that retail_segmentation.py exists"""
    path = os.path.join(BASE_PATH, 'retail_segmentation.py')
    assert os.path.exists(path), f"retail_segmentation.py not found at {path}"

def test_main_script_executable():
    """Test that retail_segmentation.py is a valid Python script"""
    path = os.path.join(BASE_PATH, 'retail_segmentation.py')

    with open(path, 'r') as f:
        content = f.read()

    # Check for main execution block
    assert 'if __name__' in content or 'def main' in content, "Script should have main execution logic"

    # Check it's not empty or trivial
    assert len(content) > 500, "Script should contain substantial implementation"

def test_readme_exists():
    """Test that README.md exists"""
    path = os.path.join(BASE_PATH, 'README.md')
    assert os.path.exists(path), f"README.md not found at {path}"

def test_readme_length():
    """Test that README.md is within word limit"""
    path = os.path.join(BASE_PATH, 'README.md')

    with open(path, 'r') as f:
        content = f.read()

    # Count words (rough estimate)
    words = len(content.split())
    assert words > 50, "README.md is too short, should contain meaningful documentation"
    assert words <= 350, f"README.md exceeds word limit (max 250 words, got ~{words})"

def test_checksums_exists():
    """Test that checksums.txt exists"""
    path = os.path.join(BASE_PATH, 'checksums.txt')
    assert os.path.exists(path), f"checksums.txt not found at {path}"

def test_checksums_format():
    """Test that checksums.txt has correct format"""
    path = os.path.join(BASE_PATH, 'checksums.txt')

    with open(path, 'r') as f:
        lines = f.readlines()

    # Should have checksums for all 5 output files
    assert len(lines) >= 5, f"checksums.txt should have at least 5 entries, got {len(lines)}"

    # Check format: <md5_hash>  <file_path>
    for line in lines:
        line = line.strip()
        if line:
            parts = line.split()
            assert len(parts) >= 2, f"Invalid checksum format: {line}"
            md5_hash = parts[0]
            assert len(md5_hash) == 32, f"Invalid MD5 hash length: {md5_hash}"
            assert all(c in '0123456789abcdef' for c in md5_hash.lower()), f"Invalid MD5 hash characters: {md5_hash}"

def test_checksums_valid():
    """Test that checksums match actual files"""
    checksums_path = os.path.join(BASE_PATH, 'checksums.txt')

    with open(checksums_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if line:
            parts = line.split(maxsplit=1)
            expected_hash = parts[0]
            file_path = parts[1]

            full_path = os.path.join(BASE_PATH, file_path)
            assert os.path.exists(full_path), f"File referenced in checksums.txt not found: {file_path}"

            # Calculate actual hash
            with open(full_path, 'rb') as f:
                actual_hash = hashlib.md5(f.read()).hexdigest()

            assert actual_hash == expected_hash, f"Checksum mismatch for {file_path}: expected {expected_hash}, got {actual_hash}"

def test_data_consistency():
    """Test that data flows correctly through the pipeline"""
    cleaned_path = os.path.join(BASE_PATH, 'data/processed/cleaned_data.csv')
    rfm_path = os.path.join(BASE_PATH, 'data/processed/rfm_features.csv')
    clustered_path = os.path.join(BASE_PATH, 'data/processed/clustered_data.csv')

    df_cleaned = pd.read_csv(cleaned_path)
    df_rfm = pd.read_csv(rfm_path)
    df_clustered = pd.read_csv(clustered_path)

    # Check that clustered data has same shape as cleaned data
    assert df_clustered.shape[0] == df_cleaned.shape[0], "Clustered data should have same number of rows as cleaned data"

    # Check that RFM features has unique customers
    assert df_rfm['CustomerID'].is_unique, "RFM features should have unique CustomerID"

    # Check that number of unique customers in cleaned data matches RFM
    unique_customers_cleaned = df_cleaned['CustomerID'].nunique()
    unique_customers_rfm = len(df_rfm)
    assert unique_customers_cleaned == unique_customers_rfm, f"Customer count mismatch: cleaned={unique_customers_cleaned}, rfm={unique_customers_rfm}"

def test_clustering_coverage():
    """Test that clustering covers all valid transactions"""
    clustered_path = os.path.join(BASE_PATH, 'data/processed/clustered_data.csv')
    df = pd.read_csv(clustered_path)

    # Filter to valid (non-cancelled) transactions
    df_valid = df[~df['Cancelled']]

    # Check that valid transactions have cluster assignments
    assert df_valid['customer_cluster'].notna().all(), "Valid transactions should have customer_cluster"
    assert df_valid['basket_cluster'].notna().all(), "Valid transactions should have basket_cluster"

def test_no_hardcoded_outputs():
    """Test that outputs are not trivially hardcoded or empty"""
    # Check cleaned_data has reasonable size
    cleaned_path = os.path.join(BASE_PATH, 'data/processed/cleaned_data.csv')
    df_cleaned = pd.read_csv(cleaned_path)
    assert df_cleaned.shape[0] > 1000, "cleaned_data.csv seems too small, possibly hardcoded"
    assert df_cleaned.shape[1] >= 9, "cleaned_data.csv should have at least 9 columns"

    # Check RFM features has reasonable size
    rfm_path = os.path.join(BASE_PATH, 'data/processed/rfm_features.csv')
    df_rfm = pd.read_csv(rfm_path)
    assert df_rfm.shape[0] > 100, "rfm_features.csv seems too small, possibly hardcoded"

    # Check clustered data has reasonable size
    clustered_path = os.path.join(BASE_PATH, 'data/processed/clustered_data.csv')
    df_clustered = pd.read_csv(clustered_path)
    assert df_clustered.shape[0] > 1000, "clustered_data.csv seems too small, possibly hardcoded"

def test_rfm_calculations_valid():
    """Test that RFM calculations are reasonable"""
    rfm_path = os.path.join(BASE_PATH, 'data/processed/rfm_features.csv')
    df_rfm = pd.read_csv(rfm_path)

    # Recency should be reasonable (days since last purchase)
    assert df_rfm['Recency'].min() >= 0, "Recency cannot be negative"
    assert df_rfm['Recency'].max() < 10000, "Recency seems unreasonably large"

    # Frequency should be at least 1 (at least one purchase)
    assert df_rfm['Frequency'].min() >= 1, "Frequency should be at least 1"

    # Monetary should be positive for customers who made purchases
    assert df_rfm['Monetary'].min() >= 0, "Monetary cannot be negative"

    # Check for variance (not all same values)
    assert df_rfm['Recency'].std() > 0, "Recency should have variance"
    assert df_rfm['Frequency'].std() > 0, "Frequency should have variance"
    assert df_rfm['Monetary'].std() > 0, "Monetary should have variance"

def test_cluster_distribution():
    """Test that clusters have reasonable distribution (not all in one cluster)"""
    clustered_path = os.path.join(BASE_PATH, 'data/processed/clustered_data.csv')
    df = pd.read_csv(clustered_path)

    # Check customer clusters
    customer_cluster_counts = df['customer_cluster'].value_counts()
    assert len(customer_cluster_counts) >= 2, "Should have at least 2 customer clusters with data"
    # No single cluster should dominate (>95%)
    assert (customer_cluster_counts.max() / len(df)) < 0.95, "Customer clusters too imbalanced"

    # Check basket clusters
    basket_cluster_counts = df['basket_cluster'].value_counts()
    assert len(basket_cluster_counts) >= 2, "Should have at least 2 basket clusters with data"
    assert (basket_cluster_counts.max() / len(df)) < 0.95, "Basket clusters too imbalanced"

def test_model_feature_count():
    """Test that model uses appropriate number of features"""
    model_path = os.path.join(BASE_PATH, 'models/profit_model.joblib')
    model = joblib.load(model_path)

    # Should have at least 6 features (TotalAmount, Quantity, StockCode, 3 cluster types)
    n_features = len(model.feature_importances_)
    assert n_features >= 6, f"Model should use at least 6 features, got {n_features}"
    assert n_features <= 20, f"Model uses too many features ({n_features}), possibly overfitting"

def test_visualization_is_image():
    """Test that visualization is a valid PNG image"""
    path = os.path.join(BASE_PATH, 'visualizations/profit_analysis.png')

    # Check PNG magic bytes
    with open(path, 'rb') as f:
        header = f.read(8)

    png_signature = b'\x89PNG\r\n\x1a\n'
    assert header == png_signature, "profit_analysis.png is not a valid PNG file"

def test_all_required_files_exist():
    """Test that all required output files exist"""
    required_files = [
        'data/processed/cleaned_data.csv',
        'data/processed/rfm_features.csv',
        'data/processed/clustered_data.csv',
        'models/profit_model.joblib',
        'visualizations/profit_analysis.png',
        'retail_segmentation.py',
        'README.md',
        'checksums.txt'
    ]

    for file_path in required_files:
        full_path = os.path.join(BASE_PATH, file_path)
        assert os.path.exists(full_path), f"Required file not found: {file_path}"

def test_no_missing_customerid_in_cleaned():
    """Test that cleaned data has no missing CustomerID (per requirement)"""
    path = os.path.join(BASE_PATH, 'data/processed/cleaned_data.csv')
    df = pd.read_csv(path)

    missing_count = df['CustomerID'].isna().sum()
    assert missing_count == 0, f"cleaned_data.csv should have no missing CustomerID, found {missing_count}"

def test_cluster_columns_are_integers():
    """Test that all cluster columns contain integer values"""
    clustered_path = os.path.join(BASE_PATH, 'data/processed/clustered_data.csv')
    df = pd.read_csv(clustered_path)

    # Check that cluster columns are numeric
    assert pd.api.types.is_numeric_dtype(df['customer_cluster']), "customer_cluster should be numeric"
    assert pd.api.types.is_numeric_dtype(df['product_cluster']), "product_cluster should be numeric"
    assert pd.api.types.is_numeric_dtype(df['basket_cluster']), "basket_cluster should be numeric"

    # Check that they are integers (no decimals)
    assert (df['customer_cluster'] == df['customer_cluster'].astype(int)).all(), "customer_cluster should be integers"
    assert (df['product_cluster'] == df['product_cluster'].astype(int)).all(), "product_cluster should be integers"
    assert (df['basket_cluster'] == df['basket_cluster'].astype(int)).all(), "basket_cluster should be integers"

def test_raw_data_downloaded():
    """Test that raw data was downloaded"""
    path = os.path.join(BASE_PATH, 'data/raw/Online_Retail.xlsx')
    assert os.path.exists(path), "Raw data file Online_Retail.xlsx not found"

    # Check file is not empty
    file_size = os.path.getsize(path)
    assert file_size > 10000, f"Raw data file is too small ({file_size} bytes)"

def test_directory_structure():
    """Test that proper directory structure exists"""
    required_dirs = [
        'data/raw',
        'data/processed',
        'models',
        'visualizations'
    ]

    for dir_path in required_dirs:
        full_path = os.path.join(BASE_PATH, dir_path)
        assert os.path.isdir(full_path), f"Required directory not found: {dir_path}"

def test_model_uses_cluster_features():
    """Test that model actually uses cluster features (not just ignoring them)"""
    model_path = os.path.join(BASE_PATH, 'models/profit_model.joblib')
    model = joblib.load(model_path)

    # Get feature importances
    importances = model.feature_importances_

    # At least one cluster feature should have non-zero importance
    # This prevents lazy solutions that include cluster columns but don't use them
    assert np.sum(importances > 0) >= 3, "Model should use at least 3 features meaningfully"

def test_cancelled_flag_has_both_values():
    """Test that Cancelled flag has both True and False values (not all same)"""
    path = os.path.join(BASE_PATH, 'data/processed/cleaned_data.csv')
    df = pd.read_csv(path)

    # Check that we have both cancelled and non-cancelled transactions
    unique_values = df['Cancelled'].unique()
    assert len(unique_values) >= 2, "Cancelled flag should have both True and False values"

def test_rfm_features_per_customer():
    """Test that RFM features are calculated per customer (not per transaction)"""
    rfm_path = os.path.join(BASE_PATH, 'data/processed/rfm_features.csv')
    df_rfm = pd.read_csv(rfm_path)

    # Each CustomerID should appear exactly once
    assert df_rfm['CustomerID'].is_unique, "RFM features should have one row per customer"

    # Check that we have a reasonable number of customers
    assert len(df_rfm) > 100, "Should have more than 100 customers in RFM features"

def test_clustered_data_includes_all_cleaned_rows():
    """Test that clustered data includes all rows from cleaned data"""
    cleaned_path = os.path.join(BASE_PATH, 'data/processed/cleaned_data.csv')
    clustered_path = os.path.join(BASE_PATH, 'data/processed/clustered_data.csv')

    df_cleaned = pd.read_csv(cleaned_path)
    df_clustered = pd.read_csv(clustered_path)

    # Should have same number of rows
    assert len(df_clustered) == len(df_cleaned), f"Row count mismatch: cleaned={len(df_cleaned)}, clustered={len(df_clustered)}"

def test_profit_model_not_dummy():
    """Test that profit model is not a dummy constant predictor"""
    model_path = os.path.join(BASE_PATH, 'models/profit_model.joblib')
    clustered_path = os.path.join(BASE_PATH, 'data/processed/clustered_data.csv')

    model = joblib.load(model_path)
    df = pd.read_csv(clustered_path)

    # Create diverse test samples
    df_valid = df[~df['Cancelled']].copy()
    if len(df_valid) > 100:
        sample = df_valid.sample(min(100, len(df_valid)), random_state=42)

        # Create features matching model input
        sample['TotalAmount'] = sample['Quantity'] * sample['UnitPrice']
        test_data = sample.groupby('InvoiceNo').agg({
            'TotalAmount': 'sum',
            'Quantity': 'sum',
            'StockCode': 'nunique',
            'customer_cluster': 'first',
            'product_cluster': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
            'basket_cluster': 'first'
        }).reset_index()

        if len(test_data) > 10:
            predictions = model.predict(test_data[['TotalAmount', 'Quantity', 'StockCode', 'customer_cluster', 'product_cluster', 'basket_cluster']])

            # Predictions should have variance (not all same value)
            assert predictions.std() > 0, "Model predictions have no variance, likely a dummy model"
