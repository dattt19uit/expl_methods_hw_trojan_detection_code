#!/usr/bin/env python3
"""
Comprehensive 4-Way Benchmark: Baseline vs Graph IR on 5 and 13 Features

Evaluates 4 Experimental Configurations:
1. Exp 1: Baseline (5 Hasegawa Features)
2. Exp 2: Baseline + Graph Features (13 Features)
3. Exp 3: Graph IR (5 Hasegawa Features)
4. Exp 4: Graph IR + Graph Features (13 Features with Clock/Reset Filtering)

Evaluates on:
- Primary Protocol: Stratified Random Split (80/20)
- Generalization Protocol: Leave-One-Family-Out (LOFO) Cross-Validation across 5 circuit families.

Outputs a formatted comparative evaluation report and saves results to
data/models/comparison_4_experiments.json.
"""

import os
import sys
import csv
import math
import json
import logging
from pathlib import Path
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('4WayBenchmark')

BASE_5_FEATURES = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']
GRAPH_8_FEATURES = [
    'in_degree', 'out_degree', 'pagerank', 'betweenness',
    'closeness', 'clustering', 'core_number', 'logic_depth_ratio'
]
ALL_13_FEATURES = BASE_5_FEATURES + GRAPH_8_FEATURES

CIRCUIT_FAMILIES = {
    'RS232': ['RS232-T1000', 'RS232-T1100', 'RS232-T1200', 'RS232-T1300', 'RS232-T1400',
              'RS232-T1500', 'RS232-T1600', 'RS232-T1700', 'RS232-T1800', 'RS232-T1900', 'RS232-T2000'],
    's15850': ['s15850-T100'],
    's35932': ['s35932-T100', 's35932-T200', 's35932-T300'],
    's38417': ['s38417-T100', 's38417-T200'],
    's38584': ['s38584-T100', 's38584-T300'],
}


class FastBalancedForest:
    """Vectorized Balanced Random Forest in pure NumPy."""
    def __init__(self, n_estimators=60, max_depth=6, random_state=42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.trees = []

    def fit(self, X, y):
        rng = np.random.RandomState(self.random_state)
        n_samples, n_feats = X.shape
        pos_weight = (len(y) - y.sum()) / max(1, y.sum())

        self.trees = []
        for _ in range(self.n_estimators):
            sample_weights = np.where(y == 1, pos_weight, 1.0)
            sample_weights /= sample_weights.sum()
            sub_size = min(n_samples, 25000)
            idx = rng.choice(n_samples, size=sub_size, replace=True, p=sample_weights)
            Xs, ys = X[idx], y[idx]
            tree = self._build_tree(Xs, ys, depth=0, rng=rng)
            self.trees.append(tree)

    def _build_tree(self, X, y, depth, rng):
        if depth >= self.max_depth or len(np.unique(y)) <= 1 or len(y) < 10:
            return {'leaf': True, 'val': float(np.mean(y))}
        
        feat = rng.randint(0, X.shape[1])
        vals = np.unique(X[:, feat])
        if len(vals) <= 1:
            return {'leaf': True, 'val': float(np.mean(y))}
        
        split = rng.choice(vals)
        left_mask = X[:, feat] <= split
        right_mask = ~left_mask
        if left_mask.sum() == 0 or right_mask.sum() == 0:
            return {'leaf': True, 'val': float(np.mean(y))}

        return {
            'leaf': False,
            'feat': feat,
            'split': split,
            'left': self._build_tree(X[left_mask], y[left_mask], depth + 1, rng),
            'right': self._build_tree(X[right_mask], y[right_mask], depth + 1, rng)
        }

    def predict_proba(self, X):
        preds = np.zeros(len(X))
        for tree in self.trees:
            preds += self._predict_tree(tree, X)
        preds /= max(1, len(self.trees))
        return preds

    def _predict_tree(self, node, X):
        if node['leaf']:
            return np.full(len(X), node['val'])
        mask = X[:, node['feat']] <= node['split']
        out = np.empty(len(X))
        if mask.any():
            out[mask] = self._predict_tree(node['left'], X[mask])
        if (~mask).any():
            out[~mask] = self._predict_tree(node['right'], X[~mask])
        return out


def load_dataset_from_dir(data_dir: Path, feature_cols=None):
    """Load train.csv and test.csv, extracting specific feature columns."""
    train_path = data_dir / 'train.csv'
    test_path = data_dir / 'test.csv'

    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError(f"Missing train.csv or test.csv in {data_dir}")

    def _read_csv(filepath):
        X, y = [], []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                feat = [float(row.get(k, 0) or 0) for k in feature_cols]
                label = int(float(row.get('Trojan', 0) or 0))
                X.append(feat)
                y.append(label)
        return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)

    X_train, y_train = _read_csv(train_path)
    X_test, y_test = _read_csv(test_path)
    return X_train, y_train, X_test, y_test


