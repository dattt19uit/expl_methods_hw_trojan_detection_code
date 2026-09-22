#!/usr/bin/env python3
"""
Leave-One-Circuit-Out (LOCO) 30-Fold Cross-Validation Benchmark Runner
Evaluates Tabular (XGBoost) and GNN (HeteroTrojanGNN) models across all 30 Trust-Hub circuits.

Matches and extends Table 9 of Whitten, Wolff & Papachristou (JETTA 2026 / arXiv:2601.18696v7):
- Replicates Table 9: XGBoost on 5 Hasegawa features with fixed threshold tau = 0.940.
- Evaluates Fair Tabular: XGBoost with validation-tuned threshold tau* on 5 and 13 features.
- Evaluates GNN Models: Config A (BaselineTrojanGNN), Config D (Hetero-5 No-Control), Config F (Hetero-13 No-Control).

Outputs:
1. outputs/results/loco_benchmark_results.json
2. outputs/results/loco_per_circuit_table.csv
"""

import argparse
import copy
import csv
import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'packages' / 'shared'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('LOCOBenchmark')

# Feature definitions
BASE_5_FEATURES = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']
GRAPH_8_FEATURES = [
    'in_degree', 'out_degree', 'pagerank', 'betweenness',
    'closeness', 'clustering', 'core_number', 'logic_depth_ratio'
]
ALL_13_FEATURES = BASE_5_FEATURES + GRAPH_8_FEATURES

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

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: Optional[np.ndarray] = None) -> Dict:
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))

    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

    denom = math.sqrt(float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)))
    mcc = float((tp * tn - fp * fn) / denom) if denom > 0 else 0.0

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

    return {
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
        'precision': float(prec), 'recall': float(rec), 'f1': float(f1),
        'mcc': float(mcc), 'roc_auc': float(roc_auc), 'pr_auc': float(pr_auc)
    }

def find_optimal_threshold(y_true: np.ndarray, y_prob: np.ndarray, steps: int = 100) -> Tuple[float, Dict]:
    best_tau = 0.5
    best_f1 = -1.0
    best_metrics = {}

    for tau in np.linspace(0.01, 0.99, steps):
        preds = (y_prob >= tau).astype(int)
        m = compute_metrics(y_true, preds, y_prob)
        if m['f1'] > best_f1:
            best_f1 = m['f1']
            best_tau = float(tau)
            best_metrics = m

    return best_tau, best_metrics

def create_xgb_classifier(random_state: int = 42, scale_pos_weight: float = 1.0):
    try:
        from xgboost import XGBClassifier
        return XGBClassifier(
            scale_pos_weight=float(scale_pos_weight),
            max_depth=6,
            learning_rate=0.3,
            n_estimators=100,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            n_jobs=-1,
            eval_metric='logloss'
        )
    except Exception as e:
        logger.warning(f"XGBoost not available ({e}), falling back to Balanced Random Forest")
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(n_estimators=100, max_depth=6, random_state=random_state, class_weight='balanced')

# -------------------------------------------------------------------------
# Tabular LOCO Evaluation
# -------------------------------------------------------------------------

