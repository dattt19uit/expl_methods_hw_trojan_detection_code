"""
Setup configuration for method1 package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="xai-method1",
    version="1.0.0",
    author="Paul Whitten, Francis Wolff, Chris Papachristou",
    author_email="pcw@case.edu",
    description="Property-Based XAI method for hardware trojan detection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/paulwhitten/expl_methods_hw_trojan_detection_code",
    packages=find_packages(exclude=["src", "src.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "xai-shared>=1.0.0",  # Depends on shared package
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scikit-learn>=1.3.0",
        "scipy>=1.10.0",
        "xgboost>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "method1-tune=method1.tuning.cli:main",
            "method1-train=method1.training.cli:main",
            "method1-train-xgboost=method1.training.cli_xgboost:main",
            "method1-kb=method1.kb_processing.cli:main",
            "method1-explain=method1.explanations.cli:main",
            "method1-optimize-thresholds=method1.optimize_thresholds:main",
        ],
    },
)
