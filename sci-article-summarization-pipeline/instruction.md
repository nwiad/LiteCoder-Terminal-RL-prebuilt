## Text Summarization Pipeline

Build a text summarization pipeline in Python that reads a collection of scientific article texts, splits them into chunks suitable for transformer-based models, generates summaries using a Hugging Face summarization model, and writes structured results to an output file.

### Technical Requirements

- Python 3.9+
- Libraries: `transformers`, `torch`, `nltk`, `pandas`
- Input file: `/app/input.json`
- Output file: `/app/output.json`

### Input Format

`/app/input.json` is a JSON array of article objects:

```json
[
  {
    "id": "article_001",
    "title": "Example Article Title",
    "text": "Full article text content here... (can be very long, up to 10000 words)"
  }
]
```

- The `text` field may contain multiple paragraphs separated by newline characters.
- The array may contain 1 to 50 articles.

### Pipeline Requirements

Implement a Python script `/app/summarize.py` that performs the following steps:

1. **Text Cleaning**: For each article's `text` field, remove excessive whitespace (collapse multiple spaces/newlines into single spaces), and strip leading/trailing whitespace.

2. **Text Chunking**: Split each cleaned article text into chunks of no more than 512 tokens (measured by whitespace-separated words). Chunks must not split mid-sentence — each chunk should end at a sentence boundary (period, question mark, or exclamation mark followed by a space or end of text). If a single sentence exceeds 512 tokens, it should be placed in its own chunk. Each article must produce at least one chunk.

3. **Summarization**: Use the Hugging Face `transformers` pipeline with the model `facebook/bart-large-cnn` to summarize each chunk. Set `max_length=130` and `min_length=30` for the summarization pipeline. Combine all chunk summaries for a single article into one final summary by joining them with a single space.

4. **Output**: Write results to `/app/output.json`.

### Output Format

`/app/output.json` must be a JSON array with one object per input article, in the same order as the input:

```json
[
  {
    "id": "article_001",
    "title": "Example Article Title",
    "num_chunks": 3,
    "summary": "Combined summary text from all chunks."
  }
]
```

- `id`: copied from input.
- `title`: copied from input.
- `num_chunks`: integer, the number of chunks the article was split into.
- `summary`: non-empty string, the concatenated summary of all chunks.

### Edge Cases

- If the input array is empty (`[]`), output an empty array `[]`.
- If an article's `text` field is empty or contains only whitespace, set `num_chunks` to `0` and `summary` to an empty string `""`.
- The pipeline must handle articles with very short text (a single sentence) as well as very long text (10000+ words).
