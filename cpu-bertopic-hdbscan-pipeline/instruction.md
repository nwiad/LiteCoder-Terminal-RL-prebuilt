## CPU-Optimized BERTopic Model with HDBSCAN Clustering

Build a BERTopic topic modeling pipeline that uses Hugging Face sentence-transformer embeddings and HDBSCAN clustering, running entirely on CPU, to organize synthetic computer science paper abstracts into coherent topics.

### Technical Requirements

- Language: Python 3.x
- Key libraries: `bertopic`, `hdbscan`, `sentence-transformers`, `scikit-learn`
- All scripts must be runnable on CPU only (no GPU/CUDA required).

### Files to Produce

| File | Purpose |
|---|---|
| `/app/generate_data.py` | Generate the synthetic dataset |
| `/app/data/abstracts.json` | Generated dataset |
| `/app/train.py` | Train the BERTopic model and produce all outputs |
| `/app/output/results.json` | Training results and topic info |
| `/app/output/model/` | Saved BERTopic model directory |
| `/app/predict.py` | Demo script for single-document inference |
| `/app/output/prediction.json` | Prediction output from demo script |

### Step 1 — Synthetic Dataset (`generate_data.py`)

Generate a synthetic dataset of computer science paper abstracts and write it to `/app/data/abstracts.json`.

Requirements:
- Produce exactly **200** abstracts.
- Each abstract must belong to one of at least **5** distinct CS sub-domains (e.g., machine learning, networking, databases, security, computer vision).
- Each abstract should be 40–120 words.
- Output JSON schema — a list of objects:

```json
[
  {
    "id": 0,
    "title": "string",
    "abstract": "string",
    "domain": "string"
  }
]
```

### Step 2 — Model Training (`train.py`)

Read `/app/data/abstracts.json`, train a BERTopic model, and write outputs.

Configuration constraints:
- Embedding model: use a lightweight sentence-transformer model (e.g., `all-MiniLM-L6-v2` or similar) configured for CPU.
- Dimensionality reduction: use UMAP with `n_components=5`.
- Clustering: use HDBSCAN with `min_cluster_size=10`.
- The model must discover **at least 3** non-outlier topics (topic label ≥ 0).

Output — `/app/output/results.json` must contain:

```json
{
  "num_topics": <int>,
  "topics": [
    {
      "topic_id": <int>,
      "count": <int>,
      "top_words": ["word1", "word2", "word3", "word4", "word5"],
      "representative_doc_ids": [<int>, ...]
    }
  ],
  "topic_assignments": [<int>, ...],
  "outlier_count": <int>
}
```

Field details:
- `num_topics`: total number of discovered topics excluding the outlier topic (-1).
- `topics`: one entry per discovered topic (including -1 for outliers). Each entry has the topic id, document count, top-5 representative words, and up to 3 representative document ids (by index in the input list).
- `topic_assignments`: list of length 200 mapping each document index to its assigned topic id.
- `outlier_count`: number of documents assigned to topic -1.

Save the trained model to `/app/output/model/` using BERTopic's built-in save method so it can be reloaded.

### Step 3 — Prediction Demo (`predict.py`)

Load the saved model from `/app/output/model/` and predict the topic for the following hard-coded input text:

```
Deep reinforcement learning has shown remarkable success in game playing and robotic control tasks, combining neural network function approximation with temporal difference learning methods.
```

Write the result to `/app/output/prediction.json`:

```json
{
  "input_text": "<the input string>",
  "predicted_topic": <int>,
  "topic_words": ["word1", "word2", ...],
  "all_topic_probabilities": { "<topic_id>": <float>, ... }
}
```

- `predicted_topic`: the integer topic id assigned.
- `topic_words`: top-5 words for the predicted topic.
- `all_topic_probabilities`: a mapping from topic id (string key) to probability (float value). If the model does not support probabilities, set this to an empty object `{}`.

### Execution Order

```bash
pip install bertopic sentence-transformers hdbscan umap-learn
python /app/generate_data.py
python /app/train.py
python /app/predict.py
```

Each script must be independently runnable in the order above and must exit with code 0 on success.
