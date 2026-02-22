# Explainable Hardware Trojan Detection Methods

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Research implementation for explainable AI-based hardware trojan detection using property-based, case-based, LIME, SHAP, and gradient attribution methods on Trust-Hub benchmark circuits.

---

## Quick Start

```bash
# 1. Clone and navigate
git clone https://github.com/paulwhitten/expl_methods_hw_trojan_detection_code.git
cd expl_methods_hw_trojan_detection_code

# 2. Install (auto-detects OS and dependencies)
./scripts/setup_environment.sh
source .venv/bin/activate

# 3. Create Trust-Hub page cache (required -- see Usage below)
#    Save https://trust-hub.org/#/benchmarks/chip-level-trojan as configs/trust_hub_page.html

# 4. Run pipeline (Phases 0-11, runs in background, logs to logs/)
./run_full_pipeline_background.sh

# 5. Run statistical analysis (confidence intervals, McNemar tests, effect sizes)
./run_complete_analysis.sh
```

---

## Methods

| # | Method | Approach |
|---|--------|----------|
| 1 | Property-Based | 31 XGBoost models over feature subsets, majority-vote ensemble |
| 2 | Case-Based | XGBoost classifier with k-NN explanations |
| 3 | LIME | Local Interpretable Model-agnostic Explanations |
| 4 | SHAP | SHapley Additive exPlanations (TreeExplainer) |
| 5 | Gradient Attribution | Gradient-based feature attributions for XGBoost |

---

## Installation

### Prerequisites

- Python 3.8+
- GraphViz + development headers (for circuit visualization)
- unrar (for Trust-Hub archives)

### Automated Setup

```bash
./scripts/setup_environment.sh
source .venv/bin/activate
```

Supports Debian, Ubuntu, Fedora, RHEL, CentOS, Arch Linux, openSUSE, macOS.

### Manual Installation

```bash
# System dependencies (Debian/Ubuntu)
sudo apt-get install graphviz libgraphviz-dev unrar

# Python environment
python3 -m venv .venv
source .venv/bin/activate

# Install all packages
./scripts/install_all.sh
```

---

## Usage

### Trust-Hub Page Cache

Before running the pipeline, create the Trust-Hub page cache:

1. Visit https://trust-hub.org/#/benchmarks/chip-level-trojan in a browser
2. Wait for all download links to appear, you may want to scroll through all trojans
3. Save as `configs/trust_hub_page.html`

Trust-Hub is a JavaScript SPA that cannot be directly scraped.

### Run the Pipeline

```bash
./run_full_pipeline_background.sh
```

Phases 0-11: download circuits, extract features, train models, optimize thresholds, generate explanations for all five methods. Output goes to `data/` (gitignored).

To run the pipeline in the foreground instead (useful for debugging):

```bash
./scripts/run_pipeline.sh
```

### Statistical Analysis

```bash
./run_complete_analysis.sh
```

Runs bootstrap confidence intervals (baseline and optimized thresholds), McNemar tests, and effect size calculations.

---

## Project Structure

```
.
├── packages/
│   ├── shared/                        # Core: circuit processing, data handling, netlist parsing
│   ├── data-acquisition/              # Trust-Hub downloader
│   ├── method1-property-based/        # Property-Based (31 XGBoost models)
│   ├── method2-case-based/            # Case-Based (XGBoost + k-NN)
│   ├── method3-lime/                  # LIME explanations
│   ├── method4-shap/                  # SHAP explanations
│   └── method5-gradient-attribution/  # Gradient attributions
│
├── scripts/
│   ├── setup_environment.sh           # Install system + Python deps
│   ├── install_all.sh                 # pip install all packages
│   ├── run_pipeline.sh                # Pipeline entry point
│   └── statistical_analysis/          # Bootstrap CI, McNemar, effect sizes
│
├── configs/
│   ├── circuit_configs.json           # Circuit metadata + trojan ground truth
│   └── pipeline_config.yaml           # Pipeline configuration
│
├── run_full_pipeline_background.sh    # Run pipeline in background
├── run_complete_analysis.sh           # Statistical analysis (post-pipeline)
├── package_results.sh                 # Archive results for sharing
│
└── data/                              # Generated output (gitignored)
```

---

## Dataset

**30 Trust-Hub Benchmark Circuits** from [trust-hub.org](https://trust-hub.org)

Each sample is one gate in a circuit, labeled trojan or clean.

| Metric | Value |
|--------|-------|
| Circuits | 30 (all contain trojans) |
| Total gate samples | 56,959 |
| Training (80%) | 45,567 |
| Test (20%) | 11,392 |
| Clean gates | 56,601 (99.4%) |
| Trojan gates | 358 (0.6%) |
| Features per gate | 5 (LGFi, ffi, ffo, PI, PO) |

Stratified 80/20 split preserving trojan ratio. Random seed: 42.

---

## Reproducibility

- **Random seed:** 42 throughout
- **Method 1:** 31 XGBoost models (all non-empty subsets of 5 features), per-property threshold optimization, majority vote
- **Method 2:** XGBoost with balanced class weighting, threshold optimized at 0.98

---

## Citation

If you use this code in your research, please cite:

```bibtex
@article{whitten2026explainability,
  title={Explainability Methods for Hardware Trojan Detection: A Systematic Comparison},
  author={Whitten, Paul and Wolff, Francis and Papachristou, Chris},
  journal={arXiv preprint arXiv:2601.18696},
  year={2026}
}
```

Method 2 uses [case-explainer](https://github.com/paulwhitten/case-explainer) for case-based explanations:

```bibtex
@software{case_explainer2025,
  author = {Whitten, Paul and Wolff, Francis and Papachristou, Chris},
  title = {Case-Explainer: General-Purpose Case-Based Explainability},
  year = {2025},
  url = {https://github.com/paulwhitten/case-explainer}
}
```

---

## Troubleshooting

**`ImportError: No module named 'pygraphviz'`** -- Install GraphViz dev headers first:
```bash
sudo apt-get install graphviz libgraphviz-dev  # Debian/Ubuntu
sudo dnf install graphviz graphviz-devel        # Fedora/RHEL
pip install --force-reinstall pygraphviz
```

**`FileNotFoundError: unrar not found`** -- `sudo apt-get install unrar`

**Out of memory during circuit processing** -- Reduce parallelism: `xai-process-circuit ... -j 4`

**`ModuleNotFoundError: No module named 'xai_shared'`** -- Reinstall:
```bash
pip install -e packages/shared
pip install -e packages/method1-property-based
```

---

## Third-Party Code

This repository includes a vendored and modified copy of
[circuitgraph](https://github.com/circuitgraph/circuitgraph) (v0.2.1)
by Ruben Purdy and Joseph Sweeney (Carnegie Mellon University),
licensed under the MIT License. See
`packages/shared/xai_shared/circuitgraph/LICENSE` for the original license.

---

## License

MIT License - see [LICENSE](LICENSE)
