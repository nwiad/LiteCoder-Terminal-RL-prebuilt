#!/usr/bin/env python3
"""Train BERTopic model on synthetic CS paper abstracts."""
import json
import os
import numpy as np

from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer


def main():
    os.makedirs("/app/output/model", exist_ok=True)

    # Load dataset
    with open("/app/data/abstracts.json", "r") as f:
        data = json.load(f)

    docs = [item["abstract"] for item in data]
    print(f"Loaded {len(docs)} documents")

    # Configure components for CPU
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

    umap_model = UMAP(
        n_components=5,
        n_neighbors=15,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
        low_memory=True,
    )

    hdbscan_model = HDBSCAN(
        min_cluster_size=10,
        min_samples=5,
        metric="euclidean",
        prediction_data=True,
    )

    vectorizer_model = CountVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
    )

    # Build BERTopic model
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        top_n_words=10,
        verbose=True,
        calculate_probabilities=True,
    )

    # Fit the model
    topics, probs = topic_model.fit_transform(docs)

    # Get topic info
    topic_info = topic_model.get_topic_info()
    print(f"\nTopic info:\n{topic_info}")

    # Count non-outlier topics (topic_id >= 0)
    non_outlier_topics = [t for t in set(topics) if t >= 0]
    num_topics = len(non_outlier_topics)
    print(f"\nDiscovered {num_topics} non-outlier topics")

    # If fewer than 3 topics, try reducing min_cluster_size
    if num_topics < 3:
        print("Too few topics found, retrying with min_cluster_size=5...")
        hdbscan_model2 = HDBSCAN(
            min_cluster_size=5,
            min_samples=3,
            metric="euclidean",
            prediction_data=True,
        )
        topic_model = BERTopic(
            embedding_model=embedding_model,
            umap_model=umap_model,
            hdbscan_model=hdbscan_model2,
            vectorizer_model=vectorizer_model,
            top_n_words=10,
            verbose=True,
            calculate_probabilities=True,
        )
        topics, probs = topic_model.fit_transform(docs)
        topic_info = topic_model.get_topic_info()
        non_outlier_topics = [t for t in set(topics) if t >= 0]
        num_topics = len(non_outlier_topics)
        print(f"After retry: {num_topics} non-outlier topics")

    # Build results
    all_topic_ids = sorted(set(topics))
    topics_list = []

    for tid in all_topic_ids:
        # Get document indices for this topic
        doc_indices = [i for i, t in enumerate(topics) if t == tid]
        count = len(doc_indices)

        # Get top words for this topic
        if tid == -1:
            # Outlier topic
            top_words = []
            try:
                topic_words = topic_model.get_topic(-1)
                if topic_words and isinstance(topic_words, list):
                    top_words = [w for w, _ in topic_words[:5]]
            except Exception:
                pass
        else:
            topic_words = topic_model.get_topic(tid)
            top_words = [w for w, _ in topic_words[:5]] if topic_words else []

        # Representative doc ids (up to 3)
        representative_doc_ids = doc_indices[:3]

        topics_list.append({
            "topic_id": int(tid),
            "count": count,
            "top_words": top_words,
            "representative_doc_ids": [int(x) for x in representative_doc_ids],
        })

    topic_assignments = [int(t) for t in topics]
    outlier_count = sum(1 for t in topics if t == -1)

    results = {
        "num_topics": num_topics,
        "topics": topics_list,
        "topic_assignments": topic_assignments,
        "outlier_count": outlier_count,
    }

    # Save results
    with open("/app/output/results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to /app/output/results.json")
    print(f"  num_topics: {num_topics}")
    print(f"  outlier_count: {outlier_count}")

    # Save model — try safetensors first, fall back to pickle-based save
    import shutil
    model_path = "/app/output/model"
    # Clean existing model dir to avoid conflicts
    if os.path.exists(model_path):
        shutil.rmtree(model_path)
    os.makedirs(model_path, exist_ok=True)

    try:
        topic_model.save(model_path, serialization="safetensors", save_ctfidf=True, save_embedding_model=embedding_model)
    except Exception as e1:
        print(f"safetensors save failed ({e1}), trying pickle serialization...")
        if os.path.exists(model_path):
            shutil.rmtree(model_path)
        os.makedirs(model_path, exist_ok=True)
        try:
            topic_model.save(model_path, serialization="pickle", save_ctfidf=True, save_embedding_model=embedding_model)
        except Exception as e2:
            print(f"pickle with embedding save failed ({e2}), saving without embedding model...")
            if os.path.exists(model_path):
                shutil.rmtree(model_path)
            os.makedirs(model_path, exist_ok=True)
            topic_model.save(model_path)
    print("Model saved to /app/output/model/")


if __name__ == "__main__":
    main()
