## Text Processing with Unix Utilities

Build a shell-based pipeline that cleans and tokenizes the Complete Works of William Shakespeare and produces unigram and bigram frequency tables, using only standard Unix utilities (e.g., `sed`, `awk`, `tr`, `sort`, `uniq`, `grep`, `cut`, `paste`). No Python, Perl, or other scripting languages are allowed — the entire pipeline must be pure shell + coreutils.

### Input

- `/app/shakespeare.txt` — the raw Project Gutenberg plain-text file of the Complete Works of William Shakespeare. This file is already provided; do not download it.

### Output Files

All output files must be produced by running a single script:

1. `/app/cleaned.txt` — the cleaned corpus, one lowercase word per line (no blank lines).
2. `/app/unigrams.tsv` — unigram frequency table.
3. `/app/bigrams.tsv` — bigram frequency table.
4. `/app/pipeline.sh` — the reproducible shell script that generates all of the above.

### Text Cleaning Rules (for `cleaned.txt`)

1. **Strip Gutenberg boilerplate.** Remove everything before the first line that starts with `*** START OF` (inclusive) and everything from the first line that starts with `*** END OF` (inclusive) onward.
2. **Lowercase** all text.
3. **Remove punctuation.** Delete all characters that are not lowercase letters (a-z), digits (0-9), or whitespace.
4. **Tokenize.** Split on whitespace so that each line contains exactly one token (word).
5. **Remove blank lines.** The final file must contain no empty lines.

### Unigram Table (`/app/unigrams.tsv`)

- Tab-separated, two columns: `word` and `count`.
- Sorted by `count` in descending numeric order. Ties are broken alphabetically (ascending) by `word`.
- No header row.
- Example rows (illustrative, not exact):
  ```
  the	27378
  and	26082
  i	22538
  ```

### Bigram Table (`/app/bigrams.tsv`)

- A bigram is two consecutive words from `cleaned.txt` (line N and line N+1).
- Tab-separated, three columns: `word1`, `word2`, and `count`.
- Sorted by `count` in descending numeric order. Ties are broken alphabetically by `word1`, then by `word2`.
- No header row.
- Example rows (illustrative, not exact):
  ```
  i	am	1234
  my	lord	1100
  ```

### Pipeline Script (`/app/pipeline.sh`)

- Must start with `#!/bin/bash` (or `#!/bin/sh`).
- Must be executable (`chmod +x`).
- When run from `/app` (i.e., `cd /app && bash pipeline.sh`), it must regenerate `cleaned.txt`, `unigrams.tsv`, and `bigrams.tsv` from `shakespeare.txt` reproducibly.
- Must use only standard Unix/coreutils commands — no Python, Perl, Ruby, or other interpreters.
