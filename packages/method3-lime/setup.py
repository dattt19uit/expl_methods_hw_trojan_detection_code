"""
Setup configuration for method3-lime package (LIME explanations).
"""

from setuptools import setup, find_packages

setup(
    name="xai-method3-lime",
    version="1.0.0",
    description="LIME (Local Interpretable Model-agnostic Explanations) for hardware trojan detection",
    author="Paul Whitten, Francis Wolff, Chris Papachristou",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "scikit-learn>=1.0.0",
        "lime>=0.2.0",
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
            "method3-lime=method3_lime.cli:main",
        ],
    },
)
