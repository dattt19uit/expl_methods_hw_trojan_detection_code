#!/bin/bash
# Run the complete XAI pipeline in the background with nohup
# This allows the pipeline to continue running even if the terminal disconnects

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Starting XAI Pipeline in Background"
echo "========================================="
echo ""
echo "Pipeline will run in the background with output to: pipeline.log"
echo "Progress can be monitored with: tail -f pipeline.log"
echo ""
echo "To check if pipeline is running:"
echo "  ps aux | grep run_pipeline.sh"
echo ""
echo "To stop the pipeline:"
echo "  pkill -f run_pipeline.sh"
echo ""
echo "Starting now..."

# Create a wrapper script that activates venv and runs pipeline
# Detect venv: check common locations relative to the repo
if [ -f "$SCRIPT_DIR/../.venv/bin/activate" ]; then
    VENV_ACTIVATE="$SCRIPT_DIR/../.venv/bin/activate"
elif [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    VENV_ACTIVATE="$SCRIPT_DIR/.venv/bin/activate"
elif [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    VENV_ACTIVATE="$SCRIPT_DIR/venv/bin/activate"
elif [ -n "$VIRTUAL_ENV" ]; then
    VENV_ACTIVATE="$VIRTUAL_ENV/bin/activate"
else
    echo "[WARNING] No virtualenv found. Running without venv activation."
    VENV_ACTIVATE=""
fi

cat > /tmp/run_pipeline_with_venv.sh << WRAPPER_EOF
#!/bin/bash
cd "$SCRIPT_DIR"
${VENV_ACTIVATE:+source "$VENV_ACTIVATE"}
bash scripts/run_pipeline.sh
WRAPPER_EOF

chmod +x /tmp/run_pipeline_with_venv.sh

# Run pipeline in background with nohup
nohup bash /tmp/run_pipeline_with_venv.sh > pipeline.log 2>&1 &

PID=$!
echo ""
echo "Pipeline started with PID: $PID"
echo "Log file: $SCRIPT_DIR/pipeline.log"
echo ""
echo "Monitor progress:"
echo "  tail -f $SCRIPT_DIR/pipeline.log"
echo ""
echo "Check status:"
echo "  ps -p $PID"
echo ""

# Wait a moment to see if it starts successfully
sleep 2

if ps -p $PID > /dev/null; then
    echo "[OK] Pipeline is running successfully!"
    echo ""
    echo "The pipeline will:"
    echo "  1. Process circuits (if needed)"
    echo "  2. Train Method 1 (Property-Based) models"
    echo "  3. Train Method 2 (XGBoost) model"
    echo "  4. Generate LIME explanations (Method 3)"
    echo "  5. Generate SHAP explanations (Method 4)"
    echo "  6. Generate Gradient attributions (Method 5)"
    echo ""
    echo "Estimated time: 8-10 minutes (depending on CPU cores)"
else
    echo "[FAIL] Pipeline failed to start. Check pipeline.log for errors:"
    tail -20 pipeline.log
    exit 1
fi
