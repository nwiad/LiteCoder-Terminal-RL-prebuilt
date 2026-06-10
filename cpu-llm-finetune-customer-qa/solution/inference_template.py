#!/usr/bin/env python3
"""CLI inference script for the fine-tuned customer-service QA model."""
import sys
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_DIR = "/app/model_output"
MAX_LENGTH = 128
MAX_NEW_TOKENS = 60


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Please provide a question as a command-line argument."}))
        sys.exit(1)

    question = sys.argv[1]

    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(MODEL_DIR)
    tokenizer.pad_token = tokenizer.eos_token
    model.eval()

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

    if "Answer:" in full_text:
        answer = full_text.split("Answer:")[-1].strip()
    else:
        answer = full_text[len(prompt):].strip()

    # Take first sentence / line
    answer = answer.split("\n")[0].strip()

    if not answer:
        answer = "I'm sorry, I don't have information about that topic."

    print(json.dumps({"answer": answer}))


if __name__ == "__main__":
    main()
