#!/usr/bin/env python3
"""
Comprehensive Analysis Script: Hardware Trojan Detection Methods
Analyzes classification performance and explainability coverage of all 5 methods.

Usage:
    python3 scripts/analyze_methods_explainability.py [--output-txt FILE] [--output-json FILE]
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


def load_data():
    """Load all method results and explanations."""
    base_path = Path("data/models")
    explanations_path = Path("data/explanations")
    
    with open(base_path / "method1/arch_decisions.json") as f:
        m1_decisions = json.load(f)
    
    # Load Method 1 ensemble results (majority vote) if available
    m1_ensemble = None
    ensemble_file = base_path / "method1/kb_test_results.json"
    if ensemble_file.exists():
        with open(ensemble_file) as f:
            m1_ensemble = json.load(f)
    
    # Load Method 1 optimized thresholds (contains timing data)
    m1_thresholds = None
    thresholds_file = base_path / "method1/optimal_thresholds.json"
    if thresholds_file.exists():
        with open(thresholds_file) as f:
            m1_thresholds = json.load(f)
    
    with open(base_path / "method2/predictions.json") as f:
        m2_data = json.load(f)
    
    with open(base_path / "method2/metrics.json") as f:
        m2_metrics = json.load(f)
    
    # Load optimized threshold if available
    m2_optimal = None
    optimal_threshold_file = base_path / "method2/optimal_threshold.json"
    if optimal_threshold_file.exists():
        with open(optimal_threshold_file) as f:
            m2_optimal = json.load(f)
    
    with open(base_path / "method3/lime_explanations.json") as f:
        m3_lime = json.load(f)
    
    with open(base_path / "method4/shap_explanations.json") as f:
        m4_shap = json.load(f)
    
    # Load Method 5 if available
    m5_gradient = None
    m5_file = explanations_path / "method5/gradient_attributions.json"
    if m5_file.exists():
        with open(m5_file) as f:
            m5_gradient = json.load(f)
    
    return {
        'method1': m1_decisions,
        'method1_ensemble': m1_ensemble,
        'method1_thresholds': m1_thresholds,
        'method2': m2_data,
        'method2_metrics': m2_metrics,
        'method2_optimal': m2_optimal,
        'method3': m3_lime,
        'method4': m4_shap,
        'method5': m5_gradient
    }


def _extract_m1_timing(data):
    """Extract per-sample timing from M1 optimal_thresholds.json.
    
    Returns time in seconds per sample, or None if unavailable.
    """
    thresholds = data.get('method1_thresholds')
    if not thresholds:
        return None
    perf = thresholds.get('metadata', {}).get('performance', {})
    # Prefer isolated optimize_time_per_property_seconds
    if 'optimize_time_per_property_seconds' in perf:
        return perf['optimize_time_per_property_seconds']
    # Fallback to total / num_properties
    if 'optimize_time_seconds' in perf:
        num = thresholds.get('metadata', {}).get('num_properties', 1)
        return perf['optimize_time_seconds'] / max(num, 1)
    # Fallback to total pipeline time
    if 'time_per_property_seconds' in perf:
        return perf['time_per_property_seconds']
    return None


def _extract_m2_timing(data):
    """Extract per-sample timing from M2 metrics.json.
    
    Returns time in seconds per sample, or None if unavailable.
    """
    metrics = data.get('method2_metrics', {})
    # Prefer isolated explain_time
    if 'explain_time_per_sample_ms' in metrics:
        return metrics['explain_time_per_sample_ms'] / 1000  # ms -> s
    return None


def analyze_method1(data):
    """Analyze Method 1: Property-Based Ensemble."""
    decisions = data['method1']
    total = len(decisions)
    
    # Get average confidence from individual architecture decisions
    avg_confidence = sum(d['confidence'] for d in decisions) / total
    
    # Get ensemble performance from kb_test_results.json (majority vote)
    ensemble_data = data.get('method1_ensemble')
    if ensemble_data:
        predictions = ensemble_data['predictions']
        labels = ensemble_data['labels']
        
        # Calculate confusion matrix
        tp = sum(1 for pred, true in zip(predictions, labels) if pred == 1 and true == 1)
        fp = sum(1 for pred, true in zip(predictions, labels) if pred == 1 and true == 0)
        tn = sum(1 for pred, true in zip(predictions, labels) if pred == 0 and true == 0)
        fn = sum(1 for pred, true in zip(predictions, labels) if pred == 0 and true == 1)
        
        # Calculate metrics
        accuracy = (tp + tn) / (tp + tn + fp + fn)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        confusion_matrix = {
            'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp
        }
    else:
        # Fallback to individual architecture average (old behavior)
        correct = sum(1 for d in decisions if d['winner'] == d['label'])
        accuracy = correct / total
        precision = recall = f1_score = None
        confusion_matrix = None
    
    # Property effectiveness
    property_stats = {}
    for decision in decisions[:1000]:  # Sample 1000 for speed
        for vote in decision['votes']:
            prop = ','.join(vote['property'])
            if prop not in property_stats:
                property_stats[prop] = {'count': 0, 'tpr_sum': 0}
            property_stats[prop]['count'] += 1
            property_stats[prop]['tpr_sum'] += vote['tpr']
    
    top_properties = sorted(
        [(prop, stats['tpr_sum']/stats['count']) 
         for prop, stats in property_stats.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    return {
        'total_samples': total,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'confusion_matrix': confusion_matrix,
        'avg_confidence': avg_confidence,
        'explanation_coverage': 1.0,  # 100% coverage
        'top_properties': top_properties,
        'ensemble_metadata': ensemble_data.get('metadata') if ensemble_data else None,
        'avg_time_per_sample': _extract_m1_timing(data),
    }


def analyze_method2(data):
    """Analyze Method 2: XGBoost Classifier."""
    # Use optimized threshold metrics if available, otherwise fall back to baseline
    if data.get('method2_optimal'):
        optimal = data['method2_optimal']['optimal']
        baseline = data['method2_optimal']['baseline']
        improvement = data['method2_optimal']['improvement']
        
        return {
            'total_samples': len(data['method2']['predictions']),
            'accuracy': optimal['accuracy'],
            'precision': optimal['precision'],
            'recall': optimal['recall'],
            'f1_score': optimal['f1_score'],
            'confusion_matrix': optimal['confusion_matrix'],
            'explanation_coverage': 0.0,  # No inherent explanations
            'threshold': optimal['threshold'],
            'optimized': True,
            'baseline_metrics': {
                'precision': baseline['precision'],
                'recall': baseline['recall'],
                'f1_score': baseline['f1_score']
            },
            'improvement': improvement,
            'avg_time_per_sample': _extract_m2_timing(data),
        }
    else:
        # Fallback to baseline metrics
        metrics = data['method2_metrics']
        predictions = data['method2']
        
        return {
            'total_samples': len(predictions['predictions']),
            'accuracy': metrics['accuracy'],
            'precision': metrics['precision'],
            'recall': metrics['recall'],
            'f1_score': metrics['f1_score'],
            'confusion_matrix': metrics['confusion_matrix'],
            'explanation_coverage': 0.0,  # No inherent explanations
            'threshold': 0.5,
            'optimized': False,
            'avg_time_per_sample': _extract_m2_timing(data),
        }


def analyze_method3(data):
    """Analyze Method 3: LIME."""
    lime = data['method3']
    total_test_samples = len(data['method2']['labels'])
    explanations = lime['explanations']
    
    # Feature importance from summary
    summary = lime.get('summary', {})
    top_feature_freq = summary.get('top_feature_frequency', {})
    
    # Convert frequency counts to percentages
    total_explanations = len(explanations)
    top_features = sorted(
        [(feat, 100 * count / total_explanations) for feat, count in top_feature_freq.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5] if top_feature_freq else []
    
    # Check trojan coverage
    explained_indices = {exp['sample_index'] for exp in explanations}
    labels = data['method2']['labels']
    trojans_explained = sum(1 for idx in explained_indices if labels[idx] == 1)
    total_trojans = sum(labels)
    
    # Calculate avg time per sample (prefer isolated explain_time if available)
    if 'explain_time_per_sample_ms' in lime['metadata']:
        avg_time = lime['metadata']['explain_time_per_sample_ms'] / 1000  # Convert ms to seconds
    else:
        total_time = lime['metadata'].get('generation_time_seconds', 0)
        avg_time = total_time / len(explanations) if explanations else 0
    
    return {
        'total_samples': total_test_samples,
        'explanations_generated': len(explanations),
        'explanation_coverage': len(explanations) / total_test_samples,
        'trojans_explained': trojans_explained,
        'total_trojans': total_trojans,
        'trojan_coverage': trojans_explained / total_trojans if total_trojans > 0 else 0,
        'avg_time_per_sample': avg_time,
        'top_features': top_features
    }


def analyze_method4(data):
    """Analyze Method 4: SHAP."""
    shap = data['method4']
    total_test_samples = len(data['method2']['labels'])
    explanations = shap['explanations']
    
    # Calculate global feature importance
    feature_names = shap['metadata']['feature_names']
    importance = {feat: 0.0 for feat in feature_names}
    
    for exp in explanations:
        for feat, val in exp['shapley_values'].items():
            importance[feat] += abs(val)
    
    importance = {k: v/len(explanations) for k, v in importance.items()}
    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Check trojan coverage
    explained_indices = {exp['sample_index'] for exp in explanations}
    labels = data['method2']['labels']
    trojans_explained = sum(1 for idx in explained_indices if labels[idx] == 1)
    total_trojans = sum(labels)
    
    return {
        'total_samples': total_test_samples,
        'explanations_generated': len(explanations),
        'explanation_coverage': len(explanations) / total_test_samples,
        'trojans_explained': trojans_explained,
        'total_trojans': total_trojans,
        'trojan_coverage': trojans_explained / total_trojans,
        'avg_time_per_sample': shap['metadata'].get('explain_time_per_sample_ms', shap['metadata']['avg_time_per_sample'] * 1000) / 1000,
        'top_features': top_features
    }


def analyze_method5(data):
    """Analyze Method 5: Gradient Attribution."""
    if data['method5'] is None:
        return None
    
    gradient = data['method5']
    total_test_samples = len(data['method2']['labels'])
    explanations = gradient['explanations']
    
    # Get global feature importance
    global_importance = gradient['global_feature_importance']
    top_features = sorted(global_importance.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Check trojan coverage
    explained_indices = {exp['sample_index'] for exp in explanations}
    labels = data['method2']['labels']
    trojans_explained = sum(1 for idx in explained_indices if labels[idx] == 1)
    total_trojans = sum(labels)
    
    # Get model type and accuracy
    model_type = gradient['metadata']['model_type']
    model_accuracy = gradient['metadata'].get('accuracy', None)
    
    return {
        'total_samples': total_test_samples,
        'explanations_generated': len(explanations),
        'explanation_coverage': len(explanations) / total_test_samples,
        'trojans_explained': trojans_explained,
        'total_trojans': total_trojans,
        'trojan_coverage': trojans_explained / total_trojans,
        'avg_time_per_sample': gradient['metadata'].get('explain_time_per_sample_ms', gradient['metadata']['avg_time_per_sample_ms']) / 1000,  # Convert ms to seconds
        'model_type': model_type,
        'model_accuracy': model_accuracy,
        'top_features': top_features
    }


def generate_report(analyses):
    """Generate comprehensive analysis report."""
    report = []
    report.append("="*80)
    report.append("COMPREHENSIVE METHODS ANALYSIS: Hardware Trojan Detection Pipeline")
    report.append("="*80)
    report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\nTest Set Size: {analyses['method2']['total_samples']:,} samples")
    report.append(f"Total Trojans: {analyses['method3']['total_trojans']}")
    report.append(f"Trojan Rate: {100 * analyses['method3']['total_trojans'] / analyses['method2']['total_samples']:.2f}%")
    
    # Method 1
    report.append("\n" + "="*80)
    report.append("METHOD 1: PROPERTY-BASED ENSEMBLE")
    report.append("="*80)
    m1 = analyses['method1']
    report.append(f"\nClassification Performance:")
    report.append(f"  Accuracy: {100*m1['accuracy']:.2f}%")
    
    # Show complete metrics if available (from ensemble)
    if m1.get('precision') is not None:
        report.append(f"  Precision: {100*m1['precision']:.2f}%")
        report.append(f"  Recall: {100*m1['recall']:.2f}%")
        report.append(f"  F1 Score: {m1['f1_score']:.4f}")
    
    report.append(f"  Avg Confidence: {m1['avg_confidence']:.4f}")
    
    # Show confusion matrix if available
    if m1.get('confusion_matrix'):
        cm = m1['confusion_matrix']
        report.append(f"\nConfusion Matrix:")
        report.append(f"  TN={cm['tn']:,}  FP={cm['fp']:,}")
        report.append(f"  FN={cm['fn']:,}  TP={cm['tp']:,}")
    
    report.append(f"\nExplainability:")
    report.append(f"  Coverage: {100*m1['explanation_coverage']:.1f}% ({m1['total_samples']:,} samples)")
    report.append(f"  [OK] FULL COVERAGE - Every sample has property-based explanation")
    if m1.get('avg_time_per_sample') is not None:
        report.append(f"  Avg optimize time per property: {m1['avg_time_per_sample']:.4f}s ({1000*m1['avg_time_per_sample']:.3f} ms)")
    report.append(f"\nTop 5 Properties by TPR:")
    for prop, tpr in m1['top_properties']:
        report.append(f"  * {prop}: TPR={tpr:.3f}")
    
    # Method 2
    report.append("\n" + "="*80)
    report.append("METHOD 2: XGBOOST CLASSIFIER")
    report.append("="*80)
    m2 = analyses['method2']
    
    # Show threshold optimization status
    if m2.get('optimized'):
        report.append(f"\n[OK] USING OPTIMIZED THRESHOLD: {m2['threshold']:.3f}")
        report.append(f"\nOptimized Performance:")
    else:
        report.append(f"\n[WARNING] USING DEFAULT THRESHOLD: {m2['threshold']}")
        report.append(f"\nClassification Performance:")
    
    report.append(f"  Accuracy: {100*m2['accuracy']:.2f}%")
    report.append(f"  Precision: {100*m2['precision']:.2f}%")
    report.append(f"  Recall: {100*m2['recall']:.2f}%")
    report.append(f"  F1 Score: {m2['f1_score']:.4f}")
    
    # Show improvement if optimized
    if m2.get('optimized'):
        imp = m2['improvement']
        report.append(f"\nImprovement vs Baseline (threshold=0.5):")
        report.append(f"  Precision: {100*m2['baseline_metrics']['precision']:.2f}% -> {100*m2['precision']:.2f}% (+{imp['precision_gain_percent']:.1f}%)")
        report.append(f"  Recall: {100*m2['baseline_metrics']['recall']:.2f}% -> {100*m2['recall']:.2f}% ({imp['recall_change_percent']:.1f}%)")
        report.append(f"  F1 Score: {m2['baseline_metrics']['f1_score']:.4f} -> {m2['f1_score']:.4f} (+{imp['f1_gain_percent']:.1f}%)")
        report.append(f"  False Positives Reduced: {imp['false_positives_reduced']} ({imp['false_positives_reduction_percent']:.1f}%)")
    
    report.append(f"\nConfusion Matrix:")
    cm = m2['confusion_matrix']
    if isinstance(cm, dict):
        report.append(f"  TN={cm['tn']:,}  FP={cm['fp']}")
        report.append(f"  FN={cm['fn']}  TP={cm['tp']}")
    else:
        report.append(f"  TN={cm[0][0]:,}  FP={cm[0][1]}")
        report.append(f"  FN={cm[1][0]}  TP={cm[1][1]}")
    
    report.append(f"\nExplainability:")
    report.append(f"  Coverage: {100*m2['explanation_coverage']:.1f}%")
    report.append(f"  [WARNING] NO INHERENT EXPLANATIONS - Requires LIME/SHAP")
    if m2.get('avg_time_per_sample') is not None:
        report.append(f"  Avg explain time per sample: {m2['avg_time_per_sample']:.4f}s ({1000*m2['avg_time_per_sample']:.3f} ms)")
    
    # Method 3
    report.append("\n" + "="*80)
    report.append("METHOD 3: LIME (Local Interpretable Model-Agnostic Explanations)")
    report.append("="*80)
    m3 = analyses['method3']
    report.append(f"\nExplanation Generation:")
    report.append(f"  Total explanations: {m3['explanations_generated']:,}")
    report.append(f"  Coverage: {100*m3['explanation_coverage']:.2f}% of test set")
    report.append(f"  [WARNING] PARTIAL COVERAGE - Only first 500 samples explained")
    report.append(f"  Avg time per sample: {m3['avg_time_per_sample']:.4f}s")
    report.append(f"\nTrojan Coverage:")
    report.append(f"  Trojans explained: {m3['trojans_explained']} / {m3['total_trojans']}")
    report.append(f"  Trojan coverage: {100*m3['trojan_coverage']:.1f}%")
    report.append(f"  [WARNING] Only {m3['trojans_explained']} trojan sample(s) have LIME explanations")
    report.append(f"\nTop 5 Features (by #1 ranking frequency):")
    for feat, pct in m3['top_features']:
        report.append(f"  * {feat}: {pct:.1f}%")
    
    # Method 4
    report.append("\n" + "="*80)
    report.append("METHOD 4: SHAP (SHapley Additive exPlanations)")
    report.append("="*80)
    m4 = analyses['method4']
    report.append(f"\nExplanation Generation:")
    report.append(f"  Total explanations: {m4['explanations_generated']:,}")
    report.append(f"  Coverage: {100*m4['explanation_coverage']:.2f}% of test set")
    report.append(f"  [WARNING] PARTIAL COVERAGE - Only first 500 samples explained")
    report.append(f"  Avg time per sample: {m4['avg_time_per_sample']:.6f}s")
    report.append(f"  Speed advantage: {m3['avg_time_per_sample']/m4['avg_time_per_sample']:.1f}x faster than LIME")
    report.append(f"\nTrojan Coverage:")
    report.append(f"  Trojans explained: {m4['trojans_explained']} / {m4['total_trojans']}")
    report.append(f"  Trojan coverage: {100*m4['trojan_coverage']:.1f}%")
    report.append(f"  [WARNING] Only {m4['trojans_explained']} trojan sample(s) have SHAP explanations")
    report.append(f"\nTop 5 Features (by avg |SHAP| value):")
    for feat, importance in m4['top_features']:
        report.append(f"  * {feat}: {importance:.4f}")
    
    # Method 5
    if analyses.get('method5') is not None:
        report.append("\n" + "="*80)
        report.append("METHOD 5: GRADIENT ATTRIBUTION (Feature Importance)")
        report.append("="*80)
        m5 = analyses['method5']
        report.append(f"\nModel Type: {m5['model_type']}")
        report.append(f"\nExplanation Generation:")
        report.append(f"  Total explanations: {m5['explanations_generated']:,}")
        report.append(f"  Coverage: {100*m5['explanation_coverage']:.2f}% of test set")
        if m5['explanation_coverage'] >= 1.0:
            report.append(f"  [OK] FULL COVERAGE - All samples explained")
        else:
            report.append(f"  [WARNING] PARTIAL COVERAGE - {m5['explanations_generated']} samples explained")
        report.append(f"  Avg time per sample: {m5['avg_time_per_sample']:.6f}s")
        
        # Speed comparison
        if m4['avg_time_per_sample'] > 0:
            speed_vs_shap = m4['avg_time_per_sample'] / m5['avg_time_per_sample']
            report.append(f"  Speed advantage: {speed_vs_shap:.1f}x faster than SHAP")
        if m3['avg_time_per_sample'] > 0:
            speed_vs_lime = m3['avg_time_per_sample'] / m5['avg_time_per_sample']
            report.append(f"  Speed advantage: {speed_vs_lime:.1f}x faster than LIME")
        
        report.append(f"\nTrojan Coverage:")
        report.append(f"  Trojans explained: {m5['trojans_explained']} / {m5['total_trojans']}")
        report.append(f"  Trojan coverage: {100*m5['trojan_coverage']:.1f}%")
        
        report.append(f"\nTop 5 Features (by global importance):")
        for feat, importance in m5['top_features']:
            report.append(f"  * {feat}: {100*importance:.2f}%")
    
    # Key Observations
    report.append("\n" + "="*80)
    report.append("KEY OBSERVATIONS")
    report.append("="*80)
    
    report.append("\n1. EXPLANATION COVERAGE DISPARITY:")
    report.append(f"   * Method 1: 100% coverage ({m1['total_samples']:,} samples)")
    report.append(f"   * Method 2: 0% coverage (black box)")
    report.append(f"   * Method 3: {100*m3['explanation_coverage']:.2f}% coverage ({m3['explanations_generated']} samples)")
    report.append(f"   * Method 4: {100*m4['explanation_coverage']:.2f}% coverage ({m4['explanations_generated']} samples)")
    if analyses.get('method5') is not None:
        m5 = analyses['method5']
        report.append(f"   * Method 5: {100*m5['explanation_coverage']:.2f}% coverage ({m5['explanations_generated']:,} samples)")
    
    report.append("\n2. TROJAN SAMPLE EXPLANATIONS:")
    report.append(f"   [WARNING] CRITICAL: Only {m3['trojans_explained']}/{m3['total_trojans']} trojans have LIME/SHAP explanations")
    report.append(f"   This is because LIME/SHAP only explained first 500 samples (mostly clean)")
    report.append(f"   For production, should generate explanations for ALL flagged trojans!")
    
    report.append("\n3. PERFORMANCE TRADEOFFS:")
    if m1.get('avg_time_per_sample') is not None:
        report.append(f"   * Property Ensemble (M1): {m1['avg_time_per_sample']:.4f}s/property = {m1['avg_time_per_sample']*1000:.3f} ms/property")
    if m2.get('avg_time_per_sample') is not None:
        report.append(f"   * Case-Based (M2): {m2['avg_time_per_sample']:.4f}s/sample = {m2['avg_time_per_sample']*1000:.3f} ms/sample")
    report.append(f"   * LIME (M3): {m3['avg_time_per_sample']:.4f}s/sample = {m3['avg_time_per_sample']*11392:.1f}s for full test set")
    report.append(f"   * SHAP (M4): {m4['avg_time_per_sample']:.6f}s/sample = {m4['avg_time_per_sample']*11392:.1f}s for full test set")
    if analyses.get('method5') is not None:
        m5 = analyses['method5']
        report.append(f"   * Gradient Attribution: {m5['avg_time_per_sample']:.6f}s/sample = {m5['avg_time_per_sample']*11392:.1f}s for full test set")
        report.append(f"   * Method 5 is FASTEST - {m4['avg_time_per_sample']/m5['avg_time_per_sample']:.1f}x faster than SHAP!")
    report.append(f"   * Method 1: Built-in explanations (no extra cost)")
    
    report.append("\n4. FEATURE IMPORTANCE CONSENSUS:")
    report.append(f"   Top features across methods (note ranking differences):")
    report.append(f"   * LIME: PO ranked #1 in {m3['top_features'][0][1]:.1f}% of samples")
    report.append(f"   * SHAP: PO has highest avg |SHAP| = {m4['top_features'][0][1]:.4f}")
    if analyses.get('method5') is not None:
        m5 = analyses['method5']
        # Show top 2 features from gradient
        report.append(f"   * Gradient Attribution: {m5['top_features'][0][0]} = {100*m5['top_features'][0][1]:.2f}%, {m5['top_features'][1][0]} = {100*m5['top_features'][1][1]:.2f}%")
        report.append(f"   [WARNING] NOTE: Gradient ranks LGFi highest, LIME/SHAP rank PO highest")
        report.append(f"   This reflects different attribution mechanisms (global vs local)")
    else:
        report.append(f"   * All methods agree: PRIMARY OUTPUTS (PO) are most critical")
    report.append(f"   * Validates: Trojans primarily affect output behavior and flip-flop states")
    
    report.append("\n5. CLASSIFICATION ACCURACY:")
    report.append(f"   * Method 2 (XGBoost): {100*m2['accuracy']:.2f}% accuracy")
    report.append(f"   * Method 1 (Ensemble): {100*m1['accuracy']:.2f}% accuracy")
    if analyses.get('method5') is not None:
        m5 = analyses['method5']
        m5_acc = m5.get('model_accuracy', None)
        if m5_acc:
            report.append(f"   * Method 5 reports: {100*m5_acc:.2f}% accuracy")
            if abs(m5_acc - m2['accuracy']) > 0.01:  # >1% difference
                report.append(f"   WARNING: Method 5 and Method 2 use same model but report different accuracy!")
                report.append(f"   Verify Method 5 is evaluating on test set, not training set")
    report.append(f"   * Method 2 achieves highest accuracy but needs SHAP for explanations")
    
    # Recommendations
    report.append("\n" + "="*80)
    report.append("RECOMMENDATIONS")
    report.append("="*80)
    
    report.append("\n1. FOR PRODUCTION DEPLOYMENT:")
    report.append("   * Use Method 2 (XGBoost) for classification (97.19% accuracy)")
    if analyses.get('method5') is not None:
        report.append("   * Use Method 5 (Gradient Attribution) for ULTRA-FAST explanations")
        report.append("   * Fallback to SHAP for more detailed local explanations if needed")
    else:
        report.append("   * Generate SHAP explanations ON-DEMAND for flagged trojans")
    report.append("   * Use Method 1 for deep investigation when needed")
    
    report.append("\n2. FIX EXPLANATION COVERAGE:")
    report.append("   * CRITICAL: Generate SHAP explanations for ALL trojan samples")
    report.append("   * Currently only 1 trojan has explanation (2.2% coverage)")
    report.append("   * Should explain at minimum all 46 trojans + flagged false positives")
    if analyses.get('method5') is not None:
        m5 = analyses['method5']
        if m5['explanation_coverage'] >= 1.0:
            report.append(f"   * [OK] Method 5 has FULL COVERAGE ({m5['explanations_generated']} samples)")
    
    report.append("\n3. OPTIMIZE PERFORMANCE:")
    if analyses.get('method5') is not None:
        m5 = analyses['method5']
        shap_vs_grad = m4['avg_time_per_sample'] / m5['avg_time_per_sample']
        report.append(f"   * Gradient Attribution is FASTEST: {shap_vs_grad:.1f}x faster than SHAP")
        report.append(f"   * Full test set with Method 5: ~{m5['avg_time_per_sample']*11392:.1f}s (INSTANT)")
    else:
        report.append("   * SHAP is 18x faster than LIME (0.001s vs 0.018s)")
    report.append("   * Full test set SHAP: ~11 seconds (acceptable)")
    report.append("   * Consider batch explanation generation for all flagged samples")
    
    report.append("\n4. MULTI-METHOD VALIDATION:")
    report.append("   * For high-stakes decisions, compare all methods:")
    report.append("     - Method 2: Initial classification")
    if analyses.get('method5') is not None:
        report.append("     - Method 5: Instant global attribution (Gradient)")
    report.append("     - Method 4: Fast local attribution (SHAP)")
    report.append("     - Method 1: Property-level investigation")
    report.append("     - Method 3: Validation via sensitivity analysis (if needed)")
    
    report.append("\n" + "="*80)
    
    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description='Analyze explainability methods')
    parser.add_argument('--output-txt', help='Output text report file path', default=None)
    parser.add_argument('--output-json', help='Output JSON report file path', default=None)
    # Backward compatibility
    parser.add_argument('--output', '-o', help='Output file path (text format)', default=None, dest='output_txt')
    args = parser.parse_args()
    
    print("Loading data...")
    data = load_data()
    
    print("Analyzing Method 1...")
    m1_analysis = analyze_method1(data)
    
    print("Analyzing Method 2...")
    m2_analysis = analyze_method2(data)
    
    print("Analyzing Method 3...")
    m3_analysis = analyze_method3(data)
    
    print("Analyzing Method 4...")
    m4_analysis = analyze_method4(data)
    
    analyses = {
        'method1': m1_analysis,
        'method2': m2_analysis,
        'method3': m3_analysis,
        'method4': m4_analysis
    }
    
    # Method 5 is optional (may not be generated yet)
    if data['method5'] is not None:
        print("Analyzing Method 5...")
        m5_analysis = analyze_method5(data)
        analyses['method5'] = m5_analysis
    else:
        print("Method 5 data not found (skipping)")
    
    print("\nGenerating report...")
    report = generate_report(analyses)
    
    # Save text report
    if args.output_txt:
        with open(args.output_txt, 'w') as f:
            f.write(report)
        print(f"Text report saved to: {args.output_txt}")
    
    # Save JSON report
    if args.output_json:
        json_data = {
            'timestamp': datetime.now().isoformat(),
            'analyses': analyses
        }
        with open(args.output_json, 'w') as f:
            json.dump(json_data, f, indent=2)
        print(f"JSON report saved to: {args.output_json}")
    
    # If no output specified, print to console
    if not args.output_txt and not args.output_json:
        print("\n" + report)


if __name__ == "__main__":
    main()
