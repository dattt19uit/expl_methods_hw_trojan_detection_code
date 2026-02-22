#!/usr/bin/env python3
"""
McNemar Statistical Tests for Phase 4 Analysis

Tests if accuracy differences between methods are statistically significant.
"""

import numpy as np
import pandas as pd
import json
from pathlib import Path
from statsmodels.stats.contingency_tables import mcnemar
import argparse


def compute_mcnemar_test(predictions1, predictions2, labels, name1="Method 1", name2="Method 2"):
    """
    Perform McNemar test for paired binary classifications.
    
    Parameters:
    - predictions1: binary predictions from method 1
    - predictions2: binary predictions from method 2
    - labels: ground truth labels
    - name1, name2: descriptive method names
    
    Returns:
    - dict with test statistic, p-value, contingency table, interpretation
    """
    # Convert to numpy arrays
    pred1 = np.array(predictions1, dtype=int)
    pred2 = np.array(predictions2, dtype=int)
    labels = np.array(labels, dtype=int)
    
    # Compute correctness for each method
    correct1 = (pred1 == labels)
    correct2 = (pred2 == labels)
    
    # Build contingency table
    # Rows: Method 1 (correct, incorrect)
    # Cols: Method 2 (correct, incorrect)
    both_correct = np.sum(correct1 & correct2)
    method1_only = np.sum(correct1 & ~correct2)
    method2_only = np.sum(~correct1 & correct2)
    both_incorrect = np.sum(~correct1 & ~correct2)
    
    contingency_table = [
        [both_correct, method2_only],
        [method1_only, both_incorrect]
    ]
    
    # Perform McNemar test
    # Use exact=False for chi-square approximation (faster, valid for large samples)
    # Use exact=True for exact test (better for small discordant pairs)
    n_discordant = method1_only + method2_only
    use_exact = n_discordant < 25
    
    result = mcnemar(contingency_table, exact=use_exact)
    
    # Compute accuracies
    acc1 = np.mean(correct1)
    acc2 = np.mean(correct2)
    acc_diff = acc2 - acc1
    
    # Interpret significance
    if result.pvalue < 0.001:
        significance = "***"
        interpretation = "highly significant difference"
    elif result.pvalue < 0.01:
        significance = "**"
        interpretation = "very significant difference"
    elif result.pvalue < 0.05:
        significance = "*"
        interpretation = "significant difference"
    else:
        significance = "ns"
        interpretation = "no significant difference"
    
    return {
        'method1': name1,
        'method2': name2,
        'statistic': float(result.statistic),
        'p_value': float(result.pvalue),
        'significance': significance,
        'interpretation': interpretation,
        'test_type': 'exact' if use_exact else 'chi-square',
        'accuracy_method1': float(acc1),
        'accuracy_method2': float(acc2),
        'accuracy_difference': float(acc_diff),
        'contingency_table': {
            'both_correct': int(both_correct),
            'method1_only_correct': int(method1_only),
            'method2_only_correct': int(method2_only),
            'both_incorrect': int(both_incorrect)
        },
        'n_samples': len(labels),
        'n_discordant_pairs': int(n_discordant)
    }


def load_method_predictions(results_dir):
    """
    Load predictions from all methods.
    
    Returns dict with predictions and labels for each method.
    """
    results_dir = Path(results_dir)
    predictions = {}
    
    # Method 1: Property-Based
    method1_path = results_dir / "method1" / "kb_test_results.json"
    if method1_path.exists():
        with open(method1_path) as f:
            data = json.load(f)
            predictions['method1'] = {
                'predictions': np.array([int(p) for p in data.get('predictions', [])]),
                'labels': np.array([int(l) for l in data.get('labels', [])])
            }
    
    # Method 2: Case-Based
    method2_path = results_dir / "method2" / "classification_results.json"
    if method2_path.exists():
        with open(method2_path) as f:
            data = json.load(f)
            predictions['method2'] = {
                'predictions': np.array([int(p) for p in data.get('predictions', [])]),
                'labels': np.array([int(l) for l in data.get('labels', [])])
            }
    
    return predictions


def compute_all_mcnemar_tests(results_dir, output_file):
    """
    Compute McNemar tests for all method pairs.
    
    Parameters:
    - results_dir: directory containing method results
    - output_file: output JSON file path
    """
    results_dir = Path(results_dir)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("McNemar Pairwise Comparison Tests")
    print("="*60)
    print("")
    
    # Load predictions
    print("Loading method predictions...")
    predictions = load_method_predictions(results_dir)
    
    if not predictions:
        print("[WARNING] No prediction data found!")
        print("This script will be ready to run once pipeline completes.")
        return None
    
    print(f"[OK] Loaded predictions from {len(predictions)} methods")
    for method, data in predictions.items():
        print(f"  - {method}: {len(data['predictions'])} samples")
    print("")
    
    # Compute all pairwise tests
    print("Computing pairwise McNemar tests...")
    print("-" * 60)
    
    test_results = {}
    method_names = list(predictions.keys())
    
    for i, method1 in enumerate(method_names):
        for method2 in method_names[i+1:]:
            pred1 = predictions[method1]['predictions']
            pred2 = predictions[method2]['predictions']
            labels = predictions[method1]['labels']
            
            # Ensure same samples
            if len(pred1) != len(pred2) or len(pred1) != len(labels):
                print(f"  [WARNING] Sample count mismatch for {method1} vs {method2}")
                continue
            
            result = compute_mcnemar_test(
                pred1, pred2, labels,
                name1=method1,
                name2=method2
            )
            
            key = f"{method1}_vs_{method2}"
            test_results[key] = result
            
            print(f"  {method1:12s} vs {method2:12s}:")
            print(f"    Accuracies: {result['accuracy_method1']:.3f} vs {result['accuracy_method2']:.3f} "
                  f"(delta = {result['accuracy_difference']:+.3f})")
            print(f"    McNemar: chi2 = {result['statistic']:.3f}, p = {result['p_value']:.4f} {result['significance']}")
            print(f"    {result['interpretation']}")
            print("")
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print("="*60)
    print(f"[OK] Results saved to: {output_file}")
    print("="*60)
    print("")
    
    # Print interpretation guide
    print("Interpretation:")
    print("-" * 60)
    print("McNemar's test assesses if two methods have significantly different")
    print("error rates on the same test set (paired data).")
    print("")
    print("Significance levels:")
    print("  *** p < 0.001 (highly significant difference)")
    print("  **  p < 0.01  (very significant difference)")
    print("  *   p < 0.05  (significant difference)")
    print("  ns  p >= 0.05 (no significant difference)")
    print("")
    print("Contingency table:")
    print("  both_correct: Both methods predict correctly")
    print("  method1_only_correct: Only method 1 correct")
    print("  method2_only_correct: Only method 2 correct")
    print("  both_incorrect: Both methods predict incorrectly")
    
    return test_results


def main():
    parser = argparse.ArgumentParser(description='Compute McNemar tests')
    parser.add_argument('--results-dir', default='data/models',
                       help='Directory containing model results')
    parser.add_argument('--output', default='data/statistical_analysis/mcnemar_tests.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    compute_all_mcnemar_tests(args.results_dir, args.output)


if __name__ == '__main__':
    main()
