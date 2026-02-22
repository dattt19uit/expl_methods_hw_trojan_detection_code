"""
Case-based Classification with Weighted Explanations (Method 2)

Supports both KNN and XGBoost models with auto-detection.
Generates case-based explanations with weighted correspondence scoring.

Model Auto-Detection:
- KNN models: Contains 'scaler' and 'X_train_scaled' fields
- XGBoost models: Contains 'model' with predict_proba method, X_train unscaled

Explanation Format:
- Lists k-nearest neighbors from training data
- Shows distance to each neighbor
- Shows trojan/non-trojan ratio for each match
- Computes weighted correspondence: weight = 1 / (distance + 1)^3
- Applies configurable trojan multiplier for imbalanced data
"""

import os
import json
import pickle
import argparse
import time
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, matthews_corrcoef, cohen_kappa_score
)

# Import case-explainer
try:
    from case_explainer import CaseExplainer
    CASE_EXPLAINER_AVAILABLE = True
except ImportError:
    CASE_EXPLAINER_AVAILABLE = False
    print("WARNING: case-explainer not available. Install with: pip install git+https://github.com/paulwhitten/case-explainer.git")


def compute_weighted_correspondence(distances, labels, trojan_weight=1.0):
    """
    Compute weighted correspondence score using legacy formula.
    
    weight = (trojan_multiplier * trojan_count) / ((distance + 1)^3)
    
    Args:
        distances: Array of distances to k neighbors
        labels: Array of labels for k neighbors (0=clean, 1=trojan)
        trojan_weight: Multiplier for trojan samples (default: 1.0)
    
    Returns:
        weights: Array [weight_clean, weight_trojan]
        prediction: Predicted class (0 or 1)
        correspondence: Correspondence score (0.0-1.0)
    """
    weights = np.array([0.0, 0.0])
    
    for dist, label in zip(distances, labels):
        # Legacy formula: weight = 1 / (distance + 1)^3
        inv_weight = (dist + 1.0) ** 3
        
        if label == 0:  # Clean
            weights[0] += 1.0 / inv_weight
        else:  # Trojan
            weights[1] += trojan_weight / inv_weight
    
    # Determine prediction based on weights
    total_weight = weights.sum()
    if total_weight > 0:
        prediction = 1 if weights[1] > weights[0] else 0
        correspondence = weights[prediction] / total_weight
    else:
        prediction = 0
        correspondence = 0.5
    
    return weights, prediction, correspondence


