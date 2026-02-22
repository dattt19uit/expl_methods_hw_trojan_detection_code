#!/usr/bin/env python3
"""
Bootstrap Confidence Intervals for Phase 4 Statistical Analysis

Computes 95% confidence intervals for key metrics using bootstrap resampling.

Supports both baseline (threshold=0.5) and optimized threshold evaluation.
Use --use-optimized-thresholds to compute CIs at optimized operating points.
"""

import numpy as np
import pandas as pd
import json
from pathlib import Path
from scipy import stats
import argparse


def bootstrap_ci(data, metric_func, n_iterations=10000, confidence=0.95, seed=None):
    """
    Compute bootstrap confidence interval for a metric.
    
    Parameters:
    - data: array-like, input data
    - metric_func: function that computes the metric from data
    - n_iterations: number of bootstrap samples
    - confidence: confidence level (default 0.95 for 95% CI)
    - seed: random seed for reproducibility (optional)
    
    Returns:
    - dict with mean, lower_bound, upper_bound, std_error
    """
    # Set random seed if provided
    if seed is not None:
        np.random.seed(seed)
    
    # Convert to numpy array for efficient indexing
    data_array = np.array(data, dtype=object)
    n = len(data_array)
    bootstrap_stats = []
    
    print(f"  Running {n_iterations} bootstrap iterations...")
    if seed is not None:
        print(f"  Random seed: {seed} (for reproducibility)")
    
    for i in range(n_iterations):
        if i % 2000 == 0 and i > 0:
            print(f"    Progress: {i}/{n_iterations} ({i/n_iterations*100:.1f}%)")
        
        # Resample with replacement
        indices = np.random.choice(n, size=n, replace=True)
        sample = [data_array[idx] for idx in indices]
        
        # Compute metric on sample
        stat = metric_func(sample)
        bootstrap_stats.append(stat)
    
    # Compute percentiles
    alpha = (1 - confidence) / 2
    lower = np.percentile(bootstrap_stats, alpha * 100)
    upper = np.percentile(bootstrap_stats, (1 - alpha) * 100)
    mean = np.mean(bootstrap_stats)
    std_error = np.std(bootstrap_stats)
    
    return {
        'mean': float(mean),
        'lower': float(lower),
        'upper': float(upper),
        'std_error': float(std_error),
        'confidence': confidence
    }


def accuracy_metric(predictions_labels):
    """Compute accuracy from (predictions, labels) tuples"""
    predictions, labels = zip(*predictions_labels)
    return np.mean(np.array(predictions) == np.array(labels))


def precision_metric(predictions_labels):
    """Compute precision from (predictions, labels) tuples"""
    predictions, labels = zip(*predictions_labels)
    predictions = np.array(predictions)
    labels = np.array(labels)
    
    true_positives = np.sum((predictions == 1) & (labels == 1))
    false_positives = np.sum((predictions == 1) & (labels == 0))
    
    if true_positives + false_positives == 0:
        return 0.0
    return true_positives / (true_positives + false_positives)


def recall_metric(predictions_labels):
    """Compute recall from (predictions, labels) tuples"""
    predictions, labels = zip(*predictions_labels)
    predictions = np.array(predictions)
    labels = np.array(labels)
    
    true_positives = np.sum((predictions == 1) & (labels == 1))
    false_negatives = np.sum((predictions == 0) & (labels == 1))
    
    if true_positives + false_negatives == 0:
        return 0.0
    return true_positives / (true_positives + false_negatives)


def f1_metric(predictions_labels):
    """Compute F1 score from (predictions, labels) tuples"""
    prec = precision_metric(predictions_labels)
    rec = recall_metric(predictions_labels)
    
    if prec + rec == 0:
        return 0.0
    return 2 * (prec * rec) / (prec + rec)


