## Task: NYC Airbnb Data Analysis Pipeline

You are a data science consultant analyzing NYC Airbnb data for a real-estate investment firm. Build a complete analysis pipeline that processes the dataset, generates insights, and produces a comprehensive report.

**Technical Requirements:**
- Python 3.x with pandas, scikit-learn, and matplotlib/seaborn
- Input: `/app/AB_NYC_2019.csv` (NYC Airbnb dataset)
- Output: `/app/report.html` (analysis report)
- Execution: Single shell script `/app/run_analysis.sh` that runs the entire pipeline

**Data Processing Requirements:**

1. **Data Loading and Validation:**
   - Load the CSV dataset from `/app/AB_NYC_2019.csv`
   - Document basic statistics (row count, column count, data types)
   - Identify missing values and data quality issues

2. **Data Cleaning:**
   - Handle missing values appropriately
   - Remove or correct outliers in price data
   - Ensure data consistency across all fields

3. **Exploratory Data Analysis:**
   - Analyze price distributions across neighborhoods
   - Examine availability patterns and trends
   - Calculate summary statistics by neighborhood groups

4. **Price Prediction Model:**
   - Build a regression model to predict listing prices
   - Use relevant features (location, room type, availability, etc.)
   - Report model performance metrics (R², RMSE, MAE)

5. **Neighborhood Clustering:**
   - Group neighborhoods by rental characteristics
   - Use clustering algorithm (e.g., K-means)
   - Identify distinct neighborhood segments

6. **Demand Forecasting:**
   - Analyze availability data as demand proxy
   - Generate demand trend insights
   - Provide forecasting metrics

**Output Requirements:**

The `/app/report.html` file must contain:
- Executive summary with key findings
- Data quality assessment results
- Price distribution visualizations
- Model performance metrics and feature importance
- Neighborhood cluster analysis with characteristics
- Demand forecast insights
- Investment recommendations based on analysis

**Execution Requirements:**

Create `/app/run_analysis.sh` that:
- Executes the complete analysis pipeline
- Generates `/app/report.html`
- Runs successfully with: `bash /app/run_analysis.sh`
- Completes without manual intervention

**Data Format:**

The input CSV contains columns including: id, name, host_id, host_name, neighbourhood_group, neighbourhood, latitude, longitude, room_type, price, minimum_nights, number_of_reviews, last_review, reviews_per_month, calculated_host_listings_count, availability_365.
