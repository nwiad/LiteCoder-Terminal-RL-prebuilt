#!/usr/bin/env python3
"""Load saved BERTopic model and predict topic for a hard-coded input text."""
import json
import os
import numpy as np

from bertopic import BERTopic
from sentence_transformers import SentenceTransformer


def main():
    input_text = (
        "Deep reinforcement learning has shown remarkable success in game playing "
        "and robotic control tasks, combining neural network function approximation "
        "with temporal difference learning methods."
    )

    print("Loading model from /app/output/model/ ...")
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    topic_model = BERTopic.load("/app/output/model/", embedding_model=embedding_model)
    print("Model loaded successfully.")

    # Predict
    topics, probs = topic_model.transform([input_text])
    predicted_topic = int(topics[0])

    # Get top words for predicted topic
    topic_words_raw = topic_model.get_topic(predicted_topic)
    if topic_words_raw and isinstance(topic_words_raw, list):
        topic_words = [w for w, _ in topic_words_raw[:5]]
    else:
        topic_words = []

    # Build probability mapping
    all_topic_probabilities = {}
    if probs is not None:
        try:
            prob_array = np.array(probs[0])
            # probs shape depends on BERTopic version
            # For calculate_probabilities=True, probs[0] is array of probabilities per topic
            topic_info = topic_model.get_topic_info()
            non_outlier_topics = sorted([t for t in topic_info["Topic"].tolist() if t >= 0])

            if len(prob_array.shape) == 0:
                # Single value - just the predicted topic probability
                all_topic_probabilities[str(predicted_topic)] = float(prob_array)
            elif len(prob_array) == len(non_outlier_topics):
                for i, tid in enumerate(non_outlier_topics):
                    all_topic_probabilities[str(tid)] = round(float(prob_array[i]), 6)
            elif len(prob_array) > 0:
                # Fallback: map available probabilities
                for i, p in enumerate(prob_array):
                    if i < len(non_outlier_topics):
                        all_topic_probabilities[str(non_outlier_topics[i])] = round(float(p), 6)
        except Exception as e:
            print(f"Warning: Could not extract probabilities: {e}")
            all_topic_probabilities = {}

    result = {
        "input_text": input_text,
        "predicted_topic": predicted_topic,
        "topic_words": topic_words,
        "all_topic_probabilities": all_topic_probabilities,
    }

    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/prediction.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"Predicted topic: {predicted_topic}")
    print(f"Topic words: {topic_words}")
    print(f"Result saved to /app/output/prediction.json")


if __name__ == "__main__":
    main()
