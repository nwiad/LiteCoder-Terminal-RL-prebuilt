## News Headline Analyzer

Build a Python system that ingests news headlines from a JSON file, performs sentiment analysis and named-entity recognition (NER) using HuggingFace transformer models, ranks stories by criticality, stores everything in SQLite, and serves the top-3 critical stories via a Flask web dashboard.

### Technical Requirements

- Language: Python 3
- Dependencies: `transformers`, `torch`, `flask`, `sqlite3` (stdlib)
- All file paths are relative to `/app`

### Input

File: `/app/headlines.json`

A JSON array of headline objects. Example:

```json
[
  {
    "id": "h001",
    "title": "Federal Reserve Raises Interest Rates by 0.5%",
    "source": "Reuters",
    "published_at": "2025-06-15T08:30:00Z"
  },
  {
    "id": "h002",
    "title": "Massive Earthquake Strikes Southern California",
    "source": "AP News",
    "published_at": "2025-06-15T09:00:00Z"
  }
]
```

Each object has fields: `id` (string, unique), `title` (string), `source` (string), `published_at` (ISO 8601 string).

### Modules to Implement

#### 1. `ingest.py`

- Read `/app/headlines.json` and insert all headlines into a SQLite database at `/app/news.db`.
- Table name: `headlines`
- Schema: `id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT, published_at TEXT, processed INTEGER DEFAULT 0`
- Duplicate `id` values must be skipped (no error raised).
- Runnable as: `python ingest.py`

#### 2. `nlpipe.py`

- Read all rows from `headlines` where `processed = 0`.
- For each headline title, run:
  - Sentiment analysis using the HuggingFace pipeline with model `cardiffnlp/twitter-roberta-base-sentiment-latest` (task `"sentiment-analysis"`). Record the label (one of `positive`, `negative`, `neutral`) and its confidence score (float 0–1).
  - Named-entity recognition using the HuggingFace pipeline with model `dslim/bert-base-NER` (task `"ner"`, `aggregation_strategy="simple"`). Record the list of unique entity strings extracted (deduplicated, original casing preserved, stripped of leading/trailing whitespace).
- Write results into a table `analysis` in `/app/news.db`.
- Schema: `headline_id TEXT PRIMARY KEY REFERENCES headlines(id), sentiment_label TEXT NOT NULL, sentiment_score REAL NOT NULL, entities TEXT NOT NULL, entity_count INTEGER NOT NULL`
  - `entities`: a JSON-encoded array of unique entity strings, e.g. `["Federal Reserve", "California"]`
  - `entity_count`: the length of that array
- After writing analysis, set `processed = 1` on the corresponding `headlines` row.
- Runnable as: `python nlpipe.py`

#### 3. `rank.py`

- Read all rows from `analysis` joined with `headlines`.
- Compute a criticality score for each headline: `score = 0.6 * neg_score + 0.4 * entity_count_norm`
  - `neg_score`: if `sentiment_label` is `"negative"`, use `sentiment_score`; otherwise use `0.0`.
  - `entity_count_norm`: `entity_count / max_entity_count` across all rows (if `max_entity_count` is 0, use 0.0).
- Write results into a table `rankings` in `/app/news.db`.
- Schema: `headline_id TEXT PRIMARY KEY REFERENCES headlines(id), score REAL NOT NULL, is_critical INTEGER NOT NULL`
- Mark the top 3 headlines by score as critical (`is_critical = 1`). All others get `is_critical = 0`. Ties are broken by `published_at` descending (more recent first).
- If there are 3 or fewer total headlines, mark all as critical.
- Runnable as: `python rank.py`

#### 4. `dashboard.py`

- A Flask application serving on `0.0.0.0:5000`.
- Route `GET /`: returns an HTML page containing a `<table>` with columns: Rank, Title, Source, Sentiment, Score. The table displays only the critical stories (where `is_critical = 1`), ordered by `score` descending.
- Route `GET /api/critical`: returns a JSON response — an array of objects with keys `headline_id`, `title`, `source`, `sentiment_label`, `score`, `is_critical`, ordered by `score` descending. Only critical stories are included.
- Runnable as: `python dashboard.py`

### Output

After running `ingest.py`, `nlpipe.py`, and `rank.py` sequentially, the SQLite database `/app/news.db` must contain the three tables (`headlines`, `analysis`, `rankings`) with the schemas described above.

The Flask app (`dashboard.py`) must serve the critical stories at the routes specified.

### Additional Output

After running the pipeline, write `/app/output.json` at the end of `rank.py` containing the full ranked list (all headlines, not just critical), sorted by score descending:

```json
[
  {
    "headline_id": "h002",
    "title": "Massive Earthquake Strikes Southern California",
    "source": "AP News",
    "sentiment_label": "negative",
    "sentiment_score": 0.92,
    "entities": ["Southern California"],
    "entity_count": 1,
    "score": 0.752,
    "is_critical": true
  }
]
```

Each object includes: `headline_id`, `title`, `source`, `sentiment_label`, `sentiment_score` (float, rounded to 4 decimal places), `entities` (array of strings), `entity_count` (integer), `score` (float, rounded to 4 decimal places), `is_critical` (boolean).
