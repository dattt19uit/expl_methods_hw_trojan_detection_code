#!/bin/bash
# Install/reinstall packages with threshold optimization support

set -e

echo "========================================"
echo "Installing Threshold Optimization Tools"
echo "========================================"
echo ""

# Activate venv if not already activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

echo "Installing shared utilities package..."
pip install -e packages/shared/

echo ""
echo "Reinstalling Method 1 with threshold optimizer..."
pip install -e packages/method1-property-based/

echo ""
echo "Reinstalling Method 2 with threshold optimizer..."
pip install -e packages/method2-case-based/

echo ""
echo "========================================"
echo "[OK] Installation Complete"
echo "========================================"
echo ""
echo "Available commands:"
echo "  method1-optimize-thresholds  - Optimize all 31 property thresholds"
echo "  method2-optimize-threshold   - Optimize Method 2 threshold"
echo ""
