#!/usr/bin/env python3
"""
Effect Size Calculations for Phase 4 Analysis

Computes Cohen's d and other effect sizes for accuracy differences.
Helps interpret practical significance beyond statistical significance.
"""

import numpy as np
import json
from pathlib import Path
import argparse


def cohens_d(mean1, std1, n1, mean2, std2, n2):
    """
    Compute Cohen's d effect size for two independent groups.
    
    Parameters:
    - mean1, mean2: means of two groups
    - std1, std2: standard deviations
    - n1, n2: sample sizes
    
    Returns:
    - Cohen's d value
    """
    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))
    
    # Cohen's d
    d = (mean1 - mean2) / pooled_std
    
    return d


def interpret_cohens_d(d):
    """
    Interpret Cohen's d magnitude.
    
    Standard interpretation:
    - |d| < 0.2: negligible
    - 0.2 <= |d| < 0.5: small
    - 0.5 <= |d| < 0.8: medium
    - |d| >= 0.8: large
    """
    abs_d = abs(d)
    
    if abs_d < 0.2:
        magnitude = "negligible"
    elif abs_d < 0.5:
        magnitude = "small"
    elif abs_d < 0.8:
        magnitude = "medium"
    else:
        magnitude = "large"
    
    return magnitude


def compute_accuracy_statistics(predictions, labels):
    """
    Compute mean and std for accuracy across bootstrap samples.
    
    For individual predictions, compute binary accuracy.
    """
    predictions = np.array(predictions)
    labels = np.array(labels)
    
    # Accuracy for this sample
    accuracy = np.mean(predictions == labels)
    
    return accuracy


def load_method_accuracies(results_dir):
    """
    Load accuracy metrics from all methods.
    
    Returns dict with mean accuracy for each method.
    """
    results_dir = Path(results_dir)
    accuracies = {}
    
    # Method 1: Property-Based
    method1_path = results_dir / "method1" / "kb_test_results.json"
    if method1_path.exists():
        with open(method1_path) as f:
            data = json.load(f)
            metrics = data.get('metrics', {})
            accuracies['method1'] = {
                'name': 'Property-Based',
                'accuracy': metrics.get('accuracy', 0.0),
                'precision': metrics.get('precision', 0.0),
                'recall': metrics.get('recall', 0.0),
                'f1': metrics.get('f1_score', 0.0)
            }
    
    # Method 2: Case-Based
    method2_path = results_dir / "method2" / "classification_results.json"
    if method2_path.exists():
        with open(method2_path) as f:
            data = json.load(f)
            metrics = data.get('metrics', {})
            accuracies['method2'] = {
                'name': 'Case-Based',
                'accuracy': metrics.get('accuracy', 0.0),
                'precision': metrics.get('precision', 0.0),
                'recall': metrics.get('recall', 0.0),
                'f1': metrics.get('f1_score', 0.0)
            }
    
    return accuracies


def compute_all_effect_sizes(ci_file, output_file):
    """
    Compute effect sizes for all metric differences.
    
    Uses bootstrap confidence intervals to estimate effect sizes.
    
    Parameters:
    - ci_file: JSON file with confidence intervals
    - output_file: output JSON file path
    """
    ci_file = Path(ci_file)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("Effect Size Analysis (Cohen's d)")
    print("="*60)
    print("")
    
    if not ci_file.exists():
        print(f"[WARNING] Confidence interval file not found: {ci_file}")
        print("Please run compute_confidence_intervals.py first.")
        return None
    
    # Load CI data
    with open(ci_file) as f:
        ci_data = json.load(f)
    
    print("Computing effect sizes from bootstrap confidence intervals...")
    print("-" * 60)
    
    effect_sizes = {}
    
    # CI data is nested: {method1: {accuracy: {mean, lower, upper, std_error}}, method2: {...}}
    methods = list(ci_data.keys())
    metrics = ['accuracy', 'precision', 'recall', 'f1']
    
    # Determine sample size from test data
    test_data_path = ci_file.parent.parent / "processed" / "test.csv"
    if test_data_path.exists():
        import csv
        with open(test_data_path) as f:
            n = sum(1 for _ in f) - 1  # subtract header
        print(f"  Test set size: n = {n}")
    else:
        n = 11392  # Known test set size
        print(f"  Using known test set size: n = {n}")
    
    # For each metric, compute pairwise effect sizes
    for metric in metrics:
        effect_sizes[metric] = {}
        
        print(f"\n{metric.upper()}:")
        
        for i, method1 in enumerate(methods):
            for method2 in methods[i+1:]:
                # Navigate nested structure
                m1_data = ci_data.get(method1, {}).get(metric)
                m2_data = ci_data.get(method2, {}).get(metric)
                
                if m1_data is None or m2_data is None:
                    continue
                
                # Get mean and CI width as proxy for std
                mean1 = m1_data['mean']
                ci_width1 = m1_data['upper'] - m1_data['lower']
                std1 = ci_width1 / 3.92  # Approximate std from 95% CI width
                
                mean2 = m2_data['mean']
                ci_width2 = m2_data['upper'] - m2_data['lower']
                std2 = ci_width2 / 3.92
                
                d = cohens_d(mean1, std1, n, mean2, std2, n)
                magnitude = interpret_cohens_d(d)
                
                comparison_key = f"{method1}_vs_{method2}"
                effect_sizes[metric][comparison_key] = {
                    'method1': method1,
                    'method2': method2,
                    'mean1': float(mean1),
                    'mean2': float(mean2),
                    'difference': float(mean2 - mean1),
                    'cohens_d': float(d),
                    'magnitude': magnitude
                }
                
                print(f"  {method1:12s} vs {method2:12s}:")
                print(f"    Means: {mean1:.3f} vs {mean2:.3f} (delta = {mean2-mean1:+.3f})")
                print(f"    Cohen's d: {d:+.3f} ({magnitude} effect)")
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(effect_sizes, f, indent=2)
    
    print("")
    print("="*60)
    print(f"[OK] Results saved to: {output_file}")
    print("="*60)
    print("")
    
    # Print interpretation guide
    print("Interpretation:")
    print("-" * 60)
    print("Cohen's d measures the standardized difference between two means.")
    print("It represents the difference in terms of standard deviations.")
    print("")
    print("Magnitude interpretation:")
    print("  |d| < 0.2:  negligible effect")
    print("  0.2 <= |d| < 0.5:  small effect")
    print("  0.5 <= |d| < 0.8:  medium effect")
    print("  |d| >= 0.8:  large effect")
    print("")
    print("Sign interpretation:")
    print("  Positive d: method1 performs better than method2")
    print("  Negative d: method2 performs better than method1")
    print("")
    print("Note: Statistical significance (p-value) tells you if a difference")
    print("      exists. Effect size tells you how meaningful that difference is.")
    
    return effect_sizes


def main():
    parser = argparse.ArgumentParser(description='Compute effect sizes')
    parser.add_argument('--ci-file', default='data/statistical_analysis/confidence_intervals.json',
                       help='Input confidence intervals JSON file')
    parser.add_argument('--output', default='data/statistical_analysis/effect_sizes.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    compute_all_effect_sizes(args.ci_file, args.output)


if __name__ == '__main__':
    main()
