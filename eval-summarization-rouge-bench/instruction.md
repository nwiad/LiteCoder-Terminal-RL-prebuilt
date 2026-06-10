## Text Summarization Model Evaluation

Benchmark a pre-trained HuggingFace abstractive-summarization model on a small slice of the CNN/DailyMail dataset, record ROUGE metrics, and provide an inference helper for generating summaries.

### Technical Requirements

- Language: Python 3.x
- Libraries: `transformers`, `datasets`, `rouge-score`, `pandas`, `torch` (CPU-only is fine)
- Model: Use `t5-small` as the pre-trained summarization model
- Dataset: CNN/DailyMail (version 3.0.0), test split only, limited to the first 100 examples

### Input

A JSON file at `/app/input_articles.json` containing sample articles to summarize. The file is a JSON array of objects, each with an `"id"` (string) and `"article"` (string) field:

```json
[
  {"id": "article_1", "article": "The full text of a news article..."},
  {"id": "article_2", "article": "Another news article text..."}
]
```

### Steps

1. Download the `t5-small` model and tokenizer from HuggingFace, and load the first 100 examples from the CNN/DailyMail test split.

2. Fine-tune the model for exactly 1 epoch on those 100 examples with these trainer settings:
   - `per_device_train_batch_size`: 1
   - `gradient_accumulation_steps`: 8
   - `fp16`: False
   - `dataloader_num_workers`: 0
   - Save the fine-tuned model to `/app/fine_tuned_model/`
   - Save the training log to `/app/training_log.json` as a JSON array of log entries (each entry is an object with at least `"loss"` and `"step"` keys from the HuggingFace Trainer).

3. Evaluate the fine-tuned model on the same 100 examples. Compute ROUGE-1, ROUGE-2, and ROUGE-L F-scores (averaged across all examples). Write the results to `/app/rouge_scores.csv` with the following exact format (header row + one data row):

   ```
   metric,f_score
   rouge1,<float>
   rouge2,<float>
   rougeL,<float>
   ```

   Each `f_score` value must be a float between 0.0 and 1.0 (inclusive), rounded to 4 decimal places.

4. Create an inference helper at `/app/inference_helper.py` that contains a function with this exact signature:

   ```python
   def summarize(article: str, model_path: str = "/app/fine_tuned_model") -> str:
   ```

   The function must:
   - Load the fine-tuned model and tokenizer from `model_path`
   - Accept a single article string and return a generated summary string
   - Work independently when imported (i.e., `from inference_helper import summarize`)

5. Use the inference helper to summarize every article in `/app/input_articles.json`. Write the results to `/app/output_summaries.json` as a JSON array of objects:

   ```json
   [
     {"id": "article_1", "summary": "Generated summary text..."},
     {"id": "article_2", "summary": "Generated summary text..."}
   ]
   ```

   - The output must contain one entry per input article, in the same order.
   - Each `"summary"` must be a non-empty string.

6. Package the following into a single tarball at `/app/handoff.tar.gz`:
   - `/app/fine_tuned_model/` (the saved model directory)
   - `/app/training_log.json`
   - `/app/rouge_scores.csv`
   - `/app/inference_helper.py`
   - `/app/output_summaries.json`

### Output Files Summary

| File | Format |
|---|---|
| `/app/fine_tuned_model/` | HuggingFace model directory (contains `config.json`, model weights, tokenizer files) |
| `/app/training_log.json` | JSON array of training log entry objects |
| `/app/rouge_scores.csv` | CSV with columns `metric`, `f_score` |
| `/app/inference_helper.py` | Python module with `summarize()` function |
| `/app/output_summaries.json` | JSON array of `{"id", "summary"}` objects |
| `/app/handoff.tar.gz` | Tarball containing all above files |
