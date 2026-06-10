Build a from-scratch, NumPy-only, soft-margin multi-class (one-vs-one) Support Vector Machine classifier. Train it on the provided Dry Bean dataset and achieve at least 85% macro-averaged F1 on the test split.

## Technical Requirements

- Language: Python 3
- Allowed libraries: `numpy`, `csv`, `json`, `collections`, `itertools`, `math` from the standard library. No scikit-learn, scipy, or other ML/optimization libraries.
- Working directory: `/app/`

## Input

Two CSV files are provided:

- `/app/data/train.csv` — training split
- `/app/data/test.csv` — test split

Each CSV has a header row. Columns (in order):

| # | Column | Type |
|---|--------|------|
| 1 | Area | float |
| 2 | Perimeter | float |
| 3 | MajorAxisLength | float |
| 4 | MinorAxisLength | float |
| 5 | AspectRation | float |
| 6 | Eccentricity | float |
| 7 | ConvexArea | float |
| 8 | EquivDiameter | float |
| 9 | Extent | float |
| 10 | Solidity | float |
| 11 | roundness | float |
| 12 | Compactness | float |
| 13 | ShapeFactor1 | float |
| 14 | ShapeFactor2 | float |
| 15 | ShapeFactor3 | float |
| 16 | ShapeFactor4 | float |
| 17 | Class | string (bean variety name) |

The `Class` column contains the bean variety label (e.g., `SEKER`, `BARBUNYA`, `BOMBAY`, `CALI`, `HOROZ`, `SIRA`, `DERMASON`). There are 7 distinct classes.

## Implementation

Create the file `/app/kernel_svm.py` containing:

1. A Gaussian (RBF) kernel function.
2. An SMO (Sequential Minimal Optimization) solver for soft-margin binary SVM.
3. A one-vs-one multi-class wrapper that trains one binary SVM per class pair and predicts via majority voting.

Create the file `/app/run.py` that:

1. Reads `/app/data/train.csv` and `/app/data/test.csv`.
2. Standardizes features (zero mean, unit variance) using statistics computed from the training set only.
3. Trains the multi-class SVM on the training data.
4. Predicts labels for the test data.
5. Computes per-class precision, recall, F1, and macro-averaged F1.
6. Writes results to `/app/results.json` and saves the model to `/app/model.npz`.

## Output

### `/app/results.json`

A JSON file with this exact structure:

```json
{
  "macro_f1": 0.87,
  "per_class": {
    "SEKER": {"precision": 0.90, "recall": 0.88, "f1": 0.89},
    "BARBUNYA": {"precision": 0.85, "recall": 0.82, "f1": 0.83}
  },
  "hyperparameters": {
    "C": 1.0,
    "gamma": 0.1
  },
  "num_support_vectors": 1234
}
```

- `macro_f1`: float, the macro-averaged F1 score across all classes. Must be >= 0.85.
- `per_class`: dict mapping each class name to its precision, recall, and f1 (all floats rounded to 4 decimal places).
- `hyperparameters`: dict with keys `C` (regularization) and `gamma` (RBF width), both floats.
- `num_support_vectors`: int, total number of support vectors across all binary classifiers.

### `/app/model.npz`

A NumPy `.npz` archive that persists the trained model. It must be loadable via `numpy.load('/app/model.npz', allow_pickle=True)` and contain at minimum:
- `gamma`: the RBF kernel width
- `C`: the regularization parameter

## Execution

Running `python /app/run.py` must produce both `/app/results.json` and `/app/model.npz` without errors.
