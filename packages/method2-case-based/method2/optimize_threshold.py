#!/usr/bin/env python3
"""
Threshold Optimizer for Method 2 (Case-Based XGBoost)

Optimizes the decision threshold to balance precision and recall
for the single unified XGBoost model in Method 2.

Usage:
    method2-optimize-threshold \\
        --predictions data/models/method2/predictions.json \\
        --test-data data/processed/test.csv \\
        --output data/models/method2/optimal_threshold.json \\
        --min-precision 0.5 \\
        --min-recall 0.7

Author: Paul Whitten, Francis Wolff, Chris Papachristou
Date: December 2025
"""

import argparse
import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# Import from shared package
from xai_shared import ThresholdOptimizer


def load_predictions(predictions_file):
    """Load Method 2 predictions with probabilities."""
    print(f"Loading predictions from {predictions_file}...")
    with open(predictions_file, 'r') as f:
        data = json.load(f)
    
    predictions = np.array(data['predictions'])
    probabilities = np.array(data['probabilities'])
    
    print(f"  Loaded {len(predictions)} predictions")
    return predictions, probabilities


def load_test_labels(test_data_file):
    """Load true labels from test CSV."""
    print(f"Loading test labels from {test_data_file}...")
    df = pd.read_csv(test_data_file)
    y_true = df['Trojan'].values
    
    trojans = np.sum(y_true == 1)
    clean = np.sum(y_true == 0)
    print(f"  Loaded {len(y_true)} labels ({clean} clean, {trojans} trojans)")
    
    return y_true


def main():
    parser = argparse.ArgumentParser(
        description='Optimize decision threshold for Method 2 XGBoost model',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Optimize with default constraints (precision >= 0.5, recall >= 0.7)
  method2-optimize-threshold \\
    --predictions data/models/method2/predictions.json \\
    --test-data data/processed/test.csv \\
    --output data/models/method2/optimal_threshold.json

  # Custom constraints
  method2-optimize-threshold \\
    --predictions data/models/method2/predictions.json \\
    --test-data data/processed/test.csv \\
    --output data/models/method2/optimal_threshold.json \\
    --min-precision 0.6 \\
    --min-recall 0.65
        """
    )
    
    parser.add_argument(
        '--predictions',
        required=True,
        help='Path to Method 2 predictions.json file'
    )
    parser.add_argument(
        '--test-data',
        required=True,
        help='Path to test.csv file with true labels'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output JSON file for optimal threshold and metrics'
    )
    parser.add_argument(
        '--min-precision',
        type=float,
        default=0.5,
        help='Minimum acceptable precision (default: 0.5)'
    )
    parser.add_argument(
        '--min-recall',
        type=float,
        default=0.7,
        help='Minimum acceptable recall (default: 0.7)'
    )
    parser.add_argument(
        '--baseline-threshold',
        type=float,
        default=0.5,
        help='Baseline threshold to compare against (default: 0.5)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("METHOD 2 THRESHOLD OPTIMIZATION")
    print("=" * 70)
    print()
    
    # Load data
    predictions, probabilities = load_predictions(args.predictions)
    y_true = load_test_labels(args.test_data)
    
    # Verify lengths match
    if len(y_true) != len(predictions):
        print(f"ERROR: Length mismatch! Labels: {len(y_true)}, Predictions: {len(predictions)}")
        return 1
    
    print()
    print("=" * 70)
    print("RUNNING THRESHOLD OPTIMIZATION")
    print("=" * 70)
    print(f"Constraints: Precision >= {args.min_precision:.1%}, Recall >= {args.min_recall:.1%}")
    print(f"Baseline threshold: {args.baseline_threshold}")
    print()
    
    # Run optimization
    optimizer = ThresholdOptimizer(
        min_precision=args.min_precision,
        min_recall=args.min_recall
    )
    
    # Extract probabilities for trojan class (class 1)
    # probabilities is array of [prob_clean, prob_trojan] pairs
    if probabilities.ndim == 2:
        y_proba = probabilities[:, 1]  # Trojan class probabilities
    else:
        y_proba = probabilities  # Already 1D
    
    optimal_threshold, optimal_metrics, all_metrics = optimizer.optimize(
        y_true=y_true,
        y_proba=y_proba
    )
    
    # Generate report
    report = optimizer.generate_report(
        optimal_threshold=optimal_threshold,
        optimal_metrics=optimal_metrics,
        all_metrics=all_metrics,
        baseline_threshold=args.baseline_threshold
    )
    
    # Add metadata
    report['metadata'] = {
        'method': 'Method 2 - Case-Based XGBoost',
        'predictions_file': args.predictions,
        'test_data_file': args.test_data,
        'timestamp': datetime.now().isoformat(),
        'num_samples': len(y_true),
        'num_trojans': int(np.sum(y_true == 1)),
        'num_clean': int(np.sum(y_true == 0))
    }
    
    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print()
    optimizer.print_summary(report)
    
    print("=" * 70)
    print(f"[OK] Results saved to {output_path}")
    print("=" * 70)
    print()
    
    # Print usage recommendation
    print("To use the optimal threshold in Method 2 classification:")
    print(f"  1. Update classify.py to use threshold = {optimal_threshold:.3f}")
    print(f"  2. Or pass --threshold {optimal_threshold:.3f} to classification command")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
