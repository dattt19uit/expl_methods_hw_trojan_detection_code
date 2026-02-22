#!/usr/bin/env python3
"""
Prepare Pipeline Data for Statistical Analysis

This script converts the pipeline output format into the format expected by 
the statistical analysis scripts. It handles the different data structures
between Method 1 (architecture-level) and Method 2 (sample-level) predictions.

Method 1 produces predictions for each architecture on each sample.
This script creates an ensemble prediction using majority voting across architectures.

Method 2 already produces sample-level predictions, so we just create an alias.
"""

import json
import numpy as np
from pathlib import Path
import argparse


def prepare_method1_data(models_dir):
    """
    Prepare Method 1 (Property-Based) data for statistical analysis.
    
    Method 1 evaluates multiple architectures (typically 31) on each test sample.
    We create ensemble predictions using majority vote across architectures.
    """
    method1_dir = Path(models_dir) / "method1"
    
    # Load architecture-level predictions and labels
    pred_file = method1_dir / "test_pred.json"
    label_file = method1_dir / "test_labels.json"
    output_file = method1_dir / "kb_test_results.json"
    
    if not pred_file.exists():
        print(f"[WARNING] Method 1 predictions not found: {pred_file}")
        return False
        
    if not label_file.exists():
        print(f"[WARNING] Method 1 labels not found: {label_file}")
        return False
    
    # Load data
    with open(pred_file) as f:
        preds_per_arch = json.load(f)  # Shape: (n_architectures, n_samples)
    with open(label_file) as f:
        labels = json.load(f)  # Shape: (n_samples,)
    
    # Convert to numpy array
    preds_array = np.array(preds_per_arch)
    n_architectures, n_samples = preds_array.shape
    
    print(f"Method 1: {n_architectures} architectures x {n_samples} samples")
    
    # Ensemble predictions: majority vote across architectures
    # For each sample, count how many architectures predict trojan (1)
    votes_per_sample = np.sum(preds_array, axis=0)
    ensemble_preds = (votes_per_sample > (n_architectures / 2)).astype(int)
    
    # Calculate ensemble accuracy
    accuracy = np.mean(ensemble_preds == np.array(labels))
    print(f"  Ensemble accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    
    # Create output in expected format
    result = {
        'predictions': ensemble_preds.tolist(),
        'labels': labels,
        'metadata': {
            'n_architectures': n_architectures,
            'n_samples': n_samples,
            'ensemble_method': 'majority_vote',
            'ensemble_accuracy': float(accuracy)
        }
    }
    
    # Write output
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"  [OK] Created: {output_file}")
    return True


def prepare_method2_data(models_dir):
    """
    Prepare Method 2 (XGBoost) data for statistical analysis.
    
    Method 2 already produces sample-level predictions in the correct format.
    We just create a compatibility alias if needed.
    """
    method2_dir = Path(models_dir) / "method2"
    
    pred_file = method2_dir / "predictions.json"
    output_file = method2_dir / "classification_results.json"
    
    if not pred_file.exists():
        print(f"[WARNING] Method 2 predictions not found: {pred_file}")
        return False
    
    # Check if output already exists and is up to date
    if output_file.exists():
        # Compare timestamps
        if output_file.stat().st_mtime >= pred_file.stat().st_mtime:
            print(f"Method 2: classification_results.json already up to date")
            return True
    
    # Load predictions
    with open(pred_file) as f:
        data = json.load(f)
    
    n_samples = len(data.get('predictions', []))
    print(f"Method 2: {n_samples} samples")
    
    # Predictions file already has the right format, just create alias/copy
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"  [OK] Created: {output_file}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Prepare pipeline data for statistical analysis'
    )
    parser.add_argument(
        '--models-dir',
        type=str,
        default='data/models',
        help='Directory containing model results (default: data/models)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Preparing Pipeline Data for Statistical Analysis")
    print("=" * 70)
    print("")
    
    models_dir = Path(args.models_dir)
    if not models_dir.exists():
        print(f"ERROR: Models directory not found: {models_dir}")
        print("   Make sure the pipeline has been run first.")
        return 1
    
    # Prepare Method 1 data
    method1_success = prepare_method1_data(models_dir)
    print("")
    
    # Prepare Method 2 data
    method2_success = prepare_method2_data(models_dir)
    print("")
    
    if method1_success and method2_success:
        print("[OK] Data preparation complete!")
        print("")
        print("Ready for statistical analysis:")
        print("  ./run_complete_analysis.sh")
        return 0
    else:
        print("[WARNING] Some data preparation steps failed")
        print("   Statistical analysis may not work correctly")
        return 1


if __name__ == '__main__':
    exit(main())
