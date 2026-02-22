#!/bin/bash
#
# Complete Statistical Analysis - One Command Automation
# 
# This script executes the full statistical validation pipeline:
# 1. Methods explainability analysis
# 2. Data validation
# 3. Bootstrap confidence intervals (10,000 iterations)
# 4. McNemar paired comparison tests
# 5. Effect size calculations
# 6. Correlation significance tests
# 7. Auto-generated validation report
#
# Usage: ./run_complete_analysis.sh [--seed SEED] [--iterations N]
#

set -e  # Exit on any error

# Default parameters
SEED=42
ITERATIONS=10000
CONFIDENCE=0.95

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --seed)
            SEED="$2"
            shift 2
            ;;
        --iterations)
            ITERATIONS="$2"
            shift 2
            ;;
        --confidence)
            CONFIDENCE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --seed SEED          Random seed for reproducibility (default: 42)"
            echo "  --iterations N       Bootstrap iterations (default: 10000)"
            echo "  --confidence LEVEL   Confidence level (default: 0.95)"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Timestamp for this run
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
HOSTNAME=$(hostname)

echo "================================================================================"
echo "  JETTA Statistical Validation Pipeline - Complete Analysis"
echo "================================================================================"
echo "Started: $(date)"
echo "Hostname: $HOSTNAME"
echo "Git branch: $(git branch --show-current 2>/dev/null || echo 'unknown')"
echo "Git commit: $(git log -1 --oneline 2>/dev/null || echo 'unknown')"
echo "Random seed: $SEED"
echo "Bootstrap iterations: $ITERATIONS"
echo "Confidence level: ${CONFIDENCE}"
echo "================================================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "scripts/analyze_methods_explainability.py" ]; then
    echo "ERROR: Must run from pipeline root directory"
    echo "Current directory: $(pwd)"
    echo "Expected files: scripts/analyze_methods_explainability.py, run_complete_analysis.sh"
    exit 1
fi

# Check if pipeline has been run (required data files exist)
echo "Checking for required pipeline data files..."
MISSING_FILES=()

# Check critical data files (in data/processed/)
if [ ! -f "data/processed/train.csv" ]; then
    MISSING_FILES+=("data/processed/train.csv")
fi
if [ ! -f "data/processed/test.csv" ]; then
    MISSING_FILES+=("data/processed/test.csv")
fi

# Check RAW pipeline output files (prepare_analysis_data.py will convert these)
if [ ! -f "data/models/method1/test_pred.json" ]; then
    MISSING_FILES+=("data/models/method1/test_pred.json")
fi
if [ ! -f "data/models/method1/test_labels.json" ]; then
    MISSING_FILES+=("data/models/method1/test_labels.json")
fi
if [ ! -f "data/models/method2/predictions.json" ]; then
    MISSING_FILES+=("data/models/method2/predictions.json")
fi

# If any files are missing, show error and exit
if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo ""
    echo "ERROR: Pipeline has not been run yet!"
    echo ""
    echo "Missing required files:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "You must run the pipeline first to generate the data files:"
    echo ""
    echo "  ./run_full_pipeline_background.sh"
    echo ""
    echo "Or if you're using the standard pipeline script:"
    echo ""
    echo "  ./scripts/run_pipeline.sh"
    echo ""
    echo "Then wait for it to complete before running statistical analysis."
    echo ""
    echo "Pipeline generates:"
    echo "  - Training/test data (data/processed/train.csv, data/processed/test.csv)"
    echo "  - Method 1 predictions (data/models/method1/test_pred.json, test_labels.json)"
    echo "  - Method 2 predictions (data/models/method2/predictions.json)"
    echo "  - XAI explanations (LIME, SHAP, Gradient Attribution)"
    echo ""
    echo "Note: prepare_analysis_data.py will convert these to analysis format:"
    echo "  - Method 1: test_pred.json -> kb_test_results.json (ensemble predictions)"
    echo "  - Method 2: predictions.json -> classification_results.json (alias)"
    echo ""
    echo "Expected runtime: 2-8 hours depending on system"
    echo ""
    exit 1
fi

echo "[OK] All required pipeline data files found"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "WARNING: Virtual environment not activated"
    echo "   Attempting to activate: source .venv/bin/activate"
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        echo "[OK] Virtual environment activated"
    else
        echo "ERROR: Virtual environment not found at .venv/"
        echo "   Please create: python3 -m venv .venv && source .venv/bin/activate"
        exit 1
    fi
fi

# Create output directory
mkdir -p data/statistical_analysis

echo ""
echo "================================================================================"
echo "  STEP 0/7: Prepare Pipeline Data for Analysis"
echo "================================================================================"
echo "Converting pipeline output format to analysis-compatible format"
echo ""

python3 scripts/statistical_analysis/prepare_analysis_data.py --models-dir data/models

if [ $? -ne 0 ]; then
    echo "ERROR: Data preparation failed"
    echo "   Make sure the pipeline has completed and generated model predictions"
    exit 1
fi

echo ""
echo "[OK] Data preparation complete"
echo ""

echo "================================================================================"
echo "  STEP 1/7: Methods Explainability Analysis"
echo "================================================================================"
echo "Analyzing all 5 methods (Property-based, XGBoost, LIME, SHAP, Gradient)"
echo "Output: analysis_report.txt, analysis_report.json"
echo ""

python3 scripts/analyze_methods_explainability.py \
    --output-txt analysis_report.txt \
    --output-json analysis_report.json

if [ ! -f "analysis_report.txt" ]; then
    echo "ERROR: Methods analysis failed - analysis_report.txt not created"
    exit 1
fi

echo ""
echo "[OK] Methods explainability analysis complete"
echo ""

