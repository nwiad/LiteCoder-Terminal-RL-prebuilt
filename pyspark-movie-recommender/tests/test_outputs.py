import os
import json
import pandas as pd
import pyarrow.parquet as pq

def test_output_file_exists():
    """Test that the recommendations.parquet file exists"""
    assert os.path.exists("/app/recommendations.parquet"), "recommendations.parquet file not found at /app/"

def test_output_is_parquet_directory():
    """Test that recommendations.parquet is a valid Parquet directory"""
    assert os.path.isdir("/app/recommendations.parquet"), "recommendations.parquet should be a directory containing Parquet files"

    # Check for at least one parquet file inside
    parquet_files = [f for f in os.listdir("/app/recommendations.parquet") if f.endswith(".parquet")]
    assert len(parquet_files) > 0, "No .parquet files found in recommendations.parquet directory"

def test_schema_structure():
    """Test that the Parquet file has the correct schema"""
    df = pd.read_parquet("/app/recommendations.parquet")

    # Check required columns exist
    assert "userId" in df.columns, "Missing 'userId' column"
    assert "recommendations" in df.columns, "Missing 'recommendations' column"

    # Check that there are only these two columns
    assert len(df.columns) == 2, f"Expected 2 columns, found {len(df.columns)}: {df.columns.tolist()}"

def test_userid_type():
    """Test that userId is integer type"""
    df = pd.read_parquet("/app/recommendations.parquet")
    assert pd.api.types.is_integer_dtype(df["userId"]), f"userId should be integer type, got {df['userId'].dtype}"

def test_recommendations_is_array():
    """Test that recommendations column contains arrays/lists"""
    df = pd.read_parquet("/app/recommendations.parquet")

    # Check that recommendations is an array-like structure
    first_rec = df["recommendations"].iloc[0]
    assert isinstance(first_rec, (list, tuple)), f"recommendations should be array/list, got {type(first_rec)}"

def test_exactly_five_recommendations_per_user():
    """Test that each user has exactly 5 recommendations"""
    df = pd.read_parquet("/app/recommendations.parquet")

    for idx, row in df.iterrows():
        user_id = row["userId"]
        recs = row["recommendations"]
        assert len(recs) == 5, f"User {user_id} has {len(recs)} recommendations, expected exactly 5"

def test_recommendation_struct_fields():
    """Test that each recommendation has movieId, title, and rating fields"""
    df = pd.read_parquet("/app/recommendations.parquet")

    for idx, row in df.iterrows():
        user_id = row["userId"]
        recs = row["recommendations"]

        for i, rec in enumerate(recs):
            assert isinstance(rec, dict), f"User {user_id} recommendation {i} should be a struct/dict, got {type(rec)}"
            assert "movieId" in rec, f"User {user_id} recommendation {i} missing 'movieId' field"
            assert "title" in rec, f"User {user_id} recommendation {i} missing 'title' field"
            assert "rating" in rec, f"User {user_id} recommendation {i} missing 'rating' field"

            # Check that there are exactly these 3 fields
            assert len(rec) == 3, f"User {user_id} recommendation {i} should have exactly 3 fields, got {len(rec)}: {list(rec.keys())}"

def test_recommendation_field_types():
    """Test that recommendation fields have correct types"""
    df = pd.read_parquet("/app/recommendations.parquet")

    for idx, row in df.iterrows():
        user_id = row["userId"]
        recs = row["recommendations"]

        for i, rec in enumerate(recs):
            # Check movieId is integer
            assert isinstance(rec["movieId"], (int, pd.Int64Dtype)), f"User {user_id} rec {i}: movieId should be integer, got {type(rec['movieId'])}"

            # Check title is string
            assert isinstance(rec["title"], str), f"User {user_id} rec {i}: title should be string, got {type(rec['title'])}"

            # Check rating is float
            assert isinstance(rec["rating"], (float, int)), f"User {user_id} rec {i}: rating should be float, got {type(rec['rating'])}"

def test_recommendations_sorted_descending():
    """Test that recommendations are sorted by rating in descending order"""
    df = pd.read_parquet("/app/recommendations.parquet")

    for idx, row in df.iterrows():
        user_id = row["userId"]
        recs = row["recommendations"]

        ratings = [rec["rating"] for rec in recs]
        sorted_ratings = sorted(ratings, reverse=True)

        assert ratings == sorted_ratings, f"User {user_id} recommendations not sorted by rating descending: {ratings}"

def test_movie_titles_not_empty():
    """Test that movie titles are not empty strings"""
    df = pd.read_parquet("/app/recommendations.parquet")

    for idx, row in df.iterrows():
        user_id = row["userId"]
        recs = row["recommendations"]

        for i, rec in enumerate(recs):
            title = rec["title"]
            assert title is not None and len(title.strip()) > 0, f"User {user_id} rec {i}: title is empty or None"

