#!/usr/bin/env python3
"""Step 2: Fine-tune distilgpt2 on customer-service QA dataset."""
import json
import os
import resource
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from datasets import Dataset

# Track peak memory
def get_peak_rss_mb():
    """Get peak RSS in MB."""
    rusage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is in KB on Linux
    return rusage.ru_maxrss / 1024.0

MODEL_NAME = "distilgpt2"
OUTPUT_DIR = "/app/model_output"
MAX_LENGTH = 128

print(f"Loading model: {MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

# Set pad token
tokenizer.pad_token = tokenizer.eos_token
model.config.pad_token_id = tokenizer.eos_token_id

# Load training data
with open("/app/train_dataset.json") as f:
    train_data = json.load(f)

print(f"Training samples: {len(train_data)}")

# Format as "Question: ... Answer: ..." for causal LM
def format_qa(item):
    return f"Question: {item['question']} Answer: {item['answer']}{tokenizer.eos_token}"

texts = [format_qa(item) for item in train_data]

# Tokenize
def tokenize_function(examples):
    tokens = tokenizer(
        examples["text"],
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
    )
    tokens["labels"] = tokens["input_ids"].copy()
    return tokens
dataset = Dataset.from_dict({"text": texts})
tokenized = dataset.map(tokenize_function, batched=True, remove_columns=["text"])

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,
)

# CPU-optimized training arguments per spec
training_args = TrainingArguments(
    output_dir="/tmp/training_output",
    overwrite_output_dir=True,
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    fp16=False,
    save_strategy="epoch",
    logging_steps=50,
    learning_rate=5e-5,
    weight_decay=0.01,
    warmup_steps=50,
    no_cuda=True,
    report_to="none",
    save_total_limit=1,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized,
    data_collator=data_collator,
)

print("Starting fine-tuning...")
trainer.train()
print("Fine-tuning complete.")

# Save model and tokenizer
os.makedirs(OUTPUT_DIR, exist_ok=True)
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Model saved to {OUTPUT_DIR}")

# Write memory report
peak_mb = get_peak_rss_mb()
memory_report = {
    "peak_rss_mb": round(peak_mb, 2),
    "within_limit": peak_mb <= 4096.0,
}
with open("/app/memory_report.json", "w") as f:
    json.dump(memory_report, f, indent=2)
print(f"Peak RSS: {peak_mb:.2f} MB, within limit: {memory_report['within_limit']}")
