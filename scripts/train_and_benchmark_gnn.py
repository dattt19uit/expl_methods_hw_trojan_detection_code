#!/usr/bin/env python3
"""
Comprehensive 6-Way Benchmark:
Evaluates BaselineTrojanGNN (Exp 5) and HeteroTrojanGNN (Exp 6) against Exp 1-4.

Factorial 2x3 Evaluation:
- Exp 1: Baseline Graph (5 Hasegawa, XGBoost)
- Exp 2: Baseline Graph (13 Features, XGBoost)
- Exp 3: Semantic Graph IR (5 Hasegawa, XGBoost)
- Exp 4: Semantic Graph IR (13 Features, XGBoost)
- Exp 5: Baseline Graph (Author's Graph, Homogeneous BaselineTrojanGNN)
- Exp 6: Semantic Graph IR (Proposed Graph IR, HeteroTrojanGNN)

Protocols:
1. Single Seed (42): Stratified 60% Train / 20% Val / 20% Test, threshold tuned on Val.
2. 10-Run Statistical Validation across seeds [42, 101, 2024, 777, 888, 999, 1234, 5678, 9999, 31415].
3. Leave-One-Family-Out (LOFO) Cross-Validation across 5 Trust-Hub circuit families:
   - RS232 (22 circuits)
   - s15850 (1 circuit)
   - s35932 (3 circuits)
   - s38417 (2 circuits)
   - s38584 (2 circuits)
4. Saves combined 6-Experiment benchmark results to data/models/comparison_6_experiments.json.
5. Saves best model weights to data/models/baseline_gnn_best.pt and data/models/hetero_gnn_best.pt.
"""

import copy
import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
from torch_geometric.data import Batch

# Add project root and packages/shared to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'packages' / 'shared'))

from xai_shared.graph_data.baseline_gnn import BaselineTrojanGNN
from xai_shared.graph_data.baseline_pyg_converter import BaselinePyGConverter
from xai_shared.graph_data.hetero_gnn import HeteroTrojanGNN
from xai_shared.graph_data.pyg_converter import CircuitPyGConverter

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


def get_device() -> torch.device:
    """Auto-detect GPU (CUDA) or CPU with thread optimization."""
    if torch.cuda.is_available():
        dev = torch.device('cuda')
        logger.info(f"Using compute device: CUDA GPU ({torch.cuda.get_device_name(0)})")
    else:
        dev = torch.device('cpu')
        num_threads = min(8, os.cpu_count() or 4)
        torch.set_num_threads(num_threads)
        logger.info(f"Using compute device: CPU ({num_threads} threads)")
    return dev


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


# =========================================================================
# Training Routine for Exp 5: BaselineTrojanGNN (Author's Graph)
# =========================================================================

def train_baseline_gnn(
    batch: Batch,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    hidden_dim: int = 64,
    num_layers: int = 2,
    epochs: int = 60,
    lr: float = 0.005,
    weight_decay: float = 1e-4,
    device: torch.device = torch.device('cpu'),
) -> Tuple[BaselineTrojanGNN, Dict]:
    """
    Trains BaselineTrojanGNN on baseline c.graph nodes.
    Symmetric to train_hetero_gnn in hyperparameters and optimizer schedule.
    """
    y_all = batch.y.cpu().numpy()
    y_train = y_all[train_idx]
    pos_cnt = int(np.sum(y_train == 1))
    neg_cnt = int(np.sum(y_train == 0))
    pos_weight_val = neg_cnt / max(1, pos_cnt)
    pos_weight = torch.tensor([pos_weight_val], dtype=torch.float32, device=device)

    in_channels = batch.x.shape[1]
    model = BaselineTrojanGNN(in_channels=in_channels, hidden_dim=hidden_dim, num_layers=num_layers, dropout=0.2)
    model.to(device)
    batch = batch.to(device)

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
        logits = model(batch.x, batch.edge_index).view(-1)
        loss = criterion(logits[train_idx_t], batch.y[train_idx_t])
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
        optimizer.step()
        scheduler.step()

        # Validation early stopping on AUC
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
        all_logits = model(batch.x, batch.edge_index).view(-1)
        val_probs = torch.sigmoid(all_logits[val_idx_t]).cpu().numpy()
        opt_tau, val_opt_metrics = find_optimal_threshold(y_all[val_idx], val_probs)

    return model, {
        'optimal_threshold': opt_tau,
        'val_metrics': val_opt_metrics,
        'val_probs': val_probs,
    }


