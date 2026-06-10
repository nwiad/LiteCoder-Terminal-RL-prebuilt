Build a real-time sentiment analysis pipeline that consumes text messages from Kafka, classifies sentiment using a scikit-learn model, and publishes results back to Kafka.

## Technical Requirements

- Python 3.8+
- kafka-python library for Kafka integration
- scikit-learn for sentiment classification
- Input: Kafka topic with JSON messages containing text field
- Output: Kafka topic with JSON messages containing text and sentiment fields

## Implementation Requirements

Create a Python application with the following components:

**1. Sentiment Model (`/app/model.pkl`)**
- Train a scikit-learn classifier on the provided training data
- Save the trained model as a pickle file at `/app/model.pkl`
- Model must accept text strings and output sentiment labels

**2. Kafka Producer (`/app/producer.py`)**
- Read messages from `/app/input.json` (array of objects with "text" field)
- Publish each message to Kafka topic `input-messages`
- Message format: `{"text": "message content"}`

**3. Sentiment Service (`/app/consumer.py`)**
- Consume messages from Kafka topic `input-messages`
- Load model from `/app/model.pkl`
- Classify sentiment for each message
- Publish results to Kafka topic `output-sentiments`
- Output format: `{"text": "message content", "sentiment": "positive|negative|neutral"}`

**4. Configuration (`/app/config.py`)**
- Kafka broker configuration (default: `localhost:9092`)
- Topic names for input and output
- Model path configuration

## Input Format

`/app/input.json` contains an array of message objects:
```json
[
  {"text": "I love this product!"},
  {"text": "This is terrible."},
  {"text": "It's okay, nothing special."}
]
```

## Output Format

Messages published to `output-sentiments` topic:
```json
{"text": "I love this product!", "sentiment": "positive"}
{"text": "This is terrible.", "sentiment": "negative"}
{"text": "It's okay, nothing special.", "sentiment": "neutral"}
```

## Training Data

Use `/app/training_data.csv` with columns: `text,sentiment`

## Error Handling

- Handle Kafka connection failures gracefully
- Log errors without crashing the pipeline
- Skip malformed messages and continue processing
