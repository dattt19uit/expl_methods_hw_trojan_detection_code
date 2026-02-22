#!/usr/bin/env python3
"""
Same Circuit Family (SCF) Cross-Validation for XGBoost Trojan Detection.

Implements leave-one-family-out cross-validation following SALTY's evaluation
methodology: when testing a circuit family, no circuits from that family appear
in training data.

Families: RS232, s15850, s35932, s38417, s38584

Usage:
    python scripts/scf_cross_validation.py \
        --circuits-dir data/circuits \
        --config configs/circuit_configs.json \
        --output data/experiments/scf_analysis
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    matthews_corrcoef,
    precision_recall_fscore_support,
)
from sklearn.utils import shuffle


FEATURE_COLS = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']
LABEL_COL = 'Trojan'
NUMERIC_START = 4  # Column index where numeric features begin in circuit CSVs
RANDOM_SEED = 42


def load_circuit_csv(filepath):
    """Load a circuit CSV and return numeric features + labels as lists."""
    rows = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            try:
                numeric = [int(v) for v in row[NUMERIC_START:]]
                rows.append(numeric)
            except (ValueError, IndexError):
                continue
    return rows


def fix_sentinels(rows):
    """Replace 99999 sentinel values with next_max + 1 per column."""
    if not rows:
        return rows

    num_cols = len(rows[0])
    columns = list(zip(*rows))

    for col_idx in range(num_cols):
        col_data = list(columns[col_idx])
        if 99999 in col_data:
            next_max = max(v for v in col_data if v < 99999) if any(v < 99999 for v in col_data) else 0
            replacement = next_max + 1
            columns[col_idx] = tuple(replacement if v == 99999 else v for v in col_data)

    return [list(row) for row in zip(*columns)]


def group_configs_by_family(config_path):
    """Read circuit_configs.json, return {family: [(key, cfg), ...]}."""
    with open(config_path) as f:
        configs = json.load(f)

    families = defaultdict(list)
    for key, cfg in configs.items():
        family = cfg.get('part', key.split('-')[0])
        families[family].append((key, cfg))

    return dict(families)


def config_to_csv_filename(cfg):
    """Build CSV filename from config fields: {part}-{impl}_{tech}.csv."""
    return f"{cfg['part']}-{cfg['impl']}_{cfg['tech']}.csv"


def load_family_data(circuits_dir, config_entries):
    """Load and concatenate CSVs for a list of (key, cfg) tuples."""
    all_rows = []
    loaded = []
    for key, cfg in config_entries:
        filename = config_to_csv_filename(cfg)
        filepath = Path(circuits_dir) / filename
        if filepath.exists():
            rows = load_circuit_csv(filepath)
            all_rows.extend(rows)
            loaded.append((key, len(rows)))
        else:
            print(f"  WARNING: Missing {filepath}")
    return all_rows, loaded


def train_and_evaluate(train_rows, test_rows):
    """Train XGBoost on train_rows, evaluate on test_rows. Return metrics dict."""
    train_arr = np.array(train_rows, dtype=float)
    test_arr = np.array(test_rows, dtype=float)

    X_train, y_train = train_arr[:, :-1], train_arr[:, -1].astype(int)
    X_test, y_test = test_arr[:, :-1], test_arr[:, -1].astype(int)

    # Class imbalance handling (same as Method 2)
    n_neg = np.sum(y_train == 0)
    n_pos = max(np.sum(y_train == 1), 1)
    scale_pos_weight = n_neg / n_pos

    model = xgb.XGBClassifier(
        objective='binary:logistic',
        eval_metric='logloss',
        scale_pos_weight=scale_pos_weight,
        max_depth=6,
        learning_rate=0.3,
        n_estimators=100,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    model.fit(X_train, y_train, verbose=False)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average='binary', zero_division=0
    )
    acc = accuracy_score(y_test, y_pred)
    mcc = matthews_corrcoef(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])

    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    tpr = tp / max(tp + fn, 1)
    tnr = tn / max(tn + fp, 1)

    return {
        'accuracy': float(acc),
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'tpr': float(tpr),
        'tnr': float(tnr),
        'mcc': float(mcc),
        'scale_pos_weight': float(scale_pos_weight),
        'confusion_matrix': {'tp': int(tp), 'fp': int(fp), 'fn': int(fn), 'tn': int(tn)},
        'train_samples': len(train_rows),
        'test_samples': len(test_rows),
        'train_trojans': int(np.sum(y_train == 1)),
        'test_trojans': int(np.sum(y_test == 1)),
    }


def run_scf_cv(circuits_dir, config_path, output_dir):
    """Run leave-one-family-out cross-validation."""
    families = group_configs_by_family(config_path)
    family_names = sorted(families.keys())

    print("=" * 70)
    print("Same Circuit Family (SCF) Cross-Validation")
    print("=" * 70)
    print(f"\nFamilies: {', '.join(family_names)}")
    print(f"Total configs: {sum(len(v) for v in families.values())}")
    print()

    # Load all data by family
    family_data = {}
    for family in family_names:
        rows, loaded = load_family_data(circuits_dir, families[family])
        rows = fix_sentinels(rows)
        family_data[family] = rows
        n_trojans = sum(1 for r in rows if r[-1] == 1)
        print(f"  {family}: {len(rows):,} samples ({n_trojans} trojans) from {len(loaded)} circuits")
        for key, n in loaded:
            print(f"    - {key}: {n:,} rows")

    print()

    # Run leave-one-family-out CV
    results = {}
    all_tp, all_fp, all_fn, all_tn = 0, 0, 0, 0

    for held_out in family_names:
        print("-" * 70)
        print(f"FOLD: Hold out {held_out}")
        print("-" * 70)

        # Build train set from all other families
        train_rows = []
        for family in family_names:
            if family != held_out:
                train_rows.extend(family_data[family])

        test_rows = family_data[held_out]

        if not test_rows:
            print(f"  SKIP: No test data for {held_out}")
            continue

        if not train_rows:
            print(f"  SKIP: No training data (all other families empty)")
            continue

        # Shuffle training data
        train_rows = [list(r) for r in shuffle(train_rows, random_state=RANDOM_SEED)]

        n_train_trojans = sum(1 for r in train_rows if r[-1] == 1)
        n_test_trojans = sum(1 for r in test_rows if r[-1] == 1)

        print(f"  Train: {len(train_rows):,} samples ({n_train_trojans} trojans)")
        print(f"  Test:  {len(test_rows):,} samples ({n_test_trojans} trojans)")

        metrics = train_and_evaluate(train_rows, test_rows)
        results[held_out] = metrics
        cm = metrics['confusion_matrix']
        all_tp += cm['tp']
        all_fp += cm['fp']
        all_fn += cm['fn']
        all_tn += cm['tn']

        print(f"  Results: P={metrics['precision']:.4f}  R={metrics['recall']:.4f}  "
              f"F1={metrics['f1']:.4f}  TPR={metrics['tpr']:.4f}  TNR={metrics['tnr']:.4f}")
        print(f"  Confusion: TP={cm['tp']}  FP={cm['fp']}  FN={cm['fn']}  TN={cm['tn']}")
        print()

    # Compute aggregate metrics
    print("=" * 70)
    print("AGGREGATE RESULTS")
    print("=" * 70)

    # Micro-averaged (from total confusion matrix)
    micro_tpr = all_tp / max(all_tp + all_fn, 1)
    micro_tnr = all_tn / max(all_tn + all_fp, 1)
    micro_precision = all_tp / max(all_tp + all_fp, 1)
    micro_recall = micro_tpr
    micro_f1 = 2 * micro_precision * micro_recall / max(micro_precision + micro_recall, 1e-10)

    # Macro-averaged (mean of per-fold metrics)
    folds_with_results = [r for r in results.values() if r['test_trojans'] > 0]
    if folds_with_results:
        macro_precision = np.mean([r['precision'] for r in folds_with_results])
        macro_recall = np.mean([r['recall'] for r in folds_with_results])
        macro_f1 = np.mean([r['f1'] for r in folds_with_results])
        macro_tpr = np.mean([r['tpr'] for r in folds_with_results])
        macro_tnr = np.mean([r['tnr'] for r in folds_with_results])
    else:
        macro_precision = macro_recall = macro_f1 = macro_tpr = macro_tnr = 0.0

    aggregate = {
        'micro': {
            'precision': float(micro_precision),
            'recall': float(micro_recall),
            'f1': float(micro_f1),
            'tpr': float(micro_tpr),
            'tnr': float(micro_tnr),
            'confusion_matrix': {'tp': all_tp, 'fp': all_fp, 'fn': all_fn, 'tn': all_tn},
        },
        'macro': {
            'precision': float(macro_precision),
            'recall': float(macro_recall),
            'f1': float(macro_f1),
            'tpr': float(macro_tpr),
            'tnr': float(macro_tnr),
        },
    }

    print(f"\nMicro-averaged (pooled confusion matrix):")
    print(f"  Precision: {micro_precision:.4f}")
    print(f"  Recall:    {micro_recall:.4f}")
    print(f"  F1:        {micro_f1:.4f}")
    print(f"  TPR:       {micro_tpr:.4f}")
    print(f"  TNR:       {micro_tnr:.4f}")
    print(f"  TP={all_tp}  FP={all_fp}  FN={all_fn}  TN={all_tn}")

    print(f"\nMacro-averaged (mean of per-fold, {len(folds_with_results)} folds with trojans):")
    print(f"  Precision: {macro_precision:.4f}")
    print(f"  Recall:    {macro_recall:.4f}")
    print(f"  F1:        {macro_f1:.4f}")
    print(f"  TPR:       {macro_tpr:.4f}")
    print(f"  TNR:       {macro_tnr:.4f}")

    # Per-fold summary table
    print(f"\nPer-Fold Summary:")
    print(f"{'Family':<12} {'Samples':>8} {'Trojans':>8} {'Prec':>8} {'Recall':>8} {'F1':>8} {'TPR':>8} {'TNR':>8}")
    print("-" * 76)
    for family in family_names:
        if family in results:
            r = results[family]
            print(f"{family:<12} {r['test_samples']:>8,} {r['test_trojans']:>8} "
                  f"{r['precision']:>8.4f} {r['recall']:>8.4f} {r['f1']:>8.4f} "
                  f"{r['tpr']:>8.4f} {r['tnr']:>8.4f}")

    # SALTY comparison
    print(f"\nSALTY Comparison (from paper):")
    print(f"  SALTY:  TPR=0.9847  TNR=0.9814")
    print(f"  Ours:   TPR={micro_tpr:.4f}  TNR={micro_tnr:.4f} (micro)")
    print(f"  Ours:   TPR={macro_tpr:.4f}  TNR={macro_tnr:.4f} (macro)")

    # Save results
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output = {
            'timestamp': datetime.now().isoformat(),
            'method': 'Same Circuit Family (SCF) Cross-Validation',
            'model': 'XGBoost (max_depth=6, n_estimators=100, scale_pos_weight=auto)',
            'features': FEATURE_COLS,
            'families': {f: [k for k, _ in families[f]] for f in family_names},
            'per_fold': results,
            'aggregate': aggregate,
            'salty_comparison': {
                'salty_tpr': 0.9847,
                'salty_tnr': 0.9814,
                'our_micro_tpr': float(micro_tpr),
                'our_micro_tnr': float(micro_tnr),
            },
        }

        output_path = Path(output_dir) / 'scf_results.json'
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"\nResults saved to {output_path}")

        # Also write a summary text file
        summary_path = Path(output_dir) / 'scf_summary.txt'
        with open(summary_path, 'w') as f:
            f.write("Same Circuit Family (SCF) Cross-Validation Results\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Model: XGBoost (5 features: {', '.join(FEATURE_COLS)})\n\n")
            f.write(f"{'Family':<12} {'Samples':>8} {'Trojans':>8} {'Prec':>8} {'Recall':>8} "
                    f"{'F1':>8} {'TPR':>8} {'TNR':>8}\n")
            f.write("-" * 76 + "\n")
            for family in family_names:
                if family in results:
                    r = results[family]
                    f.write(f"{family:<12} {r['test_samples']:>8,} {r['test_trojans']:>8} "
                            f"{r['precision']:>8.4f} {r['recall']:>8.4f} {r['f1']:>8.4f} "
                            f"{r['tpr']:>8.4f} {r['tnr']:>8.4f}\n")
            f.write("-" * 76 + "\n")
            f.write(f"\nMicro:  P={micro_precision:.4f}  R={micro_recall:.4f}  "
                    f"F1={micro_f1:.4f}  TPR={micro_tpr:.4f}  TNR={micro_tnr:.4f}\n")
            f.write(f"Macro:  P={macro_precision:.4f}  R={macro_recall:.4f}  "
                    f"F1={macro_f1:.4f}  TPR={macro_tpr:.4f}  TNR={macro_tnr:.4f}\n")
            f.write(f"\nSALTY: TPR=0.9847  TNR=0.9814\n")
        print(f"Summary saved to {summary_path}")

    return results, aggregate


def main():
    parser = argparse.ArgumentParser(
        description='Same Circuit Family (SCF) Cross-Validation for XGBoost')
    parser.add_argument('--circuits-dir', default='data/circuits',
                        help='Directory containing per-circuit CSVs')
    parser.add_argument('--config', default='configs/circuit_configs.json',
                        help='Circuit configs JSON')
    parser.add_argument('--output', default='data/experiments/scf_analysis',
                        help='Output directory for results')
    args = parser.parse_args()

    run_scf_cv(args.circuits_dir, args.config, args.output)


if __name__ == '__main__':
    main()
