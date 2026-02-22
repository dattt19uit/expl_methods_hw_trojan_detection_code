#!/usr/bin/env python3
"""
Threshold Optimizer for Method 1 (Property-Based Ensemble)

Optimizes decision thresholds for all 31 XGBoost property models
in Method 1 to balance precision and recall.

Usage:
    method1-optimize-thresholds \\
        --predictions data/models/method1/test_proba.json \\
        --labels data/models/method1/test_labels.json \\
        --output data/models/method1/optimal_thresholds.json \\
        --min-precision 0.5 \\
        --min-recall 0.7

Author: Paul Whitten, Francis Wolff, Chris Papachristou
Date: December 2025
"""

import argparse
import json
import sys
import time
import numpy as np
from pathlib import Path
from datetime import datetime

# Import from shared package
from xai_shared import ThresholdOptimizer


PROPERTY_NAMES = [
    ['LGFi'], ['ffi'], ['ffo'], ['PI'], ['PO'],
    ['LGFi', 'ffi'], ['LGFi', 'ffo'], ['LGFi', 'PI'], ['LGFi', 'PO'],
    ['ffi', 'ffo'], ['ffi', 'PI'], ['ffi', 'PO'],
    ['ffo', 'PI'], ['ffo', 'PO'], ['PI', 'PO'],
    ['LGFi', 'ffi', 'ffo'], ['LGFi', 'ffi', 'PI'], ['LGFi', 'ffi', 'PO'],
    ['LGFi', 'ffo', 'PI'], ['LGFi', 'ffo', 'PO'], ['LGFi', 'PI', 'PO'],
    ['ffi', 'ffo', 'PI'], ['ffi', 'ffo', 'PO'], ['ffi', 'PI', 'PO'],
    ['ffo', 'PI', 'PO'],
    ['LGFi', 'ffi', 'ffo', 'PI'], ['LGFi', 'ffi', 'ffo', 'PO'],
    ['LGFi', 'ffi', 'PI', 'PO'], ['LGFi', 'ffo', 'PI', 'PO'],
    ['ffi', 'ffo', 'PI', 'PO'],
    ['LGFi', 'ffi', 'ffo', 'PI', 'PO']
]


def load_predictions(predictions_file):
    """Load Method 1 predictions (probabilities for all 31 properties)."""
    print(f"Loading predictions from {predictions_file}...")
    with open(predictions_file, 'r') as f:
        probabilities = json.load(f)
    
    # probabilities is list of lists: [property][sample][class_proba]
    num_properties = len(probabilities)
    num_samples = len(probabilities[0]) if probabilities else 0
    
    print(f"  Loaded {num_properties} properties, {num_samples} samples each")
    return probabilities


def load_labels(labels_file):
    """Load true labels."""
    print(f"Loading labels from {labels_file}...")
    with open(labels_file, 'r') as f:
        labels = json.load(f)
    
    y_true = np.array(labels)
    trojans = np.sum(y_true == 1)
    clean = np.sum(y_true == 0)
    
    print(f"  Loaded {len(y_true)} labels ({clean} clean, {trojans} trojans)")
    return y_true


