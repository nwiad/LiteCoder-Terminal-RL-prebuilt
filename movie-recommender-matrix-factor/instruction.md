## Movie Recommender with Matrix Factorization (CPU-only)

Build a collaborative-filtering movie recommender on the MovieLens-100K dataset using PyTorch-based matrix factorization. Train on CPU only, evaluate top-K recommendation quality, and produce a structured results report.

### Technical Requirements

- Language: Python 3.x
- Framework: PyTorch (no GPU, no third-party rec-sys libraries such as Surprise, LightFM, etc.)
- All work runs from `/app` as the working directory

### Data

- Download the MovieLens-100K dataset programmatically (from https://files.grouplens.org/datasets/movielens/ml-100k.zip) and extract it into `/app/ml-100k/`.
- Use the `u.data` file (tab-separated: userId, movieId, rating, timestamp) as the primary ratings source.
- Use the `u.item` file for movie title lookup.

### Implementation Requirements

1. **Data Loading**: Build a PyTorch `Dataset` and `DataLoader` that yields `(userId, movieId, rating)` triples. User and movie IDs must be re-indexed to start from 0.

2. **Train/Validation Split**: Split the ratings into 80% train / 20% validation. Use a fixed random seed of `42` for reproducibility.

3. **Model**: Implement a matrix-factorization model containing:
   - User embedding and item embedding layers
   - User bias and item bias terms
   - A global bias scalar
   - The forward pass computes: `prediction = global_bias + user_bias + item_bias + dot(user_embedding, item_embedding)`

4. **Training**: Train with MSE loss. Log the average training loss per epoch. Train for at least 20 epochs.

5. **Hyperparameter Tuning**: Perform a grid search over at least 2 different values each for:
   - Latent dimension (embedding size)
   - L2 regularization weight (weight_decay)

   Select the best configuration based on validation RMSE.

6. **Evaluation**: On the validation set, compute and report:
   - RMSE (root mean squared error on rating prediction)
   - Precision@10 and Recall@10 (for top-10 recommendations per user; a relevant item is one the user rated >= 4.0 in the validation set)

7. **Model Persistence**: Save the best model's state dict to `/app/best_model.pt`.

8. **Top-5 Recommendations**: For the user with re-indexed ID `0`, generate the top-5 recommended movies (excluding movies already rated by that user in the training set). Include movie titles from `u.item`.

### Output

Write a single JSON file to `/app/output.json` with the following structure:

```json
{
  "best_hyperparameters": {
    "latent_dim": <int>,
    "weight_decay": <float>,
    "learning_rate": <float>,
    "num_epochs": <int>
  },
  "metrics": {
    "val_rmse": <float>,
    "precision_at_10": <float>,
    "recall_at_10": <float>
  },
  "top5_recommendations_user0": [
    {"movie_id": <int>, "title": "<string>", "predicted_rating": <float>},
    ...
  ],
  "num_users": <int>,
  "num_movies": <int>,
  "num_train": <int>,
  "num_val": <int>
}
```

- All float values must be rounded to 4 decimal places.
- `top5_recommendations_user0` must contain exactly 5 entries, sorted by `predicted_rating` descending.
- `movie_id` in the top-5 list refers to the original MovieLens movie ID (not the re-indexed ID).

### Constraints

- The final `val_rmse` must be below `1.0`.
- `precision_at_10` and `recall_at_10` must each be non-negative floats between 0 and 1.
- `/app/best_model.pt` must exist and be loadable via `torch.load()`.
- The entire pipeline (download, train, evaluate, output) must be runnable via `python /app/main.py`.
