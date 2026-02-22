#!/bin/bash
# Clean all generated pipeline data, keeping raw Trust-Hub source files.
#
# Usage: ./scripts/clean_pipeline.sh
#
# This removes:
#   data/circuits/          - Per-circuit feature CSVs
#   data/processed/         - Aggregated train/test data
#   data/models/            - Trained models and predictions
#   data/explanations/      - Method 5 gradient attributions
#   data/statistical_analysis/ - Bootstrap CI, McNemar, effect sizes
#   data/experiments/       - Experiment results
#
# This keeps:
#   data/raw/               - Trust-Hub Verilog source (downloads)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/../data"

if [ ! -d "$DATA_DIR" ]; then
    echo "Data directory not found: $DATA_DIR"
    exit 1
fi

# Directories to remove (everything except raw/)
DIRS_TO_CLEAN=(
    "circuits"
    "processed"
    "models"
    "explanations"
    "experiments"
    "statistical_analysis"
)

echo "Pipeline Cleanup"
echo "================"
echo ""
echo "Will remove generated data from: $DATA_DIR"
echo "Keeping: data/raw/"
echo ""

TOTAL_SIZE=0
FOUND=()
for dir in "${DIRS_TO_CLEAN[@]}"; do
    if [ -d "$DATA_DIR/$dir" ]; then
        SIZE=$(du -sh "$DATA_DIR/$dir" 2>/dev/null | cut -f1)
        echo "  $dir/ ($SIZE)"
        FOUND+=("$dir")
    fi
done

if [ ${#FOUND[@]} -eq 0 ]; then
    echo "Nothing to clean -- pipeline data directories are already empty."
    exit 0
fi

echo ""
read -p "Proceed? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

for dir in "${FOUND[@]}"; do
    rm -rf "$DATA_DIR/$dir"
    echo "  Removed $dir/"
done

echo ""
echo "Done. Remaining contents of data/:"
ls -1 "$DATA_DIR"
