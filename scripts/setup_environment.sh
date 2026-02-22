#!/bin/bash
# Setup development environment

set -e

echo "========================================="
echo "Setting up XAI Development Environment"
echo "========================================="

# Install system dependencies
echo ""
echo "Checking system dependencies..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.8+"
    exit 1
fi
echo "[OK] Python 3 found: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "WARNING: Node.js not found. Some features may not work."
    echo "  Install: https://nodejs.org/"
else
    echo "[OK] Node.js found: $(node --version)"
fi

# Check npm
if ! command -v npm &> /dev/null; then
    echo "WARNING: npm not found. Some features may not work."
else
    echo "[OK] npm found: $(npm --version)"
fi

# Check cargo (for Rust version of data-acquisition)
if ! command -v cargo &> /dev/null; then
    echo "Note: Cargo (Rust) not found. Rust downloader won't be available."
    echo "  Install: https://rustup.rs/"
else
    echo "[OK] Cargo found: $(cargo --version)"
fi

# Check git
if ! command -v git &> /dev/null; then
    echo "ERROR: git not found. Please install git."
    exit 1
fi
echo "[OK] git found: $(git --version)"

# Detect package manager
PKG_MANAGER=""
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt-get"
    DISTRO="Debian/Ubuntu"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    DISTRO="Fedora/RHEL 8+"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    DISTRO="RHEL/CentOS"
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
    DISTRO="Arch Linux"
elif command -v zypper &> /dev/null; then
    PKG_MANAGER="zypper"
    DISTRO="openSUSE"
elif command -v brew &> /dev/null; then
    PKG_MANAGER="brew"
    DISTRO="macOS"
fi

# Check Python development headers (required for building C extensions)
if [ "$PKG_MANAGER" = "apt-get" ] || [ "$PKG_MANAGER" = "dnf" ] || [ "$PKG_MANAGER" = "yum" ]; then
    # Check if python3-dev/devel is installed
    PYTHON_DEV_MISSING=0
    if [ "$PKG_MANAGER" = "apt-get" ]; then
        if ! dpkg -l | grep -q python3-dev; then
            PYTHON_DEV_MISSING=1
        fi
    elif [ "$PKG_MANAGER" = "dnf" ] || [ "$PKG_MANAGER" = "yum" ]; then
        if ! rpm -qa | grep -q python3-devel; then
            PYTHON_DEV_MISSING=1
        fi
    fi
    
    if [ $PYTHON_DEV_MISSING -eq 1 ]; then
        echo "WARNING: Python development headers not found. Required for building packages."
        echo "  Installing Python dev headers on $DISTRO..."
        case $PKG_MANAGER in
            apt-get)
                sudo apt-get update -qq && sudo apt-get install -y python3-dev
                ;;
            dnf)
                sudo dnf install -y python3-devel
                ;;
            yum)
                sudo yum install -y python3-devel
                ;;
        esac
        echo "[OK] Python development headers installed"
    else
        echo "[OK] Python development headers found"
    fi
fi

# Check Python venv module (required for virtual environment creation)
# On Debian/Ubuntu, the venv module is packaged separately as python3.X-venv
echo ""
echo "Checking Python venv module..."
if ! python3 -c "import venv" 2>/dev/null; then
    echo "WARNING: Python venv module not found. Required for virtual environment creation."
    PYTHON_MINOR=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [ -n "$PKG_MANAGER" ]; then
        echo "  Installing Python venv module on $DISTRO..."
        case $PKG_MANAGER in
            apt-get)
                # Debian/Ubuntu uses version-specific package names (e.g. python3.10-venv)
                # Try version-specific first, fall back to generic python3-venv
                if sudo apt-get update -qq && sudo apt-get install -y "python${PYTHON_MINOR}-venv" 2>/dev/null; then
                    echo "[OK] python${PYTHON_MINOR}-venv installed"
                elif sudo apt-get install -y python3-venv 2>/dev/null; then
                    echo "[OK] python3-venv installed"
                else
                    echo "ERROR: Failed to install python venv. Try manually:"
                    echo "  sudo apt install python${PYTHON_MINOR}-venv"
                    exit 1
                fi
                ;;
            dnf)
                # Fedora/RHEL: venv is usually included, but install if missing
                sudo dnf install -y python3-libs
                ;;
            yum)
                sudo yum install -y python3-libs
                ;;
            pacman)
                # Arch: venv is included with python package, ensure it's current
                sudo pacman -S --noconfirm python
                ;;
            zypper)
                sudo zypper install -y python3-venv
                ;;
            brew)
                # macOS Homebrew: venv is included with python
                echo "  venv should be included with Homebrew Python."
                echo "  Try: brew reinstall python@${PYTHON_MINOR}"
                ;;
        esac
        # Verify it worked
        if ! python3 -c "import venv" 2>/dev/null; then
            echo "ERROR: Python venv module still not available after install attempt."
            echo "  Manual install instructions by platform:"
            echo "    Debian/Ubuntu:  sudo apt install python${PYTHON_MINOR}-venv"
            echo "    Fedora/RHEL:    sudo dnf install python3-libs"
            echo "    Arch:           sudo pacman -S python"
            echo "    openSUSE:       sudo zypper install python3-venv"
            echo "    macOS:          brew reinstall python@${PYTHON_MINOR}"
            exit 1
        fi
    else
        echo "  WARNING: Could not detect package manager."
        echo "  Please install Python venv module manually:"
        echo "    Debian/Ubuntu:  sudo apt install python${PYTHON_MINOR}-venv"
        echo "    Fedora/RHEL:    sudo dnf install python3-libs"
        echo "    Arch:           sudo pacman -S python"
        echo "    openSUSE:       sudo zypper install python3-venv"
        echo "    macOS:          brew reinstall python@${PYTHON_MINOR}"
        exit 1
    fi
