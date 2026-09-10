#!/usr/bin/env python3
"""
Comprehensive 5-Way Benchmark: Evaluates HeteroTrojanGNN (Exp 5) against Exp 1-4.

Protocol strictly follows the thesis methodology:
1. Single Seed (42): Stratified 60% Train / 20% Val / 20% Test, threshold tuned on Val.
2. 10-Run Statistical Validation across seeds [42, 101, 2024, 777, 888, 999, 1234, 5678, 9999, 31415].
3. Leave-One-Family-Out (LOFO) Cross-Validation across 5 Trust-Hub circuit families:
   - RS232 (22 circuits)
   - s15850 (1 circuit)
   - s35932 (3 circuits)
   - s38417 (2 circuits)
   - s38584 (2 circuits)
4. Saves combined 5-Experiment benchmark results to data/models/comparison_5_experiments.json.
5. Saves best model weights to data/models/hetero_gnn_best.pt.
"""

import copy
import json
import logging
import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
from torch_geometric.data import Batch

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.shared.xai_shared.graph_data.hetero_gnn import HeteroTrojanGNN
from packages.shared.xai_shared.graph_data.pyg_converter import CircuitPyGConverter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GNNBenchmark')

CIRCUIT_FAMILIES = {
    'RS232': ['RS232-T1000', 'RS232-T1100', 'RS232-T1200', 'RS232-T1300', 'RS232-T1400',
              'RS232-T1500', 'RS232-T1600', 'RS232-T1700', 'RS232-T1800', 'RS232-T1900', 'RS232-T2000'],
    's15850': ['s15850-T100'],
    's35932': ['s35932-T100', 's35932-T200', 's35932-T300'],
    's38417': ['s38417-T100', 's38417-T200'],
    's38584': ['s38584-T100', 's38584-T300'],
}

SEEDS_10_RUNS = [42, 101, 2024, 777, 888, 999, 1234, 5678, 9999, 31415]


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: Optional[np.ndarray] = None) -> Dict:
    """Compute precision, recall, f1, mcc, and confusion matrix."""
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
    if y_prob is not None and len(np.unique(y_true)) > 1:
        try:
            roc_auc = float(roc_auc_score(y_true, y_prob))
        except Exception:
            roc_auc = 0.5

    return {
        'precision': float(prec),
        'recall': float(rec),
        'f1': float(f1),
        'mcc': float(mcc),
        'tp': tp,
        'fp': fp,
        'tn': tn,
        'fn': fn,
        'roc_auc': roc_auc,
    }


def find_optimal_threshold(y_true: np.ndarray, y_prob: np.ndarray, steps: int = 100) -> Tuple[float, Dict]:
    """Find threshold tau in [0.01, 0.99] maximizing F1 score."""
    best_tau = 0.5
    best_metrics = None
    best_f1 = -1.0

    for tau in np.linspace(0.01, 0.99, steps):
        y_pred = (y_prob >= tau).astype(int)
        m = compute_metrics(y_true, y_pred, y_prob)
        if m['f1'] > best_f1:
            best_f1 = m['f1']
            best_tau = float(tau)
            best_metrics = m

    if best_metrics is None:
        best_metrics = compute_metrics(y_true, (y_prob >= 0.5).astype(int), y_prob)
    best_metrics['threshold'] = best_tau
    return best_tau, best_metrics


