#!/usr/bin/env python3
"""
SHAP Explanations for Method 2 (Case-Based) Classifier

Generates SHAP (Shapley value) explanations for trained Method 2 models.
Uses TreeExplainer for XGBoost (fast) or KernelExplainer for SVM (slow).

Usage:
    python shap_explainer.py \\
        --model ../../data/models/method2/xgboost_model.pkl \\
        --training-data ../../data/processed/train.csv \\
        --test-data ../../data/processed/test.csv \\
        --output ./output_shap/shap_explanations.json \\
        --max-test-samples 100

Author: Paul Whitten, Francis Wolff, Chris Papachristou
Date: December 2025
"""

import argparse
import numpy as np
import pandas as pd
import pickle
import json
from pathlib import Path
import time
from datetime import datetime
import shap

FEATURE_NAMES = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']


def load_model(model_path):
    """Load trained model (XGBoost or SVM) with auto-detection."""
    print(f"Loading model from {model_path}...")
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    # Auto-detect model type
    if 'model' in model_data:
        # XGBoost model
        model = model_data['model']
        feature_columns = model_data.get('feature_names', model_data.get('feature_columns', FEATURE_NAMES))
        model_type = 'XGBoost'
    elif 'svm' in model_data:
        # SVM model
        model = model_data['svm']
        feature_columns = model_data.get('feature_columns', FEATURE_NAMES)
        model_type = 'SVM'
    else:
        raise ValueError("Unknown model format in pickle file")
    
    print(f"  Model type: {model_type}")
    print(f"  Model: {type(model).__name__}")
    print(f"  Features: {feature_columns}")
    
    return model, feature_columns, model_type


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
    
    return X, y, df


def create_shap_explainer(model, model_type, training_data, background_size=100):
    """
    Create SHAP explainer based on model type.
    
    For XGBoost: Uses TreeExplainer (fast, exact Shapley values)
    For SVM: Uses KernelExplainer (slow, approximate Shapley values)
    """
    if model_type == 'XGBoost':
        print(f"Creating TreeExplainer for XGBoost (fast, exact Shapley values)...")
        try:
            explainer = shap.TreeExplainer(model)
            explainer_type = 'TreeExplainer'
            print(f"  [OK] TreeExplainer created successfully")
        except Exception as e:
            print(f"  [FAIL] TreeExplainer failed: {e}")
            print(f"  Falling back to KernelExplainer (slower)...")
            background = shap.sample(training_data, min(background_size, len(training_data)))
            explainer = shap.KernelExplainer(model.predict_proba, background)
            explainer_type = 'KernelExplainer'
    else:
        # SVM - use KernelExplainer
        print(f"Creating KernelExplainer for SVM (slower, approximate Shapley values)...")
        background = shap.sample(training_data, min(background_size, len(training_data)))
        explainer = shap.KernelExplainer(model.predict_proba, background)
        explainer_type = 'KernelExplainer'
        print(f"  Background samples: {len(background)}")
    
    return explainer, explainer_type


def explain_sample(explainer, explainer_type, sample, feature_names):
    """
    Compute SHAP values for a single sample.
    
    Returns:
        shap_values: SHAP values for trojan class (class 1)
        base_value: Expected value (baseline prediction)
    """
    # Get SHAP values
    shap_values = explainer.shap_values(sample.reshape(1, -1))
    
    # Handle different output formats
    if isinstance(shap_values, list):
        # Multi-class output: [class0_values, class1_values]
        shap_values_trojan = shap_values[1][0]  # Class 1 (trojan)
    elif len(shap_values.shape) == 3:
        # Shape: (n_samples, n_features, n_classes)
        shap_values_trojan = shap_values[0, :, 1]  # Class 1
    elif len(shap_values.shape) == 2:
        # Shape: (n_samples, n_features) - already for one class
        shap_values_trojan = shap_values[0]
    else:
        # Shape: (n_features,)
        shap_values_trojan = shap_values
    
    # Get base value
    if hasattr(explainer, 'expected_value'):
        base_value = explainer.expected_value
        if isinstance(base_value, (list, np.ndarray)):
            base_value = base_value[1] if len(base_value) > 1 else base_value[0]
    else:
        base_value = 0.5  # Default
    
    return shap_values_trojan, base_value


