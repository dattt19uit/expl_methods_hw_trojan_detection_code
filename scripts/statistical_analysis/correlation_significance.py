#!/usr/bin/env python3
"""
Correlation Significance Testing for Phase 4 Statistical Analysis

Computes Spearman correlations with p-values for feature importance rankings.
"""

import numpy as np
import pandas as pd
import json
from pathlib import Path
from scipy.stats import spearmanr
import argparse


def test_correlation_significance(rankings1, rankings2, name1="Method 1", name2="Method 2"):
    """
    Compute Spearman correlation with significance test.
    
    Parameters:
    - rankings1: array of rankings from first method
    - rankings2: array of rankings from second method
    - name1, name2: descriptive names for the methods
    
    Returns:
    - dict with rho, p_value, significant, interpretation
    """
    rho, p_value = spearmanr(rankings1, rankings2)
    
    # Determine significance level
    if p_value < 0.001:
        significance = "***"
        interpretation = "highly significant"
    elif p_value < 0.01:
        significance = "**"
        interpretation = "very significant"
    elif p_value < 0.05:
        significance = "*"
        interpretation = "significant"
    else:
        significance = "ns"
        interpretation = "not significant"
    
    return {
        'rho': float(rho),
        'p_value': float(p_value),
        'significance': significance,
        'interpretation': interpretation,
        'n_features': len(rankings1),
        'comparison': f"{name1} vs {name2}"
    }


def importance_to_ranking(importance_dict, feature_order):
    """
    Convert feature importance values to rankings (1=most important).
    
    Parameters:
    - importance_dict: {feature_name: importance_value}
    - feature_order: list of feature names for consistent ordering
    
    Returns:
    - numpy array of rankings in feature_order
    """
    from scipy.stats import rankdata
    values = np.array([importance_dict.get(f, 0.0) for f in feature_order])
    # rankdata gives rank 1 to smallest; we want rank 1 for largest
    rankings = len(values) + 1 - rankdata(values)
    return rankings


def load_feature_rankings(results_dir, explanations_dir=None):
    """
    Load feature importance rankings from explainability methods.
    
    Extracts global feature importance from:
    - Method 3 (LIME): lime_explanations.json -> summary.avg_feature_weights -> mean
    - Method 4 (SHAP): shap_explanations.json -> global_feature_importance
    - Method 5 (Gradient): gradient_attributions.json -> global_feature_importance
    
    Returns dict with rankings for each method.
    """
    results_dir = Path(results_dir)
    if explanations_dir is None:
        explanations_dir = results_dir.parent / "explanations"
    else:
        explanations_dir = Path(explanations_dir)
    
    # Canonical feature order for consistent ranking comparison
    feature_order = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']
    
    rankings = {}
    importance_values = {}
    
    # Method 3: LIME - extract mean absolute weights from summary
    lime_path = results_dir / "method3" / "lime_explanations.json"
    if lime_path.exists():
        with open(lime_path) as f:
            data = json.load(f)
        avg_weights = data.get('summary', {}).get('avg_feature_weights', {})
        if avg_weights:
            lime_importance = {feat: abs(info['mean']) for feat, info in avg_weights.items()
                              if feat in feature_order}
            if len(lime_importance) == len(feature_order):
                importance_values['LIME'] = lime_importance
                rankings['LIME'] = importance_to_ranking(lime_importance, feature_order)
                print(f"  [OK] LIME importance: {lime_importance}")
    
    # Method 4: SHAP - global feature importance values
    shap_path = results_dir / "method4" / "shap_explanations.json"
    if shap_path.exists():
        with open(shap_path) as f:
            data = json.load(f)
        global_imp = data.get('global_feature_importance', {})
        if global_imp:
            shap_importance = {feat: abs(val) for feat, val in global_imp.items()
                              if feat in feature_order}
            if len(shap_importance) == len(feature_order):
                importance_values['SHAP'] = shap_importance
                rankings['SHAP'] = importance_to_ranking(shap_importance, feature_order)
                print(f"  [OK] SHAP importance: {shap_importance}")
    
    # Method 5: Gradient attribution - global feature importance
    grad_path = explanations_dir / "method5" / "gradient_attributions.json"
    if grad_path.exists():
        with open(grad_path) as f:
            data = json.load(f)
        global_imp = data.get('global_feature_importance', {})
        if global_imp:
            grad_importance = {feat: abs(val) for feat, val in global_imp.items()
                              if feat in feature_order}
            if len(grad_importance) == len(feature_order):
                importance_values['Gradient'] = grad_importance
                rankings['Gradient'] = importance_to_ranking(grad_importance, feature_order)
                print(f"  [OK] Gradient importance: {grad_importance}")
    
    return rankings, importance_values, feature_order