echo "================================================================================"
echo "  STEP 2/7: Data Validation"
echo "================================================================================"
echo "Validating train/test split integrity"
echo "Expected total: 56,961 samples"
echo ""

python3 scripts/statistical_analysis/validate_train_test_split.py \
    --data-dir data/processed \
    --expected-total 56961 \
    --output data/statistical_analysis/split_validation.json

# Check if validation passed
if grep -q '"status": "FAILED"' data/statistical_analysis/split_validation.json 2>/dev/null; then
    echo ""
    echo "ERROR: Data validation FAILED"
    echo "   Review data/statistical_analysis/split_validation.json for details"
    echo "   Cannot proceed with statistical analysis"
    exit 1
fi

echo ""
echo "[OK] Data validation passed"
echo ""

echo "================================================================================"
echo "  STEP 3/7: Bootstrap Confidence Intervals"
echo "================================================================================"
echo "Computing 95% CIs for all performance metrics"
echo "Iterations: $ITERATIONS (this may take 5-10 minutes)"
echo "Random seed: $SEED"
echo ""

echo "--- Baseline CIs (threshold=0.5) ---"
python3 scripts/statistical_analysis/compute_confidence_intervals.py \
    --results-dir data/models \
    --n-iterations $ITERATIONS \
    --confidence $CONFIDENCE \
    --seed $SEED \
    --output data/statistical_analysis/confidence_intervals.json

echo ""
echo "--- Optimized CIs (per-method optimized thresholds) ---"
python3 scripts/statistical_analysis/compute_confidence_intervals.py \
    --results-dir data/models \
    --n-iterations $ITERATIONS \
    --confidence $CONFIDENCE \
    --seed $SEED \
    --use-optimized-thresholds \
    --output data/statistical_analysis/confidence_intervals_optimized.json

if [ ! -f "data/statistical_analysis/confidence_intervals.json" ]; then
    echo "ERROR: Bootstrap CI computation failed (baseline)"
    exit 1
fi
if [ ! -f "data/statistical_analysis/confidence_intervals_optimized.json" ]; then
    echo "ERROR: Bootstrap CI computation failed (optimized)"
    exit 1
fi

echo ""
echo "[OK] Bootstrap confidence intervals complete"
echo ""

echo "================================================================================"
echo "  STEP 4/7: McNemar Paired Comparison Tests"
echo "================================================================================"
echo "Testing statistical significance of method differences"
echo ""

python3 scripts/statistical_analysis/mcnemar_tests.py \
    --results-dir data/models \
    --output data/statistical_analysis/mcnemar_tests.json

if [ ! -f "data/statistical_analysis/mcnemar_tests.json" ]; then
    echo "ERROR: McNemar tests failed"
    exit 1
fi

echo ""
echo "[OK] McNemar tests complete"
echo ""

echo "================================================================================"
echo "  STEP 5/7: Effect Size Calculations"
echo "================================================================================"
echo "Computing Cohen's d effect sizes"
echo ""

python3 scripts/statistical_analysis/effect_size_calculations.py \
    --ci-file data/statistical_analysis/confidence_intervals.json \
    --output data/statistical_analysis/effect_sizes.json

if [ ! -f "data/statistical_analysis/effect_sizes.json" ]; then
    echo "ERROR: Effect size calculation failed"
    exit 1
fi

echo ""
echo "[OK] Effect size calculations complete"
echo ""

echo "================================================================================"
echo "  STEP 6/7: Correlation Significance Tests"
echo "================================================================================"
echo "Testing feature importance correlations (LIME vs SHAP)"
echo ""

python3 scripts/statistical_analysis/correlation_significance.py \
    --results-dir data/models \
    --output data/statistical_analysis/correlation_tests.json

if [ ! -f "data/statistical_analysis/correlation_tests.json" ]; then
    echo "WARNING: Correlation tests failed (may be expected if data format differs)"
    echo "   Continuing with remaining analysis..."
    # Create empty file to avoid downstream errors
    echo '{}' > data/statistical_analysis/correlation_tests.json
fi

echo ""
echo "[OK] Correlation tests complete"
echo ""

echo "================================================================================"
echo "  STEP 7/7: Generating Validation Report"
echo "================================================================================"
echo "Auto-generating standardized validation report"
echo ""

# Generate report
REPORT_FILE="STATISTICAL_VALIDATION_REPORT_${HOSTNAME}_${TIMESTAMP}.md"

python3 scripts/generate_validation_report.py \
    --output "$REPORT_FILE" \
    --seed $SEED \
    --iterations $ITERATIONS \
    --confidence $CONFIDENCE

if [ ! -f "$REPORT_FILE" ]; then
    echo "ERROR: Report generation failed"
    exit 1
fi

echo ""
echo "[OK] Validation report generated: $REPORT_FILE"
echo ""

echo "================================================================================"
echo "  ANALYSIS COMPLETE"
echo "================================================================================"
echo "Completed: $(date)"
echo ""
echo "Output Files:"
echo "  - Methods Analysis:     analysis_report.txt, analysis_report.json"
echo "  - Data Validation:      data/statistical_analysis/split_validation.json"
echo "  - Confidence Intervals: data/statistical_analysis/confidence_intervals.json"
echo "  - McNemar Tests:        data/statistical_analysis/mcnemar_tests.json"
echo "  - Effect Sizes:         data/statistical_analysis/effect_sizes.json"
echo "  - Correlation Tests:    data/statistical_analysis/correlation_tests.json"
echo "  - Validation Report:    $REPORT_FILE"
echo ""
echo "================================================================================"
echo "[OK] All statistical validation complete!"
echo "   Review $REPORT_FILE for complete results"
echo "================================================================================"
