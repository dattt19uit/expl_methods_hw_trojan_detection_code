"""
Method 2: Case-Based Reasoning for Hardware Trojan Detection

This package implements case-based trojan detection using k-Nearest Neighbors (KNN).
Explanations are provided via similarity to known trojan/clean samples.

Key Features:
- KNN classification with weighted correspondence
- Case-based explanations showing similar training samples
- Scikit-learn implementation for efficiency
- High correspondence rate (97.4% per paper)

Paper Reference: Section III-C
"""

__version__ = "0.1.0"

from .training import train_knn_model
from .classification import classify_and_explain

__all__ = [
    'train_knn_model',
    'classify_and_explain',
]
