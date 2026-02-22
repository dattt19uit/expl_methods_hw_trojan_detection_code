"""
Method 5: Gradient-Based Feature Attribution

Provides feature attribution for explaining hardware trojan predictions.
Supports both XGBoost (feature importance) and SVM (gradient-based).
"""

from .gradient_explainer import GradientAttributionExplainer

__version__ = "1.0.0"
__all__ = ['GradientAttributionExplainer']
