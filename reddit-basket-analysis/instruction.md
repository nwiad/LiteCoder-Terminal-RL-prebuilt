## Reddit Market Basket Analysis

Perform market basket analysis on Reddit comment data to find subreddit co-occurrence patterns via the Apriori algorithm, and visualize the resulting association rules as an interactive network graph.

### Technical Requirements

- Language: Python 3.x
- Key libraries: `mlxtend` (for Apriori and association rules), `pandas`, `scipy`
- Visualization: D3.js (force-directed network in a self-contained HTML file)

### Step 1: Generate Synthetic Input Data

Since the original large dataset is not available, write a Python script `/app/generate_data.py` that creates the input file `/app/input.jsonl.gz`. This file must be a gzip-compressed JSON Lines file where each line is a JSON object representing a Reddit comment with at least these fields:

- `author` (string): username of the commenter (e.g., `"user_0001"`)
- `subreddit` (string): name of the subreddit (e.g., `"AskReddit"`)

Generate data with the following characteristics:
- At least 50,000 comment records
- At least 200 unique users
- At least 30 unique subreddits
- Users should comment in multiple subreddits so that meaningful co-occurrence patterns exist

Run this script to produce `/app/input.jsonl.gz`.

### Step 2: ETL and User-Item Matrix

Read `/app/input.jsonl.gz` by streaming the compressed file. Build a user → subreddits lookup and convert it into a binary user-item matrix (1 if user posted in subreddit, 0 otherwise). Prune subreddits that appear in fewer than 0.1% of users. Save the pruned binary transaction matrix to `/app/user_item_matrix.pkl` using pickle.

### Step 3: Apriori and Association Rules

Run the Apriori algorithm on the binary transaction matrix with:
- `min_support = 0.005`

Generate association rules filtered by:
- `lift >= 1.5`
- `confidence >= 0.30`

Save the rules to `/app/association_rules.csv` as a CSV file with the following columns (at minimum):

| Column | Description |
|---|---|
| antecedents | Comma-separated subreddit name(s) forming the left-hand side |
| consequents | Comma-separated subreddit name(s) forming the right-hand side |
| support | Float, the support value of the rule |
| confidence | Float, the confidence value of the rule |
| lift | Float, the lift value of the rule |

All float values must have at least 4 decimal places of precision. The CSV must include a header row. The file must contain at least 1 rule row (the synthetic data should be designed to guarantee this).

### Step 4: Interactive Network Visualization

Create a self-contained HTML file at `/app/network.html` that renders an interactive force-directed network graph using D3.js (loaded via CDN is acceptable). Requirements:

- Nodes represent subreddits that appear in the association rules
- Edges represent rules; edge weight corresponds to confidence
- Each node must have a tooltip or label showing the subreddit name
- Each edge must encode at least support and lift (via tooltip, title attribute, or data attributes)
- The HTML file must contain all necessary JavaScript and CSS inline (single file, no external local dependencies)
- The file must include a valid `<svg>` or `<canvas>` element for the graph
- The D3.js force simulation must be present in the script (use `d3.forceSimulation`)

### Output Summary

| File | Format | Description |
|---|---|---|
| `/app/input.jsonl.gz` | gzip JSON Lines | Synthetic Reddit comment data |
| `/app/user_item_matrix.pkl` | pickle | Binary user-item transaction matrix |
| `/app/association_rules.csv` | CSV | Association rules with required columns |
| `/app/network.html` | HTML | Self-contained interactive D3.js network |
