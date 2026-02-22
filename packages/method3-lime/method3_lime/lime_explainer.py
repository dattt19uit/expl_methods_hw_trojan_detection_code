#!/usr/bin/env python3
"""
LIME Explanations for Method 2 (Case-Based) Classifier

Generates LIME explanations for trained Method 2 XGBoost models.
Also supports legacy SVM models with auto-detection.

Usage:
    python run_lime_on_method2.py \\
        --model ../../refactor/prototype/data/models/method2/xgboost_model.pkl \\
        --train-data ../../refactor/prototype/data/training/train.csv \\
        --test-data ../../refactor/prototype/data/training/test.csv \\
        --output ./output_xgboost \\
        --max-samples 50

Author: Hardware Trojan XAI Research
Date: December 2025
"""

import argparse
import numpy as np
import pandas as pd
import pickle
import json
from lime.lime_tabular import LimeTabularExplainer
from pathlib import Path
import time
from datetime import datetime

FEATURE_NAMES = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']


def load_model(model_path):
    """Load trained model (SVM or XGBoost) with auto-detection."""
    print(f"Loading model from {model_path}...")
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    # Auto-detect model type
    if 'svm' in model_data:
        # SVM model
        model = model_data['svm']
        scaler = model_data['scaler']
        feature_columns = model_data['feature_columns']
        model_type = 'SVM'
    elif 'model' in model_data:
        # XGBoost model
        model = model_data['model']
        scaler = model_data.get('scaler', None)
        feature_columns = model_data.get('feature_names', model_data.get('feature_columns', FEATURE_NAMES))
        model_type = 'XGBoost'
    else:
        raise ValueError("Unknown model format in pickle file")
    
    print(f"  Model type: {model_type}")
    print(f"  Model: {type(model).__name__}")
    if scaler:
        print(f"  Scaler: {type(scaler).__name__}")
    print(f"  Features: {feature_columns}")
    
    return model, scaler, feature_columns, model_type


def load_csv_data(csv_path, feature_columns):
    """Load CSV data."""
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Extract features and labels
    X = df[feature_columns].values
    y = df['Trojan'].values if 'Trojan' in df.columns else None
    
    print(f"  Loaded {len(X)} samples with {X.shape[1]} features")
    if y is not None:
        trojans = sum(y)
        clean = len(y) - trojans
        print(f"  Distribution: {clean} clean, {trojans} trojans")
    
    return X, y


def create_prediction_wrapper(model, scaler, model_type):
    """Create prediction function that handles scaling."""
    if model_type == 'XGBoost':
        # XGBoost model
        def predict_proba(X):
            """Predict probabilities with XGBoost (no scaling needed)."""
            return model.predict_proba(X)
        return predict_proba
    
    # SVM model
    has_proba = hasattr(model, 'predict_proba') and hasattr(model, 'probability') and model.probability
    
    if has_proba:
        def predict_proba(X):
            """Predict probabilities with scaling."""
            X_scaled = scaler.transform(X)
            return model.predict_proba(X_scaled)
    else:
        # Use decision_function and convert to pseudo-probabilities
        def predict_proba(X):
            """Predict using decision function (convert to probabilities)."""
            X_scaled = scaler.transform(X)
            decision = model.decision_function(X_scaled)
            
            # Convert decision values to pseudo-probabilities using sigmoid
            # Positive decision -> higher prob of class 1 (trojan)
            # Negative decision -> higher prob of class 0 (clean)
            if len(decision.shape) == 1:
                decision = decision.reshape(-1, 1)
            
            # Apply sigmoid to get probabilities
            prob_positive = 1 / (1 + np.exp(-decision))
            prob_negative = 1 - prob_positive
            
            return np.hstack([prob_negative, prob_positive])
    
    return predict_proba


