## Automated Data Pipeline with ML Scoring

Build an end-to-end pipeline that ingests raw loan data, trains a default-risk classifier, and exposes a REST API endpoint to score new loan applications.

### Technical Requirements

- **Language:** Python 3.8+
- **ML Framework:** scikit-learn
- **API Framework:** FastAPI
- **Input:** CSV file at `/app/data/raw/loans.csv`
- **Model Output:** Serialized model file at `/app/models/risk_model.pkl`
- **Container:** Docker image named `loan-scorer:v1.0.0`

### Project Structure

```
/app/
├── src/
│   ├── data_processing.py
│   ├── model.py
│   └── api.py
├── data/
│   └── raw/
│       └── loans.csv
├── models/
│   └── risk_model.pkl
├── tests/
├── notebooks/
├── Dockerfile
├── requirements.txt
└── README.md
```

### Input Data Format

The input CSV at `/app/data/raw/loans.csv` must contain at minimum:
- Numeric features: `loan_amount`, `annual_income`, `debt_to_income_ratio`, `credit_score`
- Categorical features: `employment_status`, `loan_purpose`
- Target variable: `default` (binary: 0 or 1)

### Data Processing Requirements

Implement in `src/data_processing.py`:
- Handle missing values appropriately
- Encode categorical variables
- Feature engineering (create at least one derived feature)
- Train/test split (80/20)
- Return processed features and target as numpy arrays or pandas DataFrames

### Model Requirements

Implement in `src/model.py`:
- Train a logistic regression classifier for default risk prediction
- Serialize trained model to `/app/models/risk_model.pkl` using pickle or joblib
- Model must accept feature dictionary and return probability score (0.0 to 1.0)

### API Specification

Implement FastAPI service in `src/api.py`:

**Endpoint:** `POST /score`

**Request Body:**
```json
{
  "loan_amount": 15000,
  "annual_income": 50000,
  "debt_to_income_ratio": 0.35,
  "credit_score": 680,
  "employment_status": "employed",
  "loan_purpose": "debt_consolidation"
}
```

**Response Body:**
```json
{
  "default_probability": 0.23,
  "risk_category": "medium"
}
```

Where `risk_category` is:
- "low" if probability < 0.3
- "medium" if 0.3 ≤ probability < 0.7
- "high" if probability ≥ 0.7

### Testing Requirements

Create unit tests in `tests/` covering:
- Data cleaning and validation functions
- Feature engineering logic
- Model prediction functionality
- API endpoint response format

### Docker Requirements

Create `Dockerfile` that:
- Uses Python 3.8+ base image
- Installs dependencies from `requirements.txt`
- Copies source code and model file
- Exposes port 8000
- Runs FastAPI with `uvicorn src.api:app --host 0.0.0.0 --port 8000`

### Automation Script

Create `run_pipeline.sh` that executes:
1. Run all tests with pytest
2. Train model (execute training script)
3. Build Docker image `loan-scorer:v1.0.0`
4. Start container on port 8000
5. Send test request to `POST /score` endpoint and verify response format

### Version Control

- Initialize Git repository
- Commit all code, tests, and configuration files
- Tag repository with `v1.0.0`

### Documentation

Create `README.md` with:
- Setup instructions
- How to run the pipeline script
- Example curl command to test the `/score` endpoint
