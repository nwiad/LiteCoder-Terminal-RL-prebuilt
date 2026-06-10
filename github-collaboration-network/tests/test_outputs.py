import os
import json
import csv
import networkx as nx
import pytest
from datetime import datetime


# Base path for output files
BASE_PATH = "/app"


def test_commits_json_exists():
    """Test that commits.json file exists."""
    assert os.path.exists(f"{BASE_PATH}/commits.json"), "commits.json file not found"


def test_commits_json_valid_structure():
    """Test commits.json has valid structure and non-trivial data."""
    with open(f"{BASE_PATH}/commits.json", 'r') as f:
        commits = json.load(f)

    # Must be a list
    assert isinstance(commits, list), "commits.json must contain a JSON array"

    # Must have substantial commits (pandas repo has 500+ commits requirement)
    assert len(commits) >= 100, f"Expected at least 100 commits, got {len(commits)}"

    # Check structure of first few commits
    for i, commit in enumerate(commits[:10]):
        assert 'author_name' in commit, f"Commit {i} missing author_name"
        assert 'author_email' in commit, f"Commit {i} missing author_email"
        assert 'committer_name' in commit, f"Commit {i} missing committer_name"
        assert 'committer_email' in commit, f"Commit {i} missing committer_email"
        assert 'timestamp' in commit, f"Commit {i} missing timestamp"
        assert 'files' in commit, f"Commit {i} missing files"

        # Validate data types
        assert isinstance(commit['author_name'], str), "author_name must be string"
        assert isinstance(commit['author_email'], str), "author_email must be string"
        assert isinstance(commit['files'], list), "files must be a list"

        # Email should be lowercase
        assert commit['author_email'] == commit['author_email'].lower(), "Email should be lowercase"

        # Timestamp should be ISO 8601 format
        try:
            datetime.fromisoformat(commit['timestamp'].replace('Z', '+00:00'))
        except:
            pytest.fail(f"Invalid timestamp format: {commit['timestamp']}")


def test_commits_json_has_real_data():
    """Test that commits contain real repository data, not dummy data."""
    with open(f"{BASE_PATH}/commits.json", 'r') as f:
        commits = json.load(f)

    # Check for diversity in authors (not all the same)
    unique_authors = set(c['author_email'] for c in commits)
    assert len(unique_authors) >= 20, f"Expected at least 20 unique authors, got {len(unique_authors)}"

    # Check that files are not empty or dummy
    files_with_content = [c for c in commits if len(c['files']) > 0]
    assert len(files_with_content) >= len(commits) * 0.8, "Most commits should have files"

    # Check for realistic file paths (should have extensions)
    sample_files = []
    for commit in commits[:50]:
        sample_files.extend(commit['files'])

    files_with_extensions = [f for f in sample_files if '.' in os.path.basename(f)]
    assert len(files_with_extensions) > 0, "Files should have extensions"


def test_graph_edgelist_csv_exists():
    """Test that graph_edgelist.csv exists."""
    assert os.path.exists(f"{BASE_PATH}/graph_edgelist.csv"), "graph_edgelist.csv not found"


