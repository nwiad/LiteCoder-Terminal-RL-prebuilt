## Retail Sales Multi-Clustering & Profit Prediction Pipeline

Build a three-tier unsupervised segmentation pipeline for retail transactions, calibrate a profit-response model, and visualize profit drivers.

### Technical Requirements

**Language:** Python 3.x

**Required Libraries:** pandas, numpy, scikit-learn, xgboost (or lightgbm), matplotlib, seaborn, shap, kmodes, openpyxl, requests

**Input:**
- Remote dataset: https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx
- Download and save to `/app/data/raw/Online_Retail.xlsx`

**Output Files:**
- `/app/data/processed/cleaned_data.csv` - Cleaned transaction data with Cancelled flag
- `/app/data/processed/rfm_features.csv` - RFM features with product-level aggregates
- `/app/data/processed/clustered_data.csv` - Data with all cluster labels (customer_cluster, product_cluster, basket_cluster)
- `/app/models/profit_model.joblib` - Trained gradient boosting model
- `/app/visualizations/profit_analysis.png` - Bar chart + SHAP summary visualization
- `/app/retail_segmentation.py` - Complete executable pipeline script
- `/app/README.md` - Documentation (max 250 words)
- `/app/checksums.txt` - MD5 checksums of all output artifacts

### Pipeline Requirements

**1. Data Cleaning:**
- Remove rows with missing CustomerID
- Handle negative quantities and identify return orders
- Create "Cancelled" boolean flag for returns
- Save to `/app/data/processed/cleaned_data.csv`

**2. Feature Engineering:**
- Calculate RFM (Recency, Frequency, Monetary) on monthly aggregation window
- Compute product-level monthly sell-through statistics
- Merge customer and product features
- Save to `/app/data/processed/rfm_features.csv`

**3. Three-Layer Clustering:**
- Customer-level: k-means on RFM features
- Product-level: k-means on monthly sell-through statistics
- Basket-level: k-prototypes on transaction embeddings (one-hot product features + basket value)
- Append cluster labels to data and save to `/app/data/processed/clustered_data.csv`

**4. Profit-Response Model:**
- Train gradient boosting model on basket-level segments
- Predict profit lift from 10% price promotion
- Use 5-fold cross-validation
- Identify top 5 feature drivers
- Save model to `/app/models/profit_model.joblib`

**5. Visualization:**
- Bar chart: expected profit lift by top 3 basket clusters
- SHAP summary plot: top 5 profit drivers across all clusters
- Save combined figure to `/app/visualizations/profit_analysis.png`

**6. Executable Script:**
- Create `/app/retail_segmentation.py` that runs entire pipeline with single command
- Organize outputs in folder structure: data/raw/, data/processed/, models/, visualizations/

**7. Documentation:**
- Create `/app/README.md` with purpose, inputs, outputs, and execution command
- Maximum 250 words

**8. Reproducibility:**
- Fix all random seeds to 42 (numpy, scikit-learn, xgboost)
- Run pipeline twice and verify bitwise identical outputs
- Generate MD5 checksums and save to `/app/checksums.txt`

**9. Cleanup:**
- Remove intermediate/temporary files not needed for final deliverable
- Keep only version-controlled artifacts

### Data Format Specifications

**cleaned_data.csv columns (minimum):**
- InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country, Cancelled

**rfm_features.csv columns (minimum):**
- CustomerID, Recency, Frequency, Monetary, [product aggregates]

**clustered_data.csv columns (minimum):**
- All columns from cleaned_data plus: customer_cluster, product_cluster, basket_cluster

**checksums.txt format:**
```
<md5_hash>  data/processed/cleaned_data.csv
<md5_hash>  data/processed/rfm_features.csv
<md5_hash>  data/processed/clustered_data.csv
<md5_hash>  models/profit_model.joblib
<md5_hash>  visualizations/profit_analysis.png
```

### Execution

The pipeline must be executable with a single command from `/app/`:
```bash
python retail_segmentation.py
```
