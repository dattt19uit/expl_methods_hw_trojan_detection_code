#!/usr/bin/env python3
"""
Comprehensive Experimental Suite:
Empirical Proof of Tabular Baseline XGBoost (5 Hasegawa Features)
Succeeding on In-Distribution Train/Val/Test Splits but Catastrophically Collapsing under LOFO Distribution Shift.

Matches and extends:
- Baseline: Whitten, Wolff & Papachristou (JETTA 2026 / arXiv:2601.18696v7, Table 9 & Table 10)
- Benchmark Data: 30 Trust-Hub circuits from author's flattened circuitgraph (data/circuits/*.csv)
- 5 Features: LGFi, ffi, ffo, PI, PO
- Ground Truth Label: Trojan (0 = clean, 1 = Trojan)
"""

import os
import sys
import csv
import json
import math
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon
from scipy.stats import wasserstein_distance, skew
from sklearn.metrics import (
    precision_score, recall_score, f1_score, matthews_corrcoef,
    roc_auc_score, average_precision_score, confusion_matrix
)
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import StandardScaler, RobustScaler, QuantileTransformer
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb

# Set random seeds
SEEDS = [42, 101, 2024, 777, 888, 999, 1234, 5678, 9999, 31415]
BASE_5_FEATURES = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']

CIRCUIT_FAMILIES = {
    'RS232': [
        'RS232-T1000', 'RS232-T1100', 'RS232-T1200', 'RS232-T1300', 'RS232-T1400',
        'RS232-T1500', 'RS232-T1600', 'RS232-T1700', 'RS232-T1800', 'RS232-T1900', 'RS232-T2000'
    ],
    's15850': ['s15850-T100'],
    's35932': ['s35932-T100', 's35932-T200', 's35932-T300'],
    's38417': ['s38417-T100', 's38417-T200'],
    's38584': ['s38584-T100', 's38584-T300'],
}

def get_family_for_circuit(circuit_name: str) -> str:
    for fam, pats in CIRCUIT_FAMILIES.items():
        if any(p in circuit_name for p in pats):
            return fam
    return 'Unknown'

def load_all_circuits(circuits_dir: Path) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """Loads all 30 circuit CSVs and attaches circuit and family metadata."""
    circuit_files = sorted(list(circuits_dir.glob('*.csv')))
    all_dfs = []
    per_circuit_dfs = {}

    for cf in circuit_files:
        cname = cf.stem
        fam = get_family_for_circuit(cname)
        df = pd.read_csv(cf)
        df['circuit'] = cname
        df['family'] = fam
        # Ensure 5 features exist
        for f in BASE_5_FEATURES:
            df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0.0)
        df['Trojan'] = pd.to_numeric(df['Trojan'], errors='coerce').fillna(0).astype(int)
        
        all_dfs.append(df)
        per_circuit_dfs[cname] = df

    full_df = pd.concat(all_dfs, ignore_index=True)
    return full_df, per_circuit_dfs

