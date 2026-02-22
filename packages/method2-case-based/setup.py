"""
Method 2: Case-Based Reasoning for Hardware Trojan Detection

Setup script for installing method2 package and CLI commands.
"""

from setuptools import setup, find_packages

setup(
    name="method2-case-based",
    version="1.0.0",
    description="Case-based KNN trojan detection with explanations (Method 2)",
    author="Paul Whitten, Francis Wolff, Chris Papachristou",
    packages=find_packages(exclude=["src", "src.*"]),
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "scikit-learn>=1.0.0",
        "xgboost>=2.0.0",
        "case-explainer @ git+https://github.com/paulwhitten/case-explainer.git",
    ],
    entry_points={
        "console_scripts": [
            "method2-train=method2.training.cli:main",
            "method2-train-xgboost=method2.training.cli_xgboost:main",
            "method2-classify=method2.classification.cli:main",
            "method2-optimize-threshold=method2.optimize_threshold:main",
        ]
    },
    python_requires=">=3.8",
)
