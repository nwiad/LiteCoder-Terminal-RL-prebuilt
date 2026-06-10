## Analyze GitHub Collaboration Network

Build and analyze a collaboration network from GitHub commit data to extract insights about developer collaboration patterns.

**Technical Requirements:**
- Python 3.x
- Git must be available for repository cloning
- Required libraries: networkx, pandas, python-louvain (or equivalent community detection)
- Input: Git repository URL provided in `/app/repo_url.txt`
- Output files must be written to `/app/` directory

**Implementation Requirements:**

1. **Repository Setup:**
   - Read the repository URL from `/app/repo_url.txt`
   - Clone the repository to a local directory
   - The repository will have ≥500 commits and ≥20 contributors

2. **Commit Data Extraction:**
   - Parse git log to extract: author name, author email, committer name, committer email, timestamp (ISO 8601 format), and list of modified files
   - Save raw commit data to `/app/commits.json` as a JSON array where each commit object contains: `author_name`, `author_email`, `committer_name`, `committer_email`, `timestamp`, `files` (array of file paths)

3. **Co-authorship Graph Construction:**
   - Build an undirected graph where nodes are developers (identified by email address)
   - Create an edge between two developers if they modified at least one common file within a 30-day sliding window
   - Edge weight should represent the number of common files modified within the time window
   - Save the graph as:
     - `/app/graph_edgelist.csv` with columns: `source,target,weight`
     - `/app/graph.graphml` in GraphML format

4. **Network Statistics:**
   - Calculate: number of nodes, number of edges, density, average degree, diameter (if graph is connected; otherwise largest component diameter), clustering coefficient
   - Save to `/app/network_stats.json` with keys: `nodes`, `edges`, `density`, `avg_degree`, `diameter`, `clustering_coefficient`

5. **Centrality Analysis:**
   - Identify top 5 contributors by degree centrality, betweenness centrality, and eigenvector centrality
   - Save to `/app/centrality.json` with structure:
     ```json
     {
       "degree": [{"email": "...", "score": 0.xx}, ...],
       "betweenness": [{"email": "...", "score": 0.xx}, ...],
       "eigenvector": [{"email": "...", "score": 0.xx}, ...]
     }
     ```

6. **Community Detection:**
   - Apply Louvain or Leiden algorithm to detect communities
   - Save community assignments to `/app/communities.json` as: `{"email": community_id, ...}`
   - Generate a network visualization saved as `/app/network_visualization.png` with nodes colored by community

7. **Summary Report:**
   - Write a text summary to `/app/report.txt` containing:
     - Repository name and analysis date
     - Key network statistics interpretation
     - Top contributors by centrality measures
     - Number of communities detected and their sizes
     - Overall collaboration health assessment (2-3 sentences)

8. **Command-line Interface:**
   - Create `/app/analyze_network.py` that accepts `--repo-url` argument
   - When run without arguments, it should read from `/app/repo_url.txt`
   - Script should execute the full analysis pipeline and generate all required output files

**Data Format Specifications:**

- All JSON files must be valid JSON with proper formatting
- CSV files must use comma delimiters with header row
- Email addresses should be normalized to lowercase
- Timestamps in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
- Centrality scores rounded to 4 decimal places

**Edge Cases:**
- Handle commits with multiple authors/committers
- Skip binary files or files without extensions in co-authorship analysis
- If graph is disconnected, compute diameter on largest connected component