def generate_explanations(model, model_type, explainer, explainer_type, test_data, test_labels, 
                         feature_names, max_samples=None, selected_indices=None,
                         predictions_path=None, prioritize_critical=False):
    """Generate SHAP explanations for test samples."""
    
    # selected_indices tracks mapping to original test set
    if selected_indices is None:
        selected_indices = np.arange(len(test_data))
    
    print(f"\nProcessing {len(test_data)} test samples...")
    
    explanations = []
    feature_importance_global = {fname: 0.0 for fname in feature_names}
    
    start_time = time.time()
    explain_time_total = 0.0
    correct = 0
    total = 0
    trojan_correct = 0
    trojan_total = 0
    
    for i, sample in enumerate(test_data):
        sample_start = time.time()
        
        # Get prediction
        pred_proba = model.predict_proba(sample.reshape(1, -1))[0]
        pred_label = int(np.argmax(pred_proba))
        true_label = int(test_labels[i]) if test_labels is not None else None
        
        # Get SHAP values (timed)
        explain_start = time.time()
        shap_values, base_value = explain_sample(explainer, explainer_type, sample, feature_names)
        explain_time_total += time.time() - explain_start
        
        # Create feature-value mapping
        shapley_dict = {
            feature_names[j]: float(shap_values[j])
            for j in range(len(feature_names))
        }
        
        # Update global feature importance (mean absolute SHAP value)
        for fname, shap_val in shapley_dict.items():
            feature_importance_global[fname] += abs(shap_val)
        
        # Create explanation text
        sorted_features = sorted(shapley_dict.items(), key=lambda x: abs(x[1]), reverse=True)
        top_features = sorted_features[:3]
        explanation = f"Prediction: {'Trojan' if pred_label == 1 else 'Clean'}. "
        explanation += f"Top contributors: "
        explanation += ", ".join([f"{fname} ({val:+.3f})" for fname, val in top_features])
        
        # Track accuracy
        if true_label is not None:
            total += 1
            if pred_label == true_label:
                correct += 1
            if true_label == 1:
                trojan_total += 1
                if pred_label == 1:
                    trojan_correct += 1
        
        sample_time = time.time() - sample_start
        
        # Progress update
        if (i + 1) % 10 == 0 or i == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / (i + 1)
            remaining = avg_time * (len(test_data) - i - 1)
            print(f"  [OK] Sample {i+1}/{len(test_data)} ({sample_time:.3f}s) - "
                  f"Avg: {avg_time:.3f}s/sample - "
                  f"ETA: {remaining:.1f}s")
        
        explanations.append({
            'sample_index': i,
            'original_test_index': int(selected_indices[i]),  # Map back to full test set
            'true_label': true_label,
            'predicted_label': pred_label,
            'predicted_proba': [float(p) for p in pred_proba],
            'base_value': float(base_value),
            'shapley_values': shapley_dict,
            'explanation': explanation
        })
    
    total_time = time.time() - start_time
    avg_time_per_sample = total_time / len(test_data)
    
    # Normalize global feature importance
    for fname in feature_importance_global:
        feature_importance_global[fname] /= len(test_data)
    
    # Calculate metrics
    accuracy = (correct / total * 100) if total > 0 else 0
    trojan_recall = (trojan_correct / trojan_total * 100) if trojan_total > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"Completed {len(explanations)} explanations in {total_time:.2f} seconds")
    print(f"Average time per sample: {avg_time_per_sample:.3f} seconds")
    print(f"Explanation-only time: {explain_time_total:.2f}s ({1000*explain_time_total/len(test_data):.3f} ms/sample)")
    if total > 0:
        print(f"Accuracy: {accuracy:.2f}% ({correct}/{total})")
        print(f"Trojan Recall: {trojan_recall:.2f}% ({trojan_correct}/{trojan_total})")
    print(f"{'='*60}\n")
    
    return {
        'explanations': explanations,
        'global_feature_importance': feature_importance_global,
        'sampling': {
            'method': 'intelligent' if prioritize_critical else 'naive',
            'original_indices': selected_indices.tolist() if isinstance(selected_indices, np.ndarray) else list(selected_indices),
            'num_trojans': int(trojan_total),
            'num_clean': int(total - trojan_total)
        },
        'metadata': {
            'total_samples': len(explanations),
            'model_type': model_type,
            'explainer_type': explainer_type,
            'feature_names': feature_names,
            'accuracy': accuracy,
            'trojan_recall': trojan_recall,
            'total_time_seconds': total_time,
            'avg_time_per_sample': avg_time_per_sample,
            'explain_time_seconds': explain_time_total,
            'explain_time_per_sample_ms': 1000 * explain_time_total / len(test_data),
            'predictions_file': predictions_path if predictions_path else None,
            'prioritize_critical': prioritize_critical,
            'timestamp': datetime.now().isoformat()
        }
    }


