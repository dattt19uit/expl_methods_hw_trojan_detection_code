#!/bin/bash
#
# package_results.sh -- Bundle all pipeline and analysis results into a tarball
#
# Usage:
#   1. Run the full pipeline:
#        ./run_full_pipeline_background.sh
#        ./run_complete_analysis.sh
#        python3 scripts/analyze_methods_explainability.py
#   2. Package results:
#        ./package_results.sh
#
# Output: results_<hostname>_YYYYMMDD_HHMMSS.tar.gz
#
# Purpose: Cross-machine comparison of pipeline outputs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HOSTNAME="$(hostname)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BUNDLE_NAME="results_${HOSTNAME}_${TIMESTAMP}"
TARBALL="${BUNDLE_NAME}.tar.gz"
STAGING_DIR="/tmp/${BUNDLE_NAME}"

echo "=== Results Packaging Script ==="
echo "Host:      ${HOSTNAME}"
echo "Timestamp: ${TIMESTAMP}"
echo "Output:    ${TARBALL}"
echo ""

# --- Collect files -----------------------------------------------------------

# Build list of files to include (only those that exist)
FILES=()

add_if_exists() {
    for path in "$@"; do
        if [[ -e "$path" ]]; then
            FILES+=("$path")
        fi
    done
}

add_dir_if_exists() {
    for dir in "$@"; do
        if [[ -d "$dir" ]]; then
            while IFS= read -r -d '' f; do
                FILES+=("$f")
            done < <(find "$dir" -type f -print0)
        fi
    done
}

# --- Methods analysis (root-level) ---
add_if_exists \
    analysis_report.json \
    analysis_report.txt \
    analysis_report_new.txt

# --- Statistical analysis ---
add_if_exists \
    data/statistical_analysis/split_validation.json \
    data/statistical_analysis/confidence_intervals.json \
    data/statistical_analysis/confidence_intervals_optimized.json \
    data/statistical_analysis/mcnemar_tests.json \
    data/statistical_analysis/effect_sizes.json \
    data/statistical_analysis/correlation_tests.json

# --- SCF cross-validation ---
add_dir_if_exists data/experiments/scf_analysis

# --- Model results (metrics and explanations only, skip models/.pkl and bulk data) ---
add_if_exists \
    data/models/method1/test_metrics.json \
    data/models/method1/train_metrics.json \
    data/models/method1/optimal_thresholds.json \
    data/models/method1/feature_importance.json \
    data/models/method1/properties.json \
    data/models/method1/kb_test_results.json \
    data/models/method1/test_labels.json \
    data/models/method1/test_pred.json \
    data/models/method1/test_proba.json \
    data/models/method1/arch_preds.json \
    data/models/method1/similar.json

add_dir_if_exists data/models/method1/explanations
add_dir_if_exists data/models/method1/logs

add_if_exists \
    data/models/method2/metrics.json \
    data/models/method2/predictions.json \
    data/models/method2/optimal_threshold.json \
    data/models/method2/explanations.json \
    data/models/method2/xgboost_metadata.json \
    data/models/method2/classification_results.json

# --- Explainability outputs ---
add_if_exists \
    data/models/method3/lime_explanations.json \
    data/models/method3/lime_summary.txt \
    data/models/method4/shap_explanations.json

add_dir_if_exists data/explanations/method5

# --- Processed data (aggregation results, train/test splits) ---
add_if_exists \
    data/processed/aggregation_summary.json \
    data/processed/aggregation_log.txt \
    data/processed/all.csv \
    data/processed/train.csv \
    data/processed/test.csv \
    data/processed/max.csv \
    data/processed/min.csv

# --- Pipeline logs ---
add_if_exists \
    pipeline.log \
    pipeline_run.log \
    full_pipeline_run.log \
    validation_output.log \
    threshold_optimization.log \
    method1_ratio_xgboost_training.log \
    method1_ratio_threshold_optimization.log \
    method1_ratio_training.log \
    logs/process_circuit.log

# Pick up any timestamped pipeline logs
for f in pipeline_run_*.log; do
    [[ -e "$f" ]] && FILES+=("$f")
done

# --- GNN prototype logs (if present) ---
if [[ -d packages/gnn_prototype/logs ]]; then
    for f in packages/gnn_prototype/logs/*.log; do
        [[ -e "$f" ]] && FILES+=("$f")
    done
fi

# --- Config files (for reproducibility context) ---
add_if_exists \
    test_config.json \
    pyproject.toml

# --- Check we found something ---
if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "ERROR: No result files found. Run the pipeline first."
    echo "  ./run_full_pipeline_background.sh"
    echo "  ./run_complete_analysis.sh"
    echo "  python3 scripts/analyze_methods_explainability.py"
    exit 1
fi

# --- Generate checksums for JSON files ---
echo "Computing checksums..."
CHECKSUM_FILE="checksums.md5"
rm -f "$CHECKSUM_FILE"

for f in "${FILES[@]}"; do
    if [[ "$f" == *.json ]]; then
        md5sum "$f" >> "$CHECKSUM_FILE"
    fi
done

if [[ -f "$CHECKSUM_FILE" ]]; then
    FILES+=("$CHECKSUM_FILE")
fi

# --- Create tarball ---
echo "Creating tarball: ${TARBALL}"
tar -czf "$TARBALL" "${FILES[@]}"

# Clean up checksum file (it's now inside the tar)
rm -f "$CHECKSUM_FILE"

# --- Summary ---
echo ""
echo "=== Bundle Summary ==="
FILE_COUNT=${#FILES[@]}
TARBALL_SIZE=$(du -h "$TARBALL" | cut -f1)
TARBALL_BYTES=$(stat --printf='%s' "$TARBALL" 2>/dev/null || stat -f '%z' "$TARBALL" 2>/dev/null)
TARBALL_MD5=$(md5sum "$TARBALL" | awk '{print $1}')

echo "Files included: ${FILE_COUNT}"
echo "Tarball size:   ${TARBALL_SIZE} (${TARBALL_BYTES} bytes)"
echo "MD5:            ${TARBALL_MD5}"
echo "Output:         $(pwd)/${TARBALL}"
echo ""

# --- List contents by category ---
echo "=== Contents by Category ==="
JSON_COUNT=0; LOG_COUNT=0; CSV_COUNT=0; TXT_COUNT=0; OTHER_COUNT=0
for f in "${FILES[@]}"; do
    case "$f" in
        *.json) JSON_COUNT=$((JSON_COUNT + 1)) ;;
        *.log)  LOG_COUNT=$((LOG_COUNT + 1)) ;;
        *.csv)  CSV_COUNT=$((CSV_COUNT + 1)) ;;
        *.txt)  TXT_COUNT=$((TXT_COUNT + 1)) ;;
        *)      OTHER_COUNT=$((OTHER_COUNT + 1)) ;;
    esac
done
echo "  JSON files:  ${JSON_COUNT}"
echo "  Log files:   ${LOG_COUNT}"
echo "  CSV files:   ${CSV_COUNT}"
echo "  Text files:  ${TXT_COUNT}"
echo "  Other:       ${OTHER_COUNT}"
echo ""
echo "To inspect: tar -tzf ${TARBALL}"
echo ""
echo "Done."
