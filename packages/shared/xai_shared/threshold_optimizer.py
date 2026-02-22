#!/usr/bin/env python3
"""
Universal Threshold Optimizer for XGBoost Classifiers

Optimizes decision thresholds to balance precision and recall for
imbalanced classification problems. Works with any binary classifier
that outputs probabilities.

Author: Paul Whitten, Francis Wolff, Chris Papachristou
Date: December 2025
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ThresholdMetrics:
    """Metrics for a specific threshold"""
    threshold: float
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    specificity: float
    tp: int
    fp: int
    tn: int
    fn: int
    
    @property
    def fpr(self) -> float:
        """False positive rate"""
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) > 0 else 0.0
    
    @property
    def fnr(self) -> float:
        """False negative rate"""
        return self.fn / (self.fn + self.tp) if (self.fn + self.tp) > 0 else 0.0


class ThresholdOptimizer:
    """
    Optimize classification thresholds for binary classifiers.
    
    Performs grid search over thresholds to find optimal decision boundary
    that balances precision and recall according to specified constraints.
    """
    
    def __init__(self, min_precision: float = 0.5, min_recall: float = 0.7):
        """
        Initialize optimizer with constraints.
        
        Args:
            min_precision: Minimum acceptable precision (default: 0.5)
            min_recall: Minimum acceptable recall (default: 0.7)
        """
        self.min_precision = min_precision
        self.min_recall = min_recall
    
    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> ThresholdMetrics:
        """
        Calculate classification metrics for given predictions.
        
        Args:
            y_true: True labels (0/1)
            y_pred: Predicted labels (0/1)
            
        Returns:
            ThresholdMetrics object with all metrics
        """
        # Confusion matrix
        tp = np.sum((y_true == 1) & (y_pred == 1))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        tn = np.sum((y_true == 0) & (y_pred == 0))
        fn = np.sum((y_true == 1) & (y_pred == 0))
        
        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        
        return ThresholdMetrics(
            threshold=0.0,  # Will be set by caller
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            specificity=specificity,
            tp=int(tp),
            fp=int(fp),
            tn=int(tn),
            fn=int(fn)
        )
    
    def optimize(
        self, 
        y_true: np.ndarray, 
        y_proba: np.ndarray,
        thresholds: Optional[np.ndarray] = None
    ) -> Tuple[float, ThresholdMetrics, List[ThresholdMetrics]]:
        """
        Find optimal threshold via grid search.
        
        Args:
            y_true: True labels (0/1)
            y_proba: Predicted probabilities for positive class
            thresholds: Array of thresholds to test (default: 0.01 to 0.99 by 0.01)
            
        Returns:
            Tuple of (optimal_threshold, optimal_metrics, all_metrics)
        """
        if thresholds is None:
            thresholds = np.arange(0.01, 1.0, 0.01)
        
        all_metrics = []
        feasible_metrics = []
        
        for threshold in thresholds:
            # Apply threshold
            y_pred = (y_proba >= threshold).astype(int)
            
            # Calculate metrics
            metrics = self.calculate_metrics(y_true, y_pred)
            metrics.threshold = threshold
            all_metrics.append(metrics)
            
            # Check if meets constraints
            if metrics.precision >= self.min_precision and metrics.recall >= self.min_recall:
                feasible_metrics.append(metrics)
        
        # Select best threshold
        if feasible_metrics:
            # Best = highest F1 score among feasible solutions
            optimal = max(feasible_metrics, key=lambda m: m.f1_score)
        else:
            # No feasible solution - find best compromise
            # Prioritize: maximize min(precision, recall) to balance both
            optimal = max(all_metrics, key=lambda m: min(m.precision, m.recall))
        
        return optimal.threshold, optimal, all_metrics
    
    def generate_report(
        self,
        optimal_threshold: float,
        optimal_metrics: ThresholdMetrics,
        all_metrics: List[ThresholdMetrics],
        baseline_threshold: float = 0.5
    ) -> Dict:
        """
        Generate comprehensive optimization report.
        
        Args:
            optimal_threshold: Optimal threshold found
            optimal_metrics: Metrics at optimal threshold
            all_metrics: All metrics from grid search
            baseline_threshold: Baseline threshold to compare against (default: 0.5)
            
        Returns:
            Dictionary with report data
        """
        # Find baseline metrics
        baseline_metrics = min(all_metrics, key=lambda m: abs(m.threshold - baseline_threshold))
        
        # Calculate improvements
        precision_improvement = (
            (optimal_metrics.precision - baseline_metrics.precision) / baseline_metrics.precision * 100
            if baseline_metrics.precision > 0 else float('inf')
        )
        
        recall_change = (
            (optimal_metrics.recall - baseline_metrics.recall) / baseline_metrics.recall * 100
            if baseline_metrics.recall > 0 else 0.0
        )
        
        fp_reduction = baseline_metrics.fp - optimal_metrics.fp
        fp_reduction_pct = fp_reduction / baseline_metrics.fp * 100 if baseline_metrics.fp > 0 else 0.0
        
        # Find key statistics
        max_f1 = max(all_metrics, key=lambda m: m.f1_score)
        max_precision = max(all_metrics, key=lambda m: m.precision)
        max_recall = max(all_metrics, key=lambda m: m.recall)
        
        return {
            'optimal': {
                'threshold': float(optimal_threshold),
                'precision': float(optimal_metrics.precision),
                'recall': float(optimal_metrics.recall),
                'f1_score': float(optimal_metrics.f1_score),
                'accuracy': float(optimal_metrics.accuracy),
                'specificity': float(optimal_metrics.specificity),
                'confusion_matrix': {
                    'tp': optimal_metrics.tp,
                    'fp': optimal_metrics.fp,
                    'tn': optimal_metrics.tn,
                    'fn': optimal_metrics.fn
                }
            },
            'baseline': {
                'threshold': float(baseline_metrics.threshold),
                'precision': float(baseline_metrics.precision),
                'recall': float(baseline_metrics.recall),
                'f1_score': float(baseline_metrics.f1_score),
                'accuracy': float(baseline_metrics.accuracy),
                'confusion_matrix': {
                    'tp': baseline_metrics.tp,
                    'fp': baseline_metrics.fp,
                    'tn': baseline_metrics.tn,
                    'fn': baseline_metrics.fn
                }
            },
            'improvement': {
                'precision_gain_percent': float(precision_improvement),
                'recall_change_percent': float(recall_change),
                'f1_gain_percent': float(
                    (optimal_metrics.f1_score - baseline_metrics.f1_score) / baseline_metrics.f1_score * 100
                    if baseline_metrics.f1_score > 0 else 0.0
                ),
                'false_positives_reduced': int(fp_reduction),
                'false_positives_reduction_percent': float(fp_reduction_pct)
            },
            'constraints': {
                'min_precision': float(self.min_precision),
                'min_recall': float(self.min_recall),
                'constraints_met': bool(
                    optimal_metrics.precision >= self.min_precision and 
                    optimal_metrics.recall >= self.min_recall
                )
            },
            'statistics': {
                'max_f1': {
                    'threshold': float(max_f1.threshold),
                    'f1_score': float(max_f1.f1_score),
                    'precision': float(max_f1.precision),
                    'recall': float(max_f1.recall)
                },
                'max_precision': {
                    'threshold': float(max_precision.threshold),
                    'precision': float(max_precision.precision),
                    'recall': float(max_precision.recall)
                },
                'max_recall': {
                    'threshold': float(max_recall.threshold),
                    'recall': float(max_recall.recall),
                    'precision': float(max_recall.precision)
                }
            },
            'threshold_sweep': [
                {
                    'threshold': float(m.threshold),
                    'precision': float(m.precision),
                    'recall': float(m.recall),
                    'f1_score': float(m.f1_score),
                    'accuracy': float(m.accuracy)
                }
                for m in all_metrics[::5]  # Every 5th to reduce size
            ]
        }
    
    def print_summary(self, report: Dict):
        """Print human-readable optimization summary."""
        print("=" * 70)
        print("THRESHOLD OPTIMIZATION SUMMARY")
        print("=" * 70)
        print()
        
        opt = report['optimal']
        base = report['baseline']
        imp = report['improvement']
        
        print(f"Optimal Threshold: {opt['threshold']:.3f} (baseline: {base['threshold']:.3f})")
        print()
        
        print("Performance Comparison:")
        print(f"  Metric      Baseline    Optimal     Change")
        print(f"  --------------------------------------------")
        print(f"  Precision   {base['precision']:6.2%}     {opt['precision']:6.2%}     {imp['precision_gain_percent']:+6.1f}%")
        print(f"  Recall      {base['recall']:6.2%}     {opt['recall']:6.2%}     {imp['recall_change_percent']:+6.1f}%")
        print(f"  F1 Score    {base['f1_score']:6.2%}     {opt['f1_score']:6.2%}     {imp['f1_gain_percent']:+6.1f}%")
        print(f"  Accuracy    {base['accuracy']:6.2%}     {opt['accuracy']:6.2%}")
        print()
        
        print("Confusion Matrix (Optimal):")
        cm = opt['confusion_matrix']
        print(f"  TP: {cm['tp']:4d}  FP: {cm['fp']:4d}")
        print(f"  FN: {cm['fn']:4d}  TN: {cm['tn']:4d}")
        print()
        
        print(f"False Positives Reduced: {imp['false_positives_reduced']} ({imp['false_positives_reduction_percent']:.1f}%)")
        print()
        
        constraints = report['constraints']
        status = "[OK] MET" if constraints['constraints_met'] else "[ERROR] NOT MET"
        print(f"Constraints: {status}")
        print(f"  Min Precision: {constraints['min_precision']:.1%} (achieved: {opt['precision']:.1%})")
        print(f"  Min Recall:    {constraints['min_recall']:.1%} (achieved: {opt['recall']:.1%})")
        print()