def classify_with_xgboost(model_data, test_csv, output_dir, trojan_weight=1.0, k=5):
    """
    Classify using XGBoost model with case-based explanations from CaseExplainer.
    
    Uses XGBoost for predictions and CaseExplainer for explanations.
    
    Args:
        model_data: Loaded XGBoost model dictionary
        test_csv: Path to test CSV file
        output_dir: Directory to save outputs
        trojan_weight: Multiplier for trojan samples in correspondence
        k: Number of nearest neighbors for explanations (default: 5)
    
    Returns:
        metrics: Dictionary of classification metrics
    """
    if not CASE_EXPLAINER_AVAILABLE:
        raise ImportError("case-explainer is required. Install with: pip install git+https://github.com/paulwhitten/case-explainer.git")
    
    xgb_model = model_data['model']
    X_train = model_data['X_train']
    y_train = model_data['y_train']
    feature_names = model_data.get('feature_names', [])
    metadata = model_data['metadata']
    
    print(f"XGBoost Model: n_estimators={metadata.get('n_estimators', 100)}, max_depth={metadata.get('max_depth', 6)}")
    
    # Load test data
    print(f"Loading test data from {test_csv}...")
    df = pd.read_csv(test_csv)
    X_test = df.iloc[:, :-1].values
    y_test = df.iloc[:, -1].values.astype(int)
    
    print(f"Test samples: {len(X_test)}")
    print(f"Features: {X_test.shape[1]}")
    
    # Get XGBoost predictions
    print("Running XGBoost classification...")
    start_time = datetime.now()
    
    y_pred = xgb_model.predict(X_test)
    y_proba = xgb_model.predict_proba(X_test)
    
    end_time = datetime.now()
    print(f"Classification completed in {end_time - start_time}")
    
    # Create CaseExplainer for explanations
    print(f"Creating CaseExplainer (k={k})...")
    explainer = CaseExplainer(
        X_train=X_train,
        y_train=y_train,
        k=k,
        class_weights={0: 1.0, 1: trojan_weight},
        scale_data=True,  # Let CaseExplainer handle scaling
        n_jobs=-1
    )
    # Generate explanations
    print("Generating case-based explanations with CaseExplainer...")
    explain_start = time.time()
    case_explanations = explainer.explain_batch(X_test, y_test=y_test, predictions=y_pred, model=xgb_model)
    explain_elapsed = time.time() - explain_start
    explain_per_sample_ms = 1000 * explain_elapsed / len(X_test)
    print(f"Explanations completed in {explain_elapsed:.2f}s ({explain_per_sample_ms:.3f} ms/sample)")
    
    # Convert CaseExplainer explanations to legacy format
    explanations = []
    correspondence_matches = 0
    correspondence_scores = []
    
    for i, case_exp in enumerate(case_explanations):
        # Check if correspondence supports prediction
        if case_exp.correspondence_interpretation == 'correspondence':
            correspondence_matches += 1
        
        correspondence_scores.append(case_exp.correspondence)
        
        # Build matches description
        matches = []
        for neighbor in case_exp.neighbors:
            feature_str = np.array2string(neighbor.features, precision=4, suppress_small=True)
            
            # Compute weight (CaseExplainer uses 1/(d+1)^3 by default)
            weight_multiplier = trojan_weight if neighbor.label == 1 else 1.0
            weight_val = weight_multiplier / ((neighbor.distance + 1.0) ** 3)
            
            match_desc = (
                f"{feature_str} was found a distance of {neighbor.distance:.3f} "
                f"with label={'trojan' if neighbor.label == 1 else 'clean'}. "
                f"weight: {weight_val:.3f}"
            )
            matches.append(match_desc)
        
        # Build correspondence description
        correspondence_desc = (
            f"Decision {case_exp.correspondence_interpretation} "
            f"with correspondence score of {case_exp.correspondence:.3f} "
            f"for the prediction of {'trojan' if y_pred[i] == 1 else 'no trojan'} "
            f"based on neighbors from training data."
        )
        
        # Compute weights array for legacy format
        weights = np.array([0.0, 0.0])
        for neighbor in case_exp.neighbors:
            weight_multiplier = trojan_weight if neighbor.label == 1 else 1.0
            weight_val = weight_multiplier / ((neighbor.distance + 1.0) ** 3)
            weights[neighbor.label] += weight_val
        
        explanation = {
            'index': i,
            'label': int(y_test[i]),
            'decision': int(y_pred[i]),
            'confidence': float(y_proba[i][y_pred[i]]),
            'feature_vector': X_test[i].tolist(),
            'matches': matches,
            'description': correspondence_desc,
            'weights': weights.tolist(),
            'correspondence_score': float(case_exp.correspondence),
            'correspondence_interpretation': case_exp.correspondence_interpretation,
            'model_type': 'xgboost',
            'explainer_type': 'case-explainer'
        }
        explanations.append(explanation)
    
    # Compute average correspondence score
    avg_correspondence = np.mean(correspondence_scores)
    
    # Compute metrics
    print("Computing classification metrics...")
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average='binary', zero_division=0
    )
    mcc = matthews_corrcoef(y_test, y_pred)
    kappa = cohen_kappa_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    tn, fp, fn, tp = cm.ravel()
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    
    metrics = {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'mcc': float(mcc),
        'cohen_kappa': float(kappa),
        'specificity': float(specificity),
        'tpr': float(tpr),
        'confusion_matrix': cm.tolist(),
        'correspondence_rate': correspondence_matches / len(X_test),
        'avg_correspondence_score': float(avg_correspondence),
        'trojan_weight': trojan_weight,
        'model_type': 'xgboost',
        'explainer_type': 'case-explainer',
        'k_neighbors': k,
        'explain_time_seconds': explain_elapsed,
        'explain_time_per_sample_ms': explain_per_sample_ms,
        'timestamp': datetime.now().isoformat()
    }
    
    # Save outputs
    os.makedirs(output_dir, exist_ok=True)
    
    # Save predictions
    predictions_path = os.path.join(output_dir, 'predictions.json')
    with open(predictions_path, 'w') as f:
        json.dump({
            'predictions': y_pred.tolist(),
            'probabilities': y_proba.tolist(),
            'labels': y_test.tolist()
        }, f, indent=2)
    print(f"Predictions saved to {predictions_path}")
    
    # Save explanations
    explanations_path = os.path.join(output_dir, 'explanations.json')
    with open(explanations_path, 'w') as f:
        json.dump(explanations, f, indent=2)
    print(f"Explanations saved to {explanations_path}")
    
    # Save metrics
    metrics_path = os.path.join(output_dir, 'metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to {metrics_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("CLASSIFICATION RESULTS (XGBoost + CaseExplainer)")
    print("="*60)
    print(f"Accuracy:            {accuracy:.4f}")
    print(f"Precision:           {precision:.4f}")
    print(f"Recall:              {recall:.4f}")
    print(f"F1 Score:            {f1:.4f}")
    print(f"MCC:                 {mcc:.4f}")
    print(f"Cohen's Kappa:       {kappa:.4f}")
    print(f"Specificity:         {specificity:.4f}")
    print(f"TPR:                 {tpr:.4f}")
    print(f"Correspondence Rate: {metrics['correspondence_rate']:.4f}")
    print(f"Avg Correspondence:  {avg_correspondence:.4f}")
    print("="*60)
    
    return metrics


def classify_with_knn(model_data, test_csv, output_dir, trojan_weight=1.0):
    """
    Classify using KNN model with case-based explanations from CaseExplainer.
    
    Args:
        model_data: Loaded KNN model dictionary
        test_csv: Path to test CSV file
        output_dir: Directory to save outputs
        trojan_weight: Multiplier for trojan samples in correspondence
    
    Returns:
        metrics: Dictionary of classification metrics
    """
    if not CASE_EXPLAINER_AVAILABLE:
        raise ImportError("case-explainer is required. Install with: pip install git+https://github.com/paulwhitten/case-explainer.git")
    
    knn = model_data['model']
    scaler = model_data['scaler']
    X_train_scaled = model_data['X_train_scaled']
    y_train = model_data['y_train']
    metadata = model_data['metadata']
    
    k = metadata['k']
    print(f"KNN Model: k={k}, metric={metadata['metric']}")
    
    # Load test data
    print(f"Loading test data from {test_csv}...")
    df = pd.read_csv(test_csv)
    X_test = df.iloc[:, :-1].values
    y_test = df.iloc[:, -1].values.astype(int)
    X_test_scaled = scaler.transform(X_test)
    
    print(f"Test samples: {len(X_test)}")
    print(f"Features: {X_test.shape[1]}")
    
    # Get predictions and probabilities
    print("Running KNN classification...")
    start_time = datetime.now()
    
    y_pred = knn.predict(X_test_scaled)
    y_proba = knn.predict_proba(X_test_scaled)
    
    end_time = datetime.now()
    print(f"Classification completed in {end_time - start_time}")
    
    # Create CaseExplainer for explanations (use pre-scaled data since KNN already scaled)
    print(f"Creating CaseExplainer (k={k}, distance_penalty={distance_penalty})...")
    explainer = CaseExplainer(
        X_train=X_train_scaled,
        y_train=y_train,
        k=k,
        class_weights={0: 1.0, 1: trojan_weight},
        distance_penalty=distance_penalty,
        scale_data=False,  # Data already scaled by KNN model
        n_jobs=-1
    )
    
    # Generate explanations
    print("Generating case-based explanations with CaseExplainer...")
    explain_start = time.time()
    case_explanations = explainer.explain_batch(X_test_scaled, y_test=y_test, predictions=y_pred, model=knn)
    explain_elapsed = time.time() - explain_start
    explain_per_sample_ms = 1000 * explain_elapsed / len(X_test)
    print(f"Explanations completed in {explain_elapsed:.2f}s ({explain_per_sample_ms:.3f} ms/sample)")
    
    # Convert CaseExplainer explanations to legacy format
    explanations = []
    correspondence_matches = 0
    correspondence_scores = []
    
    for i, case_exp in enumerate(case_explanations):
        # Check if correspondence supports prediction
        if case_exp.correspondence_interpretation == 'correspondence':
            correspondence_matches += 1
        
        correspondence_scores.append(case_exp.correspondence)
        
        # Build matches description
        matches = []
        for neighbor in case_exp.neighbors:
            feature_str = np.array2string(neighbor.features, precision=4, suppress_small=True)
            
            # Compute weight
            weight_multiplier = trojan_weight if neighbor.label == 1 else 1.0
            weight_val = weight_multiplier / ((neighbor.distance + 1.0) ** 3)
            
            match_desc = (
                f"{feature_str} was found a distance of {neighbor.distance:.3f} "
                f"with label={'trojan' if neighbor.label == 1 else 'clean'}. "
                f"weight: {weight_val:.3f}"
            )
            matches.append(match_desc)
        
        # Build correspondence description
        correspondence_desc = (
            f"Decision {case_exp.correspondence_interpretation} "
            f"with correspondence score of {case_exp.correspondence:.3f} "
            f"for the prediction of {'trojan' if y_pred[i] == 1 else 'no trojan'} "
            f"based on neighbors from training data."
        )
        
        # Compute weights array for legacy format
        weights = np.array([0.0, 0.0])
        for neighbor in case_exp.neighbors:
            weight_multiplier = trojan_weight if neighbor.label == 1 else 1.0
            weight_val = weight_multiplier / ((neighbor.distance + 1.0) ** 3)
            weights[neighbor.label] += weight_val
        
        explanation = {
            'index': i,
            'label': int(y_test[i]),
            'decision': int(y_pred[i]),
            'confidence': float(y_proba[i][y_pred[i]]),
            'feature_vector': X_test[i].tolist(),
            'matches': matches,
            'description': correspondence_desc,
            'weights': weights.tolist(),
            'correspondence_score': float(case_exp.correspondence),
            'correspondence_interpretation': case_exp.correspondence_interpretation,
            'model_type': 'knn',
            'explainer_type': 'case-explainer'
        }
        explanations.append(explanation)
    
    # Compute average correspondence score
    avg_correspondence = np.mean(correspondence_scores)
    
    # Compute metrics
    print("Computing classification metrics...")
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average='binary', zero_division=0
    )
    mcc = matthews_corrcoef(y_test, y_pred)
    kappa = cohen_kappa_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    tn, fp, fn, tp = cm.ravel()
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    
    metrics = {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'mcc': float(mcc),
        'cohen_kappa': float(kappa),
        'specificity': float(specificity),
        'tpr': float(tpr),
        'confusion_matrix': cm.tolist(),
        'correspondence_rate': correspondence_matches / len(X_test),
        'avg_correspondence_score': float(avg_correspondence),
        'trojan_weight': trojan_weight,
        'model_type': 'knn',
        'explainer_type': 'case-explainer',
        'k_neighbors': k,
        'explain_time_seconds': explain_elapsed,
        'explain_time_per_sample_ms': explain_per_sample_ms,
        'timestamp': datetime.now().isoformat()
    }
    
    # Save outputs
    os.makedirs(output_dir, exist_ok=True)
    
    # Save predictions
    predictions_path = os.path.join(output_dir, 'predictions.json')
    with open(predictions_path, 'w') as f:
        json.dump({
            'predictions': y_pred.tolist(),
            'probabilities': y_proba.tolist(),
            'labels': y_test.tolist()
        }, f, indent=2)
    print(f"Predictions saved to {predictions_path}")
    
    # Save explanations
    explanations_path = os.path.join(output_dir, 'explanations.json')
    with open(explanations_path, 'w') as f:
        json.dump(explanations, f, indent=2)
    print(f"Explanations saved to {explanations_path}")
    
    # Save metrics
    metrics_path = os.path.join(output_dir, 'metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to {metrics_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("CLASSIFICATION RESULTS (KNN + CaseExplainer)")
    print("="*60)
    print(f"Accuracy:            {accuracy:.4f}")
    print(f"Precision:           {precision:.4f}")
    print(f"Recall:              {recall:.4f}")
    print(f"F1 Score:            {f1:.4f}")
    print(f"MCC:                 {mcc:.4f}")
    print(f"Cohen's Kappa:       {kappa:.4f}")
    print(f"Specificity:         {specificity:.4f}")
    print(f"TPR:                 {tpr:.4f}")
    print(f"Correspondence Rate: {metrics['correspondence_rate']:.4f}")
    print(f"Avg Correspondence:  {avg_correspondence:.4f}")
    print("="*60)
    
    return metrics


def classify_and_explain(model_path, test_csv, output_dir, trojan_weight=1.0, k=5):
    """
    Auto-detect model type and classify test samples with explanations.
    
    Supports both KNN and XGBoost models. Automatically detects the model type
    based on the structure of the loaded pickle file.
    
    Args:
        model_path: Path to trained model pickle file (KNN or XGBoost)
        test_csv: Path to test CSV file
        output_dir: Directory to save outputs
        trojan_weight: Multiplier for trojan samples in correspondence
        k: Number of neighbors for explanations (XGBoost only, default: 5)
    
    Returns:
        metrics: Dictionary of classification metrics
    """
    # Load model
    print(f"Loading model from {model_path}...")
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    # Auto-detect model type
    if 'scaler' in model_data and 'X_train_scaled' in model_data:
        # KNN model format
        print("Detected model type: KNN")
        return classify_with_knn(model_data, test_csv, output_dir, trojan_weight)
    
    elif 'model' in model_data and hasattr(model_data['model'], 'predict_proba'):
        # XGBoost model format
        if 'X_train' in model_data:
            print("Detected model type: XGBoost")
            return classify_with_xgboost(model_data, test_csv, output_dir, trojan_weight, k)
        else:
            raise ValueError(f"Model has predict_proba but missing X_train for explanations")
    
    else:
        raise ValueError(
            f"Unknown model format in {model_path}. "
            f"Expected KNN (with 'scaler', 'X_train_scaled') or "
            f"XGBoost (with 'model', 'X_train') format."
        )



def main():
    parser = argparse.ArgumentParser(
        description='Run classification with case-based explanations (KNN or XGBoost)'
    )
    parser.add_argument(
        '--model',
        required=True,
        help='Path to trained model pickle file (KNN or XGBoost)'
    )
    parser.add_argument(
        '--test-data',
        required=True,
        help='Path to test CSV file'
    )
    parser.add_argument(
        '--output-dir',
        default='../../data/outputs/case_based',
        help='Output directory for predictions and explanations'
    )
    parser.add_argument(
        '--trojan-weight',
        type=float,
        default=1.0,
        help='Weight multiplier for trojan samples (default: 1.0)'
    )
    parser.add_argument(
        '--k',
        type=int,
        default=5,
        help='Number of nearest neighbors for explanations (XGBoost only, default: 5)'
    )
    
    args = parser.parse_args()
    
    # Run classification with auto model detection
    classify_and_explain(
        model_path=args.model,
        test_csv=args.test_data,
        output_dir=args.output_dir,
        trojan_weight=args.trojan_weight,
        k=args.k
    )
    
    print("\n[OK] Classification and explanation generation complete!")


if __name__ == '__main__':
    main()
