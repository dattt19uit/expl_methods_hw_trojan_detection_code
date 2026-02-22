"""
Setup configuration for method5-gradient-attribution package.
"""

from setuptools import setup, find_packages

setup(
    name="xai-method5-gradient-attribution",
    version="1.0.0",
    description="Gradient-based feature attribution for hardware trojan detection (XGBoost/SVM)",
    author="Paul Whitten, Francis Wolff, Chris Papachristou",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "scikit-learn>=1.0.0",
        "scipy>=1.7.0",
        "xgboost>=1.5.0",
        "xai-shared>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "method5-gradient=method5_gradient.cli:main",
        ],
    },
)