def train_gnn(
    batch: Batch,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    hidden_dim: int = 64,
    num_layers: int = 2,
    epochs: int = 60,
    lr: float = 0.005,
    weight_decay: float = 1e-4,
    device: str = 'cpu',
) -> Tuple[HeteroTrojanGNN, Dict]:
    """
    Trains HeteroTrojanGNN on cell nodes with train_idx, early stopping on val_idx.
    """
    y_all = batch['cell'].y.cpu().numpy()
    y_train = y_all[train_idx]
    pos_cnt = int(np.sum(y_train == 1))
    neg_cnt = int(np.sum(y_train == 0))
    pos_weight_val = neg_cnt / max(1, pos_cnt)
    pos_weight = torch.tensor([pos_weight_val], dtype=torch.float32, device=device)

    model = HeteroTrojanGNN(hidden_dim=hidden_dim, num_layers=num_layers, dropout=0.2)
    model.to(device)
    batch.to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    train_idx_t = torch.tensor(train_idx, dtype=torch.long, device=device)
    val_idx_t = torch.tensor(val_idx, dtype=torch.long, device=device)

    best_val_auc = -1.0
    best_state = None

    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(batch.x_dict, batch.edge_index_dict).view(-1)
        loss = criterion(logits[train_idx_t], batch['cell'].y[train_idx_t])
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
        optimizer.step()
        scheduler.step()

        # Validation
        model.eval()
        with torch.no_grad():
            val_logits = logits[val_idx_t]
            val_probs = torch.sigmoid(val_logits).cpu().numpy()
            y_val = y_all[val_idx]
            try:
                val_auc = roc_auc_score(y_val, val_probs)
            except Exception:
                val_auc = 0.5

            if val_auc > best_val_auc:
                best_val_auc = val_auc
                best_state = copy.deepcopy(model.state_dict())

    if best_state is not None:
        model.load_state_dict(best_state)

    # Compute validation predictions at best state
    model.eval()
    with torch.no_grad():
        all_logits = model(batch.x_dict, batch.edge_index_dict).view(-1)
        val_probs = torch.sigmoid(all_logits[val_idx_t]).cpu().numpy()
        opt_tau, val_opt_metrics = find_optimal_threshold(y_all[val_idx], val_probs)

    return model, {
        'optimal_threshold': opt_tau,
        'val_metrics': val_opt_metrics,
        'val_probs': val_probs,
    }


def load_all_circuit_graphs(converter: CircuitPyGConverter) -> List:
    """Load all 30 circuit graphs from disk."""
    circuits = sorted([d.name for d in converter.graphs_dir.glob('*') if d.is_dir()])
    logger.info(f"Loading {len(circuits)} circuits from {converter.graphs_dir}...")
    t0 = time.time()
    graphs = [converter.convert_circuit(c) for c in circuits]
    logger.info(f"Successfully loaded {len(graphs)} circuit graphs in {time.time() - t0:.2f}s")
    return graphs


def run_gnn_single_seed(
    converter: CircuitPyGConverter,
    graphs: List,
    seed: int = 42,
) -> Dict:
    """Run In-Distribution 60/20/20 benchmark for Exp 5."""
    full_batch = Batch.from_data_list(graphs)
    y_cells = full_batch['cell'].y.cpu().numpy()
    n_cells = len(y_cells)
    indices = np.arange(n_cells)

    # Stratified 60% Train, 20% Val, 20% Test
    idx_tr, idx_temp, y_tr, y_temp = train_test_split(
        indices, y_cells, test_size=0.40, random_state=seed, stratify=y_cells
    )
    idx_va, idx_te, y_va, y_te = train_test_split(
        idx_temp, y_temp, test_size=0.50, random_state=seed, stratify=y_temp
    )

    logger.info(f"[Exp 5 Single Seed {seed}] Train: {len(idx_tr)} ({int(y_tr.sum())} trojans), "
                f"Val: {len(idx_va)} ({int(y_va.sum())} trojans), Test: {len(idx_te)} ({int(y_te.sum())} trojans)")

    model, val_info = train_gnn(
        batch=full_batch,
        train_idx=idx_tr,
        val_idx=idx_va,
        hidden_dim=64,
        num_layers=2,
        epochs=60,
        lr=0.005,
    )

    # Test evaluation
    model.eval()
    with torch.no_grad():
        all_logits = model(full_batch.x_dict, full_batch.edge_index_dict).view(-1)
        test_probs = torch.sigmoid(all_logits[idx_te]).cpu().numpy()

    opt_tau = val_info['optimal_threshold']
    test_pred_def = (test_probs >= 0.5).astype(int)
    test_pred_opt = (test_probs >= opt_tau).astype(int)

    def_metrics = compute_metrics(y_te, test_pred_def, test_probs)
    def_metrics['threshold'] = 0.5

    opt_metrics = compute_metrics(y_te, test_pred_opt, test_probs)
    opt_metrics['threshold'] = opt_tau
    opt_metrics['val_f1'] = val_info['val_metrics']['f1']

    # Save model checkpoint
    ckpt_path = Path('data/models/hetero_gnn_best.pt')
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'model_state_dict': model.state_dict(),
        'optimal_threshold': opt_tau,
        'seed': seed,
    }, ckpt_path)
    logger.info(f"Saved best model checkpoint to {ckpt_path}")

    return {
        'exp_name': 'Exp 5: HeteroTrojanGNN (Semantic Graph IR)',
        'train_samples': len(idx_tr),
        'train_trojans': int(y_tr.sum()),
        'val_samples': len(idx_va),
        'val_trojans': int(y_va.sum()),
        'test_samples': len(idx_te),
        'test_trojans': int(y_te.sum()),
        'num_features': 'Graph (Hetero bipartite cell<->net)',
        'validation_at_optimal': val_info['val_metrics'],
        'default_threshold': def_metrics,
        'optimal_threshold': opt_metrics,
        'roc_auc': opt_metrics['roc_auc'],
    }