# =========================================================================
# Training Routine for Exp 6: HeteroTrojanGNN (Graph IR)
# =========================================================================

def train_hetero_gnn(
    batch: Batch,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    hidden_dim: int = 64,
    num_layers: int = 2,
    epochs: int = 60,
    lr: float = 0.005,
    weight_decay: float = 1e-4,
    device: torch.device = torch.device('cpu'),
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
    batch = batch.to(device)

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


# =========================================================================
# Single Seed Benchmark
# =========================================================================

def run_single_seed_benchmark(
    baseline_graphs: List,
    hetero_graphs: List,
    seed: int = 42,
    device: torch.device = torch.device('cpu'),
) -> Tuple[Dict, Dict]:
    """Run Single-Seed 60/20/20 benchmark for Exp 5 and Exp 6."""
    logger.info(f"\n--- Running Single Seed {seed} Benchmark (Exp 5 & Exp 6) ---")

    # --- Exp 5: BaselineTrojanGNN ---
    base_batch = Batch.from_data_list(baseline_graphs)
    y_base = base_batch.y.cpu().numpy()
    n_base = len(y_base)
    idx_base = np.arange(n_base)

    idx_tr_b, idx_tmp_b, y_tr_b, y_tmp_b = train_test_split(
        idx_base, y_base, test_size=0.40, random_state=seed, stratify=y_base
    )
    idx_va_b, idx_te_b, y_va_b, y_te_b = train_test_split(
        idx_tmp_b, y_tmp_b, test_size=0.50, random_state=seed, stratify=y_tmp_b
    )

    logger.info(f"[Exp 5 Base-GNN Seed {seed}] Train: {len(idx_tr_b)} ({int(y_tr_b.sum())} trojans), "
                f"Val: {len(idx_va_b)} ({int(y_va_b.sum())} trojans), Test: {len(idx_te_b)} ({int(y_te_b.sum())} trojans)")

    base_model, base_val_info = train_baseline_gnn(
        batch=base_batch,
        train_idx=idx_tr_b,
        val_idx=idx_va_b,
        hidden_dim=64,
        num_layers=2,
        epochs=60,
        lr=0.005,
        device=device,
    )

    base_model.eval()
    with torch.no_grad():
        all_logits_b = base_model(base_batch.x.to(device), base_batch.edge_index.to(device)).view(-1)
        test_probs_b = torch.sigmoid(all_logits_b[idx_te_b]).cpu().numpy()

    opt_tau_b = base_val_info['optimal_threshold']
    def_met_b = compute_metrics(y_te_b, (test_probs_b >= 0.5).astype(int), test_probs_b)
    def_met_b['threshold'] = 0.5
    opt_met_b = compute_metrics(y_te_b, (test_probs_b >= opt_tau_b).astype(int), test_probs_b)
    opt_met_b['threshold'] = opt_tau_b
    opt_met_b['val_f1'] = base_val_info['val_metrics']['f1']

    # Save best Baseline GNN model
    base_ckpt = Path('data/models/baseline_gnn_best.pt')
    base_ckpt.parent.mkdir(parents=True, exist_ok=True)
    torch.save({'model_state_dict': base_model.state_dict(), 'optimal_threshold': opt_tau_b, 'seed': seed}, base_ckpt)

    exp5_res = {
        'exp_name': 'Exp 5: BaselineTrojanGNN (Author Baseline Graph)',
        'train_samples': len(idx_tr_b),
        'train_trojans': int(y_tr_b.sum()),
        'val_samples': len(idx_va_b),
        'val_trojans': int(y_va_b.sum()),
        'test_samples': len(idx_te_b),
        'test_trojans': int(y_te_b.sum()),
        'num_features': 'Baseline Graph (13 features + NetlistX edges)',
        'validation_at_optimal': base_val_info['val_metrics'],
        'default_threshold': def_met_b,
        'optimal_threshold': opt_met_b,
        'roc_auc': opt_met_b['roc_auc'],
    }

    # --- Exp 6: HeteroTrojanGNN ---
    het_batch = Batch.from_data_list(hetero_graphs)
    y_het = het_batch['cell'].y.cpu().numpy()
    n_het = len(y_het)
    idx_het = np.arange(n_het)

    idx_tr_h, idx_tmp_h, y_tr_h, y_tmp_h = train_test_split(
        idx_het, y_het, test_size=0.40, random_state=seed, stratify=y_het
    )
    idx_va_h, idx_te_h, y_va_h, y_te_h = train_test_split(
        idx_tmp_h, y_tmp_h, test_size=0.50, random_state=seed, stratify=y_tmp_h
    )

    logger.info(f"[Exp 6 Hetero-GNN Seed {seed}] Train: {len(idx_tr_h)} ({int(y_tr_h.sum())} trojans), "
                f"Val: {len(idx_va_h)} ({int(y_va_h.sum())} trojans), Test: {len(idx_te_h)} ({int(y_te_h.sum())} trojans)")

    het_model, het_val_info = train_hetero_gnn(
        batch=het_batch,
        train_idx=idx_tr_h,
        val_idx=idx_va_h,
        hidden_dim=64,
        num_layers=2,
        epochs=60,
        lr=0.005,
        device=device,
    )

    het_model.eval()
    with torch.no_grad():
        all_logits_h = het_model(het_batch.x_dict, het_batch.edge_index_dict).view(-1)
        test_probs_h = torch.sigmoid(all_logits_h[idx_te_h]).cpu().numpy()

    opt_tau_h = het_val_info['optimal_threshold']
    def_met_h = compute_metrics(y_te_h, (test_probs_h >= 0.5).astype(int), test_probs_h)
    def_met_h['threshold'] = 0.5
    opt_met_h = compute_metrics(y_te_h, (test_probs_h >= opt_tau_h).astype(int), test_probs_h)
    opt_met_h['threshold'] = opt_tau_h
    opt_met_h['val_f1'] = het_val_info['val_metrics']['f1']

    # Save best Hetero GNN model
    het_ckpt = Path('data/models/hetero_gnn_best.pt')
    het_ckpt.parent.mkdir(parents=True, exist_ok=True)
    torch.save({'model_state_dict': het_model.state_dict(), 'optimal_threshold': opt_tau_h, 'seed': seed}, het_ckpt)

    exp6_res = {
        'exp_name': 'Exp 6: HeteroTrojanGNN (Semantic Graph IR)',
        'train_samples': len(idx_tr_h),
        'train_trojans': int(y_tr_h.sum()),
        'val_samples': len(idx_va_h),
        'val_trojans': int(y_va_h.sum()),
        'test_samples': len(idx_te_h),
        'test_trojans': int(y_te_h.sum()),
        'num_features': 'Graph IR (Hetero bipartite cell<->net)',
        'validation_at_optimal': het_val_info['val_metrics'],
        'default_threshold': def_met_h,
        'optimal_threshold': opt_met_h,
        'roc_auc': opt_met_h['roc_auc'],
    }

    return exp5_res, exp6_res


# =========================================================================
# 10-Run Multi-Seed Statistical Validation
# =========================================================================

def run_10_runs_benchmark(
    baseline_graphs: List,
    hetero_graphs: List,
    seeds: List[int] = SEEDS_10_RUNS,
    device: torch.device = torch.device('cpu'),
) -> Tuple[Dict, Dict]:
    """Run 10 Repeated Multi-Seed runs for Exp 5 and Exp 6."""
    logger.info(f"\n--- Running 10-Run Multi-Seed Statistical Validation ---")

    # --- Exp 5: BaselineTrojanGNN ---
    base_batch = Batch.from_data_list(baseline_graphs)
    y_base = base_batch.y.cpu().numpy()
    n_base = len(y_base)
    idx_base = np.arange(n_base)

    f1s_b, precs_b, recs_b, mccs_b, aucs_b, taus_b = [], [], [], [], [], []
    for seed in seeds:
        idx_tr, idx_tmp, _, y_tmp = train_test_split(idx_base, y_base, test_size=0.40, random_state=seed, stratify=y_base)
        idx_va, idx_te, _, y_te = train_test_split(idx_tmp, y_tmp, test_size=0.50, random_state=seed, stratify=y_tmp)

        model, val_info = train_baseline_gnn(base_batch, idx_tr, idx_va, epochs=50, device=device)
        model.eval()
        with torch.no_grad():
            logits = model(base_batch.x.to(device), base_batch.edge_index.to(device)).view(-1)
            probs = torch.sigmoid(logits[idx_te]).cpu().numpy()

        opt_tau = val_info['optimal_threshold']
        m = compute_metrics(y_te, (probs >= opt_tau).astype(int), probs)
        f1s_b.append(m['f1'])
        precs_b.append(m['precision'] * 100)
        recs_b.append(m['recall'] * 100)
        mccs_b.append(m['mcc'])
        aucs_b.append(m['roc_auc'])
        taus_b.append(opt_tau)
        logger.info(f"  [Exp 5 Base-GNN] Seed {seed:5d} -> Test F1: {m['f1']:.4f}, AUC: {m['roc_auc']:.4f}, Tau*: {opt_tau:.3f}")

    exp5_stats = {
        'f1_mean': float(np.mean(f1s_b)), 'f1_std': float(np.std(f1s_b)),
        'prec_mean': float(np.mean(precs_b)), 'prec_std': float(np.std(precs_b)),
        'rec_mean': float(np.mean(recs_b)), 'rec_std': float(np.std(recs_b)),
        'mcc_mean': float(np.mean(mccs_b)), 'mcc_std': float(np.std(mccs_b)),
        'auc_mean': float(np.mean(aucs_b)), 'auc_std': float(np.std(aucs_b)),
        'thresh_mean': float(np.mean(taus_b)), 'thresh_std': float(np.std(taus_b)),
    }

    # --- Exp 6: HeteroTrojanGNN ---
    het_batch = Batch.from_data_list(hetero_graphs)
    y_het = het_batch['cell'].y.cpu().numpy()
    n_het = len(y_het)
    idx_het = np.arange(n_het)

    f1s_h, precs_h, recs_h, mccs_h, aucs_h, taus_h = [], [], [], [], [], []
    for seed in seeds:
        idx_tr, idx_tmp, _, y_tmp = train_test_split(idx_het, y_het, test_size=0.40, random_state=seed, stratify=y_het)
        idx_va, idx_te, _, y_te = train_test_split(idx_tmp, y_tmp, test_size=0.50, random_state=seed, stratify=y_tmp)

        model, val_info = train_hetero_gnn(het_batch, idx_tr, idx_va, epochs=50, device=device)
        model.eval()
        with torch.no_grad():
            logits = model(het_batch.x_dict, het_batch.edge_index_dict).view(-1)
            probs = torch.sigmoid(logits[idx_te]).cpu().numpy()

        opt_tau = val_info['optimal_threshold']
        m = compute_metrics(y_te, (probs >= opt_tau).astype(int), probs)
        f1s_h.append(m['f1'])
        precs_h.append(m['precision'] * 100)
        recs_h.append(m['recall'] * 100)
        mccs_h.append(m['mcc'])
        aucs_h.append(m['roc_auc'])
        taus_h.append(opt_tau)
        logger.info(f"  [Exp 6 Hetero-GNN] Seed {seed:5d} -> Test F1: {m['f1']:.4f}, AUC: {m['roc_auc']:.4f}, Tau*: {opt_tau:.3f}")

    exp6_stats = {
        'f1_mean': float(np.mean(f1s_h)), 'f1_std': float(np.std(f1s_h)),
        'prec_mean': float(np.mean(precs_h)), 'prec_std': float(np.std(precs_h)),
        'rec_mean': float(np.mean(recs_h)), 'rec_std': float(np.std(recs_h)),
        'mcc_mean': float(np.mean(mccs_h)), 'mcc_std': float(np.std(mccs_h)),
        'auc_mean': float(np.mean(aucs_h)), 'auc_std': float(np.std(aucs_h)),
        'thresh_mean': float(np.mean(taus_h)), 'thresh_std': float(np.std(taus_h)),
    }

    return exp5_stats, exp6_stats


# =========================================================================
# Leave-One-Family-Out (LOFO) Cross-Validation
# =========================================================================

def run_lofo_benchmark(
    baseline_graphs: List,
    hetero_graphs: List,
    device: torch.device = torch.device('cpu'),
) -> Tuple[Dict, Dict]:
    """Run Leave-One-Family-Out (LOFO) Cross-Validation for Exp 5 and Exp 6."""
    logger.info(f"\n--- Running Leave-One-Family-Out (LOFO) Cross-Validation ---")

    # Map graphs to families
    base_fams = {fam: [] for fam in CIRCUIT_FAMILIES}
    for g in baseline_graphs:
        cname = g.circuit_name
        for fam, pats in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in pats):
                base_fams[fam].append(g)
                break

    het_fams = {fam: [] for fam in CIRCUIT_FAMILIES}
    for g in hetero_graphs:
        cname = g.circuit_name
        for fam, pats in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in pats):
                het_fams[fam].append(g)
                break

    # --- Exp 5: BaselineTrojanGNN LOFO ---
    base_per_fam = {}
    tp_b, fp_b, fn_b, tn_b = 0, 0, 0, 0
    f1_list_b = []

    for holdout_fam, test_list in base_fams.items():
        train_list = [g for f, glist in base_fams.items() if f != holdout_fam for g in glist]
        b_train = Batch.from_data_list(train_list)
        b_test = Batch.from_data_list(test_list)

        y_train_all = b_train.y.cpu().numpy()
        idx_tr, idx_va = train_test_split(np.arange(len(y_train_all)), test_size=0.15, random_state=42, stratify=y_train_all)

        model, val_info = train_baseline_gnn(b_train, idx_tr, idx_va, epochs=50, device=device)
        model.eval()
        with torch.no_grad():
            logits = model(b_test.x.to(device), b_test.edge_index.to(device)).view(-1)
            probs = torch.sigmoid(logits).cpu().numpy()

        y_test = b_test.y.cpu().numpy()
        opt_tau = val_info['optimal_threshold']
        m = compute_metrics(y_test, (probs >= opt_tau).astype(int), probs)
        m['threshold'] = opt_tau
        base_per_fam[holdout_fam] = m
        tp_b += m['tp']; fp_b += m['fp']; fn_b += m['fn']; tn_b += m['tn']
        f1_list_b.append(m['f1'])
        logger.info(f"  [Exp 5 LOFO] Holdout {holdout_fam:<7} -> Prec: {m['precision']*100:5.2f}%, Rec: {m['recall']*100:5.2f}%, F1: {m['f1']:.4f}, AUC: {m['roc_auc']:.4f}")

    micro_p_b = tp_b / (tp_b + fp_b) if (tp_b + fp_b) > 0 else 0
    micro_r_b = tp_b / (tp_b + fn_b) if (tp_b + fn_b) > 0 else 0
    micro_f1_b = 2 * micro_p_b * micro_r_b / (micro_p_b + micro_r_b) if (micro_p_b + micro_r_b) > 0 else 0

    exp5_lofo = {
        'micro_precision': float(micro_p_b), 'micro_recall': float(micro_r_b),
        'micro_f1': float(micro_f1_b), 'macro_f1': float(np.mean(f1_list_b)),
        'per_family': base_per_fam,
    }

    # --- Exp 6: HeteroTrojanGNN LOFO ---
    het_per_fam = {}
    tp_h, fp_h, fn_h, tn_h = 0, 0, 0, 0
    f1_list_h = []

    for holdout_fam, test_list in het_fams.items():
        train_list = [g for f, glist in het_fams.items() if f != holdout_fam for g in glist]
        b_train = Batch.from_data_list(train_list)
        b_test = Batch.from_data_list(test_list)

        y_train_all = b_train['cell'].y.cpu().numpy()
        idx_tr, idx_va = train_test_split(np.arange(len(y_train_all)), test_size=0.15, random_state=42, stratify=y_train_all)

        model, val_info = train_hetero_gnn(b_train, idx_tr, idx_va, epochs=50, device=device)
        model.eval()
        with torch.no_grad():
            logits = model(b_test.x_dict, b_test.edge_index_dict).view(-1)
            probs = torch.sigmoid(logits).cpu().numpy()

        y_test = b_test['cell'].y.cpu().numpy()
        opt_tau = val_info['optimal_threshold']
        m = compute_metrics(y_test, (probs >= opt_tau).astype(int), probs)
        m['threshold'] = opt_tau
        het_per_fam[holdout_fam] = m
        tp_h += m['tp']; fp_h += m['fp']; fn_h += m['fn']; tn_h += m['tn']
        f1_list_h.append(m['f1'])
        logger.info(f"  [Exp 6 LOFO] Holdout {holdout_fam:<7} -> Prec: {m['precision']*100:5.2f}%, Rec: {m['recall']*100:5.2f}%, F1: {m['f1']:.4f}, AUC: {m['roc_auc']:.4f}")

    micro_p_h = tp_h / (tp_h + fp_h) if (tp_h + fp_h) > 0 else 0
    micro_r_h = tp_h / (tp_h + fn_h) if (tp_h + fn_h) > 0 else 0
    micro_f1_h = 2 * micro_p_h * micro_r_h / (micro_p_h + micro_r_h) if (micro_p_h + micro_r_h) > 0 else 0

    exp6_lofo = {
        'micro_precision': float(micro_p_h), 'micro_recall': float(micro_r_h),
        'micro_f1': float(micro_f1_h), 'macro_f1': float(np.mean(f1_list_h)),
        'per_family': het_per_fam,
    }

    return exp5_lofo, exp6_lofo


