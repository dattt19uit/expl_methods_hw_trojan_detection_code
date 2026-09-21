#!/usr/bin/env python3
"""
Supplementary Experiments for Chapter 7:
1. Dirichlet Energy & Over-smoothing Analysis (Control ON vs. Control OFF)
2. Sensitivity Analysis of RS232-T1800_90nm
3. Receptive Field Depth / Hop Semantics Balance (Config B: 2 layers vs. 4 layers)
4. Multi-Seed Variance Analysis (Seeds 42, 123, 456 across Configs C, D, E, F)
"""

import copy
import json
import logging
import math
import os
from pathlib import Path
import sys
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Batch, Data, HeteroData
from torch_geometric.nn import HeteroConv, Linear, SAGEConv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'packages' / 'shared'))

from xai_shared.graph_data.baseline_gnn import BaselineTrojanGNN
from xai_shared.graph_data.baseline_pyg_converter import BaselinePyGConverter
from xai_shared.graph_data.hetero_gnn import HeteroTrojanGNN
from xai_shared.graph_data.pyg_converter import CircuitPyGConverter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SupplementaryExperiments')

OUTPUT_DIR = REPO_ROOT / 'outputs' / 'results'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CIRCUIT_FAMILIES = {
    'RS232': ['RS232-T1000', 'RS232-T1100', 'RS232-T1200', 'RS232-T1300', 'RS232-T1400',
              'RS232-T1500', 'RS232-T1600', 'RS232-T1700', 'RS232-T1800', 'RS232-T1900', 'RS232-T2000'],
    's15850': ['s15850-T100'],
    's35932': ['s35932-T100', 's35932-T200', 's35932-T300'],
    's38417': ['s38417-T100', 's38417-T200'],
    's38584': ['s38584-T100', 's38584-T300'],
}

BASIC_5_FEATURES = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']

EDGE_TYPES_ALL = [
    ('net', 'data_input', 'cell'),
    ('net', 'control_input', 'cell'),
    ('cell', 'outputs', 'net'),
    ('cell', 'rev_data_input', 'net'),
    ('cell', 'rev_control_input', 'net'),
    ('net', 'rev_outputs', 'cell'),
]

EDGE_TYPES_NO_CTRL = [
    ('net', 'data_input', 'cell'),
    ('cell', 'outputs', 'net'),
    ('cell', 'rev_data_input', 'net'),
    ('net', 'rev_outputs', 'cell'),
]


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device('cuda')
    dev = torch.device('cpu')
    torch.set_num_threads(min(4, os.cpu_count() or 2))
    return dev


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