def compute_all_correlations(results_dir, output_file, explanations_dir=None):
    """
    Compute pairwise correlations between all methods' feature rankings.
    
    Parameters:
    - results_dir: directory containing method results
    - output_file: output JSON file path
    - explanations_dir: directory containing explanation results (default: results_dir/../explanations)
    """
    results_dir = Path(results_dir)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("Feature Ranking Correlation Analysis")
    print("="*60)
    print("")
    
    # Load rankings
    print("Loading feature rankings...")
    rankings, importance_values, feature_order = load_feature_rankings(results_dir, explanations_dir)
    
    if not rankings:
        print("[WARNING] No feature ranking data found!")
        print("Checked paths:")
        print(f"  - {results_dir / 'method3' / 'lime_explanations.json'}")
        print(f"  - {results_dir / 'method4' / 'shap_explanations.json'}")
        expl_dir = Path(explanations_dir) if explanations_dir else results_dir.parent / "explanations"
        print(f"  - {expl_dir / 'method5' / 'gradient_attributions.json'}")
        return None
    
    print(f"\n[OK] Loaded rankings from {len(rankings)} methods")
    for method, ranks in rankings.items():
        print(f"  - {method}: {len(ranks)} features, ranking = {ranks.tolist()}")
    
    # Print feature importance table
    print(f"\nFeature Importance Values:")
    print(f"  {'Feature':<8s}", end="")
    for method in importance_values:
        print(f"  {method:>12s}", end="")
    print()
    for feat in feature_order:
        print(f"  {feat:<8s}", end="")
        for method in importance_values:
            print(f"  {importance_values[method].get(feat, 0.0):>12.4f}", end="")
        print()
    
    print(f"\nFeature Rankings (1=most important):")
    print(f"  {'Feature':<8s}", end="")
    for method in rankings:
        print(f"  {method:>12s}", end="")
    print()
    for i, feat in enumerate(feature_order):
        print(f"  {feat:<8s}", end="")
        for method in rankings:
            print(f"  {int(rankings[method][i]):>12d}", end="")
        print()
    print("")
    
    # Compute all pairwise correlations
    print("Computing pairwise correlations...")
    print("-" * 60)
    
    correlations = {}
    method_names = list(rankings.keys())
    
    for i, method1 in enumerate(method_names):
        for method2 in method_names[i+1:]:
            ranks1 = rankings[method1]
            ranks2 = rankings[method2]
            
            # Ensure same length (take intersection if needed)
            if len(ranks1) != len(ranks2):
                min_len = min(len(ranks1), len(ranks2))
                ranks1 = ranks1[:min_len]
                ranks2 = ranks2[:min_len]
                print(f"  [WARNING] Truncated to {min_len} features for {method1} vs {method2}")
            
            result = test_correlation_significance(
                ranks1, ranks2,
                name1=method1,
                name2=method2
            )
            
            key = f"{method1}_vs_{method2}"
            correlations[key] = result
            
            print(f"  {method1:12s} vs {method2:12s}: "
                  f"rho = {result['rho']:6.3f}, p = {result['p_value']:.4f} {result['significance']}")
    
    print("")
    
    # Save results  
    output_data = {
        'feature_order': feature_order,
        'importance_values': {m: {f: float(v) for f, v in imp.items()} 
                             for m, imp in importance_values.items()},
        'rankings': {m: r.tolist() for m, r in rankings.items()},
        'correlations': correlations
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print("="*60)
    print(f"[OK] Results saved to: {output_file}")
    print("="*60)
    print("")
    
    # Print interpretation
    print("Interpretation:")
    print("-" * 60)
    print("Significance levels:")
    print("  *** p < 0.001 (highly significant)")
    print("  **  p < 0.01  (very significant)")
    print("  *   p < 0.05  (significant)")
    print("  ns  p >= 0.05 (not significant)")
    print("")
    print("Correlation strength:")
    print("  |rho| > 0.7: Strong")
    print("  |rho| > 0.5: Moderate")
    print("  |rho| > 0.3: Weak")
    print("  |rho| < 0.3: Very weak")
    
    return correlations


def main():
    parser = argparse.ArgumentParser(description='Compute correlation significance tests')
    parser.add_argument('--results-dir', default='data/models',
                       help='Directory containing model results')
    parser.add_argument('--explanations-dir', default=None,
                       help='Directory containing explanation results (default: results-dir/../explanations)')
    parser.add_argument('--output', default='data/statistical_analysis/correlation_tests.json',
                       help='Output JSON file')
    
    args = parser.parse_args()
    
    compute_all_correlations(args.results_dir, args.output, args.explanations_dir)


if __name__ == '__main__':
    main()
