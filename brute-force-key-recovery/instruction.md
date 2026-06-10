## Broken Key-Recovery Service

Reverse-engineer the custom key-derivation routine in the provided `recover.py` script, brute-force the unknown service code, and recover the 64-character hex master key used to encrypt `vault.crypt`.

### Provided Files

- `/app/recover.py` – The server-side key-derivation and encryption module. Contains `derive_key(service_code) -> str` (returns a 64-char hex key) and `encrypt`/`decrypt` functions (repeating-XOR using the hex key as ASCII bytes).
- `/app/vault.crypt` – A hex-encoded ciphertext produced by encrypting a plaintext message with the master key derived from an unknown service code.

### Task

1. Study `recover.py` to understand the custom derivation scheme (SHA-256 → XOR with salt → 64 rounds of block mixing → final SHA-256 → hex output) and the repeating-XOR encryption.
2. The service code is a single lowercase English word chosen from the 200 most common English nouns (e.g., "time", "year", "people", "way", "day", "man", "woman", "child", "world", "life", "hand", "part", "place", "case", "week", "company", "system", "program", "question", "work", "government", "number", "night", "point", "home", "water", "room", "mother", "area", "money", "story", "fact", "month", "lot", "right", "study", "book", "eye", "job", "word", "business", "issue", "side", "kind", "head", "house", "service", "friend", "father", "power", "hour", "game", "line", "end", "member", "law", "car", "city", "community", "name", "president", "team", "minute", "idea", "body", "information", "back", "parent", "face", "others", "level", "office", "door", "health", "person", "art", "war", "history", "party", "result", "change", "morning", "reason", "research", "girl", "guy", "moment", "air", "teacher", "force", "education", "food", "foot", "boy", "age", "policy", "process", "music", "market", "sense", "product", "effect", "class", "piece", "problem", "land", "dream", "position", "development", "road", "thing", "student", "state", "family", "group", "country", "school", "order", "form", "rate", "experience", "interest", "field", "court", "figure", "type", "center", "role", "value", "table", "church", "model", "death", "heart", "plan", "view", "river", "period", "street", "action", "price", "report", "need", "today", "voice", "record", "paper", "space", "ground", "bed", "run", "test", "half", "color", "face", "light", "south", "west", "north", "east", "town", "step", "top", "picture", "garden", "animal", "building", "movie", "bank", "season", "material", "plant", "stage", "oil", "song", "data", "summer", "letter", "window", "account", "island", "film", "tree", "fire", "condition", "wall", "star", "story", "truth", "sound", "skin", "ball", "cup", "board", "rock", "glass", "dog", "rule", "sign", "cell", "lake").
3. Iterate over all candidate words, call `derive_key()` for each, attempt to decrypt `vault.crypt`, and identify the correct service code by checking whether the decrypted output is valid readable ASCII text.
4. A successful decryption produces plaintext that starts with `VAULT CONTENTS UNLOCKED`.

### Output

Write the recovered 64-character hexadecimal master key (lowercase, no prefix, no whitespace) to:

```
/app/solution.txt
```

The file must contain exactly one line: the 64-character hex string and nothing else.

### Constraints

- Python 3.x only (you may use only the standard library).
- Do not modify `recover.py` or `vault.crypt`.
- The final answer in `solution.txt` must be exactly 64 lowercase hex characters.