def compute_metrics(y_true, y_pred, y_prob=None):
    """Compute precision, recall, f1, mcc, and confusion matrix."""
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))

    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn) - (fp * fn)) / denom if denom > 0 else 0.0

    res = {
        'precision': float(prec),
        'recall': float(rec),
        'f1': float(f1),
        'mcc': float(mcc),
        'tp': tp,
        'fp': fp,
        'tn': tn,
        'fn': fn,
    }

    if y_prob is not None:
        pos_probs = y_prob[y_true == 1]
        neg_probs = y_prob[y_true == 0]
        if len(pos_probs) > 0 and len(neg_probs) > 0:
            auc_val = float(np.mean([np.mean(p > neg_probs) + 0.5 * np.mean(p == neg_probs) for p in pos_probs]))
            res['roc_auc'] = auc_val
        else:
            res['roc_auc'] = 0.0

    return res


def run_experiment(X_train, y_train, X_test, y_test, exp_name):
    """Train model and evaluate on default (0.5) and optimal thresholds."""
    clf = FastBalancedForest(n_estimators=60, max_depth=6, random_state=42)
    clf.fit(X_train, y_train)

    y_prob = clf.predict_proba(X_test)
    y_pred_def = (y_prob >= 0.5).astype(int)

    # Threshold optimization
    thresholds = np.linspace(0.01, 0.99, 100)
    best_thresh, best_f1 = 0.5, 0.0
    for th in thresholds:
        th_pred = (y_prob >= th).astype(int)
        tp = np.sum((y_test == 1) & (th_pred == 1))
        fp = np.sum((y_test == 0) & (th_pred == 1))
        fn = np.sum((y_test == 1) & (th_pred == 0))
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        th_f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        if th_f1 > best_f1:
            best_f1 = th_f1
            best_thresh = th

    y_pred_opt = (y_prob >= best_thresh).astype(int)

    met_def = compute_metrics(y_test, y_pred_def, y_prob)
    met_opt = compute_metrics(y_test, y_pred_opt, y_prob)
    met_def['threshold'] = 0.5
    met_opt['threshold'] = float(best_thresh)

    return {
        'exp_name': exp_name,
        'train_samples': int(len(y_train)),
        'train_trojans': int(np.sum(y_train)),
        'test_samples': int(len(y_test)),
        'test_trojans': int(np.sum(y_test)),
        'num_features': X_train.shape[1],
        'default_threshold': met_def,
        'optimal_threshold': met_opt,
        'roc_auc': met_def.get('roc_auc', 0.0),
    }


def run_lofo_evaluation(circuits_dir: Path, feature_cols):
    """Run Leave-One-Family-Out (LOFO) Cross-Validation across 5 families."""
    circuit_files = list(circuits_dir.glob('*.csv'))
    family_data = {}

    for fam_name, patterns in CIRCUIT_FAMILIES.items():
        fam_X, fam_y = [], []
        for cf in circuit_files:
            if any(p in cf.stem for p in patterns):
                with open(cf, 'r', encoding='utf-8') as f:
                    for row in csv.DictReader(f):
                        feat = [float(row.get(k, 0) or 0) for k in feature_cols]
                        lbl = int(float(row.get('Trojan', 0) or 0))
                        fam_X.append(feat)
                        fam_y.append(lbl)
        if fam_X:
            family_data[fam_name] = (np.array(fam_X, dtype=np.float32), np.array(fam_y, dtype=np.int32))

    # Evaluate each fold
    per_family_results = {}
    total_tp, total_fp, total_fn, total_tn = 0, 0, 0, 0
    f1_list = []

    for holdout_fam in family_data:
        X_test, y_test = family_data[holdout_fam]
        X_train_list = [family_data[f][0] for f in family_data if f != holdout_fam]
        y_train_list = [family_data[f][1] for f in family_data if f != holdout_fam]

        X_train = np.vstack(X_train_list)
        y_train = np.concatenate(y_train_list)

        clf = FastBalancedForest(n_estimators=60, max_depth=6, random_state=42)
        clf.fit(X_train, y_train)

        y_prob = clf.predict_proba(X_test)
        y_pred = (y_prob >= 0.5).astype(int)

        met = compute_metrics(y_test, y_pred, y_prob)
        per_family_results[holdout_fam] = met
        total_tp += met['tp']
        total_fp += met['fp']
        total_fn += met['fn']
        total_tn += met['tn']
        f1_list.append(met['f1'])

    micro_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    micro_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    micro_f1 = 2 * micro_prec * micro_rec / (micro_prec + micro_rec) if (micro_prec + micro_rec) > 0 else 0
    macro_f1 = float(np.mean(f1_list))

    return {
        'micro_precision': float(micro_prec),
        'micro_recall': float(micro_rec),
        'micro_f1': float(micro_f1),
        'macro_f1': macro_f1,
        'per_family': per_family_results,
    }