def explain_sample(explainer, predict_fn, sample, num_samples=5000):
    """
    Generate LIME explanation for a single sample.
    
    Returns:
        List of feature importance dicts sorted by absolute weight
    """
    explanation = explainer.explain_instance(
        data_row=sample,
        predict_fn=predict_fn,
        num_features=len(FEATURE_NAMES),
        num_samples=num_samples
    )
    
    # Extract feature weights
    feature_weights = dict(explanation.as_list())
    
    # Sort by absolute importance
    ranking = []
    for feature, weight in sorted(
        feature_weights.items(), 
        key=lambda x: abs(x[1]), 
        reverse=True
    ):
        ranking.append({
            'feature': feature,
            'weight': float(weight),
            'abs_weight': float(abs(weight))
        })
    
    return ranking, explanation


def main():
    parser = argparse.ArgumentParser(
        description='Generate LIME explanations for Method 2 classifier (SVM or XGBoost)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python run_lime_on_method2.py \\
        --model ../2_case_based/output/xgboost_model.pkl \\
        --train-data ../../data/aggregate/train.csv \\
        --test-data ../../data/aggregate/test.csv \\
        --output ./output \\
        --max-samples 50
        """
    )
    parser.add_argument(
        '--model',
        required=True,
        help='Path to trained model (.pkl from Method 2 - SVM or XGBoost)'
    )
    parser.add_argument(
        '--svm-model',
        help='(Deprecated: use --model) Path to trained model'
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
        default=5000,
        help='Number of perturbed samples per LIME explanation (default: 5000)'
    )
    parser.add_argument(
        '--max-samples',
        type=int,
        default=None,
        help='Maximum test samples to process (for testing, default: all)'
    )
    
    args = parser.parse_args()
    
    # Handle backward compatibility
    model_path = args.model if args.model else args.svm_model
    if not model_path:
        parser.error("Either --model or --svm-model is required")
    
    print("=" * 70)
    print("LIME Explanations for Method 2 (Case-Based Classifier)")
    print("=" * 70)
    print()
    
    start_time = time.time()
    
    # Load model (auto-detect SVM or XGBoost)
    model, scaler, feature_columns, model_type = load_model(model_path)
    
    # Verify feature names match
    if feature_columns != FEATURE_NAMES:
        print(f"WARNING: Feature mismatch!")
        print(f"  Expected: {FEATURE_NAMES}")
        print(f"  Model has: {feature_columns}")
    
    # Load data
    print()
    X_train, _ = load_csv_data(args.train_data, feature_columns)
    X_test, y_test = load_csv_data(args.test_data, feature_columns)
    
    # Limit test samples if specified
    if args.max_samples is not None:
        print(f"\nLimiting to {args.max_samples} test samples")
        X_test = X_test[:args.max_samples]
        if y_test is not None:
            y_test = y_test[:args.max_samples]
    
    print(f"\nTest samples to process: {len(X_test)}")
    print(f"Perturbations per sample: {args.num_samples}")
    print(f"Estimated time: ~{len(X_test) * 10 / 60:.1f}-{len(X_test) * 30 / 60:.1f} minutes")
    
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
    
    # Count most important features (extract base feature name from discretized strings)
    feature_importance_counts = {f: 0 for f in FEATURE_NAMES}
    for result in results:
        top_feature_str = result['lime_ranking'][0]['feature']
        base_feature = extract_base_feature(top_feature_str)
        if base_feature in feature_importance_counts:
            feature_importance_counts[base_feature] += 1
    
    # Compute average absolute weights (extract base feature names)
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
            'avg_feature_weights': avg_weights_summary
        },
        'metadata': {
            'method': 'LIME (Local Interpretable Model-agnostic Explanations)',
            'model_path': model_path,
            'model_type': model_type,
            'test_data': args.test_data,
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
    print(f"Total time: {elapsed_time/60:.1f} minutes ({elapsed_time/len(results):.1f} sec/sample)")
    print()
    print("Top Feature Frequency (times each feature ranked #1):")
    for feature, count in sorted(feature_importance_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = count / len(results) * 100
        print(f"  {feature}: {count} ({percentage:.1f}%)")
    print()


if __name__ == '__main__':
    main()