def compute_detailed_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray = None) -> Dict[str, Any]:
    """Computes all classification metrics and operational EDA metrics."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    mcc = matthews_corrcoef(y_true, y_pred) if len(np.unique(y_true)) > 1 else 0.0

    roc_auc = 0.5
    pr_auc = 0.0
    if y_prob is not None and len(np.unique(y_true)) > 1:
        try:
            roc_auc = float(roc_auc_score(y_true, y_prob))
        except Exception:
            roc_auc = 0.5
        try:
            pr_auc = float(average_precision_score(y_true, y_prob))
        except Exception:
            pr_auc = 0.0

    # Operational EDA metrics
    n_clean = tn + fp
    fp_per_1000 = (fp / (n_clean / 1000.0)) if n_clean > 0 else 0.0
    crr = 1.0 - (float(tp + fp) / float(len(y_true))) if len(y_true) > 0 else 0.0

    return {
        'tp': int(tp), 'fp': int(fp), 'fn': int(fn), 'tn': int(tn),
        'precision': float(prec), 'recall': float(rec), 'f1': float(f1),
        'mcc': float(mcc), 'roc_auc': float(roc_auc), 'pr_auc': float(pr_auc),
        'fp_per_1000': float(fp_per_1000), 'crr': float(crr)
    }

def find_best_threshold(y_val: np.ndarray, prob_val: np.ndarray, steps: int = 100) -> Tuple[float, float]:
    """Scans 100 thresholds between 0.01 and 0.99 to find tau* maximizing F1 on validation."""
    best_tau = 0.5
    best_f1 = -1.0
    thresholds = np.linspace(0.01, 0.99, steps)
    for tau in thresholds:
        pred = (prob_val >= tau).astype(int)
        score = f1_score(y_val, pred, zero_division=0)
        if score > best_f1:
            best_f1 = score
            best_tau = tau
    return float(best_tau), float(best_f1)

def train_xgboost(X_train: np.ndarray, y_train: np.ndarray, seed: int = 42, max_depth: int = 6, scale_pos_mode: str = 'ratio') -> xgb.XGBClassifier:
    n_pos = np.sum(y_train == 1)
    n_neg = np.sum(y_train == 0)
    
    if scale_pos_mode == 'ratio':
        spw = float(n_neg) / max(1.0, float(n_pos))
    elif scale_pos_mode == 'sqrt':
        spw = math.sqrt(float(n_neg) / max(1.0, float(n_pos)))
    else:
        spw = 1.0

    clf = xgb.XGBClassifier(
        objective='binary:logistic',
        eval_metric='logloss',
        max_depth=max_depth,
        learning_rate=0.3,
        n_estimators=100,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=spw,
        random_state=seed,
        n_jobs=-1
    )
    clf.fit(X_train, y_train)
    return clf

# ==============================================================================
# EXPERIMENT 1: IN-DISTRIBUTION RANDOM SPLIT (60/20/20) ACROSS 10 SEEDS
# ==============================================================================
def run_in_distribution_experiments(full_df: pd.DataFrame) -> Dict[str, Any]:
    print("\n" + "="*80)
    print("EXPERIMENT 1: IN-DISTRIBUTION RANDOM SPLIT (60% Train / 20% Val / 20% Test)")
    print("="*80)

    X = full_df[BASE_5_FEATURES].values
    y = full_df['Trojan'].values

    runs_tau_opt = []
    runs_tau_05 = []
    runs_tau_author = [] # tau = 0.940 as published in Whitten et al.

    for seed in SEEDS:
        # First split 80% train+val, 20% test
        sss1 = StratifiedShuffleSplit(n_splits=1, test_size=0.20, random_state=seed)
        train_val_idx, test_idx = next(sss1.split(X, y))
        X_tv, y_tv = X[train_val_idx], y[train_val_idx]
        X_test, y_test = X[test_idx], y[test_idx]

        # Second split 75% train (60% of total), 25% val (20% of total)
        sss2 = StratifiedShuffleSplit(n_splits=1, test_size=0.25, random_state=seed)
        tr_idx, val_idx = next(sss2.split(X_tv, y_tv))
        X_train, y_train = X_tv[tr_idx], y_tv[tr_idx]
        X_val, y_val = X_tv[val_idx], y_tv[val_idx]

        clf = train_xgboost(X_train, y_train, seed=seed)
        prob_val = clf.predict_proba(X_val)[:, 1]
        prob_test = clf.predict_proba(X_test)[:, 1]

        best_tau, best_val_f1 = find_best_threshold(y_val, prob_val)

        # Evaluate at optimal tau*
        pred_opt = (prob_test >= best_tau).astype(int)
        m_opt = compute_detailed_metrics(y_test, pred_opt, prob_test)
        m_opt['tau'] = best_tau
        m_opt['val_f1'] = best_val_f1
        runs_tau_opt.append(m_opt)

        # Evaluate at default tau = 0.500
        pred_05 = (prob_test >= 0.50).astype(int)
        m_05 = compute_detailed_metrics(y_test, pred_05, prob_test)
        m_05['tau'] = 0.50
        runs_tau_05.append(m_05)

        # Evaluate at author's fixed tau = 0.940
        pred_94 = (prob_test >= 0.940).astype(int)
        m_94 = compute_detailed_metrics(y_test, pred_94, prob_test)
        m_94['tau'] = 0.940
        runs_tau_author.append(m_94)

    def aggregate_runs(runs: List[Dict]) -> Dict[str, Any]:
        agg = {}
        for k in ['f1', 'precision', 'recall', 'mcc', 'roc_auc', 'pr_auc', 'fp_per_1000', 'crr', 'tau']:
            vals = [r[k] for r in runs]
            agg[f'{k}_mean'] = float(np.mean(vals))
            agg[f'{k}_std'] = float(np.std(vals))
        return agg

    agg_opt = aggregate_runs(runs_tau_opt)
    agg_05 = aggregate_runs(runs_tau_05)
    agg_author = aggregate_runs(runs_tau_author)

    print(f"Results across {len(SEEDS)} seeds (Mean ± Std):")
    print(f"  [At Optimal tau*] F1: {agg_opt['f1_mean']:.4f} ± {agg_opt['f1_std']:.4f} | Prec: {agg_opt['precision_mean']*100:.2f}% | Rec: {agg_opt['recall_mean']*100:.2f}% | ROC-AUC: {agg_opt['roc_auc_mean']:.4f} | PR-AUC: {agg_opt['pr_auc_mean']:.4f} | tau*: {agg_opt['tau_mean']:.3f}")
    print(f"  [At Default tau=0.5] F1: {agg_05['f1_mean']:.4f} ± {agg_05['f1_std']:.4f} | Prec: {agg_05['precision_mean']*100:.2f}% | Rec: {agg_05['recall_mean']*100:.2f}% | ROC-AUC: {agg_05['roc_auc_mean']:.4f}")
    print(f"  [At Author's tau=0.940] F1: {agg_author['f1_mean']:.4f} ± {agg_author['f1_std']:.4f} | Prec: {agg_author['precision_mean']*100:.2f}% | Rec: {agg_author['recall_mean']*100:.2f}% | ROC-AUC: {agg_author['roc_auc_mean']:.4f}")

    return {
        'optimal_tau': agg_opt,
        'default_tau': agg_05,
        'author_tau': agg_author,
        'all_runs_optimal': runs_tau_opt,
    }

# ==============================================================================
# EXPERIMENT 2: LEAVE-ONE-FAMILY-OUT (LOFO) CROSS-VALIDATION
# ==============================================================================
def run_lofo_experiments(full_df: pd.DataFrame, tau_mode: str = 'val_tuned') -> Dict[str, Any]:
    print("\n" + "="*80)
    print(f"EXPERIMENT 2: LEAVE-ONE-FAMILY-OUT (LOFO 5-FOLD CV) [Threshold Mode: {tau_mode}]")
    print("="*80)

    families = list(CIRCUIT_FAMILIES.keys())
    per_family_results = {}
    tot_tp, tot_fp, tot_fn, tot_tn = 0, 0, 0, 0
    all_y_true = []
    all_y_prob = []

    for holdout_fam in families:
        test_mask = full_df['family'] == holdout_fam
        train_mask = ~test_mask

        df_train_pool = full_df[train_mask]
        df_test = full_df[test_mask]

        X_test = df_test[BASE_5_FEATURES].values
        y_test = df_test['Trojan'].values

        # Split 80% train, 20% val inside the 4 training families (stratified)
        X_pool = df_train_pool[BASE_5_FEATURES].values
        y_pool = df_train_pool['Trojan'].values

        sss = StratifiedShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
        tr_idx, val_idx = next(sss.split(X_pool, y_pool))
        X_train, y_train = X_pool[tr_idx], y_pool[tr_idx]
        X_val, y_val = X_pool[val_idx], y_pool[val_idx]

        clf = train_xgboost(X_train, y_train, seed=42)

        prob_val = clf.predict_proba(X_val)[:, 1]
        prob_test = clf.predict_proba(X_test)[:, 1]

        best_tau_val, _ = find_best_threshold(y_val, prob_val)
        best_tau_test_oracle, _ = find_best_threshold(y_test, prob_test)

        if tau_mode == 'author_fixed_94':
            tau = 0.940
        elif tau_mode == 'default_05':
            tau = 0.500
        elif tau_mode == 'oracle_test':
            tau = best_tau_test_oracle
        else: # 'val_tuned'
            tau = best_tau_val

        pred_test = (prob_test >= tau).astype(int)
        m = compute_detailed_metrics(y_test, pred_test, prob_test)
        m['tau_used'] = float(tau)
        m['val_tau_opt'] = float(best_tau_val)
        m['oracle_tau_opt'] = float(best_tau_test_oracle)
        m['test_samples'] = int(len(y_test))
        m['test_trojans'] = int(np.sum(y_test))
        m['trojan_ratio_pct'] = float(np.sum(y_test) / len(y_test) * 100.0)

        per_family_results[holdout_fam] = m

        tot_tp += m['tp']
        tot_fp += m['fp']
        tot_fn += m['fn']
        tot_tn += m['tn']

        all_y_true.extend(y_test)
        all_y_prob.extend(prob_test)

        print(f"  Holdout Family: {holdout_fam:<8} | Gates: {len(y_test):>6} | Trojans: {np.sum(y_test):>3} ({m['trojan_ratio_pct']:.2f}%) | "
              f"TP: {m['tp']:>3}, FP: {m['fp']:>4}, FN: {m['fn']:>3} | "
              f"Prec: {m['precision']*100:>5.1f}%, Rec: {m['recall']*100:>5.1f}%, F1: {m['f1']:.4f}, PR-AUC: {m['pr_auc']:.4f} (tau={tau:.3f})")

    # Micro & Macro metrics
    micro_prec = tot_tp / max(1, tot_tp + tot_fp)
    micro_rec = tot_tp / max(1, tot_tp + tot_fn)
    micro_f1 = 2 * micro_prec * micro_rec / max(1e-9, micro_prec + micro_rec)
    macro_f1 = float(np.mean([per_family_results[f]['f1'] for f in families]))
    macro_pr_auc = float(np.mean([per_family_results[f]['pr_auc'] for f in families]))
    macro_roc_auc = float(np.mean([per_family_results[f]['roc_auc'] for f in families]))
    macro_mcc = float(np.mean([per_family_results[f]['mcc'] for f in families]))

    print("-" * 80)
    print(f"LOFO SUMMARY [{tau_mode}]:")
    print(f"  Macro-F1: {macro_f1:.4f} | Micro-F1: {micro_f1:.4f} | Micro-Prec: {micro_prec*100:.2f}% | Micro-Rec: {micro_rec*100:.2f}% | Macro PR-AUC: {macro_pr_auc:.4f} | Macro MCC: {macro_mcc:.4f}")
    print(f"  Total Counts: TP={tot_tp}, FP={tot_fp}, FN={tot_fn}, TN={tot_tn} (Total gates: {len(all_y_true)}, Trojans: {tot_tp+tot_fn})")

    return {
        'tau_mode': tau_mode,
        'macro_f1': macro_f1,
        'micro_f1': float(micro_f1),
        'micro_precision': float(micro_prec),
        'micro_recall': float(micro_rec),
        'macro_pr_auc': macro_pr_auc,
        'macro_roc_auc': macro_roc_auc,
        'macro_mcc': macro_mcc,
        'total_tp': int(tot_tp),
        'total_fp': int(tot_fp),
        'total_fn': int(tot_fn),
        'total_tn': int(tot_tn),
        'per_family': per_family_results
    }

# ==============================================================================
# EXPERIMENT 3: CAN FEATURE SCALING OR ALGORITHM VARIANTS RESCUE BASELINE IN LOFO?
# ==============================================================================
def run_remedy_exploration_under_lofo(full_df: pd.DataFrame) -> Dict[str, Any]:
    print("\n" + "="*80)
    print("EXPERIMENT 3: CAN FEATURE TRANSFORMATIONS / ALTERNATIVE ALGORITHMS RESCUE BASELINE IN LOFO?")
    print("="*80)

    variants = [
        ('Raw (Standard XGBoost depth=6)', 'raw', 'xgb_d6'),
        ('StandardScaler + XGBoost depth=6', 'standard', 'xgb_d6'),
        ('RobustScaler + XGBoost depth=6', 'robust', 'xgb_d6'),
        ('QuantileTransformer + XGBoost depth=6', 'quantile', 'xgb_d6'),
        ('Shallow XGBoost (depth=3, less overfitting)', 'raw', 'xgb_d3'),
        ('Deep XGBoost (depth=9)', 'raw', 'xgb_d9'),
        ('Random Forest (100 trees, class_weight=balanced)', 'raw', 'rf_balanced'),
    ]

    results_table = []
    families = list(CIRCUIT_FAMILIES.keys())

    for label, scaler_type, algo_type in variants:
        f1_scores = []
        tot_tp, tot_fp, tot_fn = 0, 0, 0

        for holdout_fam in families:
            test_mask = full_df['family'] == holdout_fam
            train_mask = ~test_mask

            X_tr = full_df[train_mask][BASE_5_FEATURES].values
            y_tr = full_df[train_mask]['Trojan'].values
            X_te = full_df[test_mask][BASE_5_FEATURES].values
            y_te = full_df[test_mask]['Trojan'].values

            # Apply scaler
            if scaler_type == 'standard':
                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X_tr)
                X_te = scaler.transform(X_te)
            elif scaler_type == 'robust':
                scaler = RobustScaler()
                X_tr = scaler.fit_transform(X_tr)
                X_te = scaler.transform(X_te)
            elif scaler_type == 'quantile':
                scaler = QuantileTransformer(output_distribution='normal', random_state=42)
                X_tr = scaler.fit_transform(X_tr)
                X_te = scaler.transform(X_te)

            # Fit model
            if algo_type == 'xgb_d6':
                clf = train_xgboost(X_tr, y_tr, seed=42, max_depth=6)
                prob_te = clf.predict_proba(X_te)[:, 1]
            elif algo_type == 'xgb_d3':
                clf = train_xgboost(X_tr, y_tr, seed=42, max_depth=3)
                prob_te = clf.predict_proba(X_te)[:, 1]
            elif algo_type == 'xgb_d9':
                clf = train_xgboost(X_tr, y_tr, seed=42, max_depth=9)
                prob_te = clf.predict_proba(X_te)[:, 1]
            elif algo_type == 'rf_balanced':
                clf = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42, n_jobs=-1)
                clf.fit(X_tr, y_tr)
                prob_te = clf.predict_proba(X_te)[:, 1]

            pred_te = (prob_te >= 0.5).astype(int)
            f1 = f1_score(y_te, pred_te, zero_division=0)
            f1_scores.append(f1)

            tp = np.sum((y_te == 1) & (pred_te == 1))
            fp = np.sum((y_te == 0) & (pred_te == 1))
            fn = np.sum((y_te == 1) & (pred_te == 0))
            tot_tp += tp
            tot_fp += fp
            tot_fn += fn

        micro_f1 = 2 * tot_tp / max(1e-9, 2 * tot_tp + tot_fp + tot_fn)
        macro_f1 = float(np.mean(f1_scores))

        res_row = {
            'variant': label,
            'macro_f1': macro_f1,
            'micro_f1': float(micro_f1),
            'total_tp': int(tot_tp),
            'total_fp': int(tot_fp),
            'total_fn': int(tot_fn),
            'f1_per_fam': {fam: float(f) for fam, f in zip(families, f1_scores)}
        }
        results_table.append(res_row)
        print(f"  Variant: {label:<45} | Macro-F1: {macro_f1:.4f} | Micro-F1: {micro_f1:.4f} | Caught Trojans: {tot_tp}/{tot_tp+tot_fn}")

    return {'variants_results': results_table}

# ==============================================================================
# EXPERIMENT 4: FEATURE DISTRIBUTION DRIFT & MATHEMATICAL ROOT-CAUSE ANALYSIS
# ==============================================================================
def run_feature_drift_analysis(full_df: pd.DataFrame) -> Dict[str, Any]:
    print("\n" + "="*80)
    print("EXPERIMENT 4: MATHEMATICAL ROOT-CAUSE: FEATURE DISTRIBUTION DRIFT ACROSS FAMILIES")
    print("="*80)

    families = list(CIRCUIT_FAMILIES.keys())
    drift_report = {}

    stats_by_fam = {}
    for fam in families:
        df_f = full_df[full_df['family'] == fam]
        stats_by_fam[fam] = {}
        for feat in BASE_5_FEATURES:
            vals = df_f[feat].values
            stats_by_fam[fam][feat] = {
                'mean': float(np.mean(vals)),
                'std': float(np.std(vals)),
                'median': float(np.median(vals)),
                'q25': float(np.percentile(vals, 25)),
                'q75': float(np.percentile(vals, 75)),
                'max': float(np.max(vals)),
                'min': float(np.min(vals)),
                'skew': float(skew(vals)) if len(vals) > 2 else 0.0
            }

    # Compute Wasserstein distance and Jensen-Shannon Divergence between RS232 (dominant family) and other families
    pairwise_dist = {}
    base_fam = 'RS232'
    df_base = full_df[full_df['family'] == base_fam]

    for other_fam in ['s15850', 's35932', 's38417', 's38584']:
        df_other = full_df[full_df['family'] == other_fam]
        pairwise_dist[f'{base_fam}_vs_{other_fam}'] = {}

        for feat in BASE_5_FEATURES:
            v_base = df_base[feat].values
            v_other = df_other[feat].values

            # Wasserstein (Earth Mover's Distance)
            w_dist = float(wasserstein_distance(v_base, v_other))

            # Jensen-Shannon on normalized histograms
            hist_range = (min(v_base.min(), v_other.min()), max(v_base.max(), v_other.max()))
            bins = 50
            p, _ = np.histogram(v_base, bins=bins, range=hist_range, density=True)
            q, _ = np.histogram(v_other, bins=bins, range=hist_range, density=True)
            p = p / max(1e-9, p.sum())
            q = q / max(1e-9, q.sum())
            js_div = float(jensenshannon(p, q))

            pairwise_dist[f'{base_fam}_vs_{other_fam}'][feat] = {
                'wasserstein_distance': w_dist,
                'jensen_shannon_div': js_div
            }

    print("Sample Feature Drift Metrics (Mean values per family):")
    for feat in BASE_5_FEATURES:
        row_str = f"  Feature: {feat:<5} | "
        for fam in families:
            m = stats_by_fam[fam][feat]['mean']
            s = stats_by_fam[fam][feat]['std']
            row_str += f"{fam}: {m:.1f}±{s:.1f} | "
        print(row_str)

    print("\nPairwise Wasserstein Distances (Domain Divergence from RS232):")
    for pair, feats in pairwise_dist.items():
        print(f"  {pair:<18}: " + ", ".join([f"{f}={feats[f]['wasserstein_distance']:.2f}" for f in BASE_5_FEATURES]))

    return {
        'stats_by_family': stats_by_fam,
        'pairwise_divergence': pairwise_dist
    }

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
def main():
    repo_root = Path(__file__).resolve().parent.parent
    circuits_dir = repo_root / 'data' / 'circuits'
    output_dir = repo_root / 'outputs' / 'results'
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading 30 Trust-Hub circuits from author's flattened circuitgraph...")
    full_df, per_circuit = load_all_circuits(circuits_dir)
    print(f"Loaded total {len(full_df)} gates across {len(per_circuit)} circuits.")
    print(f"Total Trojans: {full_df['Trojan'].sum()} ({full_df['Trojan'].sum()/len(full_df)*100:.3f}%)\n")

    # Family summary
    print("Family Breakdown:")
    for fam, pats in CIRCUIT_FAMILIES.items():
        df_f = full_df[full_df['family'] == fam]
        print(f"  Family {fam:<8}: {len(df_f):>6} gates, {df_f['Trojan'].sum():>3} Trojans ({df_f['Trojan'].sum()/len(df_f)*100:.3f}%)")

    # Run experiments
    exp1_in_dist = run_in_distribution_experiments(full_df)
    exp2_lofo_author = run_lofo_experiments(full_df, tau_mode='author_fixed_94')
    exp2_lofo_val = run_lofo_experiments(full_df, tau_mode='val_tuned')
    exp2_lofo_05 = run_lofo_experiments(full_df, tau_mode='default_05')
    exp2_lofo_oracle = run_lofo_experiments(full_df, tau_mode='oracle_test')
    exp3_remedies = run_remedy_exploration_under_lofo(full_df)
    exp4_drift = run_feature_drift_analysis(full_df)

    # Save comprehensive results JSON
    comprehensive_results = {
        'meta': {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'features': BASE_5_FEATURES,
            'total_gates': int(len(full_df)),
            'total_trojans': int(full_df['Trojan'].sum()),
            'circuits_count': len(per_circuit),
            'families': list(CIRCUIT_FAMILIES.keys())
        },
        'exp1_in_distribution_random_split': exp1_in_dist,
        'exp2_lofo_author_fixed_94': exp2_lofo_author,
        'exp2_lofo_val_tuned': exp2_lofo_val,
        'exp2_lofo_default_05': exp2_lofo_05,
        'exp2_lofo_oracle_test': exp2_lofo_oracle,
        'exp3_remedy_exploration_under_lofo': exp3_remedies,
        'exp4_feature_drift_analysis': exp4_drift
    }

    json_path = output_dir / 'baseline_5f_trainvaltest_vs_lofo_experiments.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(comprehensive_results, f, indent=2)
    print(f"\nSaved complete results JSON to: {json_path}")

    # Generate CSV breakdown table
    csv_rows = []
    for fam in CIRCUIT_FAMILIES.keys():
        m_val = exp2_lofo_val['per_family'][fam]
        m_auth = exp2_lofo_author['per_family'][fam]
        m_ora = exp2_lofo_oracle['per_family'][fam]
        csv_rows.append({
            'Family': fam,
            'Gates': m_val['test_samples'],
            'Trojans': m_val['test_trojans'],
            'Trojan_Pct': f"{m_val['trojan_ratio_pct']:.2f}%",
            'LOFO_ValTuned_F1': m_val['f1'],
            'LOFO_ValTuned_Prec': m_val['precision'],
            'LOFO_ValTuned_Rec': m_val['recall'],
            'LOFO_ValTuned_TP': m_val['tp'],
            'LOFO_ValTuned_FP': m_val['fp'],
            'LOFO_ValTuned_FN': m_val['fn'],
            'LOFO_ValTuned_Tau': m_val['tau_used'],
            'LOFO_Author94_F1': m_auth['f1'],
            'LOFO_Author94_Rec': m_auth['recall'],
            'LOFO_Oracle_F1': m_ora['f1'],
            'LOFO_Oracle_Tau': m_ora['tau_used'],
        })

    csv_path = output_dir / 'baseline_5f_lofo_breakdown.csv'
    pd.DataFrame(csv_rows).to_csv(csv_path, index=False)
    print(f"Saved LOFO per-family breakdown CSV to: {csv_path}")

if __name__ == '__main__':
    main()

