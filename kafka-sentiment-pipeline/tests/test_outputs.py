import os
import json
import pickle
import pytest


def test_model_file_exists():
    """Test that the trained model file exists"""
    assert os.path.exists('/app/model.pkl'), "Model file /app/model.pkl does not exist"


def test_model_file_not_empty():
    """Test that the model file is not empty"""
    assert os.path.getsize('/app/model.pkl') > 0, "Model file is empty"


def test_model_is_valid_pickle():
    """Test that the model file is a valid pickle file"""
    try:
        with open('/app/model.pkl', 'rb') as f:
            model = pickle.load(f)
        assert model is not None, "Model is None"
    except Exception as e:
        pytest.fail(f"Failed to load model as pickle: {e}")


def test_model_has_predict_method():
    """Test that the loaded model has a predict method"""
    with open('/app/model.pkl', 'rb') as f:
        model = pickle.load(f)
    assert hasattr(model, 'predict'), "Model does not have predict method"


def test_model_can_classify_text():
    """Test that the model can actually classify text and return valid sentiments"""
    with open('/app/model.pkl', 'rb') as f:
        model = pickle.load(f)

    # Test with sample texts
    test_texts = [
        "I love this product!",
        "This is terrible.",
        "It's okay, nothing special."
    ]

    valid_sentiments = {'positive', 'negative', 'neutral'}

    for text in test_texts:
        prediction = model.predict([text])
        assert len(prediction) == 1, f"Model should return exactly one prediction for one input"
        assert prediction[0] in valid_sentiments, f"Model returned invalid sentiment: {prediction[0]}"


def test_model_not_hardcoded():
    """Test that the model is not just returning hardcoded values"""
    with open('/app/model.pkl', 'rb') as f:
        model = pickle.load(f)

    # Test with clearly positive and negative texts
    positive_texts = [
        "Absolutely amazing experience!",
        "Fantastic quality and fast delivery!",
        "Highly recommend to everyone!"
    ]

    negative_texts = [
        "Worst purchase ever.",
        "Disappointed with the service.",
        "Terrible quality and slow shipping."
    ]

    positive_predictions = [model.predict([text])[0] for text in positive_texts]
    negative_predictions = [model.predict([text])[0] for text in negative_texts]

    # At least 2 out of 3 positive texts should be classified as positive
    positive_count = sum(1 for p in positive_predictions if p == 'positive')
    assert positive_count >= 2, f"Model failed to classify positive texts correctly: {positive_predictions}"

    # At least 2 out of 3 negative texts should be classified as negative
    negative_count = sum(1 for p in negative_predictions if p == 'negative')
    assert negative_count >= 2, f"Model failed to classify negative texts correctly: {negative_predictions}"


def test_config_file_exists():
    """Test that config.py exists"""
    assert os.path.exists('/app/config.py'), "config.py does not exist"


def test_producer_file_exists():
    """Test that producer.py exists"""
    assert os.path.exists('/app/producer.py'), "producer.py does not exist"


def test_consumer_file_exists():
    """Test that consumer.py exists"""
    assert os.path.exists('/app/consumer.py'), "consumer.py does not exist"


def test_input_json_exists():
    """Test that input.json exists"""
    assert os.path.exists('/app/input.json'), "input.json does not exist"


