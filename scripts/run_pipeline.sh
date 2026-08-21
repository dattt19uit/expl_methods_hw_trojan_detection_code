#!/bin/bash
# Run the complete XAI pipeline

set -e

# Log configuration
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/pipeline_$(date '+%Y%m%d_%H%M%S').log"

# Log both terminal output and file
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Log file: $LOG_FILE"  # Exit on error

echo "========================================="
echo "XAI Hardware Trojan Detection Pipeline"
echo "========================================="

# Activate virtual environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -d "$REPO_DIR/venv" ]; then
    source "$REPO_DIR/venv/bin/activate"
elif [ -d "$REPO_DIR/.venv" ]; then
    source "$REPO_DIR/.venv/bin/activate"
elif [ -d "$REPO_DIR/../.venv" ]; then
    source "$REPO_DIR/../.venv/bin/activate"
elif [ -n "$VIRTUAL_ENV" ]; then
    echo "Using active virtualenv: $VIRTUAL_ENV"
else
    echo "ERROR: Virtual environment not found. Run ./scripts/install_all.sh first."
    exit 1
fi

# Configuration
DATA_DIR="data"
RAW_DIR="$DATA_DIR/raw"
PROCESSED_DIR="$DATA_DIR/processed"
MODELS_DIR="$DATA_DIR/models"
LOGS_DIR="logs"
CIRCUIT_CONFIGS="configs/circuit_configs.json"

# Create directories
mkdir -p "$RAW_DIR" "$PROCESSED_DIR" "$MODELS_DIR" "$LOGS_DIR"

echo ""
echo "========================================="
echo "Phase 0: Data Acquisition"
echo "========================================="
# Use cached HTML file since Trust-Hub is an Angular SPA
# Try local copy first, then fall back to original location
HTML_FILE="configs/trust_hub_page.html"
if [ ! -f "$HTML_FILE" ]; then
    echo "Error: Trust-Hub page HTML not found at configs/trust_hub_page.html"
    echo ""
    echo "To create the file, save the rendered Trust-Hub benchmark page:"
    echo "  1. Visit https://trust-hub.org/#/benchmarks/chip-level-trojan in a browser"
    echo "  2. Save the complete page as HTML to configs/trust_hub_page.html"
    exit 1
fi
if [ ! -d "$RAW_DIR/circuits" ] || [ -z "$(ls -A $RAW_DIR/circuits 2>/dev/null)" ]; then
    echo "Downloading circuits from Trust-Hub..."
    xai-download --output "$RAW_DIR" --html-file "$HTML_FILE" --circuits "$CIRCUIT_CONFIGS"
else
    echo "Circuits already downloaded. Skipping..."
fi

