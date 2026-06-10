Build a collaborative-filtering movie recommendation system using PySpark MLlib's ALS algorithm. Process MovieLens dataset files to generate personalized top-5 movie recommendations for all users.

## Technical Requirements

- **Language**: Python 3.x with PySpark
- **Input Files**:
  - Download from: https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
  - Extract `movies.csv` and `ratings.csv` from the archive
- **Output File**: `/app/recommendations.parquet` (single Parquet file)

## Input Specifications

**movies.csv** (comma-separated):
- Columns: `movieId`, `title`, `genres`
- Example: `1,Toy Story (1995),Adventure|Animation|Children|Comedy|Fantasy`

**ratings.csv** (comma-separated):
- Columns: `userId`, `movieId`, `rating`, `timestamp`
- Example: `1,1,4.0,964982703`

## Output Specifications

The output Parquet file at `/app/recommendations.parquet` must contain:

**Schema**:
```
userId: integer
recommendations: array<struct<movieId:integer, title:string, rating:float>>
```

**Requirements**:
- Each user must have exactly 5 movie recommendations (top-5 by predicted rating)
- Recommendations must exclude movies the user has already rated
- The `title` field must include the full movie title from `movies.csv`
- The `rating` field represents the predicted rating from the ALS model
- Recommendations must be sorted by predicted rating (descending) within each user's array

## Model Requirements

- Use PySpark MLlib's ALS (Alternating Least Squares) algorithm
- Model hyperparameters: `rank=10`, `maxIter=10`, `regParam=0.01`
- Split data: 80% training, 20% validation
- Save trained model to `/app/als_model`

## Data Processing Requirements

- Load both CSV files into Spark DataFrames with proper schema inference
- Handle the MovieLens dataset format correctly (comma-separated values)
- Join recommendation results with movie titles before final output
- Ensure all users from the original dataset receive recommendations
