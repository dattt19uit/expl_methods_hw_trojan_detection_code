#!/bin/bash
# Install all packages in development mode

set -e  # Exit on error

echo "========================================="
echo "Installing XAI Trojan Detection Packages"
echo "========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Pre-flight: check that venv module is available before attempting to create one
if ! python3 -c "import venv" 2>/dev/null; then
    PYTHON_MINOR=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo ""
    echo "ERROR: Python venv module is not installed."
    echo ""
    echo "This is common on Debian/Ubuntu where venv is a separate package."
    echo "Install it with one of:"
    echo "  Debian/Ubuntu:  sudo apt install python${PYTHON_MINOR}-venv"
    echo "  Fedora/RHEL:    sudo dnf install python3-libs"
    echo "  Arch:           sudo pacman -S python"
    echo "  openSUSE:       sudo zypper install python3-venv"
    echo "  macOS:          brew reinstall python@${PYTHON_MINOR}"
    echo ""
    echo "Or run ./scripts/setup_environment.sh which handles this automatically."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install packages in order (dependencies first)
echo ""
echo "========================================="
echo "1/7: Installing xai-shared..."
echo "========================================="
cd packages/shared
pip install -e ".[dev]"
cd ../..

echo ""
echo "========================================="
echo "2/7: Installing xai-data-acquisition..."
echo "========================================="
cd packages/data-acquisition
pip install -e ".[dev]"
cd ../..

echo ""
echo "========================================="
echo "3/7: Installing xai-method1 (property-based)..."
echo "========================================="
cd packages/method1-property-based
pip install -e ".[dev]"
cd ../..

echo ""
echo "========================================="
echo "4/7: Installing method2-case-based..."
echo "========================================="
cd packages/method2-case-based
pip install -e .
cd ../..

echo ""
echo "========================================="
echo "5/7: Installing method3-lime..."
echo "========================================="
cd packages/method3-lime
pip install -e .
cd ../..

echo ""
echo "========================================="
echo "6/7: Installing method4-shap..."
echo "========================================="
cd packages/method4-shap
pip install -e .
cd ../..

echo ""
echo "========================================="
echo "7/7: Installing method5-gradient-attribution..."
echo "========================================="
cd packages/method5-gradient-attribution
pip install -e .
cd ../..

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Installed packages:"
pip list | grep -i xai
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To deactivate:"
echo "  deactivate"
