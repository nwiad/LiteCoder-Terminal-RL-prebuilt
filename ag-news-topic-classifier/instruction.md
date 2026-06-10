## Scalable News Article Topic Classifier

Build a CPU-only, end-to-end text-classification pipeline that trains a model on the AG News dataset, evaluates it on the held-out test set, persists artifacts, and serves batch predictions via a CLI tool. Everything must be implemented in Python.

### Technical Requirements

- Language: Python 3.x
- Allowed libraries: scikit-learn, pandas, joblib, click (and their dependencies). No deep learning frameworks (PyTorch, TensorFlow, etc.).
- All code must run on CPU only.

### Project Structure

```
/app/
├── requirements.txt
├── train.py
├── predict.py
├── model/
│   ├── model.joblib
│   └── vectorizer.joblib
└── data/
    ├── train.csv
    └── test.csv
```

### Dataset

The AG News dataset must be downloaded and stored under `/app/data/`. The dataset has 4 classes:

| Label | Topic         |
|-------|---------------|
| 1     | World         |
| 2     | Sports        |
| 3     | Business      |
| 4     | Sci/Tech      |

Each CSV row contains: `label`, `title`, `description`. The train split has 120,000 samples and the test split has 7,600 samples.

### Step 1: Training (`/app/train.py`)

Running `python /app/train.py` must:

1. Load the AG News train and test CSVs from `/app/data/`.
2. Combine `title` and `description` into a single text field for each sample.
3. Build a TF-IDF vectorizer pipeline and train a LinearSVC classifier.
4. Set `random_state=42` wherever randomness is involved for reproducibility.
5. Evaluate on the test set and print a JSON summary to stdout with the following exact structure:

```json
{
  "test_accuracy": 0.XX,
  "num_train_samples": 120000,
  "num_test_samples": 7600,
  "num_classes": 4,
  "classes": ["World", "Sports", "Business", "Sci/Tech"]
}
```

- `test_accuracy` must be a float rounded to 4 decimal places.
- The model must achieve a `test_accuracy` of at least **0.88** on the AG News test set.

6. Save the trained model to `/app/model/model.joblib` and the TF-IDF vectorizer to `/app/model/vectorizer.joblib`.

### Step 2: Prediction CLI (`/app/predict.py`)

Running the CLI must load the persisted artifacts from `/app/model/` and classify input text.

**Usage:**

```
python /app/predict.py --input /app/input.json --output /app/output.json
```

**Input format** (`/app/input.json`): A JSON array of objects, each with an `"id"` (integer) and `"text"` (string):

```json
[
  {"id": 1, "text": "NASA launches new Mars rover mission"},
  {"id": 2, "text": "Stock market hits record high amid economic growth"},
  {"id": 3, "text": "World Cup final draws millions of viewers worldwide"}
]
```

**Output format** (`/app/output.json`): A JSON array of objects with `"id"`, `"predicted_label"` (integer 1-4), and `"predicted_topic"` (string from the label mapping above):

```json
[
  {"id": 1, "predicted_label": 4, "predicted_topic": "Sci/Tech"},
  {"id": 2, "predicted_label": 3, "predicted_topic": "Business"},
  {"id": 3, "predicted_label": 2, "predicted_topic": "Sports"}
]
```

- The output array must preserve the same order as the input array.
- If the input file is empty (`[]`), the output must also be `[]`.

### requirements.txt

`/app/requirements.txt` must list all required pip packages, one per line.