def load_circuit_csvs(circuits_dir: Path, feature_cols: List[str]) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """Loads feature matrix and label vector for each circuit CSV."""
    circuit_data = {}
    csv_files = sorted([f for f in circuits_dir.glob('*.csv')])
    for cf in csv_files:
        cname = cf.stem
        X, y = [], []
        with open(cf, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                feat = [float(row.get(k, 0.0) or 0.0) for k in feature_cols]
                lbl = int(float(row.get('Trojan', 0.0) or 0.0))
                X.append(feat)
                y.append(lbl)
        circuit_data[cname] = (np.array(X, dtype=np.float32), np.array(y, dtype=np.int32))
    return circuit_data

def run_tabular_loco(
    circuit_data: Dict[str, Tuple[np.ndarray, np.ndarray]],
    model_name: str,
    fixed_threshold: Optional[float] = None,
    seed: int = 42
) -> Dict[str, Dict]:
    """Runs 30-Fold Leave-One-Circuit-Out cross-validation for a tabular configuration."""
    circuit_names = sorted(list(circuit_data.keys()))
    results = {}

    for i, holdout_circuit in enumerate(circuit_names):
        X_test, y_test = circuit_data[holdout_circuit]

        # Combine remaining 29 circuits for training
        train_names = [c for c in circuit_names if c != holdout_circuit]
        X_train_full = np.vstack([circuit_data[c][0] for c in train_names])
        y_train_full = np.concatenate([circuit_data[c][1] for c in train_names])

        # Stratified validation split (15%) for threshold tuning
        n_pos = int(np.sum(y_train_full == 1))
        n_neg = int(np.sum(y_train_full == 0))
        scale_pos_weight = float(n_neg / max(1, n_pos))

        if fixed_threshold is None:
            X_tr, X_va, y_tr, y_va = train_test_split(
                X_train_full, y_train_full, test_size=0.15, random_state=seed, stratify=y_train_full
            )
            clf = create_xgb_classifier(random_state=seed, scale_pos_weight=scale_pos_weight)
            clf.fit(X_tr, y_tr)
            val_probs = clf.predict_proba(X_va)[:, 1]
            tau, _ = find_optimal_threshold(y_va, val_probs)
        else:
            # Replicate Whitten & Wolff exact setting
            tau = fixed_threshold
            clf = create_xgb_classifier(random_state=seed, scale_pos_weight=scale_pos_weight)
            clf.fit(X_train_full, y_train_full)

        test_probs = clf.predict_proba(X_test)[:, 1]
        y_pred = (test_probs >= tau).astype(int)

        m = compute_metrics(y_test, y_pred, test_probs)
        m['threshold'] = float(tau)
        m['circuit'] = holdout_circuit
        m['family'] = get_family_for_circuit(holdout_circuit)
        m['trojans'] = int(np.sum(y_test == 1))
        m['total_gates'] = len(y_test)
        results[holdout_circuit] = m

    return results

# -------------------------------------------------------------------------
# Aggregate Metrics Calculation
# -------------------------------------------------------------------------

def aggregate_loco_metrics(per_circuit_results: Dict[str, Dict]) -> Dict:
    """
    Aggregates LOCO results into RS232 family, ISCAS benchmarks, and Overall.
    Follows Whitten & Wolff Table 9 convention:
    - Degenerate folds (< 2 trojans): RS232-T1800_90nm (0 trojans) and s38584-T300 (1 trojan)
      are excluded from micro/macro aggregates when aligning with Table 9.
    """
    def _calc_group(circuits: List[str], exclude_degenerate: bool = True):
        tps, fps, fns, tns = 0, 0, 0, 0
        f1_list, prec_list, rec_list, mcc_list, pr_auc_list = [], [], [], [], []

        for c in circuits:
            r = per_circuit_results[c]
            num_trojans = r['trojans']

            is_degenerate = (num_trojans < 2)
            if exclude_degenerate and is_degenerate:
                continue

            tps += r['tp']
            fps += r['fp']
            fns += r['fn']
            tns += r['tn']

            # Only include F1 in macro if defined (trojans > 0)
            if num_trojans > 0:
                f1_list.append(r['f1'])
                prec_list.append(r['precision'])
                rec_list.append(r['recall'])
                mcc_list.append(r['mcc'])
                pr_auc_list.append(r['pr_auc'])

        micro_p = tps / (tps + fps) if (tps + fps) > 0 else 0.0
        micro_r = tps / (tps + fns) if (tps + fns) > 0 else 0.0
        micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0
        denom = math.sqrt(float((tps + fps) * (tps + fns) * (tns + fps) * (tns + fns)))
        micro_mcc = float((tps * tns - fps * fns) / denom) if denom > 0 else 0.0

        return {
            'micro_precision': float(micro_p),
            'micro_recall': float(micro_r),
            'micro_f1': float(micro_f1),
            'micro_mcc': float(micro_mcc),
            'macro_f1': float(np.mean(f1_list)) if f1_list else 0.0,
            'macro_precision': float(np.mean(prec_list)) if prec_list else 0.0,
            'macro_recall': float(np.mean(rec_list)) if rec_list else 0.0,
            'macro_mcc': float(np.mean(mcc_list)) if mcc_list else 0.0,
            'macro_pr_auc': float(np.mean(pr_auc_list)) if pr_auc_list else 0.0,
            'tp': tps, 'fp': fps, 'fn': fns, 'tn': tns,
            'valid_circuits_count': len(f1_list)
        }

    rs232_circuits = [c for c, r in per_circuit_results.items() if r['family'] == 'RS232']
    iscas_circuits = [c for c, r in per_circuit_results.items() if r['family'] != 'RS232']
    all_circuits = list(per_circuit_results.keys())

    return {
        'RS232': _calc_group(rs232_circuits, exclude_degenerate=True),
        'ISCAS': _calc_group(iscas_circuits, exclude_degenerate=True),
        'Overall_Strict': _calc_group(all_circuits, exclude_degenerate=True),
        'Overall_All30': _calc_group(all_circuits, exclude_degenerate=False),
    }

# -------------------------------------------------------------------------
# GNN LOCO Evaluation
# -------------------------------------------------------------------------

def run_gnn_loco(
    configs: List[str],
    device_str: str = 'cpu',
    seed: int = 42,
    epochs: int = 50
) -> Dict[str, Dict]:
    """Runs 30-Fold Leave-One-Circuit-Out for selected GNN configurations."""
    import torch
    from torch_geometric.data import Batch
    from xai_shared.graph_data.baseline_gnn import BaselineTrojanGNN
    from xai_shared.graph_data.baseline_pyg_converter import BaselinePyGConverter
    from xai_shared.graph_data.hetero_gnn import HeteroTrojanGNN
    from xai_shared.graph_data.pyg_converter import CircuitPyGConverter

    device = torch.device(device_str)
    if device.type == 'cpu':
        torch.set_num_threads(min(4, os.cpu_count() or 2))
    torch.manual_seed(seed)
    np.random.seed(seed)

    edge_types_all = [
        ('net', 'data_input', 'cell'),
        ('net', 'control_input', 'cell'),
        ('cell', 'outputs', 'net'),
        ('cell', 'rev_data_input', 'net'),
        ('cell', 'rev_control_input', 'net'),
        ('net', 'rev_outputs', 'cell'),
    ]

    edge_types_no_ctrl = [
        ('net', 'data_input', 'cell'),
        ('cell', 'outputs', 'net'),
        ('cell', 'rev_data_input', 'net'),
        ('net', 'rev_outputs', 'cell'),
    ]

    gnn_results = {}

    # Preload required graph data
    graphs_cache = {}
    if 'A' in configs:
        logger.info("Loading baseline compressed graphs (Config A)...")
        b_conv = BaselinePyGConverter()
        b_graphs = b_conv.convert_all()
        graphs_cache['A'] = {g.circuit_name: g for g in b_graphs}

    if any(cfg in configs for cfg in ['C', 'D']):
        logger.info("Loading Hetero graphs with 5 Basic Features (Config C/D)...")
        h_conv_5 = CircuitPyGConverter(feature_cols=BASE_5_FEATURES)
        circuits = sorted([d.name for d in h_conv_5.graphs_dir.glob('*') if d.is_dir()])
        graphs_cache['basic_5'] = {c: h_conv_5.convert_circuit(c) for c in circuits}

    if any(cfg in configs for cfg in ['E', 'F']):
        logger.info("Loading Hetero graphs with 13 Full Features (Config E/F)...")
        h_conv_13 = CircuitPyGConverter()
        circuits = sorted([d.name for d in h_conv_13.graphs_dir.glob('*') if d.is_dir()])
        graphs_cache['full_13'] = {c: h_conv_13.convert_circuit(c) for c in circuits}

    for cfg in configs:
        logger.info(f"\n=================== Running GNN LOCO for Config {cfg} ===================")
        cfg_results = {}

        if cfg == 'A':
            g_dict = graphs_cache['A']
        elif cfg in ['C', 'D']:
            g_dict = graphs_cache['basic_5']
        else:
            g_dict = graphs_cache['full_13']

        circuit_names = sorted(list(g_dict.keys()))

        for i, holdout_circuit in enumerate(circuit_names):
            t0 = time.time()
            test_graph = g_dict[holdout_circuit]
            train_graphs = [g_dict[c] for c in circuit_names if c != holdout_circuit]

            if cfg == 'A':
                b_tr = Batch.from_data_list(train_graphs)
                y_tr_all = b_tr.y.cpu().numpy()
                idx_tr, idx_va = train_test_split(np.arange(len(y_tr_all)), test_size=0.15, random_state=seed, stratify=y_tr_all)

                model = BaselineTrojanGNN(in_channels=13, hidden_channels=64, num_layers=2, dropout=0.2).to(device)
                y_tr = b_tr.y[idx_tr].to(device)
                n_pos = int(y_tr.sum().item())
                n_neg = len(idx_tr) - n_pos
                pos_weight = torch.tensor([max(1.0, float(n_neg / max(1, n_pos)))], device=device)
                criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
                optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)

                x_dev = b_tr.x.to(device)
                edge_dev = b_tr.edge_index.to(device)
                best_val_f1, best_tau, best_state = -1.0, 0.5, None

                for epoch in range(epochs):
                    model.train()
                    optimizer.zero_grad()
                    logits = model(x_dev, edge_dev).view(-1)
                    loss = criterion(logits[idx_tr], y_tr)
                    loss.backward()
                    optimizer.step()

                    if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
                        model.eval()
                        with torch.no_grad():
                            val_probs = torch.sigmoid(model(x_dev, edge_dev).view(-1)[idx_va]).cpu().numpy()
                        tau, val_m = find_optimal_threshold(y_tr_all[idx_va], val_probs)
                        if val_m['f1'] > best_val_f1:
                            best_val_f1 = val_m['f1']
                            best_state = copy.deepcopy(model.state_dict())
                            best_tau = tau

                if best_state is not None:
                    model.load_state_dict(best_state)

                model.eval()
                with torch.no_grad():
                    test_logits = model(test_graph.x.to(device), test_graph.edge_index.to(device)).view(-1)
                    test_probs = torch.sigmoid(test_logits).cpu().numpy()
                y_test = test_graph.y.cpu().numpy()

            else:
                # Hetero GNN
                edge_types = edge_types_no_ctrl if cfg in ['D', 'F'] else edge_types_all
                b_tr = Batch.from_data_list(train_graphs).to(device)
                y_tr_all = b_tr['cell'].y.cpu().numpy()
                idx_tr, idx_va = train_test_split(np.arange(len(y_tr_all)), test_size=0.15, random_state=seed, stratify=y_tr_all)

                model = HeteroTrojanGNN(hidden_dim=64, num_layers=2, dropout=0.2, edge_types=edge_types).to(device)
                y_tr = b_tr['cell'].y[idx_tr]
                n_pos = int(y_tr.sum().item())
                n_neg = len(idx_tr) - n_pos
                pos_weight = torch.tensor([max(1.0, float(n_neg / max(1, n_pos)))], device=device)
                criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
                optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)

                filtered_edge_dict = {et: b_tr.edge_index_dict[et] for et in edge_types if et in b_tr.edge_index_dict}
                best_val_f1, best_tau, best_state = -1.0, 0.5, None

                for epoch in range(epochs):
                    model.train()
                    optimizer.zero_grad()
                    logits = model(b_tr.x_dict, filtered_edge_dict).view(-1)
                    loss = criterion(logits[idx_tr], y_tr)
                    loss.backward()
                    optimizer.step()

                    if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
                        model.eval()
                        with torch.no_grad():
                            val_probs = torch.sigmoid(model(b_tr.x_dict, filtered_edge_dict).view(-1)[idx_va]).cpu().numpy()
                        tau, val_m = find_optimal_threshold(y_tr_all[idx_va], val_probs)
                        if val_m['f1'] > best_val_f1:
                            best_val_f1 = val_m['f1']
                            best_state = copy.deepcopy(model.state_dict())
                            best_tau = tau

                if best_state is not None:
                    model.load_state_dict(best_state)

                model.eval()
                test_dev = test_graph.to(device)
                test_edge_dict = {et: test_dev.edge_index_dict[et] for et in edge_types if et in test_dev.edge_index_dict}
                with torch.no_grad():
                    test_logits = model(test_dev.x_dict, test_edge_dict).view(-1)
                    test_probs = torch.sigmoid(test_logits).cpu().numpy()
                y_test = test_dev['cell'].y.cpu().numpy()

            y_pred = (test_probs >= best_tau).astype(int)
            m = compute_metrics(y_test, y_pred, test_probs)
            m['threshold'] = float(best_tau)
            m['circuit'] = holdout_circuit
            m['family'] = get_family_for_circuit(holdout_circuit)
            m['trojans'] = int(np.sum(y_test == 1))
            m['total_cells'] = len(y_test)
            m['time_s'] = round(time.time() - t0, 2)
            cfg_results[holdout_circuit] = m

            logger.info(f"  [{cfg} Fold {i+1:02d}/30] {holdout_circuit:<26} -> F1: {m['f1']:.4f}, Prec: {m['precision']*100:5.1f}%, Rec: {m['recall']*100:5.1f}%, PR-AUC: {m['pr_auc']:.4f} ({m['time_s']}s)")

        gnn_results[f"GNN_Config_{cfg}"] = cfg_results

    return gnn_results