echo ""
echo "========================================="
echo "Phase 1: Circuit Processing"
echo "========================================="
# Check if circuits already exist
CIRCUIT_COUNT=$(ls -1 "$DATA_DIR/circuits"/*.csv 2>/dev/null | wc -l)
if [ "$CIRCUIT_COUNT" -gt 0 ] && [ -f "$PROCESSED_DIR/train.csv" ]; then
    echo "Circuits and training data already exist. Skipping..."
elif [ "$CIRCUIT_COUNT" -gt 0 ]; then
    echo "Circuits exist ($CIRCUIT_COUNT files). Aggregating training data..."
    xai-aggregate-data --folder "$DATA_DIR/circuits" --output "$PROCESSED_DIR"
elif [ ! -f "$PROCESSED_DIR/train.csv" ]; then
    echo "Processing circuits and extracting features..."
    # Use --skip-graph to avoid slow GraphViz visualization generation
    # Use all but one CPU core for parallel circuit processing
    NCORES=$(( $(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4) - 1 ))
    [ "$NCORES" -lt 1 ] && NCORES=1
    xai-process-circuit --batch --config "$CIRCUIT_CONFIGS" --output-dir "$DATA_DIR/circuits" --skip-graph -j "$NCORES"
    
    echo "Aggregating training data..."
    xai-aggregate-data --folder "$DATA_DIR/circuits" --output "$PROCESSED_DIR"
else
    echo "Training data already exists. Skipping..."
fi

# Display data split validation
if [ -f "$PROCESSED_DIR/aggregation_summary.json" ]; then
    echo ""
    echo "Data Split Validation:"
    python3 -c "
import json
with open('$PROCESSED_DIR/aggregation_summary.json') as f:
    s = json.load(f)
    print(f\"  Total samples: {s['files']['total_rows']:,}\")
    print(f\"  Train samples: {s['files']['train_rows']:,} ({100*s['files']['train_rows']/s['files']['total_rows']:.1f}%)\")
    print(f\"  Test samples: {s['files']['test_rows']:,} ({100*s['files']['test_rows']/s['files']['total_rows']:.1f}%)\")
    print(f\"  \")
    print(f\"  Total trojans: {s['classes']['total_trojans']} ({100*s['classes']['total_trojans']/s['files']['total_rows']:.2f}%)\")
    print(f\"  Train trojans: {s['classes']['train_trojans']} ({100*s['classes']['train_trojans']/s['files']['train_rows']:.2f}%)\")
    print(f\"  Test trojans: {s['classes']['test_trojans']} ({100*s['classes']['test_trojans']/s['files']['test_rows']:.2f}%)\")
    
    # Validate stratification
    train_pct = 100*s['classes']['train_trojans']/s['files']['train_rows']
    test_pct = 100*s['classes']['test_trojans']/s['files']['test_rows']
    diff = abs(train_pct - test_pct)
    
    if diff < 0.01:
        print(f\"  [OK] Excellent stratification (difference: {diff:.4f}%)\")
    elif diff < 0.1:
        print(f\"  [OK] Good stratification (difference: {diff:.4f}%)\")
    else:
        print(f\"  [WARNING] Stratification could be better (difference: {diff:.4f}%)\")
"
fi

echo ""
echo "========================================="
echo "Phase 2-3: Method 1 - XGBoost Training"
echo "========================================="
if [ ! -d "$MODELS_DIR/method1/models" ]; then
    echo "Training 31 XGBoost models (no hyperparameter tuning needed)..."
    method1-train-xgboost \
        --data-folder "$PROCESSED_DIR" \
        --output "$MODELS_DIR/method1"
else
    echo "Models already trained. Skipping..."
fi

echo ""
echo "========================================="
echo "Phase 4: Method 1 - Knowledge Base Processing"
echo "========================================="
if [ ! -f "$MODELS_DIR/method1/arch_preds.json" ]; then
    echo "Processing knowledge base and computing voting weights..."
    method1-kb \
        --input "$MODELS_DIR/method1" \
        --output "$MODELS_DIR/method1"
else
    echo "KB already processed. Skipping..."
fi

echo ""
echo "========================================="
echo "Phase 5: Method 1 - Threshold Optimization"
echo "========================================="
if [ ! -f "$MODELS_DIR/method1/optimal_thresholds.json" ]; then
    echo "Optimizing decision thresholds for all 31 property models..."
    method1-optimize-thresholds \
        --predictions "$MODELS_DIR/method1/test_proba.json" \
        --labels "$MODELS_DIR/method1/test_labels.json" \
        --output "$MODELS_DIR/method1/optimal_thresholds.json" \
        --min-precision 0.3 \
        --min-recall 0.5
    
    echo ""
    echo "Threshold optimization complete. Top 5 properties by precision:"
    python -c "import json; d=json.load(open('$MODELS_DIR/method1/optimal_thresholds.json')); props=sorted([v for k,v in d.items() if k.startswith('property')], key=lambda x: x['optimal_metrics']['precision'], reverse=True)[:5]; [print(f'  {i+1}. {p[\"property_name\"]}: {100*p[\"optimal_metrics\"][\"precision\"]:.1f}% precision, {100*p[\"optimal_metrics\"][\"recall\"]:.1f}% recall (threshold={p[\"optimal_threshold\"]:.3f})') for i,p in enumerate(props)]"
else
    echo "Threshold optimization already completed. Skipping..."
fi

echo ""
echo "========================================="
echo "Phase 6: Method 1 - Explanation Generation"
echo "========================================="
if [ ! -d "$MODELS_DIR/method1/explanations" ]; then
    echo "Generating explanations..."
    method1-explain \
        --input "$MODELS_DIR/method1" \
        --output "$MODELS_DIR/method1/explanations"
else
    echo "Explanations already generated. Skipping..."
fi

echo ""
echo "========================================="
echo "Phase 7: Method 2 - XGBoost Training"
echo "========================================="
if [ ! -f "$MODELS_DIR/method2/xgboost_model.pkl" ]; then
    echo "Training XGBoost model for case-based detection..."
    method2-train-xgboost \
        --train-data "$PROCESSED_DIR/train.csv" \
        --output-dir "$MODELS_DIR/method2"
else
    echo "XGBoost model already trained. Skipping..."
fi

echo ""
echo "========================================="
echo "Phase 7: Method 2 - Classification"
echo "========================================="
if [ ! -f "$MODELS_DIR/method2/predictions.json" ]; then
    echo "Running XGBoost classification with case-based explanations..."
    method2-classify \
        --model "$MODELS_DIR/method2/xgboost_model.pkl" \
        --test-data "$PROCESSED_DIR/test.csv" \
        --output-dir "$MODELS_DIR/method2" \
        --trojan-weight 1.0 \
        --k 5
else
    echo "Classification already complete. Skipping..."
fi

echo ""
echo "========================================="
echo "Phase 8: Method 2 - Threshold Optimization"
echo "========================================="
if [ ! -f "$MODELS_DIR/method2/optimal_threshold.json" ]; then
    echo "Optimizing decision threshold for Method 2 XGBoost..."
    method2-optimize-threshold \
        --predictions "$MODELS_DIR/method2/predictions.json" \
        --test-data "$PROCESSED_DIR/test.csv" \
        --output "$MODELS_DIR/method2/optimal_threshold.json" \
        --min-precision 0.5 \
        --min-recall 0.7
    
    echo ""
    echo "Threshold optimization complete. Summary:"
    python -c "import json; d=json.load(open('$MODELS_DIR/method2/optimal_threshold.json')); print(f'  Optimal threshold: {d[\"optimal\"][\"threshold\"]:.3f}'); print(f'  Precision: {100*d[\"optimal\"][\"precision\"]:.2f}% (baseline: {100*d[\"baseline\"][\"precision\"]:.2f}%)'); print(f'  Recall: {100*d[\"optimal\"][\"recall\"]:.2f}% (baseline: {100*d[\"baseline\"][\"recall\"]:.2f}%)'); print(f'  False positives: {d[\"optimal\"][\"confusion_matrix\"][\"fp\"]} (baseline: {d[\"baseline\"][\"confusion_matrix\"][\"fp\"]})')"
else
    echo "Threshold optimization already completed. Skipping..."
fi

echo ""
echo "========================================="
echo "Phase 9: Method 3 - LIME Explanations"
echo "========================================="
if [ ! -f "$MODELS_DIR/method3/lime_explanations.json" ]; then
    echo "Generating LIME explanations with strategic sampling..."
    echo "  - 100% trojans (46 samples)"
    echo "  - 100% misclassifications (errors)"
    echo "  - 10% correctly-classified clean samples (~1,134 samples)"
    echo "  - Target: ~1,500 total samples for statistical validity"
    echo "  - Note: To process ALL test samples, remove --max-samples flag"
    method3-lime \
        --model "$MODELS_DIR/method2/xgboost_model.pkl" \
        --train-data "$PROCESSED_DIR/train.csv" \
        --test-data "$PROCESSED_DIR/test.csv" \
        --output "$MODELS_DIR/method3" \
        --num-samples 1000 \
        --predictions "$MODELS_DIR/method2/predictions.json" \
        --prioritize-critical
else
    echo "LIME explanations already generated. Skipping..."
fi

echo ""
echo "========================================="
echo "Phase 10: Method 4 - SHAP Explanations"
echo "========================================="
if [ ! -f "$MODELS_DIR/method4/shap_explanations.json" ]; then
    echo "Generating SHAP explanations with FULL coverage (all test samples)..."
    echo "  - Processing ALL 11,392 test samples"
    echo "  - Prioritizing critical samples (trojans + errors) first"
    echo "  - Fair comparison with other XAI methods"
    mkdir -p "$MODELS_DIR/method4"
    method4-shap-explain \
        --model "$MODELS_DIR/method2/xgboost_model.pkl" \
        --training-data "$PROCESSED_DIR/train.csv" \
        --test-data "$PROCESSED_DIR/test.csv" \
        --output "$MODELS_DIR/method4/shap_explanations.json" \
        --predictions "$MODELS_DIR/method2/predictions.json" \
        --prioritize-critical
else
    echo "SHAP explanations already generated. Skipping..."
fi

echo ""
echo "========================================="
echo "Phase 11: Method 5 - Gradient Attribution"
echo "========================================="
EXPLANATIONS_DIR="$DATA_DIR/explanations"
mkdir -p "$EXPLANATIONS_DIR/method5"
if [ ! -f "$EXPLANATIONS_DIR/method5/gradient_attributions.json" ]; then
    echo "Generating gradient-based feature attributions for XGBoost model..."
    method5-gradient \
        --model "$MODELS_DIR/method2/xgboost_model.pkl" \
        --train-data "$PROCESSED_DIR/train.csv" \
        --test-data "$PROCESSED_DIR/test.csv" \
        --output "$EXPLANATIONS_DIR/method5"
else
    echo "Gradient attributions already generated. Skipping..."
fi

echo ""
echo "========================================="
echo "Phase 12: Same Circuit Family (SCF) Cross-Validation"
echo "========================================="
SCF_DIR="$DATA_DIR/experiments/scf_analysis"
mkdir -p "$SCF_DIR"
if [ ! -f "$SCF_DIR/scf_results.json" ]; then
    echo "Running leave-one-family-out cross-validation (XGBoost, 5 folds)..."
    python scripts/scf_cross_validation.py \
        --circuits-dir "$DATA_DIR/circuits" \
        --config configs/circuit_configs.json \
        --output "$SCF_DIR"
else
    echo "SCF analysis already completed. Skipping..."
fi

echo ""
echo "========================================="
echo "Pipeline Complete!"
echo "========================================="
echo ""
echo "Method 1 (Property-Based) Results:"
echo "  Models:         $MODELS_DIR/method1/models/"
echo "  KB Output:      $MODELS_DIR/method1/arch_decisions.json"
echo "  Explanations:   $MODELS_DIR/method1/explanations/"
echo "  Thresholds:     $MODELS_DIR/method1/optimal_thresholds.json"
echo ""
echo "Method 2 (Case-Based XGBoost) Results:"
echo "  Model:          $MODELS_DIR/method2/xgboost_model.pkl"
echo "  Predictions:    $MODELS_DIR/method2/predictions.json"
echo "  Explanations:   $MODELS_DIR/method2/explanations.json"
echo "  Metrics:        $MODELS_DIR/method2/metrics.json"
echo "  Threshold:      $MODELS_DIR/method2/optimal_threshold.json"
echo ""
echo "Method 3 (LIME Explanations) Results:"
echo "  Explanations: $MODELS_DIR/method3/lime_explanations.json"
echo "  Summary:      $MODELS_DIR/method3/lime_summary.txt"
echo ""
echo "Method 4 (SHAP Explanations) Results:"
echo "  Explanations: $MODELS_DIR/method4/shap_explanations.json"
echo ""
echo "Method 5 (Gradient Attribution) Results:"
echo "  Attributions: $EXPLANATIONS_DIR/method5/gradient_attributions.json"
echo "  Summary:      $EXPLANATIONS_DIR/method5/summary.txt"
echo ""
echo "SCF Cross-Validation Results:"
echo "  Results:  $SCF_DIR/scf_results.json"
echo "  Summary:  $SCF_DIR/scf_summary.txt"
echo ""
echo "View results:"
echo "  Method 1: ls -lh $MODELS_DIR/method1/explanations/"
echo "  Method 2: cat $MODELS_DIR/method2/metrics.json"
echo "  Method 3: cat $MODELS_DIR/method3/lime_summary.txt"
echo "  Method 4: python -c 'import json; d=json.load(open(\"$MODELS_DIR/method4/shap_explanations.json\")); print(f\"Samples: {d[\"metadata\"][\"total_samples\"]}, Accuracy: {d[\"metadata\"][\"accuracy\"]:.2f}%, Time: {d[\"metadata\"][\"avg_time_per_sample\"]:.3f}s/sample\")'"
echo "  Method 5: cat $EXPLANATIONS_DIR/method5/summary.txt"
echo ""
echo "Run comprehensive analysis:"
echo "  python scripts/analyze_methods_explainability.py -o analysis_report.txt"
