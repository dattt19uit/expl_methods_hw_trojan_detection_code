#!/usr/bin/env python3
"""Print Python and library versions used by the pipeline."""

import sys


def get_version(module_name, import_name=None):
    """Try to import a module and return its version string."""
    if import_name is None:
        import_name = module_name
    try:
        mod = __import__(import_name)
        return getattr(mod, "__version__", "installed (version unknown)")
    except ImportError:
        return "NOT INSTALLED"


def main():
    print(f"Python          {sys.version}")
    print()

    # All external dependencies from setup.py files across packages
    libraries = [
        ("NumPy", "numpy"),
        ("pandas", "pandas"),
        ("scikit-learn", "sklearn"),
        ("XGBoost", "xgboost"),
        ("SciPy", "scipy"),
        ("matplotlib", "matplotlib"),
        ("statsmodels", "statsmodels"),
        ("LIME", "lime"),
        ("SHAP", "shap"),
        ("case-explainer", "case_explainer"),
        ("BeautifulSoup4", "bs4"),
        ("requests", "requests"),
        ("pygraphviz", "pygraphviz"),
        ("joblib", "joblib"),
    ]

    max_name = max(len(name) for name, _ in libraries)
    for name, import_name in libraries:
        version = get_version(name, import_name)
        print(f"{name:<{max_name}}  {version}")


if __name__ == "__main__":
    main()