# =========================================================================
# Main Execution
# =========================================================================

def main():
    logger.info("=" * 80)
    logger.info("STARTING 6-WAY COMPREHENSIVE BENCHMARK: BASELINE vs GRAPH IR (XGBoost & GNN)")
    logger.info("=" * 80)

    device = get_device()

    # Load baseline graphs
    logger.info("\nLoading Baseline circuit graphs (NetlistX c.graph)...")
    base_converter = BaselinePyGConverter()
    t0 = time.time()
    baseline_graphs = base_converter.convert_all()
    logger.info(f"Loaded {len(baseline_graphs)} baseline graphs in {time.time()-t0:.2f}s")

    # Load Graph IR hetero graphs
    logger.info("\nLoading Semantic Graph IR hetero graphs (CircuitPyGConverter)...")
    het_converter = CircuitPyGConverter()
    t0 = time.time()
    circuits = sorted([d.name for d in het_converter.graphs_dir.glob('*') if d.is_dir()])
    hetero_graphs = [het_converter.convert_circuit(c) for c in circuits]
    logger.info(f"Loaded {len(hetero_graphs)} Graph IR graphs in {time.time()-t0:.2f}s")

    # 1. Single Seed Benchmark
    exp5_single, exp6_single = run_single_seed_benchmark(baseline_graphs, hetero_graphs, seed=42, device=device)

    # 2. 10-Run Statistical Validation
    exp5_stats, exp6_stats = run_10_runs_benchmark(baseline_graphs, hetero_graphs, seeds=SEEDS_10_RUNS, device=device)

    # 3. LOFO Cross-Validation
    exp5_lofo, exp6_lofo = run_lofo_benchmark(baseline_graphs, hetero_graphs, device=device)

    # 4. Load comparison_4_experiments.json and merge Exp 5 & Exp 6
    comp4_path = Path('data/models/comparison_4_experiments.json')
    if comp4_path.exists():
        with open(comp4_path, 'r') as f:
            comp_data = json.load(f)
    else:
        comp_data = {'single_run': {}, 'statistical_10_runs': {}, 'lofo_cross_validation': {}}

    comp_data['single_run']['exp5'] = exp5_single
    comp_data['single_run']['exp6'] = exp6_single

    comp_data['statistical_10_runs']['Exp 5 (Base-GNN)'] = exp5_stats
    comp_data['statistical_10_runs']['Exp 6 (GIR-HeteroGNN)'] = exp6_stats

    comp_data['lofo_cross_validation']['exp5'] = exp5_lofo
    comp_data['lofo_cross_validation']['exp6'] = exp6_lofo

    # Save 6-experiment comparison
    comp6_path = Path('data/models/comparison_6_experiments.json')
    with open(comp6_path, 'w', encoding='utf-8') as f:
        json.dump(comp_data, f, indent=2)
    logger.info(f"\nSaved combined 6-Experiment Benchmark to {comp6_path}")

    # Also save comparison_5_experiments.json for backwards compatibility
    comp5_path = Path('data/models/comparison_5_experiments.json')
    with open(comp5_path, 'w', encoding='utf-8') as f:
        json.dump(comp_data, f, indent=2)

    # 5. Print Detailed 6-Way Comparative Tables
    exp_keys = ['exp1', 'exp2', 'exp3', 'exp4', 'exp5', 'exp6']
    stat_keys = [
        'Exp 1 (Base-5)', 'Exp 2 (Base-13)',
        'Exp 3 (GIR-5)', 'Exp 4 (GIR-13)',
        'Exp 5 (Base-GNN)', 'Exp 6 (GIR-HeteroGNN)'
    ]

    print("\n" + "=" * 145)
    print("                      6-WAY COMPREHENSIVE BENCHMARK: BASELINE vs GRAPH IR (XGBOOST vs GNN)")
    print("=" * 145)

    print("\n--- 1. SINGLE-SEED BENCHMARK (60/20/20 Stratified Split at Val-Tuned Tau*) ---")
    hdr = f"{'Metric':<22} | {'Exp 1 (Base-5)':<15} | {'Exp 2 (Base-13)':<15} | {'Exp 3 (GIR-5)':<15} | {'Exp 4 (GIR-13)':<15} | {'Exp 5 (Base-GNN)':<16} | {'Exp 6 (GIR-GNN)':<16}"
    print(hdr)
    print("-" * 145)
    for mkey, mname in [('f1', 'F1-Score'), ('precision', 'Precision (%)'), ('recall', 'Recall (%)'), ('mcc', 'MCC'), ('roc_auc', 'ROC-AUC'), ('threshold', 'Optimal Tau*')]:
        row = f"{mname:<22} | "
        for ek in exp_keys:
            if ek in comp_data['single_run']:
                res = comp_data['single_run'][ek]['optimal_threshold']
                val = res.get(mkey, 0.0)
                if mkey in ['precision', 'recall']:
                    val *= 100.0
                    row += f"{val:>13.2f}% | "
                else:
                    row += f"{val:>15.4f} | "
            else:
                row += f"{'N/A':>15} | "
        print(row)

    print("\n--- 2. 10-RUN STATISTICAL VALIDATION (Mean +/- Std across 10 Seeds) ---")
    print(hdr)
    print("-" * 145)
    for metric_prefix, mname in [('f1', 'F1-Score'), ('prec', 'Precision (%)'), ('rec', 'Recall (%)'), ('mcc', 'MCC'), ('auc', 'ROC-AUC')]:
        row = f"{mname:<22} | "
        for sk in stat_keys:
            if sk in comp_data['statistical_10_runs']:
                sdict = comp_data['statistical_10_runs'][sk]
                m_val = sdict.get(f'{metric_prefix}_mean', 0.0)
                s_val = sdict.get(f'{metric_prefix}_std', 0.0)
                if metric_prefix in ['prec', 'rec']:
                    row += f"{m_val:>5.1f} +/- {s_val:<4.1f}% | "
                else:
                    row += f"{m_val:.3f} +/- {s_val:.3f} | "
            else:
                row += f"{'N/A':>15} | "
        print(row)

    print("\n--- 3. LEAVE-ONE-FAMILY-OUT (LOFO) CROSS-VALIDATION ---")
    print(hdr)
    print("-" * 145)
    for lkey, lname in [('macro_f1', 'LOFO Macro F1'), ('micro_f1', 'LOFO Micro F1'), ('micro_precision', 'LOFO Micro Prec (%)'), ('micro_recall', 'LOFO Micro Rec (%)')]:
        row = f"{lname:<22} | "
        for ek in exp_keys:
            if ek in comp_data['lofo_cross_validation']:
                lres = comp_data['lofo_cross_validation'][ek]
                val = lres.get(lkey, 0.0)
                if 'precision' in lkey or 'recall' in lkey:
                    val *= 100.0
                    row += f"{val:>13.2f}% | "
                else:
                    row += f"{val:>15.4f} | "
            else:
                row += f"{'N/A':>15} | "
        print(row)
    print("=" * 145 + "\n")


if __name__ == '__main__':
    main()