def test_input_json_valid():
    """Test that input.json is valid JSON with expected structure"""
    with open('/app/input.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data, list), "input.json should contain a list"
    assert len(data) > 0, "input.json should not be empty"

    for item in data:
        assert isinstance(item, dict), "Each item in input.json should be a dict"
        assert 'text' in item, "Each item should have a 'text' field"


def test_model_trained_on_training_data():
    """Test that the model was actually trained (not just an empty pipeline)"""
    with open('/app/model.pkl', 'rb') as f:
        model = pickle.load(f)

    # Check if it's a pipeline (expected structure)
    from sklearn.pipeline import Pipeline
    assert isinstance(model, Pipeline), "Model should be a sklearn Pipeline"

    # Check that the pipeline has been fitted (has vocabulary)
    assert hasattr(model.named_steps['tfidf'], 'vocabulary_'), "TF-IDF vectorizer has not been fitted"
    assert len(model.named_steps['tfidf'].vocabulary_) > 0, "TF-IDF vocabulary is empty"


def test_model_sentiment_distribution():
    """Test that the model can predict all three sentiment classes (not biased to one)"""
    with open('/app/model.pkl', 'rb') as f:
        model = pickle.load(f)

    # Load input messages
    with open('/app/input.json', 'r') as f:
        messages = json.load(f)

    texts = [msg['text'] for msg in messages]
    predictions = model.predict(texts)

    unique_sentiments = set(predictions)

    # The model should predict at least 2 different sentiment classes
    # (to avoid a trivial model that always returns the same sentiment)
    assert len(unique_sentiments) >= 2, f"Model only predicts {unique_sentiments}, seems biased or hardcoded"


def test_all_input_messages_have_predictions():
    """Test that we can get predictions for all input messages"""
    with open('/app/model.pkl', 'rb') as f:
        model = pickle.load(f)

    with open('/app/input.json', 'r') as f:
        messages = json.load(f)

    assert len(messages) == 10, f"Expected 10 input messages, found {len(messages)}"

    for msg in messages:
        text = msg['text']
        prediction = model.predict([text])
        assert len(prediction) == 1, f"Expected 1 prediction for '{text}'"
        assert prediction[0] in {'positive', 'negative', 'neutral'}, f"Invalid sentiment for '{text}': {prediction[0]}"


def test_config_has_required_variables():
    """Test that config.py defines required configuration variables"""
    import sys
    sys.path.insert(0, '/app')
    import config

    assert hasattr(config, 'KAFKA_BROKER'), "config.py missing KAFKA_BROKER"
    assert hasattr(config, 'INPUT_TOPIC'), "config.py missing INPUT_TOPIC"
    assert hasattr(config, 'OUTPUT_TOPIC'), "config.py missing OUTPUT_TOPIC"
    assert hasattr(config, 'MODEL_PATH'), "config.py missing MODEL_PATH"


def test_producer_imports_successfully():
    """Test that producer.py can be imported without errors"""
    import sys
    sys.path.insert(0, '/app')
    try:
        import producer
    except Exception as e:
        pytest.fail(f"Failed to import producer.py: {e}")


def test_consumer_imports_successfully():
    """Test that consumer.py can be imported without errors"""
    import sys
    sys.path.insert(0, '/app')
    try:
        import consumer
    except Exception as e:
        pytest.fail(f"Failed to import consumer.py: {e}")


def test_model_predictions_match_expected_sentiments():
    """Test that model predictions are reasonable for the input messages"""
    with open('/app/model.pkl', 'rb') as f:
        model = pickle.load(f)

    # Expected sentiments based on the input.json content
    expected_mappings = {
        "I love this product!": "positive",
        "This is terrible.": "negative",
        "It's okay, nothing special.": "neutral",
        "Absolutely amazing experience!": "positive",
        "Worst purchase ever.": "negative",
        "Pretty average, meets expectations.": "neutral",
        "Fantastic quality and fast delivery!": "positive",
        "Disappointed with the service.": "negative",
        "Not bad, could be better.": "neutral",
        "Highly recommend to everyone!": "positive"
    }

    correct_predictions = 0
    total_predictions = len(expected_mappings)

    for text, expected_sentiment in expected_mappings.items():
        prediction = model.predict([text])[0]
        if prediction == expected_sentiment:
            correct_predictions += 1

    # Model should get at least 70% correct (7 out of 10)
    accuracy = correct_predictions / total_predictions
    assert accuracy >= 0.7, f"Model accuracy too low: {accuracy:.2%} ({correct_predictions}/{total_predictions} correct)"
