# xai-method3-lime

LIME (Local Interpretable Model-agnostic Explanations) for hardware trojan detection. Provides sample-level explanations for Method 2 XGBoost classifier predictions.

## Overview

Method 3 generates LIME explanations that show which features are most important for each individual prediction made by the Method 2 classifier. LIME perturbs features locally and observes prediction changes to identify discriminative features.

**Key Features:**
- Model-agnostic (works with XGBoost or SVM)
- Per-sample explanations (local interpretability)
- Fast execution (~0.02-0.06 sec/sample)
- Feature importance rankings with directional weights

## Installation

```bash
# Install from package directory
cd packages/method3-lime
pip install -e .
```

The package will be automatically installed by `scripts/install_all.sh`.

## Usage

### Command Line

```bash
# Generate LIME explanations for all test samples
method3-lime \
  --model data/models/method2/xgboost_model.pkl \
  --train-data data/processed/train.csv \
  --test-data data/processed/test.csv \
  --output data/models/method3

# Limit to first 500 samples (recommended for quick testing)
method3-lime \
  --model data/models/method2/xgboost_model.pkl \
  --train-data data/processed/train.csv \
  --test-data data/processed/test.csv \
  --output data/models/method3 \
  --max-samples 500

# Adjust perturbations (more = more accurate, but slower)
method3-lime \
  --model data/models/method2/xgboost_model.pkl \
  --train-data data/processed/train.csv \
  --test-data data/processed/test.csv \
  --output data/models/method3 \
  --num-samples 5000
```

### Pipeline Integration

LIME runs automatically as Phase 8 in the pipeline:

```bash
./scripts/run_pipeline.sh
```

Phase 8 will:
1. Load the trained Method 2 XGBoost model
2. Generate LIME explanations for test samples
3. Save explanations and summary statistics

## Output Files

```
data/models/method3/
├── lime_explanations.json    # Per-sample explanations
└── lime_summary.txt          # Summary statistics
```

### lime_explanations.json

Contains detailed explanations for each sample:

```json
{
  "explanations": [
    {
      "sample_index": 0,
      "features": {"LGFi": 5.2, "ffi": 2.1, "ffo": 1.8, "PI": 3.0, "PO": 4.5},
      "prediction": {
        "class": 0,
        "confidence": 0.998,
        "prob_clean": 0.998,
        "prob_trojan": 0.002
      },
      "true_label": 0,
      "lime_ranking": [
        {"feature": "PO > 4.00", "weight": 0.0542, "abs_weight": 0.0542},
        {"feature": "LGFi <= 5.50", "weight": -0.0321, "abs_weight": 0.0321}
      ]
    }
  ],
  "summary": {
    "num_samples": 11392,
    "feature_names": ["LGFi", "ffi", "ffo", "PI", "PO"],
    "top_feature_frequency": {...},
    "avg_feature_weights": {...}
  }
}
```

### lime_summary.txt

Human-readable summary:

```
LIME Explanation Summary
========================

Samples processed: 500
Total time: 12.3 minutes (0.024 sec/sample)

Top Feature Frequency (times each feature ranked #1):
  PO: 174 (34.8%)
  ffo: 98 (19.6%)
  LGFi: 81 (16.2%)
  ffi: 8 (1.6%)
  PI: 7 (1.4%)

Average Absolute LIME Weights:
  PO: 0.0332 +/- 0.0121
  ffo: 0.0320 +/- 0.0117
  LGFi: 0.0228 +/- 0.0128
  PI: 0.0221 +/- 0.0144
  ffi: 0.0143 +/- 0.0095
```

## Performance

- **Speed:** ~0.024 seconds per sample (41x faster than expected!)
- **Accuracy:** Same as base classifier (98.6%)
- **Scalability:** Can process all 11,392 test samples in ~4.5 minutes

## Interpretation

LIME weights show feature influence on predictions:

- **Positive weight:** Feature pushes toward TROJAN classification
- **Negative weight:** Feature pushes toward CLEAN classification
- **Magnitude:** Strength of influence

Example:
```
ffo > 1.00: +0.0449  -> High flip-flop outputs strongly suggest trojan
PI <= 0.00: -0.0183  -> Lack of primary inputs suggests clean
```

## Configuration Options

### --num-samples (default: 1000)
Number of perturbed samples generated per explanation. Higher values give more stable explanations but take longer.

- **500:** Fast, less stable (~0.015 sec/sample)
- **1000:** Balanced (default, ~0.024 sec/sample)
- **5000:** Slow, very stable (~0.1 sec/sample)

### --max-samples (default: all)
Maximum test samples to process. Useful for testing:

- **10:** Quick test (~1 second)
- **100:** Development (~2 seconds)
- **500:** Production subset (~12 seconds)
- **all:** Full dataset (~4.5 minutes)

## Dependencies

- `numpy>=1.20.0`
- `pandas>=1.3.0`
- `scikit-learn>=1.0.0`
- `lime>=0.2.0`
- `xai-shared>=1.0.0`

## Integration with Other Methods

LIME complements the other explanation methods:

- **Method 1:** Global property-based explanations (which properties matter?)
- **Method 2:** Case-based explanations (which similar samples influenced this?)
- **Method 3 (LIME):** Local feature explanations (which feature values matter for this sample?)

## Comparison: LIME vs Method 2 Explanations

| Aspect | Method 2 (Case-Based) | Method 3 (LIME) |
|--------|----------------------|-----------------|
| **Type** | Example-based | Feature-based |
| **Output** | Similar training samples | Feature weights |
| **Scope** | Global (k-NN search) | Local (perturbations) |
| **Speed** | Very fast (<0.001s) | Fast (~0.024s) |
| **Use Case** | "What similar circuits exist?" | "What features drove this decision?" |

Both methods work together to provide comprehensive explanations.

## Troubleshooting

### "ModuleNotFoundError: No module named 'lime'"
```bash
pip install lime
# or
pip install -e packages/method3-lime/
```

### "LIME is taking too long"
Use `--max-samples` to limit processing:
```bash
method3-lime ... --max-samples 100
```

### "Feature mismatch warning"
The model and data should have the same features:
- `LGFi, ffi, ffo, PI, PO` for Method 2

This warning usually doesn't affect results but indicates data inconsistency.

## References

- **LIME Paper:** Ribeiro et al., "Why Should I Trust You?" KDD 2016
- **GitHub:** https://github.com/marcotcr/lime
- **Documentation:** https://lime-ml.readthedocs.io/

## See Also

- `../method1-property-based/` - Property-based detection
- `../method2-case-based/` - Case-based detection and explanations
- `../../scripts/run_pipeline.sh` - Full pipeline with all methods
