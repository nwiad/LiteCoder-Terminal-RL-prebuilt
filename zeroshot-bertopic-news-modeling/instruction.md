## Zero-shot Topic Modeling with Sentence Transformers & BERTopic

Build a zero-shot topic modeling pipeline that discovers and labels topics in news articles without pre-labeled training data, using BERTopic with Sentence Transformers.

### Technical Requirements

- Language: Python 3.x
- Core libraries: `bertopic`, `sentence-transformers`, `scikit-learn`, `numpy`
- Entry script: `/app/solution.py` — running `python solution.py` must execute the full pipeline and produce all output files.

### Pipeline Specification

1. **Data Preparation**: Load the 20 Newsgroups dataset from `sklearn.datasets.fetch_20newsgroups`. Use the `test` subset with the following 5 categories only: `rec.sport.baseball`, `sci.med`, `comp.graphics`, `talk.politics.guns`, `soc.religion.christian`. Remove headers, footers, and quotes (use `remove=('headers', 'footers', 'quotes')`). Write the prepared documents to `/app/documents.json` as a JSON array of strings.

2. **Zero-shot Topic Modeling**: Build a BERTopic zero-shot topic model using the following candidate topic labels (in this exact order):
   - `"Sports"`, `"Medicine & Health"`, `"Computer Graphics"`, `"Gun Policy & Politics"`, `"Religion & Christianity"`

   Use a Sentence Transformer embedding model (e.g., `all-MiniLM-L6-v2` or similar) for document embeddings.

3. **Document-Topic Mapping**: Assign each document a topic. Write the results to `/app/topic_assignments.json` as a JSON array of objects, each with:
   - `doc_index` (int): zero-based index of the document in the prepared corpus
   - `topic_id` (int): the assigned topic ID from BERTopic (note: -1 indicates outlier)
   - `topic_label` (string): the human-readable topic label assigned by the model

   Example:
   ```json
   [
     {"doc_index": 0, "topic_id": 1, "topic_label": "Medicine & Health"},
     {"doc_index": 1, "topic_id": -1, "topic_label": "Outlier"}
   ]
   ```

4. **Metrics & Summary**: Compute and write the following to `/app/metrics.json`:
   - `total_documents` (int): number of documents in the corpus
   - `num_topics` (int): number of discovered topics (excluding outlier topic -1)
   - `outlier_count` (int): number of documents assigned to topic -1
   - `outlier_ratio` (float): `outlier_count / total_documents`, rounded to 4 decimal places
   - `topic_distribution` (object): mapping from each topic label (string) to the count of documents assigned to it (int), including an `"Outlier"` key if outliers exist
   - `candidate_labels` (list of strings): the 5 candidate labels used

   Example:
   ```json
   {
     "total_documents": 500,
     "num_topics": 5,
     "outlier_count": 23,
     "outlier_ratio": 0.046,
     "topic_distribution": {"Sports": 120, "Medicine & Health": 95, "Outlier": 23},
     "candidate_labels": ["Sports", "Medicine & Health", "Computer Graphics", "Gun Policy & Politics", "Religion & Christianity"]
   }
   ```

5. **Model Saving**: Save the trained BERTopic model to the directory `/app/saved_model/` using BERTopic's built-in serialization. The directory must exist after execution.

### Output Files Summary

| File | Format |
|---|---|
| `/app/documents.json` | JSON array of strings |
| `/app/topic_assignments.json` | JSON array of objects |
| `/app/metrics.json` | JSON object |
| `/app/saved_model/` | BERTopic serialized model directory |

### Constraints

- The pipeline must run end-to-end via `python solution.py` with no interactive input.
- All JSON output files must be valid, parseable JSON with UTF-8 encoding.
- `topic_assignments.json` must contain exactly one entry per document (length equals `total_documents` in metrics).
- `num_topics` in metrics must be greater than 0.
- `outlier_ratio` must be between 0.0 and 1.0 inclusive.
- The sum of all values in `topic_distribution` must equal `total_documents`.