def run_gnn_10_runs(
    converter: CircuitPyGConverter,
    graphs: List,
    seeds: List[int] = SEEDS_10_RUNS,
) -> Dict:
    """Run 10 Repeated Multi-Seed runs for Exp 5."""
    full_batch = Batch.from_data_list(graphs)
    y_cells = full_batch['cell'].y.cpu().numpy()
    n_cells = len(y_cells)
    indices = np.arange(n_cells)

    f1s, precs, recs, mccs, aucs, taus = [], [], [], [], [], []

    for seed in seeds:
        idx_tr, idx_temp, y_tr, y_temp = train_test_split(
            indices, y_cells, test_size=0.40, random_state=seed, stratify=y_cells
        )
        idx_va, idx_te, y_va, y_te = train_test_split(
            idx_temp, y_temp, test_size=0.50, random_state=seed, stratify=y_temp
        )

        model, val_info = train_gnn(
            batch=full_batch,
            train_idx=idx_tr,
            val_idx=idx_va,
            hidden_dim=64,
            num_layers=2,
            epochs=50,
            lr=0.005,
        )

        model.eval()
        with torch.no_grad():
            all_logits = model(full_batch.x_dict, full_batch.edge_index_dict).view(-1)
            test_probs = torch.sigmoid(all_logits[idx_te]).cpu().numpy()

        opt_tau = val_info['optimal_threshold']
        test_pred_opt = (test_probs >= opt_tau).astype(int)
        opt_met = compute_metrics(y_te, test_pred_opt, test_probs)

        f1s.append(opt_met['f1'])
        precs.append(opt_met['precision'] * 100)
        recs.append(opt_met['recall'] * 100)
        mccs.append(opt_met['mcc'])
        aucs.append(opt_met['roc_auc'])
        taus.append(opt_tau)
        logger.info(f"  Seed {seed:5d} -> Test F1: {opt_met['f1']:.4f}, AUC: {opt_met['roc_auc']:.4f}, Tau: {opt_tau:.3f}")

    return {
        'f1_mean': float(np.mean(f1s)),
        'f1_std': float(np.std(f1s)),
        'prec_mean': float(np.mean(precs)),
        'prec_std': float(np.std(precs)),
        'rec_mean': float(np.mean(recs)),
        'rec_std': float(np.std(recs)),
        'mcc_mean': float(np.mean(mccs)),
        'mcc_std': float(np.std(mccs)),
        'auc_mean': float(np.mean(aucs)),
        'auc_std': float(np.std(aucs)),
        'thresh_mean': float(np.mean(taus)),
        'thresh_std': float(np.std(taus)),
    }