# -------------------------------------------------------------------------
# Main Execution Flow
# -------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Leave-One-Circuit-Out (LOCO) 30-Fold Benchmark")
    parser.add_argument('--mode', choices=['tabular', 'gnn', 'all'], default='tabular', help="Evaluation mode")
    parser.add_argument('--gnn_configs', nargs='+', default=['A', 'D', 'F'], help="GNN configurations to run")
    parser.add_argument('--seed', type=int, default=42, help="Random seed")
    parser.add_argument('--epochs', type=int, default=50, help="GNN epochs")
    parser.add_argument('--dry_run', action='store_true', help="Check data files and exit")
    parser.add_argument('--output_dir', type=str, default='outputs/results', help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base_circuits_dir = REPO_ROOT / 'data' / 'circuits'
    base13_circuits_dir = REPO_ROOT / 'data' / 'circuits_baseline_13'
    gir_circuits_dir = REPO_ROOT / 'data' / 'circuits_graph_ir'

    logger.info("=" * 90)
    logger.info("LEAVE-ONE-CIRCUIT-OUT (LOCO) 30-FOLD CROSS-VALIDATION BENCHMARK")
    logger.info(f"Mode: {args.mode}, Seed: {args.seed}, Output Dir: {out_dir}")
    logger.info("=" * 90)

    # 1. Load data
    logger.info("Loading tabular datasets for 30 circuits...")
    data_base5 = load_circuit_csvs(base_circuits_dir, BASE_5_FEATURES)
    data_base13 = load_circuit_csvs(base13_circuits_dir, ALL_13_FEATURES)
    data_gir5 = load_circuit_csvs(gir_circuits_dir, BASE_5_FEATURES)
    data_gir13 = load_circuit_csvs(gir_circuits_dir, ALL_13_FEATURES)

    logger.info(f"Found {len(data_base5)} circuits in data/circuits")
    if args.dry_run:
        logger.info("Dry run successful! Exiting.")
        return

    json_path = out_dir / 'loco_benchmark_results.json'
    all_benchmark_results = {}
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                all_benchmark_results = json.load(f)
            logger.info(f"Loaded {len(all_benchmark_results)} existing models from: {json_path}")
        except Exception as e:
            logger.warning(f"Could not load existing {json_path}: {e}")
    csv_rows = []

    # 2. Tabular Experiments
    if args.mode in ['tabular', 'all']:
        logger.info("\n>>> [1/5] Running Model: XGBoost_Base5_Fixed (Whitten & Wolff Table 9 Replicate, tau=0.940)...")
        t0 = time.time()
        res_b5_fixed = run_tabular_loco(data_base5, "XGBoost_Base5_Fixed", fixed_threshold=0.940, seed=args.seed)
        logger.info(f"Completed in {time.time() - t0:.2f}s")
        all_benchmark_results['XGBoost_Base5_Fixed_tau0.940'] = {
            'detailed': res_b5_fixed,
            'aggregates': aggregate_loco_metrics(res_b5_fixed)
        }

        logger.info("\n>>> [2/5] Running Model: XGBoost_Base5_Tuned (Fair Val-Tuned Threshold)...")
        t0 = time.time()
        res_b5_tuned = run_tabular_loco(data_base5, "XGBoost_Base5_Tuned", fixed_threshold=None, seed=args.seed)
        logger.info(f"Completed in {time.time() - t0:.2f}s")
        all_benchmark_results['XGBoost_Base5_ValTuned'] = {
            'detailed': res_b5_tuned,
            'aggregates': aggregate_loco_metrics(res_b5_tuned)
        }

        logger.info("\n>>> [3/5] Running Model: XGBoost_Base13_Tuned (13 Baseline Features)...")
        t0 = time.time()
        res_b13_tuned = run_tabular_loco(data_base13, "XGBoost_Base13_Tuned", fixed_threshold=None, seed=args.seed)
        logger.info(f"Completed in {time.time() - t0:.2f}s")
        all_benchmark_results['XGBoost_Base13_ValTuned'] = {
            'detailed': res_b13_tuned,
            'aggregates': aggregate_loco_metrics(res_b13_tuned)
        }

        logger.info("\n>>> [4/5] Running Model: XGBoost_GIR5_Tuned (Graph IR 5 Features)...")
        t0 = time.time()
        res_gir5_tuned = run_tabular_loco(data_gir5, "XGBoost_GIR5_Tuned", fixed_threshold=None, seed=args.seed)
        logger.info(f"Completed in {time.time() - t0:.2f}s")
        all_benchmark_results['XGBoost_GIR5_ValTuned'] = {
            'detailed': res_gir5_tuned,
            'aggregates': aggregate_loco_metrics(res_gir5_tuned)
        }

        logger.info("\n>>> [5/5] Running Model: XGBoost_GIR13_Tuned (Graph IR 13 Features)...")
        t0 = time.time()
        res_gir13_tuned = run_tabular_loco(data_gir13, "XGBoost_GIR13_Tuned", fixed_threshold=None, seed=args.seed)
        logger.info(f"Completed in {time.time() - t0:.2f}s")
        all_benchmark_results['XGBoost_GIR13_ValTuned'] = {
            'detailed': res_gir13_tuned,
            'aggregates': aggregate_loco_metrics(res_gir13_tuned)
        }

    # 3. GNN Experiments
    if args.mode in ['gnn', 'all']:
        logger.info(f"\n>>> Running GNN LOCO for configs: {args.gnn_configs}...")
        gnn_res = run_gnn_loco(args.gnn_configs, seed=args.seed, epochs=args.epochs)
        for mname, detailed_dict in gnn_res.items():
            all_benchmark_results[mname] = {
                'detailed': detailed_dict,
                'aggregates': aggregate_loco_metrics(detailed_dict)
            }

    # 4. Save JSON Report
    json_path = out_dir / 'loco_benchmark_results.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_benchmark_results, f, indent=2)
    logger.info(f"\nSuccessfully exported full results to: {json_path}")

    # 5. Build and Save CSV Table
    for model_key, model_data in all_benchmark_results.items():
        for circuit_name, r in model_data['detailed'].items():
            csv_rows.append({
                'circuit': circuit_name,
                'family': r['family'],
                'trojans': r['trojans'],
                'model': model_key,
                'threshold': r['threshold'],
                'tp': r['tp'],
                'fp': r['fp'],
                'fn': r['fn'],
                'tn': r['tn'],
                'precision': r['precision'],
                'recall': r['recall'],
                'f1': r['f1'],
                'mcc': r['mcc'],
                'pr_auc': r['pr_auc'],
                'roc_auc': r['roc_auc']
            })

    csv_path = out_dir / 'loco_per_circuit_table.csv'
    pd.DataFrame(csv_rows).to_csv(csv_path, index=False)
    logger.info(f"Successfully exported per-circuit table to: {csv_path}")

    # 6. Print Summary Comparison Table
    print("\n" + "=" * 115)
    print("               LEAVE-ONE-CIRCUIT-OUT (LOCO) 30-FOLD BENCHMARK SUMMARY TABLE")
    print("=" * 115)
    header = f"{'Model Configuration':<35} | {'RS232 Micro F1':<15} | {'RS232 Macro F1':<15} | {'ISCAS Micro F1':<15} | {'ISCAS Macro F1':<15} | {'Overall Micro F1':<15}"
    print(header)
    print("-" * 115)

    for mkey, mdata in all_benchmark_results.items():
        aggs = mdata['aggregates']
        r_micro = aggs['RS232']['micro_f1']
        r_macro = aggs['RS232']['macro_f1']
        i_micro = aggs['ISCAS']['micro_f1']
        i_macro = aggs['ISCAS']['macro_f1']
        o_micro = aggs['Overall_Strict']['micro_f1']
        print(f"{mkey:<35} | {r_micro:<15.4f} | {r_macro:<15.4f} | {i_micro:<15.4f} | {i_macro:<15.4f} | {o_micro:<15.4f}")
    print("=" * 115)

if __name__ == '__main__':
    main()

