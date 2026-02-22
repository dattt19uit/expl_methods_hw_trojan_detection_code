# Method 2: Case-Based Reasoning

Case-based trojan detection using k-Nearest Neighbors (KNN) with weighted explanations.

## Overview

**Paper Section:** III-C  
**Key Insight:** Explain predictions by showing similarity to known trojan/clean samples  
**Correspondence:** ~97.4% (highest of all methods)

## Features

- **KNN Classification:** Scikit-learn KNeighborsClassifier
- **Weighted Correspondence:** weight = 1 / (distance + 1)^3
- **Case-Based Explanations:** Shows k-nearest training samples
- **Fast Inference:** ~50-500ms per sample

## Installation

```bash
cd packages/method2-case-based
pip install -e .
```

## CLI Commands

### Training

```bash
method2-train \
    --input data/processed/train.csv \
    --output data/models/method2 \
    --k 5 \
    --metric euclidean \
    --weights distance
```

**Arguments:**
- `--input`: Training CSV file
- `--output`: Output directory for model
- `--k`: Number of neighbors (default: 5)
- `--metric`: Distance metric (`euclidean`, `manhattan`, `chebyshev`, `minkowski`)
- `--weights`: Weight function (`uniform` or `distance`)

**Outputs:**
- `knn_model.pkl`: Trained model + scaler + training data
- `knn_metadata.json`: Training metadata

### Classification

```bash
method2-classify \
    --model data/models/method2/knn_model.pkl \
    --input data/processed/test.csv \
    --output data/models/method2 \
    --trojan-weight 1.0
```

**Arguments:**
- `--model`: Path to trained model pickle file
- `--input`: Test CSV file
- `--output`: Output directory for results
- `--trojan-weight`: Multiplier for trojan samples (default: 1.0)

**Outputs:**
- `predictions.json`: Predictions and probabilities
- `explanations.json`: Case-based explanations with nearest neighbors
- `metrics.json`: Accuracy, precision, recall, F1, MCC, correspondence

## Python API

```python
from method2.training import train_knn_model
from method2.classification import classify_and_explain

# Train
train_knn_model(
    train_csv="data/processed/train.csv",
    output_dir="data/models/method2",
    k=5,
    metric="euclidean",
    weights="distance"
)

# Classify
classify_and_explain(
    model_path="data/models/method2/knn_model.pkl",
    test_csv="data/processed/test.csv",
    output_dir="data/models/method2",
    trojan_weight=1.0
)
```

## Explanation Format

Each explanation includes:
- **Prediction:** Trojan (1) or Clean (0)
- **Confidence:** Probability of prediction
- **k-Nearest Neighbors:** List of similar training samples with:
  - Distance to test sample
  - Label (trojan/clean)
  - Weight contribution: `1 / (distance + 1)^3`
- **Correspondence Score:** Agreement between prediction and weighted neighbors

Example:
```json
{
  "index": 0,
  "decision": 1,
  "confidence": 0.87,
  "matches": [
    "Distance 0.123 to trojan sample, weight: 0.512",
    "Distance 0.156 to trojan sample, weight: 0.398",
    "Distance 0.234 to clean sample, weight: 0.074"
  ],
  "correspondence_score": 0.91,
  "description": "Decision corresponds with weight 0.91 for trojan based on neighbors"
}
```

## Performance

| Metric | Expected |
|--------|----------|
| Training Time | 1-5 min |
| Inference Time | 50-500ms per sample |
| Accuracy | 97-99% |
| Correspondence | 97.4% |
| Memory | Stores full training set |

## Algorithm

1. **Training:**
   - Normalize features with StandardScaler
   - Build KNN index with specified metric
   - Store training data for explanations

2. **Classification:**
   - Scale test features
   - Find k-nearest neighbors
   - Compute weighted vote: `weight = 1 / (distance + 1)^3`
   - Apply trojan multiplier if specified
   - Generate explanation with neighbor details

## Tuning Tips

- **k:** Larger k = smoother decision boundary, more robust
  - Small circuits: k=3-5
  - Large circuits: k=7-10
- **metric:** Euclidean works well for normalized features
- **trojan_weight:** Increase if trojans are underrepresented (e.g., 2.0-5.0)
