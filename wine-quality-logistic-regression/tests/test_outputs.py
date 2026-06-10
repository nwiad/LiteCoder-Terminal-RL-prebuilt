import os
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


def test_model_file_exists():
    """Test that the model file exists at the expected location."""
    model_path = "/app/wine_logreg.pkl"
    assert os.path.exists(model_path), f"Model file not found at {model_path}"
    assert os.path.isfile(model_path), f"{model_path} is not a file"
    assert os.path.getsize(model_path) > 0, f"Model file at {model_path} is empty"


def test_model_is_loadable():
    """Test that the model file can be loaded with joblib."""
    model_path = "/app/wine_logreg.pkl"
    try:
        model = joblib.load(model_path)
    except Exception as e:
        raise AssertionError(f"Failed to load model with joblib: {e}")

    assert model is not None, "Loaded model is None"


def test_model_is_logistic_regression():
    """Test that the loaded model is a LogisticRegression instance."""
    model_path = "/app/wine_logreg.pkl"
    model = joblib.load(model_path)

    assert isinstance(model, LogisticRegression), \
        f"Model is not a LogisticRegression instance, got {type(model)}"


def test_model_is_trained():
    """Test that the model has been fitted (has coef_ and intercept_)."""
    model_path = "/app/wine_logreg.pkl"
    model = joblib.load(model_path)

    assert hasattr(model, 'coef_'), "Model does not have coef_ attribute (not fitted)"
    assert hasattr(model, 'intercept_'), "Model does not have intercept_ attribute (not fitted)"
    assert model.coef_ is not None, "Model coef_ is None"
    assert model.intercept_ is not None, "Model intercept_ is None"


def test_model_has_correct_number_of_features():
    """Test that the model was trained on 11 features (wine physicochemical properties)."""
    model_path = "/app/wine_logreg.pkl"
    model = joblib.load(model_path)

    n_features = model.coef_.shape[1]
    assert n_features == 11, \
        f"Model should have 11 features (wine properties), but has {n_features}"


def test_model_is_binary_classifier():
    """Test that the model is configured for binary classification."""
    model_path = "/app/wine_logreg.pkl"
    model = joblib.load(model_path)

    # LogisticRegression for binary classification has coef_ shape (1, n_features)
    assert model.coef_.shape[0] == 1, \
        f"Model should be binary classifier (coef_ shape[0] == 1), got shape {model.coef_.shape}"

    # Should have 2 classes
    assert hasattr(model, 'classes_'), "Model does not have classes_ attribute"
    assert len(model.classes_) == 2, \
        f"Model should have 2 classes for binary classification, got {len(model.classes_)}"


def test_model_can_predict():
    """Test that the model can make predictions on sample data."""
    model_path = "/app/wine_logreg.pkl"
    model = joblib.load(model_path)

    # Create sample data with 11 features (typical wine property ranges)
    sample_data = np.array([[
        7.4,    # fixed acidity
        0.7,    # volatile acidity
        0.0,    # citric acid
        1.9,    # residual sugar
        0.076,  # chlorides
        11.0,   # free sulfur dioxide
        34.0,   # total sulfur dioxide
        0.9978, # density
        3.51,   # pH
        0.56,   # sulphates
        9.4     # alcohol
    ]])

    try:
        predictions = model.predict(sample_data)
    except Exception as e:
        raise AssertionError(f"Model failed to make predictions: {e}")

    assert predictions is not None, "Predictions are None"
    assert len(predictions) == 1, f"Expected 1 prediction, got {len(predictions)}"
    assert predictions[0] in [0, 1], \
        f"Binary prediction should be 0 or 1, got {predictions[0]}"


def test_model_can_predict_proba():
    """Test that the model can output probability predictions."""
    model_path = "/app/wine_logreg.pkl"
    model = joblib.load(model_path)

    # Create sample data
    sample_data = np.array([[
        7.4, 0.7, 0.0, 1.9, 0.076, 11.0, 34.0, 0.9978, 3.51, 0.56, 9.4
    ]])

    try:
        probas = model.predict_proba(sample_data)
    except Exception as e:
        raise AssertionError(f"Model failed to predict probabilities: {e}")

    assert probas is not None, "Probability predictions are None"
    assert probas.shape == (1, 2), \
        f"Expected probability shape (1, 2), got {probas.shape}"

    # Probabilities should sum to 1
    assert np.isclose(probas.sum(), 1.0, atol=1e-6), \
        f"Probabilities should sum to 1, got {probas.sum()}"

    # Probabilities should be in [0, 1]
    assert np.all(probas >= 0) and np.all(probas <= 1), \
        "Probabilities should be between 0 and 1"


def test_model_coefficients_are_reasonable():
    """Test that model coefficients are non-zero and reasonable."""
    model_path = "/app/wine_logreg.pkl"
    model = joblib.load(model_path)

    coefficients = model.coef_[0]

    # At least some coefficients should be non-zero
    non_zero_count = np.count_nonzero(np.abs(coefficients) > 1e-6)
    assert non_zero_count > 0, "All coefficients are zero - model not properly trained"

    # Coefficients should be finite
    assert np.all(np.isfinite(coefficients)), "Model has non-finite coefficients"

    # Intercept should be finite
    assert np.isfinite(model.intercept_[0]), "Model has non-finite intercept"


def test_model_predictions_vary():
    """Test that the model produces different predictions for different inputs."""
    model_path = "/app/wine_logreg.pkl"
    model = joblib.load(model_path)

    # Create two very different wine samples
    low_quality_wine = np.array([[
        8.0, 1.2, 0.0, 2.0, 0.15, 5.0, 20.0, 0.999, 3.3, 0.4, 9.0
    ]])

    high_quality_wine = np.array([[
        7.0, 0.3, 0.5, 2.0, 0.05, 30.0, 100.0, 0.995, 3.3, 0.8, 12.5
    ]])

    probas_low = model.predict_proba(low_quality_wine)
    probas_high = model.predict_proba(high_quality_wine)

    # The model should produce different probability distributions
    # (not necessarily different predictions, but different probabilities)
    assert not np.allclose(probas_low, probas_high, atol=0.01), \
        "Model produces identical probabilities for very different inputs - likely not trained properly"


def test_model_handles_multiple_samples():
    """Test that the model can handle batch predictions."""
    model_path = "/app/wine_logreg.pkl"
    model = joblib.load(model_path)

    # Create 5 sample wines
    sample_data = np.array([
        [7.4, 0.7, 0.0, 1.9, 0.076, 11.0, 34.0, 0.9978, 3.51, 0.56, 9.4],
        [7.8, 0.88, 0.0, 2.6, 0.098, 25.0, 67.0, 0.9968, 3.20, 0.68, 9.8],
        [7.8, 0.76, 0.04, 2.3, 0.092, 15.0, 54.0, 0.9970, 3.26, 0.65, 9.8],
        [11.2, 0.28, 0.56, 1.9, 0.075, 17.0, 60.0, 0.9980, 3.16, 0.58, 9.8],
        [7.4, 0.59, 0.08, 4.4, 0.086, 6.0, 29.0, 0.9974, 3.38, 0.50, 9.0]
    ])

    predictions = model.predict(sample_data)
    probas = model.predict_proba(sample_data)

    assert len(predictions) == 5, f"Expected 5 predictions, got {len(predictions)}"
    assert probas.shape == (5, 2), f"Expected probability shape (5, 2), got {probas.shape}"