else
    echo "[OK] Python venv module available"
fi

# Check GraphViz (required for pygraphviz Python package)
if ! command -v dot &> /dev/null; then
    echo "WARNING: GraphViz not found. Required for circuit visualization."
    if [ -n "$PKG_MANAGER" ]; then
        echo "  Installing GraphViz on $DISTRO..."
        case $PKG_MANAGER in
            apt-get)
                sudo apt-get update -qq && sudo apt-get install -y graphviz libgraphviz-dev
                ;;
            dnf)
                sudo dnf install -y graphviz graphviz-devel
                ;;
            yum)
                sudo yum install -y graphviz graphviz-devel
                ;;
            pacman)
                sudo pacman -S --noconfirm graphviz
                ;;
            zypper)
                sudo zypper install -y graphviz graphviz-devel
                ;;
            brew)
                brew install graphviz
                ;;
        esac
        echo "[OK] GraphViz installed"
    else
        echo "  WARNING: Could not detect package manager."
        echo "  Please install GraphViz manually:"
        echo "    Debian/Ubuntu: sudo apt-get install graphviz libgraphviz-dev python3-dev"
        echo "    Fedora/RHEL:   sudo dnf install graphviz graphviz-devel python3-devel"
        echo "    Arch:          sudo pacman -S graphviz"
        echo "    macOS:         brew install graphviz"
    fi
else
    echo "[OK] GraphViz found: $(dot -V 2>&1)"
fi

# Check unrar (for extracting Trust-Hub RAR archives)
if ! command -v unrar &> /dev/null; then
    echo "WARNING: unrar not found. Required for extracting Trust-Hub circuits."
    if [ -n "$PKG_MANAGER" ]; then
        echo "  Installing unrar on $DISTRO..."
        case $PKG_MANAGER in
            apt-get)
                sudo apt-get update -qq && sudo apt-get install -y unrar
                ;;
            dnf)
                sudo dnf install -y unrar
                ;;
            yum)
                sudo yum install -y unrar
                ;;
            pacman)
                sudo pacman -S --noconfirm unrar
                ;;
            zypper)
                sudo zypper install -y unrar
                ;;
            brew)
                brew install unrar
                ;;
        esac
        echo "[OK] unrar installed"
    else
        echo "  WARNING: Could not detect package manager."
        echo "  Please install unrar manually:"
        echo "    Debian/Ubuntu: sudo apt-get install unrar"
        echo "    Fedora/RHEL:   sudo dnf install unrar"
        echo "    Arch:          sudo pacman -S unrar"
        echo "    macOS:         brew install unrar"
    fi
else
    echo "[OK] unrar found: $(unrar --version | head -1)"
fi

# Initialize git if needed
if [ ! -d ".git" ]; then
    echo ""
    echo "Initializing git repository..."
    git init
    echo "[OK] Git repository initialized"
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo ""
    echo "Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
env/
ENV/
*.egg-info/
dist/
build/

# Data
data/
*.csv
*.pkl
*.json
logs/
results/
nohup.out
!configs/*.json

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
EOF
    echo "[OK] .gitignore created"
fi

# Install packages
echo ""
echo "Installing Python packages..."
./scripts/install_all.sh

echo ""
echo "========================================="
echo "Environment Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Run the pipeline:"
echo "     ./scripts/run_pipeline.sh"
echo ""
echo "  3. Or run individual commands:"
echo "     method1-tune --help"
echo "     method1-train --help"
echo "     method1-kb --help"
echo "     method1-explain --help"
