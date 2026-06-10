## Build a Movie Recommender System

Build a collaborative-filtering-based movie recommender system using PySpark and the MovieLens 1M dataset. The system trains an ALS model, evaluates it, and exposes a CLI to generate top-N movie recommendations for any user.

### Technical Requirements

- Language: Python 3.x with PySpark (Spark MLlib)
- Dataset: MovieLens 1M (download from https://files.grouplens.org/datasets/movielens/ml-1m.zip)
- Cache the downloaded dataset under `/app/ml-1m/`

### Pipeline Steps

1. **Data Loading**: Load `ratings.dat`, `movies.dat`, and `users.dat` from `/app/ml-1m/` into Spark DataFrames. The `::` delimiter must be handled correctly.

2. **Data Cleaning**:
   - Remove duplicate ratings (same user + same movie). Keep only the latest rating per (user, movie) pair.
   - Drop rows with any null/missing values in required columns.
   - Ensure column types: `UserID` (int), `MovieID` (int), `Rating` (float), `Timestamp` (int).

3. **Train/Test Split**: Split cleaned ratings 80/20 using `randomSplit([0.8, 0.2], seed=42)`.

4. **Model Training**: Train an ALS collaborative filtering model. Use `coldStartStrategy="drop"` to handle cold-start during evaluation. The `userCol`, `itemCol`, and `ratingCol` must be `UserID`, `MovieID`, and `Rating` respectively.

5. **Evaluation**: Compute RMSE on the test set. The RMSE must be below 1.0.

6. **Recommendation Function**: Implement `recommend_for_user(user_id, n=10)` that returns a list of tuples `(movie_title, predicted_rating)` sorted by predicted_rating descending. Predicted ratings should be rounded to 4 decimal places.

### Output Files

#### `/app/output/recommendations.json`

A JSON file containing the top-5 recommendations for user ID 123. Structure:

```json
{
  "user_id": 123,
  "recommendations": [
    {"movie_title": "Some Movie (2000)", "predicted_rating": 4.8521},
    ...
  ],
  "count": 5
}
```

- `recommendations` is a list of objects, each with `movie_title` (string) and `predicted_rating` (float, 4 decimal places).
- `count` equals the length of `recommendations`.
- The list is sorted by `predicted_rating` descending.

#### `/app/output/report.txt`

A plain-text report containing at minimum:
- A line matching the pattern `RMSE: <value>` (e.g., `RMSE: 0.8734`) where the value is the test-set RMSE rounded to 4 decimal places.
- A section listing the top-5 recommendations for user 123 with movie titles and predicted ratings.
- A summary of data-cleaning steps performed.
- The ALS model parameters used (rank, regParam, maxIter).

### CLI Interface

Provide a script `/app/recommend.py` that can be invoked as:

```
python /app/recommend.py <user_id> <n>
```

- `user_id` (required): integer user ID
- `n` (optional, default 10): number of recommendations

The script must print output to stdout as valid JSON with the same schema as `recommendations.json`:

```json
{
  "user_id": 456,
  "recommendations": [
    {"movie_title": "...", "predicted_rating": 4.1234},
    ...
  ],
  "count": 5
}
```

- Exit code 0 on success.
- If the user_id does not exist in the dataset, print `{"error": "User <user_id> not found"}` to stdout and exit with code 1.

### Constraints

- All output files must be written under `/app/output/` (create the directory if needed).
- The pipeline must be fully re-runnable: running `recommend.py` should work without re-training if a saved model exists.
- Save the trained ALS model to `/app/output/als_model/`.
