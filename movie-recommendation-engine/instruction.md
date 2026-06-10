## Task: Movie Recommendation Engine with Collaborative Filtering

Build a collaborative filtering recommendation system using matrix factorization on the MovieLens 100K dataset to predict user movie ratings.

**Technical Requirements:**
- Python 3.x with PyTorch
- Input: MovieLens 100K dataset (u.data file) at `/app/ml-100k/u.data`
- Output: JSON file at `/app/results.json`

**Dataset Format:**
The input file `/app/ml-100k/u.data` is tab-separated with columns: `user_id`, `item_id`, `rating`, `timestamp`. Each rating is an integer from 1 to 5.

**Implementation Requirements:**
1. Load and split the dataset into training (80%) and test (20%) sets using random sampling with seed=42
2. Implement a matrix factorization model with embedding dimensions for users and items
3. Train the model using Mean Squared Error loss with at least 10 epochs
4. Evaluate on the test set using RMSE (Root Mean Squared Error) and MAE (Mean Absolute Error)
5. Implement a recommendation function that takes a user_id and returns top-N movie predictions

**Output Format:**
Save results to `/app/results.json` with the following structure:
```json
{
  "model_performance": {
    "rmse": <float>,
    "mae": <float>
  },
  "sample_recommendations": {
    "<user_id>": [<item_id1>, <item_id2>, <item_id3>, ...]
  }
}
```

The `sample_recommendations` should contain predictions for at least user_id 1, showing the top 5 recommended movie IDs (items the user hasn't rated yet, ranked by predicted rating).

**Model Persistence:**
Save the trained PyTorch model to `/app/model.pth` for future use.
