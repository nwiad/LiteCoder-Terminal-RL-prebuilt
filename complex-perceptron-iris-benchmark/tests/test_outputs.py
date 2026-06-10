import os
import json
import pytest


def test_results_json_exists():
    """Test that results.json file exists"""
    assert os.path.exists('/app/results.json'), "results.json file not found at /app/results.json"


def test_results_json_valid_format():
    """Test that results.json is valid JSON and has correct structure"""
    with open('/app/results.json', 'r') as f:
        results = json.load(f)

    # Check top-level keys
    assert 'real_perceptron' in results, "Missing 'real_perceptron' key in results.json"
    assert 'complex_perceptron' in results, "Missing 'complex_perceptron' key in results.json"

    # Check real_perceptron fields
    real = results['real_perceptron']
    assert 'mean_accuracy' in real, "Missing 'mean_accuracy' in real_perceptron"
    assert 'std_accuracy' in real, "Missing 'std_accuracy' in real_perceptron"
    assert 'training_time_seconds' in real, "Missing 'training_time_seconds' in real_perceptron"

    # Check complex_perceptron fields
    complex_p = results['complex_perceptron']
    assert 'mean_accuracy' in complex_p, "Missing 'mean_accuracy' in complex_perceptron"
    assert 'std_accuracy' in complex_p, "Missing 'std_accuracy' in complex_perceptron"
    assert 'training_time_seconds' in complex_p, "Missing 'training_time_seconds' in complex_perceptron"


def test_results_json_accuracy_values():
    """Test that accuracy values are reasonable (not trivial or hardcoded)"""
    with open('/app/results.json', 'r') as f:
        results = json.load(f)

    real_acc = results['real_perceptron']['mean_accuracy']
    complex_acc = results['complex_perceptron']['mean_accuracy']

    # Check type
    assert isinstance(real_acc, (int, float)), "real_perceptron mean_accuracy must be numeric"
    assert isinstance(complex_acc, (int, float)), "complex_perceptron mean_accuracy must be numeric"

    # Check range (0.0 to 1.0)
    assert 0.0 <= real_acc <= 1.0, f"real_perceptron mean_accuracy {real_acc} out of range [0.0, 1.0]"
    assert 0.0 <= complex_acc <= 1.0, f"complex_perceptron mean_accuracy {complex_acc} out of range [0.0, 1.0]"

    # Reject trivial solutions (accuracy too low - worse than random guessing for 3 classes)
    assert real_acc > 0.4, f"real_perceptron mean_accuracy {real_acc} too low (worse than random guessing)"
    assert complex_acc > 0.4, f"complex_perceptron mean_accuracy {complex_acc} too low (worse than random guessing)"

    # Reject hardcoded perfect scores (perceptrons on Iris rarely get perfect 1.0)
    assert real_acc < 0.999, f"real_perceptron mean_accuracy {real_acc} suspiciously perfect (likely hardcoded)"
    assert complex_acc < 0.999, f"complex_perceptron mean_accuracy {complex_acc} suspiciously perfect (likely hardcoded)"


def test_results_json_std_accuracy_values():
    """Test that std_accuracy values are reasonable"""
    with open('/app/results.json', 'r') as f:
        results = json.load(f)

    real_std = results['real_perceptron']['std_accuracy']
    complex_std = results['complex_perceptron']['std_accuracy']

    # Check type
    assert isinstance(real_std, (int, float)), "real_perceptron std_accuracy must be numeric"
    assert isinstance(complex_std, (int, float)), "complex_perceptron std_accuracy must be numeric"

    # Check non-negative
    assert real_std >= 0.0, f"real_perceptron std_accuracy {real_std} must be non-negative"
    assert complex_std >= 0.0, f"complex_perceptron std_accuracy {complex_std} must be non-negative"

    # Check reasonable upper bound (std shouldn't exceed 0.5 for 5-fold CV)
    assert real_std < 0.5, f"real_perceptron std_accuracy {real_std} unreasonably high"
    assert complex_std < 0.5, f"complex_perceptron std_accuracy {complex_std} unreasonably high"

    # Reject exactly zero std (suspiciously perfect - all folds identical)
    assert real_std > 0.001, f"real_perceptron std_accuracy {real_std} is zero (suspiciously perfect)"
    assert complex_std > 0.001, f"complex_perceptron std_accuracy {complex_std} is zero (suspiciously perfect)"


def test_results_json_training_time_values():
    """Test that training_time_seconds values are reasonable"""
    with open('/app/results.json', 'r') as f:
        results = json.load(f)

    real_time = results['real_perceptron']['training_time_seconds']
    complex_time = results['complex_perceptron']['training_time_seconds']

    # Check type
    assert isinstance(real_time, (int, float)), "real_perceptron training_time_seconds must be numeric"
    assert isinstance(complex_time, (int, float)), "complex_perceptron training_time_seconds must be numeric"

    # Check positive (training must take some time)
    assert real_time > 0.0, f"real_perceptron training_time_seconds {real_time} must be positive"
    assert complex_time > 0.0, f"complex_perceptron training_time_seconds {complex_time} must be positive"

    # Check reasonable upper bound (shouldn't take more than 5 minutes for Iris dataset)
    assert real_time < 300.0, f"real_perceptron training_time_seconds {real_time} unreasonably high"
    assert complex_time < 300.0, f"complex_perceptron training_time_seconds {complex_time} unreasonably high"


