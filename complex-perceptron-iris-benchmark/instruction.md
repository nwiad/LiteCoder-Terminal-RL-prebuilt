Implement and benchmark a quantum-inspired perceptron with complex-valued weights against a classical real-valued perceptron on the Iris dataset.

**Technical Requirements:**
- Python 3.x
- Libraries: numpy, pandas, scikit-learn (for OpenML data loading and PCA only), matplotlib
- Input: Iris dataset from OpenML (dataset ID: 61)
- Output files: /app/results.json, /app/report.ipynb

**Implementation Requirements:**

1. **Data Loading:**
   - Fetch Iris dataset from OpenML (ID: 61) and store as pandas DataFrame
   - Use all 4 features and 3 classes

2. **Real-Valued Perceptron:**
   - Implement from scratch (no scikit-learn models)
   - Use sigmoid activation function: σ(z) = 1/(1+e^(-z))
   - Train with stochastic gradient descent (SGD)
   - Support multi-class classification (one-vs-rest or softmax)

3. **Complex-Valued Perceptron:**
   - Extend perceptron to use complex-valued weights (w ∈ ℂ^n)
   - Implement complex activation function (e.g., apply sigmoid to both real and imaginary parts, or use phase-based activation)
   - Train with complex-valued gradient descent

4. **Evaluation:**
   - Perform 5-fold cross-validation on both models
   - Calculate mean and standard deviation of accuracy across folds
   - Measure wall-clock training time for both models

5. **Visualization:**
   - Create decision boundary plots for both models
   - Use first two PCA dimensions for visualization
   - Save plots as separate files or embed in notebook

**Output Format:**

`/app/results.json` must contain:
```json
{
  "real_perceptron": {
    "mean_accuracy": <float>,
    "std_accuracy": <float>,
    "training_time_seconds": <float>
  },
  "complex_perceptron": {
    "mean_accuracy": <float>,
    "std_accuracy": <float>,
    "training_time_seconds": <float>
  }
}
```

`/app/report.ipynb` must:
- Load results.json
- Display a markdown table comparing both models with columns: Model, Mean Accuracy, Std Accuracy, Training Time
- Include decision boundary visualizations for both models
