"""
Method 4: SHAP (SHapley Additive exPlanations)

Provides Shapley value-based explanations for trojan predictions.
Uses TreeExplainer for XGBoost (fast) or KernelExplainer for SVM (slow).
"""

__version__ = "0.1.0"