class HomogeneousCellNetGNNFlexible(nn.Module):
    def __init__(self, hidden_dim: int = 64, num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.num_layers = num_layers
        self.cell_in = Linear(-1, hidden_dim)
        self.net_in = Linear(-1, hidden_dim)
        self.convs = nn.ModuleList([SAGEConv(hidden_dim, hidden_dim) for _ in range(num_layers)])
        self.norms = nn.ModuleList([nn.LayerNorm(hidden_dim) for _ in range(num_layers)])
        self.dropout = dropout
        self.classifier = nn.Sequential(
            Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            Linear(hidden_dim // 2, 1)
        )

    def forward(self, batch: HeteroData) -> torch.Tensor:
        h_cell = F.relu(self.cell_in(batch['cell'].x))
        h_net = F.relu(self.net_in(batch['net'].x))
        num_cells = h_cell.size(0)

        h = torch.cat([h_cell, h_net], dim=0)

        edge_list = []
        for (src_type, rel, dst_type), edge_idx in batch.edge_index_dict.items():
            s_idx = edge_idx[0].clone()
            d_idx = edge_idx[1].clone()
            if src_type == 'net':
                s_idx += num_cells
            if dst_type == 'net':
                d_idx += num_cells
            edge_list.append(torch.stack([s_idx, d_idx], dim=0))

        if edge_list:
            merged_edge_index = torch.cat(edge_list, dim=1)
        else:
            merged_edge_index = torch.empty((2, 0), dtype=torch.long, device=h.device)

        for i in range(len(self.convs)):
            h_new = self.convs[i](h, merged_edge_index)
            h = self.norms[i](F.relu(h_new) + h)
            if self.dropout > 0:
                h = F.dropout(h, p=self.dropout, training=self.training)

        return self.classifier(h[:num_cells])


def train_hetero_model(
    batch_train: HeteroData,
    idx_tr: np.ndarray,
    idx_va: np.ndarray,
    edge_types: List[Tuple[str, str, str]],
    device: torch.device,
    epochs: int = 50,
    lr: float = 0.005,
    seed: int = 42
):
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = HeteroTrojanGNN(hidden_dim=64, num_layers=2, dropout=0.2, edge_types=edge_types).to(device)
    batch_train = batch_train.to(device)
    y_tr = batch_train['cell'].y[idx_tr]
    n_pos = int(y_tr.sum().item())
    n_neg = len(idx_tr) - n_pos
    pos_weight = torch.tensor([max(1.0, float(n_neg / max(1, n_pos)))], device=device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    best_val_f1 = -1.0
    best_state = None
    best_tau = 0.5
    y_all = batch_train['cell'].y.cpu().numpy()

    filtered_edge_dict = {et: batch_train.edge_index_dict[et] for et in edge_types if et in batch_train.edge_index_dict}

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        logits = model(batch_train.x_dict, filtered_edge_dict).view(-1)
        loss = criterion(logits[idx_tr], y_tr)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
            model.eval()
            with torch.no_grad():
                val_logits = model(batch_train.x_dict, filtered_edge_dict).view(-1)
                val_probs = torch.sigmoid(val_logits[idx_va]).cpu().numpy()
            tau, val_m = find_optimal_threshold(y_all[idx_va], val_probs)
            if val_m['f1'] > best_val_f1:
                best_val_f1 = val_m['f1']
                best_state = copy.deepcopy(model.state_dict())
                best_tau = tau

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_tau


def train_config_b_flexible(
    batch_train: HeteroData,
    idx_tr: np.ndarray,
    idx_va: np.ndarray,
    num_layers: int,
    device: torch.device,
    epochs: int = 50,
    seed: int = 42
):
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = HomogeneousCellNetGNNFlexible(hidden_dim=64, num_layers=num_layers, dropout=0.2).to(device)
    batch_train = batch_train.to(device)
    y_tr = batch_train['cell'].y[idx_tr]
    n_pos = int(y_tr.sum().item())
    n_neg = len(idx_tr) - n_pos
    pos_weight = torch.tensor([max(1.0, float(n_neg / max(1, n_pos)))], device=device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)

    best_val_f1 = -1.0
    best_state = None
    best_tau = 0.5
    y_all = batch_train['cell'].y.cpu().numpy()

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        logits = model(batch_train).view(-1)
        loss = criterion(logits[idx_tr], y_tr)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
            model.eval()
            with torch.no_grad():
                val_logits = model(batch_train).view(-1)
                val_probs = torch.sigmoid(val_logits[idx_va]).cpu().numpy()
            tau, val_m = find_optimal_threshold(y_all[idx_va], val_probs)
            if val_m['f1'] > best_val_f1:
                best_val_f1 = val_m['f1']
                best_state = copy.deepcopy(model.state_dict())
                best_tau = tau

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_tau


def extract_layer_embeddings(model: HeteroTrojanGNN, data: HeteroData, edge_types: List[Tuple[str, str, str]]):
    model.eval()
    with torch.no_grad():
        h_dict = {
            'cell': F.relu(model.cell_in(data.x_dict['cell'])),
            'net': F.relu(model.net_in(data.x_dict['net'])),
        }
        filtered_edges = {et: data.edge_index_dict[et] for et in edge_types if et in data.edge_index_dict}

        layer_embeddings = {'cell': [h_dict['cell'].clone()]}

        for i in range(model.num_layers):
            h_new = model.convs[i](h_dict, filtered_edges)
            h_dict = {
                k: model.norms[i][k](F.relu(h_new[k]) + h_dict[k])
                for k in h_dict.keys()
            }
            layer_embeddings['cell'].append(h_dict['cell'].clone())

    return layer_embeddings['cell']


def compute_dirichlet_and_cosine(h_cell: torch.Tensor, max_samples: int = 3000, seed: int = 42) -> Tuple[float, float]:
    """
    Computes:
    1. Normalized Dirichlet Energy: E_D(H) = ||h_u - h_v||^2 / (2 * Var(H) * N)
    2. Mean Pairwise Cosine Distance: 1 - CosSim(h_u, h_v)
    """
    N = h_cell.size(0)
    if N <= 1:
        return 0.0, 0.0

    torch.manual_seed(seed)
    np.random.seed(seed)

    if N > max_samples:
        perm = torch.randperm(N)[:max_samples]
        h_sample = h_cell[perm]
    else:
        h_sample = h_cell

    # L2 normalize embeddings for cosine distance
    h_norm = F.normalize(h_sample, p=2, dim=-1)
    sim_matrix = torch.mm(h_norm, h_norm.t())
    triu_indices = torch.triu_indices(h_sample.size(0), h_sample.size(0), offset=1)
    pairwise_sims = sim_matrix[triu_indices[0], triu_indices[1]]
    mean_cosine_dist = float((1.0 - pairwise_sims).mean().item())

    # Normalized Dirichlet Energy
    # Sum of squared differences between sampled pairs divided by average energy
    diffs = h_sample[triu_indices[0]] - h_sample[triu_indices[1]]
    sq_diff = (diffs ** 2).sum(dim=-1).mean().item()
    h_var = (h_sample ** 2).sum(dim=-1).mean().item()
    dirichlet_norm = float(sq_diff / (2.0 * max(h_var, 1e-8)))

    return dirichlet_norm, mean_cosine_dist


# =========================================================================
# Main Supplementary Experiments
# =========================================================================

def run_all_supplementary_experiments():
    device = get_device()
    logger.info(f"Using device: {device}")

    # 1. Load Data
    logger.info("Loading graphs...")
    het_conv_basic = CircuitPyGConverter(feature_cols=BASIC_5_FEATURES)
    circuits = sorted([d.name for d in het_conv_basic.graphs_dir.glob('*') if d.is_dir()])
    het_graphs_basic = [het_conv_basic.convert_circuit(c) for c in circuits]

    het_conv_full = CircuitPyGConverter()
    het_graphs_full = [het_conv_full.convert_circuit(c) for c in circuits]

    base_converter = BaselinePyGConverter()
    base_graphs = base_converter.convert_all()

    # Family mapping
    base_fams = {fam: [] for fam in CIRCUIT_FAMILIES}
    for g in base_graphs:
        cname = g.circuit_name
        for fam, pats in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in pats):
                base_fams[fam].append(g)
                break

    het_basic_fams = {fam: [] for fam in CIRCUIT_FAMILIES}
    for g in het_graphs_basic:
        cname = g.circuit_name
        for fam, pats in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in pats):
                het_basic_fams[fam].append(g)
                break

    het_full_fams = {fam: [] for fam in CIRCUIT_FAMILIES}
    for g in het_graphs_full:
        cname = g.circuit_name
        for fam, pats in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in pats):
                het_full_fams[fam].append(g)
                break

    results_out = {}

    # ---------------------------------------------------------------------
    # EXPERIMENT 1: Dirichlet Energy & Over-smoothing (Control ON vs OFF)
    # ---------------------------------------------------------------------
    logger.info("\n=======================================================")
    logger.info("EXPERIMENT 1: Dirichlet Energy & Over-smoothing Analysis")
    logger.info("=======================================================")

    test_circuits = ['s35932-T100', 's38417-T100', 'RS232-T1000_90nm', 's15850-T100']
    dirichlet_results = {}

    # Train Config C & D on full basic dataset with seed 42 to inspect embeddings
    b_all_basic = Batch.from_data_list(het_graphs_basic).to(device)
    y_all_basic = b_all_basic['cell'].y.cpu().numpy()
    idx_tr_b, idx_va_b = train_test_split(np.arange(len(y_all_basic)), test_size=0.15, random_state=42, stratify=y_all_basic)

    logger.info("Training Config C (Control ON) for Dirichlet measurement...")
    model_c, _ = train_hetero_model(b_all_basic, idx_tr_b, idx_va_b, EDGE_TYPES_ALL, device, epochs=50, seed=42)

    logger.info("Training Config D (Control OFF) for Dirichlet measurement...")
    model_d, _ = train_hetero_model(b_all_basic, idx_tr_b, idx_va_b, EDGE_TYPES_NO_CTRL, device, epochs=50, seed=42)

    for cname in test_circuits:
        matching = [g for g in het_graphs_basic if g.circuit_name == cname]
        if not matching:
            continue
        g_c = matching[0].to(device)

        embs_c = extract_layer_embeddings(model_c, g_c, EDGE_TYPES_ALL)
        embs_d = extract_layer_embeddings(model_d, g_c, EDGE_TYPES_NO_CTRL)

        c_metrics = []
        d_metrics = []
        for l_idx in range(len(embs_c)):
            e_c, cos_c = compute_dirichlet_and_cosine(embs_c[l_idx])
            e_d, cos_d = compute_dirichlet_and_cosine(embs_d[l_idx])
            c_metrics.append({'layer': l_idx, 'dirichlet_energy': round(e_c, 4), 'cosine_distance': round(cos_c, 4)})
            d_metrics.append({'layer': l_idx, 'dirichlet_energy': round(e_d, 4), 'cosine_distance': round(cos_d, 4)})

        dirichlet_results[cname] = {
            'Config_C_Control_ON': c_metrics,
            'Config_D_Control_OFF': d_metrics,
        }
        logger.info(f"Circuit {cname}:")
        logger.info(f"  Layer 0 -> C: E_D={c_metrics[0]['dirichlet_energy']}, CosDist={c_metrics[0]['cosine_distance']} | D: E_D={d_metrics[0]['dirichlet_energy']}, CosDist={d_metrics[0]['cosine_distance']}")
        logger.info(f"  Layer 2 -> C: E_D={c_metrics[2]['dirichlet_energy']}, CosDist={c_metrics[2]['cosine_distance']} | D: E_D={d_metrics[2]['dirichlet_energy']}, CosDist={d_metrics[2]['cosine_distance']}")

    results_out['dirichlet_oversmoothing'] = dirichlet_results

    # ---------------------------------------------------------------------
    # EXPERIMENT 2: Sensitivity Analysis of RS232-T1800_90nm
    # ---------------------------------------------------------------------
    logger.info("\n=======================================================")
    logger.info("EXPERIMENT 2: Sensitivity Analysis of RS232-T1800_90nm")
    logger.info("=======================================================")

    # Compare LOFO on Config D (5 feats) and Config F (13 feats) with vs without T1800_90nm
    sensitivity_results = {}
    for cfg_name, edge_types, fam_dict in [
        ('Config_D', EDGE_TYPES_NO_CTRL, het_basic_fams),
        ('Config_F', EDGE_TYPES_NO_CTRL, het_full_fams),
    ]:
        # Case A: Standard (with T1800_90nm)
        # Train on non-RS232, test on RS232
        train_with = [g for f, glist in fam_dict.items() if f != 'RS232' for g in glist]
        test_with = fam_dict['RS232']
        b_tr_w = Batch.from_data_list(train_with).to(device)
        b_te_w = Batch.from_data_list(test_with).to(device)
        y_tr_w = b_tr_w['cell'].y.cpu().numpy()
        idx_tr_w, idx_va_w = train_test_split(np.arange(len(y_tr_w)), test_size=0.15, random_state=42, stratify=y_tr_w)

        m_w, tau_w = train_hetero_model(b_tr_w, idx_tr_w, idx_va_w, edge_types, device, epochs=50, seed=42)
        m_w.eval()
        filt_w = {et: b_te_w.edge_index_dict[et] for et in edge_types if et in b_te_w.edge_index_dict}
        with torch.no_grad():
            probs_w = torch.sigmoid(m_w(b_te_w.x_dict, filt_w).view(-1)).cpu().numpy()
        y_te_w = b_te_w['cell'].y.cpu().numpy()
        res_with = compute_metrics(y_te_w, (probs_w >= tau_w).astype(int), probs_w)

        # Case B: Excluded T1800_90nm
        test_without = [g for g in fam_dict['RS232'] if 'T1800_90nm' not in g.circuit_name]
        b_te_wo = Batch.from_data_list(test_without).to(device)
        filt_wo = {et: b_te_wo.edge_index_dict[et] for et in edge_types if et in b_te_wo.edge_index_dict}
        with torch.no_grad():
            probs_wo = torch.sigmoid(m_w(b_te_wo.x_dict, filt_wo).view(-1)).cpu().numpy()
        y_te_wo = b_te_wo['cell'].y.cpu().numpy()
        res_without = compute_metrics(y_te_wo, (probs_wo >= tau_w).astype(int), probs_wo)

        sensitivity_results[cfg_name] = {
            'with_T1800_90nm': res_with,
            'without_T1800_90nm': res_without,
            'delta_f1': round(res_without['f1'] - res_with['f1'], 4),
            'delta_precision': round(res_without['precision'] - res_with['precision'], 4),
            'delta_recall': round(res_without['recall'] - res_with['recall'], 4),
        }
        logger.info(f"{cfg_name} RS232 Fold:")
        logger.info(f"  With T1800-90nm:    F1={res_with['f1']:.4f}, Prec={res_with['precision']:.4f}, Rec={res_with['recall']:.4f}")
        logger.info(f"  Without T1800-90nm: F1={res_without['f1']:.4f}, Prec={res_without['precision']:.4f}, Rec={res_without['recall']:.4f}")

    results_out['t1800_sensitivity'] = sensitivity_results

    # ---------------------------------------------------------------------
    # EXPERIMENT 3: Receptive Field Depth (Config B: 2-layer vs. 4-layer)
    # ---------------------------------------------------------------------
    logger.info("\n=======================================================")
    logger.info("EXPERIMENT 3: Receptive Field Balance (Config B: 2 vs. 4 layers)")
    logger.info("=======================================================")

    b_results = {'2_layers': {}, '4_layers': {}}
    families = list(CIRCUIT_FAMILIES.keys())

    for holdout_fam in families:
        train_h = [g for f, glist in het_basic_fams.items() if f != holdout_fam for g in glist]
        test_h = het_basic_fams[holdout_fam]
        b_tr = Batch.from_data_list(train_h)
        b_te = Batch.from_data_list(test_h)
        y_tr = b_tr['cell'].y.cpu().numpy()
        idx_tr, idx_va = train_test_split(np.arange(len(y_tr)), test_size=0.15, random_state=42, stratify=y_tr)
        y_te = b_te['cell'].y.cpu().numpy()

        # 2 layers (1 gate hop)
        m_b2, tau_b2 = train_config_b_flexible(b_tr, idx_tr, idx_va, num_layers=2, device=device, epochs=50, seed=42)
        m_b2.eval()
        with torch.no_grad():
            probs_b2 = torch.sigmoid(m_b2(b_te.to(device)).view(-1)).cpu().numpy()
        res_b2 = compute_metrics(y_te, (probs_b2 >= tau_b2).astype(int), probs_b2)
        b_results['2_layers'][holdout_fam] = res_b2

        # 4 layers (2 gate hops)
        m_b4, tau_b4 = train_config_b_flexible(b_tr, idx_tr, idx_va, num_layers=4, device=device, epochs=50, seed=42)
        m_b4.eval()
        with torch.no_grad():
            probs_b4 = torch.sigmoid(m_b4(b_te.to(device)).view(-1)).cpu().numpy()
        res_b4 = compute_metrics(y_te, (probs_b4 >= tau_b4).astype(int), probs_b4)
        b_results['4_layers'][holdout_fam] = res_b4

        logger.info(f"Holdout {holdout_fam:<7}: B(2-layer) F1={res_b2['f1']:.4f} | B(4-layer) F1={res_b4['f1']:.4f}")

    macro_f1_b2 = np.mean([b_results['2_layers'][f]['f1'] for f in families])
    macro_f1_b4 = np.mean([b_results['4_layers'][f]['f1'] for f in families])
    results_out['hop_semantics_balance'] = {
        'detailed': b_results,
        'macro_f1_2_layers': round(float(macro_f1_b2), 4),
        'macro_f1_4_layers': round(float(macro_f1_b4), 4),
        'delta_f1': round(float(macro_f1_b4 - macro_f1_b2), 4)
    }
    logger.info(f"Macro F1: Config B (2 layers) = {macro_f1_b2:.4f} vs. Config B (4 layers) = {macro_f1_b4:.4f} (Delta = {macro_f1_b4 - macro_f1_b2:+.4f})")

    # ---------------------------------------------------------------------
    # EXPERIMENT 4: Multi-Seed Variance Analysis (Seeds 42, 123, 456)
    # ---------------------------------------------------------------------
    logger.info("\n=======================================================")
    logger.info("EXPERIMENT 4: Multi-Seed Variance Analysis (Seeds 42, 123, 456)")
    logger.info("=======================================================")

    seeds = [42, 123, 456]
    multi_seed_results = {'C': {}, 'D': {}, 'E': {}, 'F': {}}

    configs_to_test = [
        ('C', EDGE_TYPES_ALL, het_basic_fams),
        ('D', EDGE_TYPES_NO_CTRL, het_basic_fams),
        ('E', EDGE_TYPES_ALL, het_full_fams),
        ('F', EDGE_TYPES_NO_CTRL, het_full_fams),
    ]

    for cfg_code, edge_types, fam_dict in configs_to_test:
        logger.info(f"Running Multi-Seed Evaluation for Config {cfg_code}...")
        seed_f1s = []
        seed_praucs = []
        seed_mccs = []

        for seed in seeds:
            fam_f1s = []
            fam_praucs = []
            fam_mccs = []
            for holdout_fam in families:
                train_h = [g for f, glist in fam_dict.items() if f != holdout_fam for g in glist]
                test_h = fam_dict[holdout_fam]
                b_tr = Batch.from_data_list(train_h).to(device)
                b_te = Batch.from_data_list(test_h).to(device)
                y_tr = b_tr['cell'].y.cpu().numpy()
                idx_tr, idx_va = train_test_split(np.arange(len(y_tr)), test_size=0.15, random_state=seed, stratify=y_tr)

                m, tau = train_hetero_model(b_tr, idx_tr, idx_va, edge_types, device, epochs=50, seed=seed)
                m.eval()
                filt = {et: b_te.edge_index_dict[et] for et in edge_types if et in b_te.edge_index_dict}
                with torch.no_grad():
                    probs = torch.sigmoid(m(b_te.x_dict, filt).view(-1)).cpu().numpy()
                y_te = b_te['cell'].y.cpu().numpy()
                res = compute_metrics(y_te, (probs >= tau).astype(int), probs)
                fam_f1s.append(res['f1'])
                fam_praucs.append(res['pr_auc'])
                fam_mccs.append(res['mcc'])

            macro_f1 = float(np.mean(fam_f1s))
            macro_prauc = float(np.mean(fam_praucs))
            macro_mcc = float(np.mean(fam_mccs))

            seed_f1s.append(macro_f1)
            seed_praucs.append(macro_prauc)
            seed_mccs.append(macro_mcc)
            logger.info(f"  Config {cfg_code} [Seed {seed}]: Macro F1={macro_f1:.4f}, PR-AUC={macro_prauc:.4f}, MCC={macro_mcc:.4f}")

        multi_seed_results[cfg_code] = {
            'seeds': seeds,
            'f1_scores': [round(x, 4) for x in seed_f1s],
            'f1_mean': round(float(np.mean(seed_f1s)), 4),
            'f1_std': round(float(np.std(seed_f1s)), 4),
            'prauc_mean': round(float(np.mean(seed_praucs)), 4),
            'prauc_std': round(float(np.std(seed_praucs)), 4),
            'mcc_mean': round(float(np.mean(seed_mccs)), 4),
            'mcc_std': round(float(np.std(seed_mccs)), 4),
        }
        logger.info(f"==> Config {cfg_code} Final: F1 = {np.mean(seed_f1s):.4f} +/- {np.std(seed_f1s):.4f}, PR-AUC = {np.mean(seed_praucs):.4f} +/- {np.std(seed_praucs):.4f}")

    results_out['multi_seed_variance'] = multi_seed_results

    # Save to JSON
    out_file = OUTPUT_DIR / 'supplementary_experiments.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results_out, f, indent=2)
    logger.info(f"\nAll supplementary experiments completed successfully! Results saved to {out_file}")


if __name__ == '__main__':
    run_all_supplementary_experiments()

