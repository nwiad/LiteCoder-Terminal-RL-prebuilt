#!/usr/bin/env python3
"""Step 3: Evaluate base and fine-tuned models on test set."""
import json
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "distilgpt2"
FINETUNED_DIR = "/app/model_output"
MAX_LENGTH = 128
MAX_NEW_TOKENS = 60


def load_model_and_tokenizer(path):
    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path)
    tokenizer.pad_token = tokenizer.eos_token
    model.eval()
    return model, tokenizer


def generate_answer(model, tokenizer, question):
    """Generate answer for a question using the model."""
    prompt = f"Question: {question} Answer:"
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=MAX_LENGTH)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            num_beams=1,
            pad_token_id=tokenizer.eos_token_id,
        )
    full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Extract answer after "Answer:" prefix
    if "Answer:" in full_text:
        answer = full_text.split("Answer:")[-1].strip()
    else:
        answer = full_text[len(prompt):].strip()
    # Take first sentence or up to first newline
    answer = answer.split("\n")[0].strip()
    return answer

def normalize_text(text):
    """Normalize text for comparison."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def compute_f1(prediction, reference):
    """Compute token-level F1 between prediction and reference."""
    pred_tokens = normalize_text(prediction).split()
    ref_tokens = normalize_text(reference).split()
    if not pred_tokens or not ref_tokens:
        return float(pred_tokens == ref_tokens)
    common = set(pred_tokens) & set(ref_tokens)
    if not common:
        return 0.0
    # Count occurrences
    from collections import Counter
    pred_counts = Counter(pred_tokens)
    ref_counts = Counter(ref_tokens)
    overlap = sum(min(pred_counts[t], ref_counts[t]) for t in common)
    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def compute_exact_match(prediction, reference):
    """Check if normalized prediction matches reference."""
    return float(normalize_text(prediction) == normalize_text(reference))


def evaluate_model(model, tokenizer, test_data, label="model"):
    """Evaluate model on test data, return metrics."""
    total_em = 0.0
    total_f1 = 0.0
    n = len(test_data)
    for i, item in enumerate(test_data):
        pred = generate_answer(model, tokenizer, item["question"])
        ref = item["answer"]
        # Strip any prefix variations from reference for fair comparison
        # The reference may have prefixes like "Sure! " etc.
        total_em += compute_exact_match(pred, ref)
        total_f1 += compute_f1(pred, ref)
        if i < 3:
            print(f"  [{label}] Q: {item['question'][:60]}")
            print(f"  [{label}] Pred: {pred[:80]}")
            print(f"  [{label}] Ref:  {ref[:80]}")
            print()
    return {
        "exact_match": round(total_em / n, 4),
        "f1": round(total_f1 / n, 4),
    }


if __name__ == "__main__":
    # Load test data
    with open("/app/test_dataset.json") as f:
        test_data = json.load(f)
    print(f"Test samples: {len(test_data)}")

    # Evaluate base model
    print("\n=== Evaluating base model ===")
    base_model, base_tok = load_model_and_tokenizer(MODEL_NAME)
    base_metrics = evaluate_model(base_model, base_tok, test_data, "base")
    print(f"Base metrics: {base_metrics}")
    del base_model, base_tok

    # Evaluate fine-tuned model
    print("\n=== Evaluating fine-tuned model ===")
    ft_model, ft_tok = load_model_and_tokenizer(FINETUNED_DIR)
    ft_metrics = evaluate_model(ft_model, ft_tok, test_data, "finetuned")
    print(f"Fine-tuned metrics: {ft_metrics}")
    del ft_model, ft_tok

    # Compute deltas
    em_delta = round(ft_metrics["exact_match"] - base_metrics["exact_match"], 4)
    f1_delta = round(ft_metrics["f1"] - base_metrics["f1"], 4)

    evaluation = {
        "base_model": base_metrics,
        "fine_tuned_model": ft_metrics,
        "improvement": {
            "exact_match_delta": em_delta,
            "f1_delta": f1_delta,
        },
    }

    with open("/app/evaluation.json", "w") as f:
        json.dump(evaluation, f, indent=2)

    print(f"\nResults saved to /app/evaluation.json")
    print(f"EM delta: {em_delta}, F1 delta: {f1_delta}")
    if f1_delta > 0:
        print("Fine-tuned model shows improvement!")
    else:
        print("WARNING: Fine-tuned model did not improve over base.")