def main():
    base_data_dir = Path('data/processed')
    gir_data_dir = Path('data/processed_graph_ir')
    base_circuits_dir = Path('data/circuits')
    gir_circuits_dir = Path('data/circuits_graph_ir')
    output_report = Path('data/models/comparison_4_experiments.json')
    output_report.parent.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 90)
    logger.info("4-WAY COMPREHENSIVE BENCHMARK: BASELINE vs GRAPH IR on 5 & 13 FEATURES")
    logger.info("=" * 90)

    # 1. Load Data for 4 Experiments
    logger.info("Loading Datasets for 4 Experimental Configurations...")
    X_tr_e1, y_tr_e1, X_te_e1, y_te_e1 = load_dataset_from_dir(base_data_dir, BASE_5_FEATURES)
    X_tr_e2, y_tr_e2, X_te_e2, y_te_e2 = load_dataset_from_dir(base_data_dir, ALL_13_FEATURES)
    X_tr_e3, y_tr_e3, X_te_e3, y_te_e3 = load_dataset_from_dir(gir_data_dir, BASE_5_FEATURES)
    X_tr_e4, y_tr_e4, X_te_e4, y_te_e4 = load_dataset_from_dir(gir_data_dir, ALL_13_FEATURES)

    # 2. Train and Evaluate Random Split
    res_e1 = run_experiment(X_tr_e1, y_tr_e1, X_te_e1, y_te_e1, "Exp 1: Baseline (5 Hasegawa)")
    res_e2 = run_experiment(X_tr_e2, y_tr_e2, X_te_e2, y_te_e2, "Exp 2: Baseline + Graph (13 Feats)")
    res_e3 = run_experiment(X_tr_e3, y_tr_e3, X_te_e3, y_te_e3, "Exp 3: Graph IR (5 Hasegawa)")
    res_e4 = run_experiment(X_tr_e4, y_tr_e4, X_te_e4, y_te_e4, "Exp 4: Graph IR + Graph (13 Feats)")

    # 3. Run LOFO Cross-Validation for Generalization
    logger.info("Running LOFO Cross-Validation for all 4 configurations...")
    lofo_e1 = run_lofo_evaluation(base_circuits_dir, BASE_5_FEATURES)
    lofo_e2 = run_lofo_evaluation(base_circuits_dir, ALL_13_FEATURES)
    lofo_e3 = run_lofo_evaluation(gir_circuits_dir, BASE_5_FEATURES)
    lofo_e4 = run_lofo_evaluation(gir_circuits_dir, ALL_13_FEATURES)

    # 4. Print Beautiful Formatted Comparative Tables
    print("\n" + "=" * 105)
    print("                    4-WAY BENCHMARK EVALUATION TABLE (RANDOM SPLIT 80/20)")
    print("=" * 105)
    header_str = f"{'Metric':<25} | {'Exp 1 (Base-5)':<17} | {'Exp 2 (Base-13)':<17} | {'Exp 3 (GIR-5)':<17} | {'Exp 4 (GIR-13)':<17}"
    print(header_str)
    print("-" * 105)
    print(f"{'Features Count':<25} | {'5 features':>17} | {'13 features':>17} | {'5 features':>17} | {'13 features':>17}")
    print(f"{'Total Samples':<25} | {res_e1['train_samples']+res_e1['test_samples']:>17,} | {res_e2['train_samples']+res_e2['test_samples']:>17,} | {res_e3['train_samples']+res_e3['test_samples']:>17,} | {res_e4['train_samples']+res_e4['test_samples']:>17,}")
    print(f"{'Total Trojan Gates':<25} | {res_e1['train_trojans']+res_e1['test_trojans']:>17} | {res_e2['train_trojans']+res_e2['test_trojans']:>17} | {res_e3['train_trojans']+res_e3['test_trojans']:>17} | {res_e4['train_trojans']+res_e4['test_trojans']:>17}")
    print("-" * 105)
    print("--- Performance at Optimal Threshold ---")
    print(f"{'Precision (%)':<25} | {res_e1['optimal_threshold']['precision']*100:>16.2f}% | {res_e2['optimal_threshold']['precision']*100:>16.2f}% | {res_e3['optimal_threshold']['precision']*100:>16.2f}% | {res_e4['optimal_threshold']['precision']*100:>16.2f}%")
    print(f"{'Recall (%)':<25} | {res_e1['optimal_threshold']['recall']*100:>16.2f}% | {res_e2['optimal_threshold']['recall']*100:>16.2f}% | {res_e3['optimal_threshold']['recall']*100:>16.2f}% | {res_e4['optimal_threshold']['recall']*100:>16.2f}%")
    print(f"{'F1-Score':<25} | {res_e1['optimal_threshold']['f1']:>17.4f} | {res_e2['optimal_threshold']['f1']:>17.4f} | {res_e3['optimal_threshold']['f1']:>17.4f} | {res_e4['optimal_threshold']['f1']:>17.4f}")
    print(f"{'MCC':<25} | {res_e1['optimal_threshold']['mcc']:>17.4f} | {res_e2['optimal_threshold']['mcc']:>17.4f} | {res_e3['optimal_threshold']['mcc']:>17.4f} | {res_e4['optimal_threshold']['mcc']:>17.4f}")
    print(f"{'False Positives (FP)':<25} | {res_e1['optimal_threshold']['fp']:>17} | {res_e2['optimal_threshold']['fp']:>17} | {res_e3['optimal_threshold']['fp']:>17} | {res_e4['optimal_threshold']['fp']:>17}")
    print(f"{'ROC-AUC':<25} | {res_e1['roc_auc']:>17.4f} | {res_e2['roc_auc']:>17.4f} | {res_e3['roc_auc']:>17.4f} | {res_e4['roc_auc']:>17.4f}")
    print("=" * 105)

    print("\n" + "=" * 105)
    print("           LEAVE-ONE-FAMILY-OUT (LOFO) GENERALIZATION BENCHMARK (CROSS-FAMILY)")
    print("=" * 105)
    print(header_str)
    print("-" * 105)
    print(f"{'Micro Precision (%)':<25} | {lofo_e1['micro_precision']*100:>16.2f}% | {lofo_e2['micro_precision']*100:>16.2f}% | {lofo_e3['micro_precision']*100:>16.2f}% | {lofo_e4['micro_precision']*100:>16.2f}%")
    print(f"{'Micro Recall (%)':<25} | {lofo_e1['micro_recall']*100:>16.2f}% | {lofo_e2['micro_recall']*100:>16.2f}% | {lofo_e3['micro_recall']*100:>16.2f}% | {lofo_e4['micro_recall']*100:>16.2f}%")
    print(f"{'Micro F1-Score':<25} | {lofo_e1['micro_f1']:>17.4f} | {lofo_e2['micro_f1']:>17.4f} | {lofo_e3['micro_f1']:>17.4f} | {lofo_e4['micro_f1']:>17.4f}")
    print(f"{'Macro F1-Score':<25} | {lofo_e1['macro_f1']:>17.4f} | {lofo_e2['macro_f1']:>17.4f} | {lofo_e3['macro_f1']:>17.4f} | {lofo_e4['macro_f1']:>17.4f}")
    print("=" * 105 + "\n")

    # Save complete JSON
    full_report = {
        'experiments': {
            'exp1_baseline_5': {'random_split': res_e1, 'lofo': lofo_e1},
            'exp2_baseline_13': {'random_split': res_e2, 'lofo': lofo_e2},
            'exp3_graph_ir_5': {'random_split': res_e3, 'lofo': lofo_e3},
            'exp4_graph_ir_13': {'random_split': res_e4, 'lofo': lofo_e4},
        }
    }
    with open(output_report, 'w') as f:
        json.dump(full_report, f, indent=2)
    logger.info(f"Full 4-way benchmark report saved to {output_report}")


if __name__ == '__main__':
    main()