def run_gnn_lofo(
    converter: CircuitPyGConverter,
    graphs: List,
) -> Dict:
    """
    Run Leave-One-Family-Out (LOFO) Cross-Validation for Exp 5 across 5 families.
    """
    family_graphs = {fam: [] for fam in CIRCUIT_FAMILIES}
    for g in graphs:
        cname = g.circuit_name
        for fam, patterns in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in patterns):
                family_graphs[fam].append(g)
                break

    per_family_results = {}
    total_tp, total_fp, total_fn, total_tn = 0, 0, 0, 0
    f1_list = []

    for holdout_fam, test_g_list in family_graphs.items():
        train_g_list = []
        for f, glist in family_graphs.items():
            if f != holdout_fam:
                train_g_list.extend(glist)

        batch_train = Batch.from_data_list(train_g_list)
        batch_test = Batch.from_data_list(test_g_list)

        y_train_all = batch_train['cell'].y.cpu().numpy()
        n_train_cells = len(y_train_all)
        train_indices = np.arange(n_train_cells)

        # Internal 85/15 validation split on training families for early stopping & threshold tuning
        idx_tr, idx_va = train_test_split(
            train_indices, test_size=0.15, random_state=42, stratify=y_train_all
        )

        logger.info(f"[Exp 5 LOFO Holdout: {holdout_fam}] Train cells: {len(idx_tr)}, Val cells: {len(idx_va)}, Test cells: {len(batch_test['cell'].y)}")

        model, val_info = train_gnn(
            batch=batch_train,
            train_idx=idx_tr,
            val_idx=idx_va,
            hidden_dim=64,
            num_layers=2,
            epochs=50,
            lr=0.005,
        )

        model.eval()
        with torch.no_grad():
            test_logits = model(batch_test.x_dict, batch_test.edge_index_dict).view(-1)
            test_probs = torch.sigmoid(test_logits).cpu().numpy()

        y_test = batch_test['cell'].y.cpu().numpy()
        opt_tau = val_info['optimal_threshold']
        # Also evaluate default 0.5 and optimal
        met_opt = compute_metrics(y_test, (test_probs >= opt_tau).astype(int), test_probs)
        met_opt['threshold'] = opt_tau

        logger.info(f"  Holdout {holdout_fam} -> TP: {met_opt['tp']}, FP: {met_opt['fp']}, "
                    f"FN: {met_opt['fn']}, Prec: {met_opt['precision']:.4f}, Rec: {met_opt['recall']:.4f}, F1: {met_opt['f1']:.4f}, AUC: {met_opt['roc_auc']:.4f}")

        per_family_results[holdout_fam] = met_opt
        total_tp += met_opt['tp']
        total_fp += met_opt['fp']
        total_fn += met_opt['fn']
        total_tn += met_opt['tn']
        f1_list.append(met_opt['f1'])

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
    logger.info("=" * 80)
    logger.info("STARTING HETEROGENEOUS GNN BENCHMARK (EXP 5) vs BASELINE EXP 1-4")
    logger.info("=" * 80)

    converter = CircuitPyGConverter()
    graphs = load_all_circuit_graphs(converter)

    # 1. Single Seed Benchmark (Seed 42)
    logger.info("\n--- Running Exp 5: Single Seed 42 Benchmark ---")
    exp5_single = run_gnn_single_seed(converter, graphs, seed=42)

    # 2. 10-Run Statistical Validation
    logger.info("\n--- Running Exp 5: 10-Run Multi-Seed Statistical Validation ---")
    exp5_10runs = run_gnn_10_runs(converter, graphs, seeds=SEEDS_10_RUNS)

    # 3. LOFO Cross-Validation
    logger.info("\n--- Running Exp 5: Leave-One-Family-Out (LOFO) Cross-Validation ---")
    exp5_lofo = run_gnn_lofo(converter, graphs)

    # 4. Load comparison_4_experiments.json and merge Exp 5
    comp4_path = Path('data/models/comparison_4_experiments.json')
    if comp4_path.exists():
        with open(comp4_path, 'r') as f:
            comp_data = json.load(f)
    else:
        comp_data = {'single_run': {}, 'statistical_10_runs': {}, 'lofo_cross_validation': {}}

    comp_data['single_run']['exp5'] = exp5_single
    comp_data['statistical_10_runs']['Exp 5 (Hetero-GNN)'] = exp5_10runs
    comp_data['lofo_cross_validation']['exp5'] = exp5_lofo

    comp5_path = Path('data/models/comparison_5_experiments.json')
    with open(comp5_path, 'w', encoding='utf-8') as f:
        json.dump(comp_data, f, indent=2)

    logger.info(f"\nSaved combined 5-Experiment Benchmark to {comp5_path}")
    logger.info("=" * 80)
    logger.info("BENCHMARK SUMMARY (EXP 5 vs EXP 4):")
    logger.info(f"Exp 4 Single Seed F1: {comp_data['single_run']['exp4']['optimal_threshold']['f1']:.4f}")
    logger.info(f"Exp 5 Single Seed F1: {exp5_single['optimal_threshold']['f1']:.4f}")
    exp4_10runs_key = next(k for k in comp_data['statistical_10_runs'] if '4' in k and k != 'Exp 5 (Hetero-GNN)')
    logger.info(f"Exp 4 10-Runs F1: {comp_data['statistical_10_runs'][exp4_10runs_key]['f1_mean']:.4f} +/- {comp_data['statistical_10_runs'][exp4_10runs_key]['f1_std']:.4f}")
    logger.info(f"Exp 5 10-Runs F1: {exp5_10runs['f1_mean']:.4f} +/- {exp5_10runs['f1_std']:.4f}")
    logger.info(f"Exp 4 LOFO Micro F1: {comp_data['lofo_cross_validation']['exp4']['micro_f1']:.4f}, Macro F1: {comp_data['lofo_cross_validation']['exp4']['macro_f1']:.4f}")
    logger.info(f"Exp 5 LOFO Micro F1: {exp5_lofo['micro_f1']:.4f}, Macro F1: {exp5_lofo['macro_f1']:.4f}")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