def test_movie_ids_positive():
    """Test that all movieId values are positive integers"""
    df = pd.read_parquet("/app/recommendations.parquet")

    for idx, row in df.iterrows():
        user_id = row["userId"]
        recs = row["recommendations"]

        for i, rec in enumerate(recs):
            movie_id = rec["movieId"]
            assert movie_id > 0, f"User {user_id} rec {i}: movieId should be positive, got {movie_id}"

def test_predicted_ratings_reasonable():
    """Test that predicted ratings are in a reasonable range"""
    df = pd.read_parquet("/app/recommendations.parquet")

    for idx, row in df.iterrows():
        user_id = row["userId"]
        recs = row["recommendations"]

        for i, rec in enumerate(recs):
            rating = rec["rating"]
            # ALS can predict outside 0-5 range, but should be somewhat reasonable
            assert -10 <= rating <= 15, f"User {user_id} rec {i}: rating {rating} is unreasonably out of range"

def test_no_duplicate_movies_per_user():
    """Test that each user doesn't have duplicate movie recommendations"""
    df = pd.read_parquet("/app/recommendations.parquet")

    for idx, row in df.iterrows():
        user_id = row["userId"]
        recs = row["recommendations"]

        movie_ids = [rec["movieId"] for rec in recs]
        unique_movie_ids = set(movie_ids)

        assert len(movie_ids) == len(unique_movie_ids), f"User {user_id} has duplicate movie recommendations: {movie_ids}"

def test_all_users_have_recommendations():
    """Test that all users from the original dataset have recommendations"""
    # Load original ratings to get user count
    ratings_df = pd.read_csv("/app/ratings.csv")
    unique_users_in_ratings = ratings_df["userId"].nunique()

    # Load recommendations
    recs_df = pd.read_parquet("/app/recommendations.parquet")
    unique_users_in_recs = recs_df["userId"].nunique()

    # Should have recommendations for all users (or close to all if some users have cold start issues)
    # Allow for some users to be missing due to cold start, but should be at least 90% coverage
    coverage = unique_users_in_recs / unique_users_in_ratings
    assert coverage >= 0.9, f"Only {unique_users_in_recs}/{unique_users_in_ratings} users have recommendations ({coverage:.1%})"

def test_model_saved():
    """Test that the ALS model was saved to /app/als_model"""
    assert os.path.exists("/app/als_model"), "ALS model not saved to /app/als_model"
    assert os.path.isdir("/app/als_model"), "/app/als_model should be a directory"

def test_recommendations_exclude_rated_movies():
    """Test that recommendations don't include movies the user has already rated"""
    # Load original ratings
    ratings_df = pd.read_csv("/app/ratings.csv")
    user_rated_movies = ratings_df.groupby("userId")["movieId"].apply(set).to_dict()

    # Load recommendations
    recs_df = pd.read_parquet("/app/recommendations.parquet")

    # Sample check on first 10 users
    for idx, row in recs_df.head(10).iterrows():
        user_id = row["userId"]
        recs = row["recommendations"]

        if user_id in user_rated_movies:
            rated_movies = user_rated_movies[user_id]
            recommended_movies = {rec["movieId"] for rec in recs}

            overlap = rated_movies & recommended_movies
            assert len(overlap) == 0, f"User {user_id} has recommendations for already-rated movies: {overlap}"

def test_not_all_same_recommendations():
    """Test that not all users get identical recommendations (sanity check for personalization)"""
    df = pd.read_parquet("/app/recommendations.parquet")

    # Get movie IDs for first 5 users
    if len(df) >= 5:
        rec_sets = []
        for idx, row in df.head(5).iterrows():
            movie_ids = tuple(sorted([rec["movieId"] for rec in row["recommendations"]]))
            rec_sets.append(movie_ids)

        # At least 2 users should have different recommendations
        unique_rec_sets = set(rec_sets)
        assert len(unique_rec_sets) >= 2, "All users have identical recommendations - model may not be personalized"

def test_output_not_empty():
    """Test that the output file is not empty"""
    df = pd.read_parquet("/app/recommendations.parquet")
    assert len(df) > 0, "recommendations.parquet is empty"

def test_no_null_values():
    """Test that there are no null values in critical fields"""
    df = pd.read_parquet("/app/recommendations.parquet")

    assert df["userId"].notna().all(), "Found null values in userId column"
    assert df["recommendations"].notna().all(), "Found null values in recommendations column"

    # Check within recommendations array
    for idx, row in df.iterrows():
        user_id = row["userId"]
        recs = row["recommendations"]

        for i, rec in enumerate(recs):
            assert rec["movieId"] is not None, f"User {user_id} rec {i}: movieId is null"
            assert rec["title"] is not None, f"User {user_id} rec {i}: title is null"
            assert rec["rating"] is not None, f"User {user_id} rec {i}: rating is null"