def main():
    parser = argparse.ArgumentParser(
        description='Optimize decision thresholds for all Method 1 property models',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Optimize all 31 properties with default constraints
  method1-optimize-thresholds \\
    --predictions data/models/method1/test_proba.json \\
    --labels data/models/method1/test_labels.json \\
    --output data/models/method1/optimal_thresholds.json

  # Custom constraints
  method1-optimize-thresholds \\
    --predictions data/models/method1/test_proba.json \\
    --labels data/models/method1/test_labels.json \\
    --output data/models/method1/optimal_thresholds.json \\
    --min-precision 0.6 \\
    --min-recall 0.65
        """
    )
    
    parser.add_argument(
        '--predictions',
        required=True,
        help='Path to Method 1 test_proba.json file'
    )
    parser.add_argument(
        '--labels',
        required=True,
        help='Path to Method 1 test_labels.json file'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output JSON file for optimal thresholds'
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
    print("METHOD 1 THRESHOLD OPTIMIZATION (31 Properties)")
    print("=" * 70)
    print()
    
    # Load data
    probabilities = load_predictions(args.predictions)
    y_true = load_labels(args.labels)
    
    # Verify lengths
    num_properties = len(probabilities)
    num_samples = len(probabilities[0]) if probabilities else 0
    
    if num_samples != len(y_true):
        print(f"ERROR: Length mismatch! Labels: {len(y_true)}, Samples: {num_samples}")
        return 1
    
    print()
    print("=" * 70)
    print("RUNNING THRESHOLD OPTIMIZATION FOR ALL PROPERTIES")
    print("=" * 70)
    print(f"Constraints: Precision >= {args.min_precision:.1%}, Recall >= {args.min_recall:.1%}")
    print(f"Baseline threshold: {args.baseline_threshold}")
    print()
    
    # Start timing
    start_time = time.perf_counter()
    
    # Initialize optimizer
    optimizer = ThresholdOptimizer(
        min_precision=args.min_precision,
        min_recall=args.min_recall
    )
    
    # Optimize each property
    results = {}
    optimize_time_total = 0.0
    summary_stats = {
        'constraints_met': 0,
        'avg_precision_gain': 0.0,
        'avg_fp_reduction': 0.0,
        'properties': []
    }
    
    for prop_idx in range(num_properties):
        prop_name = ' + '.join(PROPERTY_NAMES[prop_idx])
        print(f"[{prop_idx+1:2d}/{num_properties}] Optimizing property: {prop_name}")
        
        # Extract probabilities for this property
        # probabilities[prop_idx] is list of [prob_clean, prob_trojan] for each sample
        prop_proba = np.array(probabilities[prop_idx])
        
        # Extract trojan class probabilities (class 1)
        if prop_proba.ndim == 2 and prop_proba.shape[1] == 2:
            y_proba = prop_proba[:, 1]
        else:
            y_proba = prop_proba  # Already 1D
        
        # Optimize (timed)
        optimize_start = time.perf_counter()
        optimal_threshold, optimal_metrics, all_metrics = optimizer.optimize(
            y_true=y_true,
            y_proba=y_proba
        )
        optimize_time_total += time.perf_counter() - optimize_start
        
        # Generate report
        report = optimizer.generate_report(
            optimal_threshold=optimal_threshold,
            optimal_metrics=optimal_metrics,
            all_metrics=all_metrics,
            baseline_threshold=args.baseline_threshold
        )
        
        # Store results
        results[f'property_{prop_idx}'] = {
            'property_index': prop_idx,
            'property_name': prop_name,
            'property_features': PROPERTY_NAMES[prop_idx],
            'optimal_threshold': report['optimal']['threshold'],
            'optimal_metrics': report['optimal'],
            'baseline_metrics': report['baseline'],
            'improvement': report['improvement'],
            'constraints_met': report['constraints']['constraints_met']
        }
        
        # Update summary
        if report['constraints']['constraints_met']:
            summary_stats['constraints_met'] += 1
        
        summary_stats['avg_precision_gain'] += report['improvement']['precision_gain_percent']
        summary_stats['avg_fp_reduction'] += report['improvement']['false_positives_reduced']
        
        summary_stats['properties'].append({
            'index': prop_idx,
            'name': prop_name,
            'threshold': optimal_threshold,
            'precision': optimal_metrics.precision,
            'recall': optimal_metrics.recall,
            'f1_score': optimal_metrics.f1_score,
            'constraints_met': report['constraints']['constraints_met']
        })
        
        # Print brief status
        status = "[OK]" if report['constraints']['constraints_met'] else "[WARNING]"
        print(f"    {status} Threshold: {optimal_threshold:.3f}, "
              f"Precision: {optimal_metrics.precision:.1%}, "
              f"Recall: {optimal_metrics.recall:.1%}, "
              f"F1: {optimal_metrics.f1_score:.3f}")
        print()
    
    # End timing
    elapsed_time = time.perf_counter() - start_time
    
    # Calculate averages
    summary_stats['avg_precision_gain'] /= num_properties
    summary_stats['avg_fp_reduction'] /= num_properties
    summary_stats['constraints_met_percent'] = summary_stats['constraints_met'] / num_properties * 100
    
    # Add metadata
    results['metadata'] = {
        'method': 'Method 1 - Property-Based Ensemble (31 XGBoost models)',
        'num_properties': num_properties,
        'predictions_file': args.predictions,
        'labels_file': args.labels,
        'timestamp': datetime.now().isoformat(),
        'num_samples': len(y_true),
        'num_trojans': int(np.sum(y_true == 1)),
        'num_clean': int(np.sum(y_true == 0)),
        'constraints': {
            'min_precision': args.min_precision,
            'min_recall': args.min_recall
        },
        'performance': {
            'mode': 'sequential',
            'total_time_seconds': elapsed_time,
            'time_per_property_seconds': elapsed_time / num_properties,
            'optimize_time_seconds': optimize_time_total,
            'optimize_time_per_property_seconds': optimize_time_total / num_properties
        }
    }
    
    results['summary'] = summary_stats
    
    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("=" * 70)
    print("OPTIMIZATION SUMMARY")
    print("=" * 70)
    print()
    print(f"Properties optimized: {num_properties}")
    print(f"Elapsed time: {elapsed_time:.3f} seconds ({elapsed_time/num_properties*1000:.1f} ms/property)")
    print(f"Mode: Sequential (no parallelization)")
    print(f"Constraints met: {summary_stats['constraints_met']}/{num_properties} "
          f"({summary_stats['constraints_met_percent']:.1f}%)")
    print(f"Average precision gain: {summary_stats['avg_precision_gain']:+.1f}%")
    print(f"Average FP reduction: {summary_stats['avg_fp_reduction']:.0f} per property")
    print()
    
    print("Top 5 Properties by F1 Score:")
    top_props = sorted(summary_stats['properties'], key=lambda x: x['f1_score'], reverse=True)[:5]
    for i, prop in enumerate(top_props, 1):
        status = "[OK]" if prop['constraints_met'] else "[WARNING]"
        print(f"  {i}. {status} {prop['name']:30s} F1: {prop['f1_score']:.3f}, "
              f"P: {prop['precision']:.1%}, R: {prop['recall']:.1%}")
    
    print()
    print("=" * 70)
    print(f"[OK] Results saved to {output_path}")
    print("=" * 70)
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
