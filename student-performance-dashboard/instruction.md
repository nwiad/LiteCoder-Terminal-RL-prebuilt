## Interactive Web-based Student Performance Dashboard

Build an interactive Plotly Dash web dashboard that visualizes student academic performance and predicts final grades from study-time features, using a synthetic dataset you generate.

### Technical Requirements

- Language: Python 3.9+
- Libraries: Pandas, NumPy, Scikit-learn, Plotly Dash, Seaborn or Matplotlib
- All output files use the paths specified below

### Step 1: Generate Synthetic Dataset

Generate a reproducible synthetic student dataset and write it to `/app/data/students.csv`.

- Use NumPy random seed `42` for reproducibility
- At least 200 rows
- Must contain at least these columns (additional columns allowed):
  - `student_id`: unique integer identifier starting from 1
  - `study_hours_per_week`: float, range roughly 0–40
  - `attendance_rate`: float between 0.0 and 1.0
  - `assignments_completed`: integer, range 0–50
  - `previous_grade`: float, range 0–100
  - `extracurricular_hours`: float, range 0–20
  - `final_grade`: float, range 0–100 (the target variable)
- `final_grade` must have a meaningful statistical relationship with the study-time related features (correlation with `study_hours_per_week` should be positive)

### Step 2: Exploratory Data Analysis

Produce descriptive statistics and two visualizations:

- Write descriptive statistics (mean, std, min, max, etc. for all numeric columns) to `/app/outputs/descriptive_stats.csv`
- Save two insightful plots as:
  - `/app/outputs/plot1.png`
  - `/app/outputs/plot2.png`
- One plot must be a correlation heatmap of numeric columns
- The other plot must show the relationship between `study_hours_per_week` and `final_grade`

### Step 3: Train a Regression Model

Train a regression model to predict `final_grade` from the feature columns.

- Use either `RandomForestRegressor` or `GradientBoostingRegressor` from Scikit-learn
- Use an 80/20 train-test split with `random_state=42`
- Features must include at minimum: `study_hours_per_week`, `attendance_rate`, `assignments_completed`, `previous_grade`, `extracurricular_hours`
- Write evaluation metrics to `/app/outputs/model_metrics.txt` in this exact format (one metric per line):
  ```
  RMSE: <value>
  R2: <value>
  ```
  where `<value>` is a float rounded to 4 decimal places
- The model must achieve R² > 0.5 on the test set
- Save the predicted-vs-actual values for the test set to `/app/outputs/predictions.csv` with columns: `actual`, `predicted`

### Step 4: Build the Dash Dashboard

Create a Plotly Dash application in `/app/app.py`.

- The app must run on host `0.0.0.0` and port `8050`
- The dashboard must include:
  - The two EDA plots (embedded or recreated as Plotly figures)
  - A predicted-vs-actual scatter plot from the model results
  - A slider input for `study_hours_per_week` (range 0–40) that dynamically displays the model's predicted grade for the selected value (using median/mean values for other features)
- The app must have a callback that updates the predicted grade when the slider value changes
- The predicted grade display element must have the Dash component id `predicted-grade-output`
- The slider must have the Dash component id `study-hours-slider`

### Step 5: Package the Project

- Create `/app/student_dashboard.tar.gz` containing all project files (data, outputs, app.py, and any supporting scripts)
- Create `/app/README.md` documenting the startup command to run the dashboard

### Output File Summary

| File | Description |
|---|---|
| `/app/data/students.csv` | Synthetic dataset (≥200 rows, ≥7 columns) |
| `/app/outputs/descriptive_stats.csv` | Descriptive statistics for all numeric columns |
| `/app/outputs/plot1.png` | Correlation heatmap |
| `/app/outputs/plot2.png` | Study hours vs final grade plot |
| `/app/outputs/model_metrics.txt` | RMSE and R² on test set |
| `/app/outputs/predictions.csv` | Actual vs predicted values |
| `/app/app.py` | Dash application entry point |
| `/app/student_dashboard.tar.gz` | Project archive |
| `/app/README.md` | Startup documentation |