def test_graph_edgelist_csv_valid_format():
    """Test graph_edgelist.csv has valid CSV format with proper columns."""
    with open(f"{BASE_PATH}/graph_edgelist.csv", 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Check header
    assert 'source' in rows[0].keys(), "Missing 'source' column"
    assert 'target' in rows[0].keys(), "Missing 'target' column"
    assert 'weight' in rows[0].keys(), "Missing 'weight' column"

    # Must have edges
    assert len(rows) > 0, "Graph should have at least one edge"

    # Validate data
    for i, row in enumerate(rows[:20]):
        assert '@' in row['source'], f"Row {i}: source should be an email"
        assert '@' in row['target'], f"Row {i}: target should be an email"
        assert row['source'] == row['source'].lower(), "Emails should be lowercase"
        assert row['target'] == row['target'].lower(), "Emails should be lowercase"

        # Weight should be positive integer
        weight = int(row['weight'])
        assert weight > 0, f"Row {i}: weight should be positive"


def test_graph_graphml_exists_and_valid():
    """Test that graph.graphml exists and is valid GraphML format."""
    assert os.path.exists(f"{BASE_PATH}/graph.graphml"), "graph.graphml not found"

    # Try to load with networkx
    G = nx.read_graphml(f"{BASE_PATH}/graph.graphml")

    # Should have nodes and edges
    assert G.number_of_nodes() > 0, "Graph should have nodes"
    assert G.number_of_edges() > 0, "Graph should have edges"


def test_graph_consistency():
    """Test that CSV and GraphML represent the same graph."""
    # Load CSV
    with open(f"{BASE_PATH}/graph_edgelist.csv", 'r') as f:
        reader = csv.DictReader(f)
        csv_edges = [(row['source'], row['target'], int(row['weight'])) for row in reader]

    # Load GraphML
    G = nx.read_graphml(f"{BASE_PATH}/graph.graphml")

    # Node counts should match
    csv_nodes = set()
    for src, tgt, _ in csv_edges:
        csv_nodes.add(src)
        csv_nodes.add(tgt)

    assert G.number_of_nodes() == len(csv_nodes), "Node count mismatch between CSV and GraphML"
    assert G.number_of_edges() == len(csv_edges), "Edge count mismatch between CSV and GraphML"


def test_network_stats_json_exists():
    """Test that network_stats.json exists."""
    assert os.path.exists(f"{BASE_PATH}/network_stats.json"), "network_stats.json not found"


def test_network_stats_json_valid_structure():
    """Test network_stats.json has all required fields with valid values."""
    with open(f"{BASE_PATH}/network_stats.json", 'r') as f:
        stats = json.load(f)

    required_keys = ['nodes', 'edges', 'density', 'avg_degree', 'diameter', 'clustering_coefficient']
    for key in required_keys:
        assert key in stats, f"Missing required key: {key}"

    # Validate types and ranges
    assert isinstance(stats['nodes'], int), "nodes should be integer"
    assert isinstance(stats['edges'], int), "edges should be integer"
    assert stats['nodes'] > 0, "Should have at least one node"
    assert stats['edges'] >= 0, "Edges should be non-negative"

    # Density should be between 0 and 1
    assert 0 <= stats['density'] <= 1, f"Density should be in [0,1], got {stats['density']}"

    # Average degree should be reasonable
    assert stats['avg_degree'] >= 0, "Average degree should be non-negative"

    # Diameter should be non-negative integer
    assert isinstance(stats['diameter'], int), "Diameter should be integer"
    assert stats['diameter'] >= 0, "Diameter should be non-negative"

    # Clustering coefficient should be between 0 and 1
    assert 0 <= stats['clustering_coefficient'] <= 1, f"Clustering coefficient should be in [0,1], got {stats['clustering_coefficient']}"


def test_network_stats_realistic_values():
    """Test that network statistics are realistic, not dummy values."""
    with open(f"{BASE_PATH}/network_stats.json", 'r') as f:
        stats = json.load(f)

    # For a real collaboration network, we expect:
    # - Multiple nodes (at least 20 contributors)
    assert stats['nodes'] >= 10, f"Expected at least 10 nodes, got {stats['nodes']}"

    # - Some edges (people collaborate)
    assert stats['edges'] > 0, "Should have at least one collaboration edge"

    # - Average degree relationship: avg_degree = 2 * edges / nodes
    expected_avg_degree = (2 * stats['edges']) / stats['nodes']
    assert abs(stats['avg_degree'] - expected_avg_degree) < 0.01, \
        f"Average degree calculation incorrect: expected {expected_avg_degree}, got {stats['avg_degree']}"


def test_centrality_json_exists():
    """Test that centrality.json exists."""
    assert os.path.exists(f"{BASE_PATH}/centrality.json"), "centrality.json not found"


def test_centrality_json_valid_structure():
    """Test centrality.json has valid structure."""
    with open(f"{BASE_PATH}/centrality.json", 'r') as f:
        centrality = json.load(f)

    required_keys = ['degree', 'betweenness', 'eigenvector']
    for key in required_keys:
        assert key in centrality, f"Missing required key: {key}"
        assert isinstance(centrality[key], list), f"{key} should be a list"
        assert len(centrality[key]) <= 5, f"{key} should have at most 5 entries"

        # Check structure of each entry
        for i, entry in enumerate(centrality[key]):
            assert 'email' in entry, f"{key}[{i}] missing email"
            assert 'score' in entry, f"{key}[{i}] missing score"
            assert '@' in entry['email'], f"{key}[{i}] email should contain @"
            assert entry['email'] == entry['email'].lower(), f"{key}[{i}] email should be lowercase"

            # Score should be a number between 0 and 1
            assert isinstance(entry['score'], (int, float)), f"{key}[{i}] score should be numeric"
            assert 0 <= entry['score'] <= 1, f"{key}[{i}] score should be in [0,1], got {entry['score']}"


def test_centrality_scores_ordered():
    """Test that centrality scores are in descending order."""
    with open(f"{BASE_PATH}/centrality.json", 'r') as f:
        centrality = json.load(f)

    for measure in ['degree', 'betweenness', 'eigenvector']:
        scores = [entry['score'] for entry in centrality[measure]]
        assert scores == sorted(scores, reverse=True), f"{measure} scores should be in descending order"


def test_centrality_emails_from_graph():
    """Test that centrality emails are actual nodes from the graph."""
    # Load graph
    G = nx.read_graphml(f"{BASE_PATH}/graph.graphml")
    graph_nodes = set(G.nodes())

    # Load centrality
    with open(f"{BASE_PATH}/centrality.json", 'r') as f:
        centrality = json.load(f)

    # Check that all emails are in the graph
    for measure in ['degree', 'betweenness', 'eigenvector']:
        for entry in centrality[measure]:
            assert entry['email'] in graph_nodes, \
                f"{measure} email {entry['email']} not found in graph nodes"


def test_communities_json_exists():
    """Test that communities.json exists."""
    assert os.path.exists(f"{BASE_PATH}/communities.json"), "communities.json not found"


def test_communities_json_valid_structure():
    """Test communities.json has valid structure."""
    with open(f"{BASE_PATH}/communities.json", 'r') as f:
        communities = json.load(f)

    # Should be a dictionary
    assert isinstance(communities, dict), "communities.json should be a dictionary"

    # Should have entries
    assert len(communities) > 0, "communities.json should not be empty"

    # Check structure
    for email, community_id in communities.items():
        assert '@' in email, f"Key {email} should be an email address"
        assert isinstance(community_id, int), f"Community ID for {email} should be integer"
        assert community_id >= 0, f"Community ID should be non-negative"


def test_communities_cover_all_nodes():
    """Test that all graph nodes have community assignments."""
    # Load graph
    G = nx.read_graphml(f"{BASE_PATH}/graph.graphml")
    graph_nodes = set(G.nodes())

    # Load communities
    with open(f"{BASE_PATH}/communities.json", 'r') as f:
        communities = json.load(f)

    community_nodes = set(communities.keys())

    # All graph nodes should have community assignments
    assert graph_nodes == community_nodes, \
        f"Community assignments don't match graph nodes. Missing: {graph_nodes - community_nodes}"


def test_network_visualization_exists():
    """Test that network_visualization.png exists and is non-empty."""
    assert os.path.exists(f"{BASE_PATH}/network_visualization.png"), "network_visualization.png not found"

    # Check file size (should be substantial for a real visualization)
    file_size = os.path.getsize(f"{BASE_PATH}/network_visualization.png")
    assert file_size > 1000, f"Visualization file too small ({file_size} bytes), likely not a real image"


def test_report_txt_exists():
    """Test that report.txt exists."""
    assert os.path.exists(f"{BASE_PATH}/report.txt"), "report.txt not found"


def test_report_txt_valid_content():
    """Test report.txt has required content sections."""
    with open(f"{BASE_PATH}/report.txt", 'r') as f:
        report = f.read()

    # Should not be empty
    assert len(report) > 100, "Report should have substantial content"

    # Should contain key sections (case-insensitive)
    report_lower = report.lower()
    assert 'repository' in report_lower or 'repo' in report_lower, "Report should mention repository"
    assert 'analysis' in report_lower or 'date' in report_lower, "Report should mention analysis date"
    assert 'network' in report_lower or 'statistics' in report_lower, "Report should mention network statistics"
    assert 'nodes' in report_lower or 'developers' in report_lower, "Report should mention nodes/developers"
    assert 'edges' in report_lower or 'collaborations' in report_lower, "Report should mention edges/collaborations"
    assert 'centrality' in report_lower or 'contributors' in report_lower, "Report should mention centrality/contributors"
    assert 'community' in report_lower or 'communities' in report_lower, "Report should mention communities"
    assert 'collaboration' in report_lower or 'health' in report_lower or 'assessment' in report_lower, \
        "Report should have collaboration health assessment"


def test_report_contains_actual_statistics():
    """Test that report contains actual statistics from the analysis."""
    # Load statistics
    with open(f"{BASE_PATH}/network_stats.json", 'r') as f:
        stats = json.load(f)

    with open(f"{BASE_PATH}/report.txt", 'r') as f:
        report = f.read()

    # Report should mention the actual number of nodes
    assert str(stats['nodes']) in report, "Report should contain actual node count"

    # Report should mention the actual number of edges
    assert str(stats['edges']) in report, "Report should contain actual edge count"


def test_analyze_network_py_exists():
    """Test that analyze_network.py script exists."""
    assert os.path.exists(f"{BASE_PATH}/analyze_network.py"), "analyze_network.py not found"


def test_analyze_network_py_is_executable_script():
    """Test that analyze_network.py is a valid Python script."""
    with open(f"{BASE_PATH}/analyze_network.py", 'r') as f:
        content = f.read()

    # Should have substantial content
    assert len(content) > 100, "Script should have substantial content"

    # Should be Python code (check for common Python keywords)
    assert 'import' in content or 'def' in content, "Should be a Python script"


def test_end_to_end_data_consistency():
    """Test that data is consistent across all output files."""
    # Load all data
    with open(f"{BASE_PATH}/commits.json", 'r') as f:
        commits = json.load(f)

    with open(f"{BASE_PATH}/network_stats.json", 'r') as f:
        stats = json.load(f)

    with open(f"{BASE_PATH}/centrality.json", 'r') as f:
        centrality = json.load(f)

    with open(f"{BASE_PATH}/communities.json", 'r') as f:
        communities = json.load(f)

    G = nx.read_graphml(f"{BASE_PATH}/graph.graphml")

    # Network stats should match graph
    assert stats['nodes'] == G.number_of_nodes(), "Node count mismatch"
    assert stats['edges'] == G.number_of_edges(), "Edge count mismatch"

    # Communities should cover all nodes
    assert len(communities) == G.number_of_nodes(), "Community count should match node count"

    # Centrality should reference actual nodes
    all_centrality_emails = set()
    for measure in ['degree', 'betweenness', 'eigenvector']:
        for entry in centrality[measure]:
            all_centrality_emails.add(entry['email'])

    graph_nodes = set(G.nodes())
    assert all_centrality_emails.issubset(graph_nodes), "Centrality emails should be graph nodes"
