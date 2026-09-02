"""
Setup configuration for xai_shared package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="xai-shared",
    version="1.0.0",
    author="Paul Whitten, Francis Wolff, Chris Papachristou",
    author_email="pcw@case.edu",
    description="Shared infrastructure for XAI hardware trojan detection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/paulwhitten/expl_methods_hw_trojan_detection_code",
    packages=find_packages(),
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
        # circuitgraph is vendored (modified) in xai_shared/circuitgraph/
        # Its transitive deps (lark, networkx) must be listed here explicitly:
        "lark>=1.1.0",
        "networkx>=3.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scikit-learn>=1.3.0",
        "matplotlib>=3.7.0",
        "scipy>=1.10.0",
        "pygraphviz>=1.11",  # Requires GraphViz system libraries (see setup_environment.sh)
        "statsmodels>=0.13.0",  # Required for McNemar tests in statistical analysis
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "xai-process-circuit=xai_shared.circuit_processing.cli:main",
            "xai-aggregate-data=xai_shared.data_handling.cli:main",
            "xai-compute-graph-metrics=xai_shared.circuit_processing.compute_graph_metrics_cli:main",
        ],
    },
)
