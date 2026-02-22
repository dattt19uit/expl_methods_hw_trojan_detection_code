#!/bin/bash
# Check threshold optimization results and compare with previous runs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Threshold Optimization Results Checker"
echo "========================================="
echo ""

# Check if pipeline is still running
PIPELINE_PID=$(pgrep -f run_pipeline.sh 2>/dev/null || true)
if [ -n "$PIPELINE_PID" ]; then
    echo "[WAIT] Pipeline is still running (PID: $PIPELINE_PID)"
    echo "   Run this script again after pipeline completes."
    echo ""
    echo "Current progress:"
    tail -5 pipeline.log
    exit 0
fi

echo "[OK] Pipeline completed!"
echo ""

# Check Phase 5 (Method 1) threshold optimization
echo "========================================="
echo "Phase 5: Method 1 Threshold Optimization"
echo "========================================="
echo ""

if [ -f "data/models/method1/optimal_thresholds.json" ]; then
    echo "[OK] Optimal thresholds file found"
    echo ""
    
    # Extract performance metrics from JSON
    echo "Performance Metrics:"
    python3 << 'PYEOF'
import json
with open('data/models/method1/optimal_thresholds.json', 'r') as f:
    data = json.load(f)

if 'performance' in data:
    perf = data['performance']
    print(f"  Processing time: {perf.get('processing_time_seconds', 'N/A'):.3f} seconds")
    print(f"  Mode: {perf.get('mode', 'N/A')}")
    print(f"  Num cores: {perf.get('num_cores', 'N/A')}")
    
    if 'baseline_time_seconds' in perf:
        baseline = perf['baseline_time_seconds']
        actual = perf['processing_time_seconds']
        speedup = baseline / actual if actual > 0 else 0
        print(f"  Baseline (sequential): {baseline:.3f} seconds")
        print(f"  Speedup: {speedup:.2f}x")
    print()

# Show sample thresholds
print("Sample Optimal Thresholds:")
for i in [0, 15, 30]:
    key = f'property_{i}'
    if key in data:
        prop = data[key]
        print(f"  {key}: threshold={prop['threshold']:.3f}, " + 
              f"precision={prop['metrics']['precision']:.1%}, " +
              f"recall={prop['metrics']['recall']:.1%}")
PYEOF
else
    echo "[ERROR] Optimal thresholds file not found"
fi

echo ""

# Check Phase 8 (Method 2) threshold optimization
echo "========================================="
echo "Phase 8: Method 2 Threshold Optimization"
echo "========================================="
echo ""

if [ -f "data/models/method2/optimal_threshold.json" ]; then
    echo "[OK] Optimal threshold file found"
    echo ""
    
    python3 << 'PYEOF'
import json
with open('data/models/method2/optimal_threshold.json', 'r') as f:
    data = json.load(f)

print(f"Optimal threshold: {data['threshold']:.3f}")
print(f"Precision: {data['metrics']['precision']:.1%}")
print(f"Recall: {data['metrics']['recall']:.1%}")
print(f"F1-score: {data['metrics']['f1']:.3f}")

if 'performance' in data:
    perf = data['performance']
    print(f"\nProcessing time: {perf.get('processing_time_seconds', 'N/A'):.3f} seconds")
PYEOF
else
    echo "[ERROR] Optimal threshold file not found"
fi

echo ""

# Extract relevant lines from pipeline log
echo "========================================="
echo "Pipeline Log - Threshold Optimization"
echo "========================================="
echo ""

echo "Phase 5 (Method 1):"
grep -A 30 "Phase 5: Method 1 - Threshold Optimization" pipeline.log | grep -E "(Loaded|Optimizing|Processing time|speedup|cores|Saved)" | head -15

echo ""
echo "Phase 8 (Method 2):"
grep -A 15 "Phase 8: Method 2 - Threshold Optimization" pipeline.log | grep -E "(Loaded|Optimizing|Processing time|threshold|Saved)" | head -10

echo ""
echo "========================================="
echo "Complete! Check pipeline.log for full details."
echo "========================================="
