"""
Gradient-Based Feature Attribution for Hardware Trojan Detection

This module implements feature attribution for explaining trojan predictions.
Supports both XGBoost (default, using feature importance) and SVM (using gradients).

For XGBoost: Uses built-in feature importance (gain-based) for fast attribution
For SVM: Computes gradient of decision function w.r.t. input features

Author: XAI Framework
Date: December 13, 2025
"""

import numpy as np
from scipy.stats import spearmanr, pearsonr
import warnings
from typing import Dict, List, Tuple, Optional, Union
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


class GradientAttributionExplainer:
    """
    Feature attribution for trojan detection (XGBoost and SVM).
    
    For XGBoost: Uses built-in feature importance (gain-based) - FAST!
    For SVM: Computes gradient of decision function - slower but interpretable
    
    Attributes:
        model: Trained model (XGBoost or SVM)
        feature_names: List of feature names
        model_type: 'XGBoost' or 'SVM' (auto-detected)
        epsilon: Finite difference step size (for SVM gradients)
        n_features: Number of features
    """
    
    def __init__(self, model, feature_names: List[str], epsilon: float = 1e-5):
        """
        Initialize feature attribution explainer.
        
        Args:
            model: Trained model (XGBoost or SVM)
            feature_names: List of feature names for interpretation
            epsilon: Finite difference step size for SVM gradients (default 1e-5)
        """
        self.model = model
        self.feature_names = feature_names
        self.epsilon = epsilon
        self.n_features = len(feature_names)
        
        # Auto-detect model type
        self.model_type = self._detect_model_type()
        
        # Store stats for gradient normalization
        self.gradient_stats = {
            'mean': None,
            'std': None,
            'min': None,
            'max': None
        }
    
    def _detect_model_type(self) -> str:
        """Auto-detect whether model is XGBoost or SVM."""
        model_class = type(self.model).__name__
        
        if HAS_XGBOOST and isinstance(self.model, (xgb.XGBClassifier, xgb.Booster)):
            return 'XGBoost'
        elif 'XGB' in model_class:
            return 'XGBoost'
        elif hasattr(self.model, 'decision_function') and 'SV' in model_class:
            return 'SVM'
        elif hasattr(self.model, 'decision_function'):
            return 'SVM'
        else:
            raise ValueError(
                f"Cannot determine model type for {model_class}. "
                "Expected XGBoost or SVM model."
            )
    
    def get_feature_importance_xgboost(self, importance_type: str = 'gain') -> np.ndarray:
        """Get XGBoost feature importance scores."""
        if self.model_type != 'XGBoost':
            raise ValueError("This method only works with XGBoost models")
        
        importance_dict = self.model.get_booster().get_score(importance_type=importance_type)
        
        importance = np.zeros(self.n_features)
        for i in range(self.n_features):
            key = f'f{i}'
            importance[i] = importance_dict.get(key, 0.0)
        
        return importance
    
    def compute_gradient(self, x_sample: np.ndarray, method: str = 'central') -> np.ndarray:
        """
        Compute feature attribution for a sample.
        
        For XGBoost: Returns global feature importance (gain-based)
        For SVM: Computes gradient of decision function
        """
        x_sample = np.asarray(x_sample).flatten()
        
        if len(x_sample) != self.n_features:
            raise ValueError(
                f"Sample has {len(x_sample)} features, expected {self.n_features}"
            )
        
        # XGBoost: Use feature importance (fast!)
        if self.model_type == 'XGBoost':
            importance = self.get_feature_importance_xgboost(importance_type='gain')
            # Weight by feature values for sample-specific attribution
            attribution = importance * np.abs(x_sample)
            return attribution
        
        # SVM: Compute numerical gradient
        gradient = np.zeros(self.n_features)
        
        if method == 'central':
            for i in range(self.n_features):
                x_plus = x_sample.copy()
                x_minus = x_sample.copy()
                x_plus[i] += self.epsilon
                x_minus[i] -= self.epsilon
                
                f_plus = self.model.decision_function(x_plus.reshape(1, -1))[0]
                f_minus = self.model.decision_function(x_minus.reshape(1, -1))[0]
                
                gradient[i] = (f_plus - f_minus) / (2 * self.epsilon)
        
        elif method == 'forward':
            f_center = self.model.decision_function(x_sample.reshape(1, -1))[0]
            
            for i in range(self.n_features):
                x_plus = x_sample.copy()
                x_plus[i] += self.epsilon
                
                f_plus = self.model.decision_function(x_plus.reshape(1, -1))[0]
                gradient[i] = (f_plus - f_center) / self.epsilon
        
        else:
            raise ValueError(f"Unknown method: {method}. Use 'central' or 'forward'.")
        
        return gradient
    
    def normalize_gradient(self, gradient: np.ndarray, method: str = 'l2') -> np.ndarray:
        """Normalize gradient to [0, 1] scale for interpretability."""
        abs_gradient = np.abs(gradient)
        
        if method == 'l2':
            norm = np.sqrt(np.sum(abs_gradient ** 2)) + 1e-10
        elif method == 'l1':
            norm = np.sum(abs_gradient) + 1e-10
        elif method == 'max':
            norm = np.max(abs_gradient) + 1e-10
        elif method == 'abs_sum':
            norm = np.sum(abs_gradient) + 1e-10
        else:
            raise ValueError(f"Unknown normalization method: {method}")
        
        return abs_gradient / norm
    
    def explain_prediction(
        self, 
        x_sample: np.ndarray,
        prediction: Optional[float] = None,
        prediction_confidence: Optional[float] = None,
        top_k: int = 3,
        show_direction: bool = True
    ) -> Dict:
        """
        Generate complete explanation from gradient analysis.
        
        Returns dict with:
        - 'raw_attribution': Raw attribution values
        - 'normalized_importance': L2-normalized importance scores
        - 'top_features': Top k features with interpretation
        - 'prediction': Prediction value
        - 'model_type': 'XGBoost' or 'SVM'
        - 'method': 'feature_attribution' or 'gradient_attribution'
        """
        # Compute attribution
        attribution = self.compute_gradient(x_sample)
        
        # Normalize
        normalized = self.normalize_gradient(attribution, method='l2')
        
        # Get prediction if not provided
        if prediction is None:
            if self.model_type == 'XGBoost':
                pred_proba = self.model.predict_proba(x_sample.reshape(1, -1))[0]
                prediction = pred_proba[1]  # Probability of trojan class
            else:
                prediction = self.model.decision_function(x_sample.reshape(1, -1))[0]
        
        # Sort by importance
        sorted_idx = np.argsort(normalized)[::-1]
        
        # Generate interpretation for top features
        interpretation = []
        for rank, idx in enumerate(sorted_idx[:top_k]):
            direction = "increases" if attribution[idx] > 0 else "decreases"
            
            if self.model_type == 'XGBoost':
                interp_str = (
                    f"{self.feature_names[idx]} (importance: {normalized[idx]:.1%}, "
                    f"value: {x_sample[idx]:.4f}) - high importance feature"
                )
            else:
                interp_str = (
                    f"{self.feature_names[idx]} (importance: {normalized[idx]:.1%}, "
                    f"gradient: {attribution[idx]:+.4f}) {direction}s trojan likelihood"
                )
            
            interpretation.append({
                'rank': rank + 1,
                'feature': self.feature_names[idx],
                'feature_value': float(x_sample[idx]),
                'importance': float(normalized[idx]),
                'attribution': float(attribution[idx]),
                'direction': direction if show_direction else None,
                'interpretation': interp_str
            })
        
        return {
            'raw_attribution': attribution.tolist(),
            'normalized_importance': normalized.tolist(),
            'top_features': interpretation,
            'full_feature_importance': [
                {
                    'feature': self.feature_names[i],
                    'importance': float(normalized[i]),
                    'attribution': float(attribution[i])
                }
                for i in sorted_idx
            ],
            'prediction': float(prediction),
            'prediction_confidence': prediction_confidence,
            'model_type': self.model_type,
            'method': 'feature_attribution' if self.model_type == 'XGBoost' else 'gradient_attribution'
        }
