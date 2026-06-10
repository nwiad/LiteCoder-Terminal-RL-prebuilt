## Implementing TextRank for Extractive Summarization

Build a TextRank-based extractive summarizer in pure Python that takes a news article as input and outputs the top-N most relevant sentences. Only the Python standard library and `scipy` (specifically `scipy.sparse`) are allowed — no external NLP libraries (no NLTK, spaCy, gensim, sklearn, etc.).

### Technical Requirements

- Language: Python 3
- Allowed dependencies: Python standard library + `scipy`
- Entry point: `python textrank.py <input_file> <top_k>`
  - `<input_file>`: path to a plain-text article file
  - `<top_k>`: integer, number of top sentences to extract
- Input file: `/app/article.txt` (plain UTF-8 text, one or more paragraphs)
- Output file: `/app/output.json`

### Pipeline Specification

1. **Sentence Tokenization**: Split the article text into sentences using regex. A sentence boundary is defined by `.`, `!`, or `?` followed by whitespace or end-of-string. Each resulting sentence must be stripped of leading/trailing whitespace. Empty sentences (after stripping) must be discarded.

2. **TF-IDF Vectorization**: For each sentence, compute a TF-IDF vector. Tokenize words by extracting sequences of alphanumeric characters (case-insensitive, lowercased). TF is the raw term frequency within a sentence. IDF is computed as `log(N / df)` where `N` is the total number of sentences and `df` is the number of sentences containing the term. Use Python's `math.log` (natural logarithm).

3. **Similarity Matrix**: Compute pairwise cosine similarity between all sentence TF-IDF vectors. A sentence's similarity with itself must be set to `0.0` (no self-loops).

4. **PageRank**: Run the PageRank algorithm on the similarity matrix to score each sentence. Use a damping factor of `0.85` and iterate until convergence (L1 norm of score change < `1e-6`) or a maximum of `100` iterations.

5. **Top-K Selection**: Select the top-k sentences by PageRank score. If there is a tie in scores, prefer the sentence that appears earlier in the document. Output the selected sentences in their original document order (not ranked by score).

### Output Format

Write a JSON file to `/app/output.json` with the following structure:

```json
{
  "num_sentences": <int>,
  "top_k": <int>,
  "sentences": [
    {
      "index": <int>,
      "score": <float>,
      "text": "<string>"
    }
  ]
}
```

- `num_sentences`: total number of sentences detected in the article
- `top_k`: the k value used
- `sentences`: array of selected sentences, ordered by their original position in the document
  - `index`: 0-based position of the sentence in the original sentence list
  - `score`: PageRank score (floating point, not rounded)
  - `text`: the original sentence text (stripped)

### CLI Behavior

- When invoked as `python textrank.py /app/article.txt 3`, the script must read the article, run the full pipeline, and write `/app/output.json`.
- If `<top_k>` exceeds the number of sentences, return all sentences (sorted by original order).
- The script must also print the final summary sentences (one per line, in document order) to stdout.