def run_shap_explanations(model_path, training_data_path, test_data_path, 
                          output_path, max_test_samples=None, background_size=100,
                          predictions_path=None, prioritize_critical=False):
    """Main function to generate SHAP explanations."""
    
    # Load model
    model, feature_names, model_type = load_model(model_path)
    
    # Load data
    X_train, y_train, _ = load_csv_data(training_data_path, feature_names)
    X_test, y_test, _ = load_csv_data(test_data_path, feature_names)
    
    # Intelligent sample selection
    original_indices = np.arange(len(X_test))
    selected_indices = original_indices
    
    if max_test_samples is not None and prioritize_critical and predictions_path:
        print(f"\n{'='*70}")
        print("INTELLIGENT SAMPLING: Prioritizing critical samples")
        print(f"{'='*70}")
        
        # Load Method 2 predictions
        with open(predictions_path, 'r') as f:
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
        
        if len(critical_indices) <= max_test_samples:
            # Include all critical + sample of TNs
            n_tn_sample = max_test_samples - len(critical_indices)
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
            print(f"\n[WARNING] More critical samples ({len(critical_indices)}) than max_test_samples ({max_test_samples})")
            print(f"  Priority order: Trojans > FPs > FNs")
            selected_indices = critical_indices[:max_test_samples]
            print(f"[OK] Explaining top {max_test_samples} critical samples")
        
        # Apply selection
        X_test = X_test[selected_indices]
        if y_test is not None:
            y_test = y_test[selected_indices]
        
        print(f"\nFinal sample composition:")
        print(f"  Total samples: {len(selected_indices)}")
        print(f"  Trojans: {np.sum(y_test == 1)}")
        print(f"  Clean: {np.sum(y_test == 0)}")
        
    elif max_test_samples is not None:
        # Fallback to naive sampling
        print(f"\nNaive sampling: Taking first {max_test_samples} samples")
        print("  (Use --prioritize-critical --predictions <file> for intelligent sampling)")
        X_test = X_test[:max_test_samples]
        selected_indices = original_indices[:max_test_samples]
        if y_test is not None:
            y_test = y_test[:max_test_samples]
    
    # Create SHAP explainer
    explainer, explainer_type = create_shap_explainer(model, model_type, X_train, background_size)
    
    # Generate explanations
    results = generate_explanations(
        model, model_type, explainer, explainer_type,
        X_test, y_test, feature_names, max_test_samples, selected_indices, 
        predictions_path, prioritize_critical
    )
    
    # Save results
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Saved explanations to {output_path}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Generate SHAP explanations for Method 2 classifier')
    parser.add_argument('--model', type=str, required=True,
                       help='Path to trained model pickle file')
    parser.add_argument('--training-data', type=str, required=True,
                       help='Path to training CSV file')
    parser.add_argument('--test-data', type=str, required=True,
                       help='Path to test CSV file')
    parser.add_argument('--output', type=str, required=True,
                       help='Output path for SHAP explanations JSON')
    parser.add_argument('--max-test-samples', type=int, default=None,
                       help='Maximum number of test samples to explain (default: all)')
    parser.add_argument('--background-size', type=int, default=100,
                       help='Number of background samples for KernelExplainer (default: 100)')
    
    args = parser.parse_args()
    
    run_shap_explanations(
        model_path=args.model,
        training_data_path=args.training_data,
        test_data_path=args.test_data,
        output_path=args.output,
        max_test_samples=args.max_test_samples,
        background_size=args.background_size
    )


if __name__ == '__main__':
    main()
