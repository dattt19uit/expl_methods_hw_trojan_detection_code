#!/usr/bin/env python3
"""
CLI wrapper for gradient attribution explanations in the pipeline.
"""

import argparse
import sys
import json
import time
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate gradient-based feature attribution for Method 2 classifier',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate gradient attribution for XGBoost model
  method5-gradient \\
    --model data/models/method2/xgboost_model.pkl \\
    --train-data data/processed/train.csv \\
    --test-data data/processed/test.csv \\
    --output data/explanations/method5
  
  # Limit samples for testing
  method5-gradient \\
    --model data/models/method2/xgboost_model.pkl \\
    --train-data data/processed/train.csv \\
    --test-data data/processed/test.csv \\
    --output data/explanations/method5 \\
    --max-samples 100
        """
    )
    
    parser.add_argument(
        '--model',
        required=True,
        help='Path to trained model (.pkl from Method 2 - SVM or XGBoost)'
    )
    parser.add_argument(
        '--train-data',
        required=True,
        help='Path to training CSV'
    )
    parser.add_argument(
        '--test-data',
        required=True,
        help='Path to test CSV'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for gradient attribution results'
    )
    parser.add_argument(
        '--max-samples',
        type=int,
        default=None,
        help='Maximum test samples to process (default: all)'
    )
    
    args = parser.parse_args()
    
    from method5_gradient.gradient_explainer import GradientAttributionExplainer
    
    print("=" * 70)
    print("Gradient-Based Feature Attribution for Method 2 Classifier")
    print("=" * 70)
    print()
    
    start_time = time.time()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load model
    print(f"Loading model from: {args.model}")
    with open(args.model, 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data['model']
    scaler = model_data.get('scaler', None)
    feature_columns = model_data.get('feature_columns', ['ffo', 'ffi', 'PO', 'LGFi', 'PI'])
    
    print(f"  Model type: {type(model).__name__}")
    print(f"  Features: {feature_columns}")
    print()
    
    # Load data
    print(f"Loading training data from: {args.train_data}")
    train_df = pd.read_csv(args.train_data)
    
    print(f"Loading test data from: {args.test_data}")
    test_df = pd.read_csv(args.test_data)
    
    # Extract features and labels
    X_train = train_df[feature_columns].values
    # Try both 'Trojan' and 'trojan' for label column
    label_col = 'Trojan' if 'Trojan' in train_df.columns else 'trojan'
    y_train = train_df[label_col].values
    
    X_test = test_df[feature_columns].values
    y_test = test_df[label_col].values
    test_circuits = test_df['circuit_name'].values if 'circuit_name' in test_df.columns else [f'circuit_{i}' for i in range(len(y_test))]
    
    # Apply scaling if available
    if scaler is not None:
        X_test = scaler.transform(X_test)
        print("  Applied StandardScaler transformation")
    
    # Limit samples if requested
    if args.max_samples is not None and args.max_samples < len(X_test):
        print(f"  Limiting to first {args.max_samples} test samples")
        X_test = X_test[:args.max_samples]
        y_test = y_test[:args.max_samples]
        test_circuits = test_circuits[:args.max_samples]
    
    print(f"  Training samples: {len(X_train)}")
    print(f"  Test samples: {len(X_test)}")
    print()
    
    # Create explainer
    print("Creating gradient attribution explainer...")
    explainer = GradientAttributionExplainer(
        model=model,
        feature_names=feature_columns,
        epsilon=1e-5
    )
    print(f"  Detected model type: {explainer.model_type}")
    print()
    
    # Generate predictions
    print("Generating predictions...")
    if hasattr(model, 'predict_proba'):
        predictions = model.predict(X_test)
        probabilities = model.predict_proba(X_test)
        pred_confidence = np.max(probabilities, axis=1)
    else:
        predictions = model.predict(X_test)
        pred_confidence = np.abs(model.decision_function(X_test))
    
    accuracy = np.mean(predictions == y_test)
    print(f"  Accuracy: {100 * accuracy:.2f}% ({np.sum(predictions == y_test)}/{len(y_test)})")
    print()
    
    # Generate explanations
    print(f"Generating gradient attributions for {len(X_test)} samples...")
    print(f"  (Estimated time: ~{len(X_test) * 0.012:.1f} seconds for XGBoost, ~{len(X_test) * 5:.1f} seconds for SVM)")
    print()
    
    explanations = []
    explain_start = time.time()
    explain_only_total = 0.0
    
    for i, (x_sample, y_true, pred, conf, circuit) in enumerate(zip(X_test, y_test, predictions, pred_confidence, test_circuits)):
        if (i + 1) % max(1, len(X_test) // 10) == 0:
            elapsed = time.time() - explain_start
            rate = (i + 1) / elapsed
            remaining = (len(X_test) - i - 1) / rate
            print(f"  Progress: {i + 1}/{len(X_test)} ({100*(i+1)/len(X_test):.1f}%) - "
                  f"{rate:.1f} samples/sec - ETA: {remaining:.0f}s")
        
        # Generate explanation (timed)
        explain_call_start = time.time()
        explanation = explainer.explain_prediction(
            x_sample=x_sample,
            prediction=float(pred),
            prediction_confidence=float(conf),
            top_k=5,
            show_direction=True
        )
        explain_only_total += time.time() - explain_call_start
        
        # Add metadata
        explanation['sample_index'] = int(i)
        explanation['circuit_name'] = str(circuit)
        explanation['true_label'] = int(y_true)
        explanation['predicted_label'] = int(pred)
        explanation['correct'] = bool(pred == y_true)
        
        explanations.append(explanation)
    
    explain_elapsed = time.time() - explain_start
    print()
    print(f"  Completed {len(explanations)} attributions in {explain_elapsed:.2f} seconds")
    print(f"  Average time per sample: {1000 * explain_elapsed / len(explanations):.3f} milliseconds")
    print(f"  Explanation-only time: {explain_only_total:.2f}s ({1000 * explain_only_total / len(explanations):.3f} ms/sample)")
    print()
    
    # Compute global feature importance
    print("Computing global feature importance...")
    all_normalized_importance = np.array([exp['normalized_importance'] for exp in explanations])
    global_importance = np.mean(all_normalized_importance, axis=0)
    
    global_feature_importance = {
        feature: float(importance)
        for feature, importance in zip(feature_columns, global_importance)
    }
    
    # Sort by importance
    sorted_features = sorted(global_feature_importance.items(), key=lambda x: x[1], reverse=True)
    print("  Global Feature Importance (averaged across all samples):")
    for feat, imp in sorted_features:
        print(f"    {feat}: {100*imp:.2f}%")
    print()
    
    # Save results
    output_file = output_dir / 'gradient_attributions.json'
    print(f"Saving results to: {output_file}")
    
    output_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'model_file': str(args.model),
            'model_type': explainer.model_type,
            'feature_names': feature_columns,
            'n_samples': len(explanations),
            'accuracy': float(accuracy),
            'processing_time_seconds': float(explain_elapsed),
            'avg_time_per_sample_ms': float(1000 * explain_elapsed / len(explanations)),
            'explain_time_seconds': float(explain_only_total),
            'explain_time_per_sample_ms': float(1000 * explain_only_total / len(explanations))
        },
        'global_feature_importance': global_feature_importance,
        'explanations': explanations
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"  Saved {len(explanations)} explanations")
    print()
    
    # Generate summary statistics
    summary_file = output_dir / 'summary.txt'
    print(f"Generating summary: {summary_file}")
    
    with open(summary_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("Gradient Attribution Summary\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Model: {args.model}\n")
        f.write(f"Model Type: {explainer.model_type}\n\n")
        
        f.write(f"Data:\n")
        f.write(f"  Training samples: {len(X_train)}\n")
        f.write(f"  Test samples: {len(X_test)}\n")
        f.write(f"  Features: {feature_columns}\n\n")
        
        f.write(f"Performance:\n")
        f.write(f"  Accuracy: {100*accuracy:.2f}%\n")
        f.write(f"  Processing time: {explain_elapsed:.2f} seconds\n")
        f.write(f"  Avg time/sample: {1000*explain_elapsed/len(explanations):.3f} ms\n\n")
        
        f.write("Global Feature Importance:\n")
        for feat, imp in sorted_features:
            f.write(f"  {feat:<10s}: {100*imp:>6.2f}%\n")
        f.write("\n")
        
        # Sample explanation
        f.write("Sample Explanation (first test sample):\n")
        f.write("-" * 70 + "\n")
        sample_exp = explanations[0]
        f.write(f"Circuit: {sample_exp['circuit_name']}\n")
        f.write(f"True label: {'Trojan' if sample_exp['true_label'] == 1 else 'Clean'}\n")
        f.write(f"Predicted: {'Trojan' if sample_exp['predicted_label'] == 1 else 'Clean'}\n")
        f.write(f"Confidence: {sample_exp['prediction_confidence']:.4f}\n\n")
        
        f.write("Top 5 Most Important Features:\n")
        for top_feat in sample_exp['top_features']:
            f.write(f"  {top_feat['rank']}. {top_feat['interpretation']}\n")
    
    print("  Summary saved")
    print()
    
    total_elapsed = time.time() - start_time
    print("=" * 70)
    print(f"Gradient Attribution Complete!")
    print(f"Total time: {total_elapsed:.2f} seconds")
    print(f"Output directory: {output_dir}")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