def compute_all_confidence_intervals(results_dir, output_file, n_iterations=10000,
                                     confidence=0.95, seed=None,
                                     use_optimized_thresholds=False):
    """
    Compute confidence intervals for all key metrics.
    
    Parameters:
    - results_dir: directory containing model results
    - output_file: output JSON file path
    - n_iterations: number of bootstrap iterations
    - confidence: confidence level (default 0.95)
    - seed: random seed for reproducibility (optional)
    - use_optimized_thresholds: if True, re-threshold probabilities using
      optimized thresholds from optimal_threshold(s).json files
    """
    results_dir = Path(results_dir)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    threshold_mode = "OPTIMIZED" if use_optimized_thresholds else "BASELINE (0.5)"
    
    print("="*60)
    print("Bootstrap Confidence Interval Computation")
    print("="*60)
    print(f"Threshold Mode: {threshold_mode}")
    print(f"Iterations: {n_iterations}")
    print(f"Confidence Level: {confidence*100:.0f}%")
    if seed is not None:
        print(f"Random Seed: {seed}")
    print("")
    
    all_results = {}
    
    # Method 1: Property-Based
    print("Method 1: Property-Based Detection")
    print("-" * 60)
    
    if use_optimized_thresholds:
        pred_label_pairs = _load_method1_optimized(results_dir)
    else:
        pred_label_pairs = _load_method1_baseline(results_dir)
    
    if pred_label_pairs is not None:
        print(f"  Samples: {len(pred_label_pairs)}")
        all_results['method1'] = {
            'accuracy': bootstrap_ci(pred_label_pairs, accuracy_metric, n_iterations, confidence, seed),
            'precision': bootstrap_ci(pred_label_pairs, precision_metric, n_iterations, confidence, seed),
            'recall': bootstrap_ci(pred_label_pairs, recall_metric, n_iterations, confidence, seed),
            'f1': bootstrap_ci(pred_label_pairs, f1_metric, n_iterations, confidence, seed)
        }
        print(f"  [OK] Computed CIs for accuracy, precision, recall, F1")
    
    print("")
    
    # Method 2: Case-Based (XGBoost)
    print("Method 2: Case-Based Detection")
    print("-" * 60)
    
    if use_optimized_thresholds:
        pred_label_pairs = _load_method2_optimized(results_dir)
    else:
        pred_label_pairs = _load_method2_baseline(results_dir)
    
    if pred_label_pairs is not None:
        print(f"  Samples: {len(pred_label_pairs)}")
        all_results['method2'] = {
            'accuracy': bootstrap_ci(pred_label_pairs, accuracy_metric, n_iterations, confidence, seed),
            'precision': bootstrap_ci(pred_label_pairs, precision_metric, n_iterations, confidence, seed),
            'recall': bootstrap_ci(pred_label_pairs, recall_metric, n_iterations, confidence, seed),
            'f1': bootstrap_ci(pred_label_pairs, f1_metric, n_iterations, confidence, seed)
        }
        print(f"  [OK] Computed CIs for accuracy, precision, recall, F1")
    
    print("")
    
    # Save results
    metadata = {
        'threshold_mode': 'optimized' if use_optimized_thresholds else 'baseline',
        'n_iterations': n_iterations,
        'confidence': confidence,
        'seed': seed
    }
    output_data = {'metadata': metadata, **all_results}
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print("="*60)
    print(f"[OK] Results saved to: {output_file}")
    print("="*60)
    print("")
    
    # Print summary
    print("Summary:")
    print("-" * 60)
    for method_key in ['method1', 'method2']:
        if method_key not in all_results:
            continue
        metrics = all_results[method_key]
        print(f"\n{method_key.upper()} ({threshold_mode}):")
        for metric_name, ci in metrics.items():
            print(f"  {metric_name:12s}: {ci['mean']:.3f} (95% CI: {ci['lower']:.3f}-{ci['upper']:.3f})")
    
    return all_results


def _load_method1_baseline(results_dir):
    """Load Method 1 predictions at default threshold (majority vote on 0.5 thresholds)."""
    path = results_dir / "method1" / "kb_test_results.json"
    if not path.exists():
        print(f"  [WARNING] Results file not found: {path}")
        return None
    with open(path) as f:
        data = json.load(f)
    predictions = np.array([int(p) for p in data['predictions']])
    labels = np.array([int(l) for l in data['labels']])
    return list(zip(predictions, labels))


