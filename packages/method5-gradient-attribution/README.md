# Method 5: Gradient-Based Feature Attribution

Provides feature attribution explanations for hardware trojan detection using gradient-based analysis (for SVM) or feature importance (for XGBoost).

## Overview

This package implements feature attribution to explain which features are most important for trojan predictions. It automatically detects the model type and uses the appropriate method:

- **XGBoost**: Uses built-in feature importance (gain-based) - Ultra-fast (~12ms per sample)
- **SVM**: Computes gradients via finite differences - Slower (~5ms per sample)

## Installation

```bash
cd /path/to/refactor/prototype/packages/method5-gradient-attribution
pip install -e .
```

## Usage

### Command Line

```bash
# Generate gradient attributions for all test samples
method5-gradient \
  --model data/models/method2/xgboost_model.pkl \
  --train-data data/processed/train.csv \
  --test-data data/processed/test.csv \
  --output data/explanations/method5

# Limit to first 100 samples for testing
method5-gradient \
  --model data/models/method2/xgboost_model.pkl \
  --train-data data/processed/train.csv \
  --test-data data/processed/test.csv \
  --output data/explanations/method5 \
  --max-samples 100
```

### Python API

```python
from method5_gradient import GradientAttributionExplainer
import pickle

# Load model
with open('data/models/method2/xgboost_model.pkl', 'rb') as f:
    model_data = pickle.load(f)

model = model_data['model']

# Create explainer
explainer = GradientAttributionExplainer(
    model=model,
    feature_names=['ffo', 'ffi', 'PO', 'LGFi', 'PI']
)

# Explain a prediction
explanation = explainer.explain_prediction(test_sample)

print(f"Model type: {explanation['model_type']}")
print(f"Top features: {explanation['top_features']}")
```

## Output Format

### gradient_attributions.json

```json
{
  "metadata": {
    "timestamp": "2025-12-13T...",
    "model_type": "XGBoost",
    "feature_names": ["ffo", "ffi", "PO", "LGFi", "PI"],
    "n_samples": 11392,
    "accuracy": 0.761,
    "processing_time_seconds": 136.8,
    "avg_time_per_sample_ms": 12.0
  },
  "global_feature_importance": {
    "LGFi": 0.567,
    "PO": 0.559,
    "ffi": 0.228,
    "PI": 0.169,
    "ffo": 0.125
  },
  "explanations": [
    {
      "sample_index": 0,
      "circuit_name": "s35932",
      "true_label": 0,
      "predicted_label": 0,
      "correct": true,
      "prediction": 0.023,
      "prediction_confidence": 0.977,
      "model_type": "XGBoost",
      "method": "feature_attribution",
      "top_features": [
        {
          "rank": 1,
          "feature": "LGFi",
          "feature_value": 458.639,
          "importance": 0.800,
          "attribution": 366.98,
          "direction": "increases",
          "interpretation": "LGFi (importance: 80.0%, value: 458.6390) - high importance feature"
        }
      ],
      "normalized_importance": [0.800, 0.478, 0.190, 0.250, 0.180],
      "raw_attribution": [366.98, 171.89, 46.02, 77.21, 42.68]
    }
  ]
}
```

## Performance

- **XGBoost**: ~12 ms per sample (11,392 samples in ~137 seconds)
- **SVM**: ~5 ms per sample (gradient computation)
- **Memory**: Minimal (~100 MB for full test set)

## Integration with Pipeline

Method 5 runs after Method 2 (Case-Based Classification) as Phase 10:

```
Phase 1-7: Training and prediction
Phase 8: Method 3 LIME explanations
Phase 9: Method 4 SHAP explanations
Phase 10: Method 5 Gradient Attribution <- NEW!
```

## See Also

- `gradient_explainer.py` - Core implementation
- `cli.py` - Command-line interface
- Main repo: `methods/5_gradient_attribution/` - Original implementation with property attribution