def test_models_produce_different_results():
    """Test that real and complex perceptrons produce different results (not copy-paste)"""
    with open('/app/results.json', 'r') as f:
        results = json.load(f)

    real_acc = results['real_perceptron']['mean_accuracy']
    complex_acc = results['complex_perceptron']['mean_accuracy']

    # Models should produce different accuracy values (not identical copy-paste)
    assert abs(real_acc - complex_acc) > 0.001, \
        f"real and complex perceptrons have identical accuracy ({real_acc}), likely copy-paste"


def test_report_notebook_exists():
    """Test that report.ipynb file exists"""
    assert os.path.exists('/app/report.ipynb'), "report.ipynb file not found at /app/report.ipynb"


def test_report_notebook_valid_format():
    """Test that report.ipynb is valid Jupyter notebook format"""
    with open('/app/report.ipynb', 'r') as f:
        notebook = json.load(f)

    # Check required notebook structure
    assert 'cells' in notebook, "Notebook missing 'cells' key"
    assert 'metadata' in notebook, "Notebook missing 'metadata' key"
    assert 'nbformat' in notebook, "Notebook missing 'nbformat' key"
    assert 'nbformat_minor' in notebook, "Notebook missing 'nbformat_minor' key"

    # Check cells is a list
    assert isinstance(notebook['cells'], list), "Notebook 'cells' must be a list"
    assert len(notebook['cells']) > 0, "Notebook must have at least one cell"


def test_report_notebook_loads_results():
    """Test that notebook loads results.json"""
    with open('/app/report.ipynb', 'r') as f:
        notebook = json.load(f)

    # Convert all cell sources to single string for searching
    all_sources = []
    for cell in notebook['cells']:
        if 'source' in cell:
            if isinstance(cell['source'], list):
                all_sources.extend(cell['source'])
            else:
                all_sources.append(cell['source'])

    notebook_content = ''.join(all_sources)

    # Check that notebook loads results.json
    assert 'results.json' in notebook_content, "Notebook must load results.json"
    assert 'json.load' in notebook_content or 'json.loads' in notebook_content, \
        "Notebook must parse JSON from results.json"


def test_report_notebook_has_comparison_table():
    """Test that notebook creates comparison table with required columns"""
    with open('/app/report.ipynb', 'r') as f:
        notebook = json.load(f)

    # Convert all cell sources to single string
    all_sources = []
    for cell in notebook['cells']:
        if 'source' in cell:
            if isinstance(cell['source'], list):
                all_sources.extend(cell['source'])
            else:
                all_sources.append(cell['source'])

    notebook_content = ''.join(all_sources)

    # Check for table creation (DataFrame or markdown table)
    has_dataframe = 'DataFrame' in notebook_content or 'pd.DataFrame' in notebook_content
    has_markdown_table = '|' in notebook_content and ('Model' in notebook_content or 'model' in notebook_content)

    assert has_dataframe or has_markdown_table, \
        "Notebook must create a comparison table (DataFrame or markdown)"

    # Check for required columns/fields
    assert 'Mean Accuracy' in notebook_content or 'mean_accuracy' in notebook_content, \
        "Table must include Mean Accuracy column"
    assert 'Std Accuracy' in notebook_content or 'std_accuracy' in notebook_content, \
        "Table must include Std Accuracy column"
    assert 'Training Time' in notebook_content or 'training_time' in notebook_content, \
        "Table must include Training Time column"


def test_report_notebook_has_visualizations():
    """Test that notebook includes decision boundary visualizations"""
    with open('/app/report.ipynb', 'r') as f:
        notebook = json.load(f)

    # Convert all cell sources to single string
    all_sources = []
    for cell in notebook['cells']:
        if 'source' in cell:
            if isinstance(cell['source'], list):
                all_sources.extend(cell['source'])
            else:
                all_sources.append(cell['source'])

    notebook_content = ''.join(all_sources)

    # Check for visualization references (images or plots)
    has_image_display = 'Image(' in notebook_content or 'display(' in notebook_content
    has_plot = 'plt.' in notebook_content or 'matplotlib' in notebook_content
    has_png_ref = '.png' in notebook_content

    assert has_image_display or has_plot or has_png_ref, \
        "Notebook must include decision boundary visualizations"

    # Check for both model visualizations
    has_real_viz = 'real' in notebook_content.lower() and ('boundary' in notebook_content.lower() or 'decision' in notebook_content.lower())
    has_complex_viz = 'complex' in notebook_content.lower() and ('boundary' in notebook_content.lower() or 'decision' in notebook_content.lower())

    assert has_real_viz, "Notebook must include real perceptron visualization"
    assert has_complex_viz, "Notebook must include complex perceptron visualization"


def test_report_notebook_not_empty():
    """Test that notebook is not just an empty template"""
    with open('/app/report.ipynb', 'r') as f:
        notebook = json.load(f)

    # Count non-empty cells
    non_empty_cells = 0
    for cell in notebook['cells']:
        if 'source' in cell:
            source = cell['source']
            if isinstance(source, list):
                source = ''.join(source)
            if source.strip():
                non_empty_cells += 1

    assert non_empty_cells >= 4, \
        f"Notebook has only {non_empty_cells} non-empty cells, likely an empty template"


def test_results_file_not_empty():
    """Test that results.json is not an empty file"""
    file_size = os.path.getsize('/app/results.json')
    assert file_size > 50, f"results.json is too small ({file_size} bytes), likely empty or dummy"


def test_notebook_file_not_empty():
    """Test that report.ipynb is not an empty file"""
    file_size = os.path.getsize('/app/report.ipynb')
    assert file_size > 200, f"report.ipynb is too small ({file_size} bytes), likely empty or dummy"