def _load_method1_optimized(results_dir):
    """
    Load Method 1 predictions using per-property optimized thresholds.
    
    Each of 31 property models has its own optimal threshold.
    Re-threshold each model's probabilities, then majority-vote.
    """
    proba_path = results_dir / "method1" / "test_proba.json"
    labels_path = results_dir / "method1" / "test_labels.json"
    thresh_path = results_dir / "method1" / "optimal_thresholds.json"
    
    for p in [proba_path, labels_path, thresh_path]:
        if not p.exists():
            print(f"  [WARNING] Missing: {p}")
            return None
    
    with open(proba_path) as f:
        all_proba = json.load(f)  # list of 31 arrays, each [n_samples][2]
    with open(labels_path) as f:
        labels = json.load(f)  # [n_samples]
    with open(thresh_path) as f:
        thresholds_data = json.load(f)
    
    n_properties = len(all_proba)
    n_samples = len(labels)
    
    # Build per-property optimized predictions
    votes = np.zeros(n_samples, dtype=int)
    thresholds_used = []
    
    for i in range(n_properties):
        key = f"property_{i}"
        if key not in thresholds_data:
            # Fall back to 0.5 if no optimized threshold
            thresh = 0.5
        else:
            thresh = thresholds_data[key].get('optimal_threshold', 0.5)
        thresholds_used.append(thresh)
        
        proba = np.array(all_proba[i])
        # proba[j] = [p_clean, p_trojan]; predict trojan if p_trojan >= threshold
        trojan_proba = proba[:, 1] if proba.ndim == 2 else proba
        property_preds = (trojan_proba >= thresh).astype(int)
        votes += property_preds
    
    # Majority vote: predict trojan if > half the properties say trojan
    majority = n_properties / 2
    predictions = (votes > majority).astype(int)
    labels_arr = np.array([int(l) for l in labels])
    
    print(f"  Optimized thresholds: min={min(thresholds_used):.2f}, "
          f"max={max(thresholds_used):.2f}, mean={np.mean(thresholds_used):.2f}")
    print(f"  Trojan predictions: {predictions.sum()} / {n_samples}")
    
    return list(zip(predictions, labels_arr))


def _load_method2_baseline(results_dir):
    """Load Method 2 predictions at default threshold=0.5."""
    path = results_dir / "method2" / "classification_results.json"
    if not path.exists():
        print(f"  [WARNING] Results file not found: {path}")
        return None
    with open(path) as f:
        data = json.load(f)
    predictions = np.array([int(p) for p in data['predictions']])
    labels = np.array([int(l) for l in data['labels']])
    return list(zip(predictions, labels))


def _load_method2_optimized(results_dir):
    """
    Load Method 2 predictions re-thresholded at the optimized threshold.
    
    Reads raw probabilities from classification_results.json or predictions.json,
    applies the threshold from optimal_threshold.json.
    """
    thresh_path = results_dir / "method2" / "optimal_threshold.json"
    if not thresh_path.exists():
        print(f"  [WARNING] Missing: {thresh_path}")
        return None
    
    with open(thresh_path) as f:
        thresh_data = json.load(f)
    threshold = thresh_data['optimal']['threshold']
    print(f"  Optimized threshold: {threshold}")
    
    # Try classification_results.json first (has probabilities), then predictions.json
    for fname in ["classification_results.json", "predictions.json"]:
        path = results_dir / "method2" / fname
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            if 'probabilities' in data:
                proba = np.array(data['probabilities'])
                labels = np.array([int(l) for l in data['labels']])
                # proba[i] = [p_clean, p_trojan]
                trojan_proba = proba[:, 1] if proba.ndim == 2 else proba
                predictions = (trojan_proba >= threshold).astype(int)
                print(f"  Re-thresholded from {fname}: {predictions.sum()} trojan predictions / {len(labels)} samples")
                return list(zip(predictions, labels))
    
    print(f"  [WARNING] No probability data found in method2/")
    return None


def main():
    parser = argparse.ArgumentParser(description='Compute bootstrap confidence intervals')
    parser.add_argument('--results-dir', default='data/models',
                       help='Directory containing model results')
    parser.add_argument('--output', default=None,
                       help='Output JSON file (default: auto-named based on threshold mode)')
    parser.add_argument('--n-iterations', type=int, default=10000,
                       help='Number of bootstrap iterations (default: 10000)')
    parser.add_argument('--confidence', type=float, default=0.95,
                       help='Confidence level (default: 0.95 for 95%% CI)')
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed for reproducibility (optional)')
    parser.add_argument('--use-optimized-thresholds', action='store_true',
                       help='Compute CIs at optimized thresholds instead of baseline (0.5)')
    
    args = parser.parse_args()
    
    # Default output path depends on threshold mode
    if args.output is None:
        if args.use_optimized_thresholds:
            args.output = 'data/statistical_analysis/confidence_intervals_optimized.json'
        else:
            args.output = 'data/statistical_analysis/confidence_intervals.json'
    
    compute_all_confidence_intervals(
        args.results_dir, args.output, args.n_iterations, args.confidence,
        args.seed, args.use_optimized_thresholds
    )


if __name__ == '__main__':
    main()
