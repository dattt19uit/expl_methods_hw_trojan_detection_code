# Method 4: SHAP Explanations

SHAP (SHapley Additive exPlanations) provides theoretically-grounded feature importance explanations based on Shapley values from cooperative game theory.

## Features

- **TreeExplainer for XGBoost**: Fast, exact Shapley values (0.01-0.1 sec/sample)
- **KernelExplainer for SVM**: Model-agnostic, approximate Shapley values (10-60 sec/sample)
- **Auto-detection**: Automatically selects best explainer based on model type
- **Global feature importance**: Identifies most important features across all samples
- **Per-sample explanations**: Shows which features contributed to each prediction

## Installation

```bash
cd refactor/prototype/packages/method4-shap
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Generate SHAP explanations for 100 samples
method4-shap-explain \
  --model ../../data/models/method2/xgboost_model.pkl \
  --training-data ../../data/processed/train.csv \
  --test-data ../../data/processed/test.csv \
  --output ../../output/shap/explanations.json \
  --max-test-samples 100

# Process all test samples (may take longer)
method4-shap-explain \
  --model ../../data/models/method2/xgboost_model.pkl \
  --training-data ../../data/processed/train.csv \
  --test-data ../../data/processed/test.csv \
  --output ../../output/shap/explanations.json
```

### Python API

```python
from method4_shap.shap_explainer import run_shap_explanations

results = run_shap_explanations(
    model_path='data/models/method2/xgboost_model.pkl',
    training_data_path='data/processed/train.csv',
    test_data_path='data/processed/test.csv',
    output_path='output/shap/explanations.json',
    max_test_samples=100
)
```

## Output Format

The output JSON file contains:

```json
{
  "explanations": [
    {
      "sample_index": 0,
      "true_label": 1,
      "predicted_label": 1,
      "predicted_proba": [0.02, 0.98],
      "base_value": 0.52,
      "shapley_values": {
        "ffo": 0.15,
        "ffi": -0.02,
        "PO": 0.08,
        "LGFi": 0.12,
        "PI": -0.03
      },
      "explanation": "Prediction: Trojan. Top contributors: ffo (+0.15), LGFi (+0.12), PO (+0.08)"
    }
  ],
  "global_feature_importance": {
    "ffo": 0.120,
    "LGFi": 0.098,
    "PO": 0.087,
    "ffi": 0.065,
    "PI": 0.052
  },
  "metadata": {
    "total_samples": 100,
    "model_type": "XGBoost",
    "explainer_type": "TreeExplainer",
    "accuracy": 97.5,
    "trojan_recall": 95.0,
    "avg_time_per_sample": 0.015
  }
}
```

## Performance

### XGBoost (TreeExplainer - Default)
- **Speed**: 0.01-0.1 seconds per sample
- **Quality**: Exact Shapley values (not approximate)
- **11k samples**: ~2 minutes total

### SVM (KernelExplainer)
- **Speed**: 10-60 seconds per sample
- **Quality**: Approximate Shapley values
- **11k samples**: 30-180 hours total (impractical)

## Understanding Shapley Values

Shapley values represent the average marginal contribution of each feature across all possible feature coalitions:

- **Positive value**: Feature pushes prediction toward trojan (class 1)
- **Negative value**: Feature pushes prediction toward clean (class 0)
- **Magnitude**: Importance of the contribution

Example:
```
ffo: +0.15  -> Strong evidence for trojan
LGFi: +0.12 -> Moderate evidence for trojan
PI: -0.03   -> Weak evidence for clean
```

## Integration with Pipeline

This package integrates with the refactor/prototype pipeline as Phase 9:

```bash
cd refactor/prototype
./scripts/run_pipeline.sh
```

The pipeline will automatically:
1. Train XGBoost model (Phase 6)
2. Generate SHAP explanations (Phase 9, optional)
3. Save results to `output/shap/explanations.json`

## References

- Lundberg & Lee (2017). "A Unified Approach to Interpreting Model Predictions" (NeurIPS)
- SHAP documentation: https://shap.readthedocs.io/
- Shapley value theory: https://en.wikipedia.org/wiki/Shapley_value
