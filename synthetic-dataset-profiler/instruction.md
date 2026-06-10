## Synthetic Dataset Generator and Performance Profiler

Create a Python tool that generates synthetic datasets with configurable statistical properties and profiles the performance of pandas operations on them.

**Technical Requirements:**
- Python 3.x with pandas, numpy, scikit-learn
- Input: JSON configuration file at `/app/config.json`
- Output: CSV datasets, JSON timing results, and execution log

**Implementation Requirements:**

1. **CLI Script (`synth_benchmark.py`):**
   - Accept a single command-line argument: path to JSON config file
   - Execute dataset generation and profiling based on config
   - Log all output to `/app/execution.log`

2. **Configuration Format (`/app/config.json`):**
   - Must support multiple dataset profiles as a JSON array
   - Each profile must specify:
     - `rows`: integer (number of rows)
     - `columns`: array of column definitions with `name`, `type` (numeric/categorical/date), and `null_rate` (0.0-1.0)
     - `output_name`: string (base name for output files)

3. **Dataset Generation:**
   - Generate CSV files named as `/app/{output_name}_dataset.csv`
   - Support numeric (int/float), categorical (string), and date columns
   - Apply specified null rates to each column
   - For numeric columns with correlation specified in config, generate correlated data

4. **Performance Profiling:**
   - Time the following pandas operations on each generated dataset:
     - `read_csv`: loading the CSV file
     - `groupby`: groupby aggregation on categorical column
     - `merge`: self-join operation
     - `pivot_table`: pivot operation
     - `fillna`: filling null values
   - Measure execution time in milliseconds
   - Save results to `/app/{output_name}_timings.json` with structure:
     ```json
     {
       "dataset_shape": [rows, cols],
       "operations": [
         {"name": "operation_name", "duration_ms": float}
       ]
     }
     ```

5. **Output Files:**
   - CSV datasets: `/app/{output_name}_dataset.csv`
   - Timing results: `/app/{output_name}_timings.json`
   - Execution log: `/app/execution.log`

**Edge Cases:**
- Handle empty datasets (0 rows)
- Handle columns with 100% null rate
- Handle missing or malformed config files gracefully with error messages
