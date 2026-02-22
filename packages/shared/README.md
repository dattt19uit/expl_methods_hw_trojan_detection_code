# xai-shared

**Shared infrastructure for XAI hardware trojan detection**

---

## Installation

```bash
pip install -e .
```

---

## Modules

### `circuit_processing`
Circuit parsing and feature extraction using CircuitGraph.

**Files to migrate:**
- `process_circuit.py` -> `circuit_processing/processor.py`
- `blackbox_definitions.py` -> `circuit_processing/blackbox.py`

### `data_handling`
CSV aggregation, splitting, and data management.

**Files to migrate:**
- `aggregate_training_data.py` -> `data_handling/aggregate.py`
- `csv_01_fix_max.py` -> `data_handling/fix_max.py`
- `csv_02_shuffle.py` -> `data_handling/shuffle.py`
- `csv_03_split_test.py` -> `data_handling/split.py`

### `evaluation`
Model evaluation and metrics computation.

**Files to migrate:**
- `evaluate_accuracy.py` -> `evaluation/accuracy.py`
- `quantitative_explainability_metrics.py` -> `evaluation/metrics.py`

### `utils`
Common utilities (config loading, logging, file operations).

---

## Usage

```python
from xai_shared.circuit_processing import CircuitProcessor
from xai_shared.data_handling import aggregate_data
from xai_shared.evaluation import evaluate_model

# Process circuit
processor = CircuitProcessor()
features = processor.extract_features("s27_90nm.v")

# Aggregate data
aggregate_data(input_dir="csv_data/", output_file="train.csv")

# Evaluate model
metrics = evaluate_model(predictions, labels)
```

---

## Command-Line Tools

After installation, command-line tools are available:

```bash
# Process a circuit
xai-process-circuit --circuit s27_90nm.v --output csv_data/

# Aggregate training data
xai-aggregate-data --input csv_data/ --output train.csv
```

---

## Testing

```bash
pytest tests/
```

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Format code
black xai_shared/

# Type checking
mypy xai_shared/

# Linting
flake8 xai_shared/
```
