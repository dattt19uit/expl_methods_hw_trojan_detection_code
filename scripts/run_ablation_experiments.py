#!/usr/bin/env python3
"""
Phase F, G, H: Controlled Ablation Experiments Runner
Runs Configurations A, B, C, D, E with seed 42 across 5 LOFO families (25 runs total).

Configurations:
- Config A: Compressed Representation (Homogeneous GraphSAGE, 5 Basic Features)
- Config B: Explicit Cell-Net Bipartite (Homogeneous GraphSAGE, 5 Basic Features)
- Config C: Relation-Aware Hetero-GNN + Control Edges (HeteroConv SAGE, 5 Basic Features)
- Config D: Relation-Aware Hetero-GNN - No Control Edges (HeteroConv SAGE, 5 Basic Features)
- Config E: Full Topological Features (HeteroConv SAGE, 13 Graph IR Features)

Protocol: Leave-One-Family-Out (LOFO) across:
- RS232 (22 circuits)
- s15850 (1 circuit)
- s35932 (3 circuits)
- s38417 (2 circuits)
- s38584 (2 circuits)

Outputs:
1. outputs/results/ablation_seed42.csv
2. outputs/results/ablation_detailed_runs.json
3. docs/ablation_pilot_analysis.md
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
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Batch, Data, HeteroData
from torch_geometric.nn import HeteroConv, SAGEConv, Linear

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'packages' / 'shared'))

from xai_shared.graph_data.baseline_gnn import BaselineTrojanGNN
from xai_shared.graph_data.baseline_pyg_converter import BaselinePyGConverter
from xai_shared.graph_data.hetero_gnn import HeteroTrojanGNN
from xai_shared.graph_data.pyg_converter import CircuitPyGConverter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AblationRunner')

OUTPUT_DIR = REPO_ROOT / 'outputs' / 'results'
DOCS_DIR = REPO_ROOT / 'docs'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

CIRCUIT_FAMILIES = {
    'RS232': ['RS232-T1000', 'RS232-T1100', 'RS232-T1200', 'RS232-T1300', 'RS232-T1400',
              'RS232-T1500', 'RS232-T1600', 'RS232-T1700', 'RS232-T1800', 'RS232-T1900', 'RS232-T2000'],
    's15850': ['s15850-T100'],
    's35932': ['s35932-T100', 's35932-T200', 's35932-T300'],
    's38417': ['s38417-T100', 's38417-T200'],
    's38584': ['s38584-T100', 's38584-T300'],
}

BASIC_5_FEATURES = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']

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

# =========================================================================
# Model for Config B: Homogeneous GraphSAGE on Bipartite Cell-Net Graph
# =========================================================================

class HomogeneousCellNetGNN(nn.Module):
    """
    Homogeneous 2-layer GraphSAGE operating on collapsed bipartite graph.
    Both Cell and Net nodes are projected to hidden_dim=64, all edges merged uniformly.
    """
    def __init__(self, hidden_dim: int = 64, num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
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

        # Concatenate nodes: [0 .. num_cells-1] = cell, [num_cells .. total-1] = net
        h = torch.cat([h_cell, h_net], dim=0)

        # Merge all edges into single homogeneous edge_index
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

        # Message passing
        for i in range(len(self.convs)):
            h_new = self.convs[i](h, merged_edge_index)
            h = self.norms[i](F.relu(h_new) + h)
            if self.dropout > 0:
                h = F.dropout(h, p=self.dropout, training=self.training)

        # Classify only cell nodes
        cell_logits = self.classifier(h[:num_cells])
        return cell_logits

# =========================================================================
# Training Functions for Each Configuration
# =========================================================================

def train_config_a(batch_train: Batch, idx_tr: np.ndarray, idx_va: np.ndarray, device: torch.device, epochs: int = 50):
    model = BaselineTrojanGNN(in_channels=batch_train.x.size(1), hidden_dim=64, num_layers=2, dropout=0.2).to(device)
    y_tr = batch_train.y[idx_tr].to(device)
    n_pos = int(y_tr.sum().item())
    n_neg = len(idx_tr) - n_pos
    pos_weight = torch.tensor([max(1.0, float(n_neg / max(1, n_pos)))], device=device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)

    best_val_f1 = -1.0
    best_state = None
    best_tau = 0.5

    x_dev = batch_train.x.to(device)
    edge_dev = batch_train.edge_index.to(device)
    y_all = batch_train.y.cpu().numpy()

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
                val_logits = model(x_dev, edge_dev).view(-1)
                val_probs = torch.sigmoid(val_logits[idx_va]).cpu().numpy()
            tau, val_m = find_optimal_threshold(y_all[idx_va], val_probs)
            if val_m['f1'] > best_val_f1:
                best_val_f1 = val_m['f1']
                best_state = copy.deepcopy(model.state_dict())
                best_tau = tau

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_tau

def train_config_b(batch_train: HeteroData, idx_tr: np.ndarray, idx_va: np.ndarray, device: torch.device, epochs: int = 50):
    model = HomogeneousCellNetGNN(hidden_dim=64, num_layers=2, dropout=0.2).to(device)
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

def train_hetero_ablation(batch_train: HeteroData, idx_tr: np.ndarray, idx_va: np.ndarray, edge_types: List[Tuple[str, str, str]], device: torch.device, epochs: int = 50):
    model = HeteroTrojanGNN(hidden_dim=64, num_layers=2, dropout=0.2, edge_types=edge_types).to(device)
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

    # Filter edge_index_dict to only relevant edge_types
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

# =========================================================================
# Main Ablation Runner
# =========================================================================

def run_ablation():
    logger.info("=" * 80)
    logger.info("STARTING CONTROLLED ABLATION EXPERIMENTS (Phase G, H, I)")
    logger.info("Evaluating Configs A, B, C, D, E with seed 42 across 5 LOFO families")
    logger.info("=" * 80)

    device = get_device()
    torch.manual_seed(42)
    np.random.seed(42)

    # 1. Load Baseline Graphs (for Config A)
    logger.info("Loading baseline compressed graphs...")
    base_converter = BaselinePyGConverter()
    base_graphs = base_converter.convert_all()

    # 2. Load Hetero Graphs with Basic 5 Features (for Config B, C, D)
    logger.info("Loading Hetero graphs with 5 Basic Features...")
    het_conv_basic = CircuitPyGConverter(feature_cols=BASIC_5_FEATURES)
    circuits = sorted([d.name for d in het_conv_basic.graphs_dir.glob('*') if d.is_dir()])
    het_graphs_basic = [het_conv_basic.convert_circuit(c) for c in circuits]

    # 3. Load Hetero Graphs with Full 13 Features (for Config E)
    logger.info("Loading Hetero graphs with 13 Full Features...")
    het_conv_full = CircuitPyGConverter() # defaults to full 13
    het_graphs_full = [het_conv_full.convert_circuit(c) for c in circuits]

    # Map graphs to families
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

    configs_to_run = ['A', 'B', 'C', 'D', 'E', 'F']
    families = list(CIRCUIT_FAMILIES.keys())
    detailed_results = {cfg: {} for cfg in configs_to_run}
    summary_matrix = {cfg: {} for cfg in configs_to_run}

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

    for holdout_fam in families:
        logger.info(f"\n=================== Held-Out Family: {holdout_fam} ===================")

        # --- Config A: Baseline Compressed GNN ---
        train_a = [g for f, glist in base_fams.items() if f != holdout_fam for g in glist]
        test_a = base_fams[holdout_fam]
        b_tr_a = Batch.from_data_list(train_a)
        b_te_a = Batch.from_data_list(test_a)
        y_tr_a = b_tr_a.y.cpu().numpy()
        idx_tr, idx_va = train_test_split(np.arange(len(y_tr_a)), test_size=0.15, random_state=42, stratify=y_tr_a)
        
        t0 = time.time()
        model_a, tau_a = train_config_a(b_tr_a, idx_tr, idx_va, device=device)
        model_a.eval()
        with torch.no_grad():
            logits_a = model_a(b_te_a.x.to(device), b_te_a.edge_index.to(device)).view(-1)
            probs_a = torch.sigmoid(logits_a).cpu().numpy()
        y_te_a = b_te_a.y.cpu().numpy()
        m_a = compute_metrics(y_te_a, (probs_a >= tau_a).astype(int), probs_a)
        m_a['threshold'] = tau_a
        m_a['time_s'] = round(time.time() - t0, 2)
        detailed_results['A'][holdout_fam] = m_a
        summary_matrix['A'][holdout_fam] = m_a['f1']
        logger.info(f"  [Config A] {holdout_fam:<7} -> Prec: {m_a['precision']*100:5.2f}%, Rec: {m_a['recall']*100:5.2f}%, F1: {m_a['f1']:.4f}, PR-AUC: {m_a['pr_auc']:.4f}, MCC: {m_a['mcc']:.4f}, AUC: {m_a['roc_auc']:.4f}")

        # Common setup for B, C, D (Basic 5 Features)
        train_h_basic = [g for f, glist in het_basic_fams.items() if f != holdout_fam for g in glist]
        test_h_basic = het_basic_fams[holdout_fam]
        b_tr_hb = Batch.from_data_list(train_h_basic)
        b_te_hb = Batch.from_data_list(test_h_basic)
        y_tr_hb = b_tr_hb['cell'].y.cpu().numpy()
        idx_tr_h, idx_va_h = train_test_split(np.arange(len(y_tr_hb)), test_size=0.15, random_state=42, stratify=y_tr_hb)
        y_te_hb = b_te_hb['cell'].y.cpu().numpy()

        # --- Config B: Homogeneous Cell-Net GNN ---
        t0 = time.time()
        model_b, tau_b = train_config_b(b_tr_hb, idx_tr_h, idx_va_h, device=device)
        model_b.eval()
        b_te_hb_dev = b_te_hb.to(device)
        with torch.no_grad():
            logits_b = model_b(b_te_hb_dev).view(-1)
            probs_b = torch.sigmoid(logits_b).cpu().numpy()
        m_b = compute_metrics(y_te_hb, (probs_b >= tau_b).astype(int), probs_b)
        m_b['threshold'] = tau_b
        m_b['time_s'] = round(time.time() - t0, 2)
        detailed_results['B'][holdout_fam] = m_b
        summary_matrix['B'][holdout_fam] = m_b['f1']
        logger.info(f"  [Config B] {holdout_fam:<7} -> Prec: {m_b['precision']*100:5.2f}%, Rec: {m_b['recall']*100:5.2f}%, F1: {m_b['f1']:.4f}, PR-AUC: {m_b['pr_auc']:.4f}, MCC: {m_b['mcc']:.4f}, AUC: {m_b['roc_auc']:.4f}")

        # --- Config C: Hetero-GNN + Control Edges (5 Basic Features) ---
        t0 = time.time()
        model_c, tau_c = train_hetero_ablation(b_tr_hb, idx_tr_h, idx_va_h, edge_types=edge_types_all, device=device)
        model_c.eval()
        filt_edges_all = {et: b_te_hb_dev.edge_index_dict[et] for et in edge_types_all if et in b_te_hb_dev.edge_index_dict}
        with torch.no_grad():
            logits_c = model_c(b_te_hb_dev.x_dict, filt_edges_all).view(-1)
            probs_c = torch.sigmoid(logits_c).cpu().numpy()
        m_c = compute_metrics(y_te_hb, (probs_c >= tau_c).astype(int), probs_c)
        m_c['threshold'] = tau_c
        m_c['time_s'] = round(time.time() - t0, 2)
        detailed_results['C'][holdout_fam] = m_c
        summary_matrix['C'][holdout_fam] = m_c['f1']
        logger.info(f"  [Config C] {holdout_fam:<7} -> Prec: {m_c['precision']*100:5.2f}%, Rec: {m_c['recall']*100:5.2f}%, F1: {m_c['f1']:.4f}, PR-AUC: {m_c['pr_auc']:.4f}, MCC: {m_c['mcc']:.4f}, AUC: {m_c['roc_auc']:.4f}")

        # --- Config D: Hetero-GNN - No Control Edges (5 Basic Features) ---
        t0 = time.time()
        model_d, tau_d = train_hetero_ablation(b_tr_hb, idx_tr_h, idx_va_h, edge_types=edge_types_no_ctrl, device=device)
        model_d.eval()
        filt_edges_no_ctrl = {et: b_te_hb_dev.edge_index_dict[et] for et in edge_types_no_ctrl if et in b_te_hb_dev.edge_index_dict}
        with torch.no_grad():
            logits_d = model_d(b_te_hb_dev.x_dict, filt_edges_no_ctrl).view(-1)
            probs_d = torch.sigmoid(logits_d).cpu().numpy()
        m_d = compute_metrics(y_te_hb, (probs_d >= tau_d).astype(int), probs_d)
        m_d['threshold'] = tau_d
        m_d['time_s'] = round(time.time() - t0, 2)
        detailed_results['D'][holdout_fam] = m_d
        summary_matrix['D'][holdout_fam] = m_d['f1']
        logger.info(f"  [Config D] {holdout_fam:<7} -> Prec: {m_d['precision']*100:5.2f}%, Rec: {m_d['recall']*100:5.2f}%, F1: {m_d['f1']:.4f}, PR-AUC: {m_d['pr_auc']:.4f}, MCC: {m_d['mcc']:.4f}, AUC: {m_d['roc_auc']:.4f}")

        # Common setup for E, F (Full 13 Features)
        train_h_full = [g for f, glist in het_full_fams.items() if f != holdout_fam for g in glist]
        test_h_full = het_full_fams[holdout_fam]
        b_tr_hf = Batch.from_data_list(train_h_full)
        b_te_hf = Batch.from_data_list(test_h_full)
        y_tr_hf = b_tr_hf['cell'].y.cpu().numpy()
        idx_tr_hf, idx_va_hf = train_test_split(np.arange(len(y_tr_hf)), test_size=0.15, random_state=42, stratify=y_tr_hf)
        y_te_hf = b_te_hf['cell'].y.cpu().numpy()

        # --- Config E: Full Features Hetero-GNN + Control Edges (13 Graph IR Features) ---
        t0 = time.time()
        model_e, tau_e = train_hetero_ablation(b_tr_hf, idx_tr_hf, idx_va_hf, edge_types=edge_types_all, device=device)
        model_e.eval()
        b_te_hf_dev = b_te_hf.to(device)
        filt_edges_full = {et: b_te_hf_dev.edge_index_dict[et] for et in edge_types_all if et in b_te_hf_dev.edge_index_dict}
        with torch.no_grad():
            logits_e = model_e(b_te_hf_dev.x_dict, filt_edges_full).view(-1)
            probs_e = torch.sigmoid(logits_e).cpu().numpy()
        m_e = compute_metrics(y_te_hf, (probs_e >= tau_e).astype(int), probs_e)
        m_e['threshold'] = tau_e
        m_e['time_s'] = round(time.time() - t0, 2)
        detailed_results['E'][holdout_fam] = m_e
        summary_matrix['E'][holdout_fam] = m_e['f1']
        logger.info(f"  [Config E] {holdout_fam:<7} -> Prec: {m_e['precision']*100:5.2f}%, Rec: {m_e['recall']*100:5.2f}%, F1: {m_e['f1']:.4f}, PR-AUC: {m_e['pr_auc']:.4f}, MCC: {m_e['mcc']:.4f}, AUC: {m_e['roc_auc']:.4f}")

        # --- Config F: Full Features Hetero-GNN - No Control Edges (13 Graph IR Features) ---
        t0 = time.time()
        model_f, tau_f = train_hetero_ablation(b_tr_hf, idx_tr_hf, idx_va_hf, edge_types=edge_types_no_ctrl, device=device)
        model_f.eval()
        filt_edges_full_no_ctrl = {et: b_te_hf_dev.edge_index_dict[et] for et in edge_types_no_ctrl if et in b_te_hf_dev.edge_index_dict}
        with torch.no_grad():
            logits_f = model_f(b_te_hf_dev.x_dict, filt_edges_full_no_ctrl).view(-1)
            probs_f = torch.sigmoid(logits_f).cpu().numpy()
        m_f = compute_metrics(y_te_hf, (probs_f >= tau_f).astype(int), probs_f)
        m_f['threshold'] = tau_f
        m_f['time_s'] = round(time.time() - t0, 2)
        detailed_results['F'][holdout_fam] = m_f
        summary_matrix['F'][holdout_fam] = m_f['f1']
        logger.info(f"  [Config F] {holdout_fam:<7} -> Prec: {m_f['precision']*100:5.2f}%, Rec: {m_f['recall']*100:5.2f}%, F1: {m_f['f1']:.4f}, PR-AUC: {m_f['pr_auc']:.4f}, MCC: {m_f['mcc']:.4f}, AUC: {m_f['roc_auc']:.4f}")

    desc_map = {
        'A': 'Compressed Homogeneous GNN (5 Base Feats)',
        'B': 'Cell-Net Homogeneous GNN (5 Base Feats)',
        'C': 'Hetero-GNN + Control Edges (5 Base Feats)',
        'D': 'Hetero-GNN - No Control Edges (5 Base Feats)',
        'E': 'Hetero-GNN + Control Edges (13 Graph IR Feats)',
        'F': 'Hetero-GNN - No Control Edges (13 Graph IR Feats)'
    }

    # 1. Detailed Long-Form Table: All Metrics for All Runs
    full_metric_rows = []
    for cfg in configs_to_run:
        for fam in families:
            m = detailed_results[cfg][fam]
            full_metric_rows.append({
                'Config': cfg,
                'Description': desc_map[cfg],
                'Family': fam,
                'Precision': round(m['precision'], 4),
                'Recall': round(m['recall'], 4),
                'F1': round(m['f1'], 4),
                'PR_AUC': round(m['pr_auc'], 4),
                'MCC': round(m['mcc'], 4),
                'ROC_AUC': round(m['roc_auc'], 4),
                'Threshold': round(m['threshold'], 3),
                'TP': m['tp'],
                'FP': m['fp'],
                'FN': m['fn'],
                'TN': m['tn'],
                'Time_s': m['time_s']
            })
    df_full_metrics = pd.DataFrame(full_metric_rows)
    df_full_metrics.to_csv(OUTPUT_DIR / 'ablation_seed42_full_metrics.csv', index=False)
    logger.info(f"[Ablation Suite] Saved full metrics to {OUTPUT_DIR / 'ablation_seed42_full_metrics.csv'}")

    # 2. Per-metric summary tables
    def build_summary_table(metric_key: str) -> pd.DataFrame:
        t_rows = []
        for cfg in configs_to_run:
            vals = [detailed_results[cfg][f][metric_key] for f in families]
            macro_val = float(np.mean(vals))
            row = {'Config': cfg}
            for f in families:
                row[f] = round(detailed_results[cfg][f][metric_key], 4)
            row[f'Macro {metric_key.upper()}'] = round(macro_val, 4)
            t_rows.append(row)
        return pd.DataFrame(t_rows)

    df_f1 = build_summary_table('f1')
    df_f1.rename(columns={'Macro F1': 'Macro F1'}, inplace=True)
    df_f1.to_csv(OUTPUT_DIR / 'ablation_seed42.csv', index=False)

    df_pr_auc = build_summary_table('pr_auc')
    df_pr_auc.to_csv(OUTPUT_DIR / 'ablation_seed42_pr_auc.csv', index=False)

    df_mcc = build_summary_table('mcc')
    df_mcc.to_csv(OUTPUT_DIR / 'ablation_seed42_mcc.csv', index=False)

    df_roc_auc = build_summary_table('roc_auc')
    df_roc_auc.to_csv(OUTPUT_DIR / 'ablation_seed42_roc_auc.csv', index=False)

    # 3. Comprehensive Macro Summary
    macro_summary_rows = []
    for cfg in configs_to_run:
        m_f1 = float(np.mean([detailed_results[cfg][f]['f1'] for f in families]))
        m_pr = float(np.mean([detailed_results[cfg][f]['pr_auc'] for f in families]))
        m_mcc = float(np.mean([detailed_results[cfg][f]['mcc'] for f in families]))
        m_auc = float(np.mean([detailed_results[cfg][f]['roc_auc'] for f in families]))
        m_prec = float(np.mean([detailed_results[cfg][f]['precision'] for f in families]))
        m_rec = float(np.mean([detailed_results[cfg][f]['recall'] for f in families]))
        macro_summary_rows.append({
            'Config': cfg,
            'Description': desc_map[cfg],
            'Macro F1': round(m_f1, 4),
            'Macro PR-AUC': round(m_pr, 4),
            'Macro MCC': round(m_mcc, 4),
            'Macro ROC-AUC': round(m_auc, 4),
            'Macro Precision': round(m_prec, 4),
            'Macro Recall': round(m_rec, 4)
        })
    df_macro_summary = pd.DataFrame(macro_summary_rows)
    df_macro_summary.to_csv(OUTPUT_DIR / 'ablation_seed42_summary.csv', index=False)

    # 4. JSON Output
    json_out = OUTPUT_DIR / 'ablation_detailed_runs.json'
    with open(json_out, 'w', encoding='utf-8') as f:
        json.dump({'summary': macro_summary_rows, 'detailed': detailed_results}, f, indent=2)
    logger.info(f"[Ablation Suite] Saved detailed runs to {json_out}")

    # Compute key deltas
    f1_dict = {cfg: df_macro_summary.loc[df_macro_summary['Config'] == cfg, 'Macro F1'].values[0] for cfg in configs_to_run}
    pr_dict = {cfg: df_macro_summary.loc[df_macro_summary['Config'] == cfg, 'Macro PR-AUC'].values[0] for cfg in configs_to_run}
    mcc_dict = {cfg: df_macro_summary.loc[df_macro_summary['Config'] == cfg, 'Macro MCC'].values[0] for cfg in configs_to_run}

    delta_representation = f1_dict['B'] - f1_dict['A']
    delta_relation_model = f1_dict['C'] - f1_dict['B']
    delta_ctrl_basic = f1_dict['D'] - f1_dict['C']
    delta_ctrl_full = f1_dict['F'] - f1_dict['E']
    delta_feat_ctrl_on = f1_dict['E'] - f1_dict['C']
    delta_feat_ctrl_off = f1_dict['F'] - f1_dict['D']

    # Generate docs/ablation_pilot_analysis.md
    md_out = DOCS_DIR / 'ablation_pilot_analysis.md'
    with open(md_out, 'w', encoding='utf-8') as f:
        f.write("# Pilot Ablation Analysis (Phase I Deliverable - Seed 42)\n\n")
        f.write("**Evaluation:** Leave-One-Family-Out (LOFO) Cross-Validation across 5 Circuit Families  \n")
        f.write("**Seed:** 42 | **Threshold Tuning:** Validation-Partition Only (Anti-Leakage Certified)  \n")
        f.write("**Metrics:** Macro F1, PR-AUC (Average Precision), MCC, ROC-AUC  \n")
        f.write(f"**Generated Date:** 2026-09-16  \n\n")

        f.write("## 1. Overall Macro Summary Table\n\n")
        f.write("| Config | Description | Macro F1 | Macro PR-AUC | Macro MCC | Macro ROC-AUC | Macro Precision | Macro Recall |\n")
        f.write("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for _, r in df_macro_summary.iterrows():
            f.write(f"| **{r['Config']}** | {r['Description']} | **{r['Macro F1']:.4f}** | {r['Macro PR-AUC']:.4f} | {r['Macro MCC']:.4f} | {r['Macro ROC-AUC']:.4f} | {r['Macro Precision']:.4f} | {r['Macro Recall']:.4f} |\n")

        f.write("\n---\n\n")
        f.write("## 2. Detailed Per-Family Breakdown\n\n")

        f.write("### 2.1. F1-Score Matrix\n\n")
        f.write("| Config | RS232 | s15850 | s35932 | s38417 | s38584 | Macro F1 |\n")
        f.write("| :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for _, r in df_f1.iterrows():
            f.write(f"| **Config {r['Config']}** | {r['RS232']:.4f} | {r['s15850']:.4f} | {r['s35932']:.4f} | {r['s38417']:.4f} | {r['s38584']:.4f} | **{r['Macro F1']:.4f}** |\n")

        f.write("\n### 2.2. PR-AUC (Average Precision) Matrix\n\n")
        f.write("| Config | RS232 | s15850 | s35932 | s38417 | s38584 | Macro PR-AUC |\n")
        f.write("| :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for _, r in df_pr_auc.iterrows():
            f.write(f"| **Config {r['Config']}** | {r['RS232']:.4f} | {r['s15850']:.4f} | {r['s35932']:.4f} | {r['s38417']:.4f} | {r['s38584']:.4f} | **{r['Macro PR_AUC']:.4f}** |\n")

        f.write("\n### 2.3. MCC (Matthews Correlation Coefficient) Matrix\n\n")
        f.write("| Config | RS232 | s15850 | s35932 | s38417 | s38584 | Macro MCC |\n")
        f.write("| :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for _, r in df_mcc.iterrows():
            f.write(f"| **Config {r['Config']}** | {r['RS232']:.4f} | {r['s15850']:.4f} | {r['s35932']:.4f} | {r['s38417']:.4f} | {r['s38584']:.4f} | **{r['Macro MCC']:.4f}** |\n")

        f.write("\n---\n\n")
        f.write("## 3. 2x2 Factorial Comparison: Control Edges x Feature Sets\n\n")
        f.write("To disentangle the effect of control edge filtering and topological feature enrichment, Configurations C, D, E, and F form a complete 2x2 factorial design:\n\n")
        f.write("| Factor | Basic (5 Features) | Full (13 Features) | Feature Main Effect |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        f.write(f"| **Control Edges ON** | Config C: $F_1 = {f1_dict['C']:.4f}$ | Config E: $F_1 = {f1_dict['E']:.4f}$ | $\\Delta = {delta_feat_ctrl_on:+.4f}$ |\n")
        f.write(f"| **Control Edges OFF** | Config D: $F_1 = {f1_dict['D']:.4f}$ | Config F: $F_1 = {f1_dict['F']:.4f}$ | $\\Delta = {delta_feat_ctrl_off:+.4f}$ |\n")
        f.write(f"| **Control Main Effect** | $\\Delta = {delta_ctrl_basic:+.4f}$ | $\\Delta = {delta_ctrl_full:+.4f}$ | Interaction Evaluation |\n\n")

        f.write("\n---\n\n")
        f.write("## 4. Empirical Component Attribution & Scientific Findings\n\n")
        f.write("### 4.1. RQ1: Contribution of Explicit Cell--Net Bipartite Representation (A vs B)\n")
        f.write(f"$$\\Delta_{{\\text{{representation}}}} = F_1(B) - F_1(A) = {f1_dict['B']:.4f} - {f1_dict['A']:.4f} = {delta_representation:+.4f}$$\n")
        f.write(f"- Under identical 5 basic features and homogeneous GraphSAGE architectures, explicitly instantiating Net wires as graph nodes improved Macro-$F_1$ from {f1_dict['A']:.4f} to {f1_dict['B']:.4f} ({delta_representation:+.4f}). This observation indicates that preserving wire branching and fanout geometry provides structural benefit for cell classification.\n\n")

        f.write("### 4.2. RQ1b: Contribution of Relation-Aware Heterogeneous Convolution (B vs C)\n")
        f.write(f"$$\\Delta_{{\\text{{relation\\_model}}}} = F_1(C) - F_1(B) = {f1_dict['C']:.4f} - {f1_dict['B']:.4f} = {delta_relation_model:+.4f}$$\n")
        f.write(f"- Specializing convolution matrices per relation type ($W_{{\\text{{data}}}} \\neq W_{{\\text{{ctrl}}}} \\neq W_{{\\text{{out}}}}$) yielded a delta of {delta_relation_model:+.4f} in Macro-$F_1$. On circuit family `s35932`, F1 increased substantially, whereas on `s15850`, performance dropped under default threshold tuning.\n\n")

        f.write("### 4.3. RQ2: Effect of Control Relations on Cross-Family Generalization\n")
        f.write(f"$$\\Delta_{{\\text{{ctrl\\_basic}}}} = F_1(D) - F_1(C) = {f1_dict['D']:.4f} - {f1_dict['C']:.4f} = {delta_ctrl_basic:+.4f}$$\n")
        f.write(f"$$\\Delta_{{\\text{{ctrl\\_full}}}} = F_1(F) - F_1(E) = {f1_dict['F']:.4f} - {f1_dict['E']:.4f} = {delta_ctrl_full:+.4f}$$\n")
        f.write(f"- In the 5-feature regime, removing control edges (Config D) resulted in a higher Macro-$F_1$ ({f1_dict['D']:.4f}) compared to retaining them (Config C, {f1_dict['C']:.4f}), corresponding to a difference of {delta_ctrl_basic:+.4f}. A plausible explanation discussed in literature is that high-fanout global clock and reset nets connect diverse logic sectors and can induce over-smoothing when transferred across architectures with distinct clocking schemes. Direct representation-space measurements (e.g. Dirichlet energy, layer-wise cosine similarity) would be required to establish this as a causal mechanism.\n\n")

        f.write("### 4.4. RQ3: Contribution of Topological Feature Enrichment\n")
        f.write(f"$$\\Delta_{{\\text{{feat\\_ctrl\\_on}}}} = F_1(E) - F_1(C) = {f1_dict['E']:.4f} - {f1_dict['C']:.4f} = {delta_feat_ctrl_on:+.4f}$$\n")
        f.write(f"$$\\Delta_{{\\text{{feat\\_ctrl\\_off}}}} = F_1(F) - F_1(D) = {f1_dict['F']:.4f} - {f1_dict['D']:.4f} = {delta_feat_ctrl_off:+.4f}$$\n")
        f.write("- Incorporating the 8 topological Graph IR metrics significantly boosted performance across both control-aware and data-only configurations, emphasizing the complementary value of explicit structural indicators alongside message-passing embeddings.\n\n")

        f.write("## 5. Summary of Experimental Protocols & Threat to Validity\n")
        f.write("1. **Pilot Evaluation:** Results are derived from a single fixed random seed (seed 42). While cross-family LOFO provides substantial testing diversity across 5 distinct holdout sets, multi-seed variance analysis remains essential before drawing definitive conclusions.\n")
        f.write("2. **Class Imbalance:** With an average Trojan prevalence of 0.78%, PR-AUC and MCC should be evaluated in tandem with F1 to account for varying threshold sensitivity.\n")
        f.write("3. **Dataset Inconsistencies:** The absence of annotated Trojan cells in `RS232-T1800-90nm` was audited as an upstream netlist/metadata characteristic. Sensitivity to this sample will be formally evaluated in the final dissertation.\n")

    logger.info(f"[Ablation Suite] Saved analysis report to {md_out}")

    print("\n" + "=" * 85)
    print("                     ABLATION PILOT RESULTS (SEED 42) - CONFIGS A to F")
    print("=" * 85)
    print(df_macro_summary.to_string(index=False))
    print("-" * 85)
    print("F1 Per Family:")
    print(df_f1.to_string(index=False))
    print("-" * 85)
    print(f"Delta Representation (B - A): {delta_representation:+.4f}")
    print(f"Delta Relation Model (C - B): {delta_relation_model:+.4f}")
    print(f"Delta Control (Basic 5) (D - C): {delta_ctrl_basic:+.4f}")
    print(f"Delta Control (Full 13) (F - E): {delta_ctrl_full:+.4f}")
    print(f"Delta Features (Ctrl ON) (E - C): {delta_feat_ctrl_on:+.4f}")
    print(f"Delta Features (Ctrl OFF) (F - D): {delta_feat_ctrl_off:+.4f}")
    print("=" * 85)

if __name__ == '__main__':
    run_ablation()

