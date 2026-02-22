#!/usr/bin/env python3
"""
CLI wrapper for LIME explanations in the pipeline.
"""

import argparse
import sys
from pathlib import Path


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate LIME explanations for Method 2 classifier (XGBoost/SVM)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate LIME explanations for XGBoost model
  method3-lime \\
    --model data/models/method2/xgboost_model.pkl \\
    --train-data data/processed/train.csv \\
    --test-data data/processed/test.csv \\
    --output data/models/method3
  
  # Limit samples for testing
  method3-lime \\
    --model data/models/method2/xgboost_model.pkl \\
    --train-data data/processed/train.csv \\
    --test-data data/processed/test.csv \\
    --output data/models/method3 \\
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
        help='Path to training CSV (for LIME background distribution)'
    )
    parser.add_argument(
        '--test-data',
        required=True,
        help='Path to test CSV'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for LIME results'
    )
    parser.add_argument(
        '--num-samples',
        type=int,
        default=1000,
        help='Number of perturbed samples per LIME explanation (default: 1000)'
    )
    parser.add_argument(
        '--max-samples',
        type=int,
        default=None,
        help='Maximum test samples to process (default: all)'
    )
    parser.add_argument(
        '--predictions',
        default=None,
        help='Path to Method 2 predictions.json for intelligent sampling (prioritizes trojans and FPs)'
    )
    parser.add_argument(
        '--prioritize-critical',
        action='store_true',
        help='Prioritize trojan samples and false positives over random sampling'
    )
    
    args = parser.parse_args()
    
    # Import the main function from lime_explainer
    from method3_lime.lime_explainer import (
        load_model,
        load_csv_data,
        create_prediction_wrapper,
        explain_sample,
        FEATURE_NAMES
    )
    from lime.lime_tabular import LimeTabularExplainer
    import time
    import json
    import numpy as np
    from datetime import datetime
    
    print("=" * 70)
    print("LIME Explanations for Method 2 (Case-Based Classifier)")
    print("=" * 70)
    print()
    
    start_time = time.time()
    
    # Load model (auto-detect SVM or XGBoost)
    model, scaler, feature_columns, model_type = load_model(args.model)
    
    # Verify feature names match
    if feature_columns != FEATURE_NAMES:
        print(f"WARNING: Feature mismatch!")
        print(f"  Expected: {FEATURE_NAMES}")
        print(f"  Model has: {feature_columns}")
    
    # Load data
    print()
    X_train, _ = load_csv_data(args.train_data, feature_columns)
    X_test, y_test = load_csv_data(args.test_data, feature_columns)
    
    # Intelligent sample selection
    original_indices = np.arange(len(X_test))
    selected_indices = original_indices
    
    if args.max_samples is not None and args.prioritize_critical and args.predictions:
        print(f"\n{'='*70}")
        print("INTELLIGENT SAMPLING: Prioritizing critical samples")
        print(f"{'='*70}")
        
        # Load Method 2 predictions
        with open(args.predictions, 'r') as f:
            predictions_data = json.load(f)
        predictions = np.array(predictions_data['predictions'])
        
        # Identify critical sample indices
        trojan_indices = np.where(y_test == 1)[0]
        fp_indices = np.where((predictions == 1) & (y_test == 0))[0]
        fn_indices = np.where((predictions == 0) & (y_test == 1))[0]
        tn_indices = np.where((predictions == 0) & (y_test == 0))[0]
        
        # Prioritize: All trojans > All FPs > All FNs > Sample of TNs
        critical_indices = np.concatenate([trojan_indices, fp_indices, fn_indices])
        
        print(f"\nCritical sample breakdown:")
        print(f"  True Trojans (TP + FN): {len(trojan_indices)}")
        print(f"  False Positives:        {len(fp_indices)}")
        print(f"  False Negatives:        {len(fn_indices)}")
        print(f"  True Negatives:         {len(tn_indices)}")
        print(f"  Total critical:         {len(critical_indices)}")
        
        if len(critical_indices) <= args.max_samples:
            # Include all critical + sample of TNs
            n_tn_sample = args.max_samples - len(critical_indices)
            if n_tn_sample > 0 and len(tn_indices) > 0:
                tn_sample = np.random.choice(tn_indices, 
                                           min(n_tn_sample, len(tn_indices)), 
                                           replace=False)
                selected_indices = np.concatenate([critical_indices, tn_sample])
                print(f"\n[OK] Explaining ALL critical samples + {len(tn_sample)} TNs")
            else:
                selected_indices = critical_indices
                print(f"\n[OK] Explaining ALL {len(critical_indices)} critical samples")
        else:
            # Too many critical samples, prioritize within critical
            print(f"\n[WARNING] More critical samples ({len(critical_indices)}) than max_samples ({args.max_samples})")
            print(f"  Priority order: Trojans > FPs > FNs")
            selected_indices = critical_indices[:args.max_samples]
            print(f"[OK] Explaining top {args.max_samples} critical samples")
        
        # Apply selection
        X_test = X_test[selected_indices]
        if y_test is not None:
            y_test = y_test[selected_indices]
        
        print(f"\nFinal sample composition:")
        print(f"  Total samples: {len(selected_indices)}")
        print(f"  Trojans: {np.sum(y_test == 1)}")
        print(f"  Clean: {np.sum(y_test == 0)}")
        
    elif args.max_samples is not None:
        # Fallback to naive sampling
        print(f"\nNaive sampling: Taking first {args.max_samples} samples")
        print("  (Use --prioritize-critical --predictions <file> for intelligent sampling)")
        X_test = X_test[:args.max_samples]
        selected_indices = original_indices[:args.max_samples]
        if y_test is not None:
            y_test = y_test[:args.max_samples]
    
    print(f"\nTest samples to process: {len(X_test)}")
    print(f"Perturbations per sample: {args.num_samples}")
    print(f"Estimated time: ~{len(X_test) * 0.024:.1f} seconds")
    
    # Create prediction wrapper
    print("\nCreating LIME explainer...")
    predict_fn = create_prediction_wrapper(model, scaler, model_type)
    
    # Create LIME explainer (use unscaled training data)
    explainer = LimeTabularExplainer(
        training_data=X_train,
        feature_names=FEATURE_NAMES,
        class_names=['Clean', 'Trojan'],
        mode='classification',
        discretize_continuous=True
    )
    print("  Explainer created successfully")
    
    # Generate explanations
    print("\nGenerating LIME explanations...")
    print()
    
    results = []
    explain_time_total = 0.0
    
    for idx in range(len(X_test)):
        if idx % 50 == 0 and idx > 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / idx
            remaining = (len(X_test) - idx) * avg_time
            print(f"  Progress: {idx}/{len(X_test)} ({idx/len(X_test)*100:.1f}%) - "
                  f"Elapsed: {elapsed/60:.1f}min - ETA: {remaining/60:.1f}min")
        elif idx % 10 == 0:
            print(f"  Progress: {idx}/{len(X_test)}")
        
        sample = X_test[idx]
        
        # Generate LIME explanation (timed)
        explain_start = time.time()
        ranking, explanation = explain_sample(
            explainer, 
            predict_fn, 
            sample, 
            args.num_samples
        )
        explain_time_total += time.time() - explain_start
        
        # Get prediction
        pred_proba = predict_fn(sample.reshape(1, -1))[0]
        pred_class = 1 if pred_proba[1] > 0.5 else 0
        
        # Create result entry
        result = {
            'sample_index': int(idx),
            'original_test_index': int(selected_indices[idx]),  # Map back to full test set
            'features': {feat: float(val) for feat, val in zip(FEATURE_NAMES, sample)},
            'prediction': {
                'class': int(pred_class),
                'confidence': float(pred_proba[pred_class]),
                'prob_clean': float(pred_proba[0]),
                'prob_trojan': float(pred_proba[1])
            },
            'true_label': int(y_test[idx]) if y_test is not None else None,
            'lime_ranking': ranking
        }
        results.append(result)
    
    # Compute summary statistics
    print()
    print("Computing summary statistics...")
    
    def extract_base_feature(lime_str):
        """Extract base feature name from LIME's discretized strings.
        
        LIME produces strings like '2.00 < PO <= 4.00', 'ffo <= 0.00',
        'PO > 6.00'. The split()[0] approach fails when the string starts
        with a threshold number. Instead, match against known feature names.
        """
        for name in FEATURE_NAMES:
            if name in lime_str:
                return name
        return lime_str  # fallback for unknown features
    
    # Count most important features
    feature_importance_counts = {f: 0 for f in FEATURE_NAMES}
    for result in results:
        top_feature_str = result['lime_ranking'][0]['feature']
        base_feature = extract_base_feature(top_feature_str)
        if base_feature in feature_importance_counts:
            feature_importance_counts[base_feature] += 1
    
    # Compute average absolute weights
    avg_abs_weights = {f: [] for f in FEATURE_NAMES}
    for result in results:
        for item in result['lime_ranking']:
            feature_str = item['feature']
            base_feature = extract_base_feature(feature_str)
            if base_feature in avg_abs_weights:
                avg_abs_weights[base_feature].append(item['abs_weight'])
    
    avg_weights_summary = {
        f: {
            'mean': float(np.mean(weights)),
            'std': float(np.std(weights)),
            'min': float(np.min(weights)),
            'max': float(np.max(weights))
        }
        for f, weights in avg_abs_weights.items()
    }
    
    # Save results
    print()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'lime_explanations.json'
    print(f"Saving results to {output_file}...")
    
    output_data = {
        'explanations': results,
        'summary': {
            'num_samples': len(results),
            'feature_names': FEATURE_NAMES,
            'num_perturbations': args.num_samples,
            'top_feature_frequency': feature_importance_counts,
            'avg_feature_weights': avg_weights_summary,
            'sampling': {
                'method': 'intelligent' if (args.prioritize_critical and args.predictions) else 'naive',
                'original_indices': selected_indices.tolist() if isinstance(selected_indices, np.ndarray) else list(selected_indices),
                'num_trojans': int(np.sum(y_test == 1)) if y_test is not None else None,
                'num_clean': int(np.sum(y_test == 0)) if y_test is not None else None
            }
        },
        'metadata': {
            'method': 'LIME (Local Interpretable Model-agnostic Explanations)',
            'model_path': args.model,
            'model_type': model_type,
            'test_data': args.test_data,
            'predictions_file': args.predictions if args.predictions else None,
            'prioritize_critical': args.prioritize_critical,
            'generation_time_seconds': time.time() - start_time,
            'explain_time_seconds': explain_time_total,
            'explain_time_per_sample_ms': 1000 * explain_time_total / len(results) if results else 0,
            'timestamp': datetime.now().isoformat()
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    # Save summary to separate file
    summary_file = output_dir / 'lime_summary.txt'
    elapsed_time = time.time() - start_time
    
    with open(summary_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("LIME Explanation Summary\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Samples processed: {len(results)}\n")
        f.write(f"Total time: {elapsed_time/60:.1f} minutes ({elapsed_time/len(results):.1f} sec/sample)\n")
        f.write(f"Explanation-only time: {explain_time_total:.2f}s ({1000*explain_time_total/len(results):.3f} ms/sample)\n\n")
        f.write("Top Feature Frequency (times each feature ranked #1):\n")
        for feature, count in sorted(feature_importance_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(results) * 100
            f.write(f"  {feature}: {count} ({percentage:.1f}%)\n")
        f.write("\nAverage Absolute LIME Weights:\n")
        for feature in sorted(avg_weights_summary.keys(), key=lambda x: avg_weights_summary[x]['mean'], reverse=True):
            stats = avg_weights_summary[feature]
            f.write(f"  {feature}: {stats['mean']:.4f} +/- {stats['std']:.4f} (range: {stats['min']:.4f}-{stats['max']:.4f})\n")
    
    # Print summary
    print()
    print("=" * 70)
    print("[OK] LIME Explanation Generation Complete!")
    print("=" * 70)
    print(f"Samples processed: {len(results)}")
    print(f"Output files:")
    print(f"  {output_file}")
    print(f"  {summary_file}")
    print(f"Total time: {elapsed_time/60:.1f} minutes ({elapsed_time/len(results):.3f} sec/sample)")
    print()
    print("Top Feature Frequency (times each feature ranked #1):")
    for feature, count in sorted(feature_importance_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = count / len(results) * 100
        print(f"  {feature}: {count} ({percentage:.1f}%)")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
