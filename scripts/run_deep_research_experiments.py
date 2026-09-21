#!/usr/bin/env python3
"""
Deep Research Supplementary Experiments:
1. Parameter-Matched Architecture Control (Config B vs. Config B-Wide vs. Config C)
2. Learnable Control-Relation Gating (HeteroTrojanGNN-Gate)
3. Domain Identity & Circuit-Family Probing (FamilyProbeAcc)
4. Structural Noise & Netlist Perturbation Robustness (Edge drop, Net mask, Relation noise)
5. Dirichlet Energy on Constant Dataflow Reference Operator (G_data)
"""

import copy
import json
import logging
import math
import os
from pathlib import Path
import random
import sys
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Batch, HeteroData
from torch_geometric.nn import HeteroConv, Linear, SAGEConv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'packages' / 'shared'))

from xai_shared.graph_data.hetero_gnn import HeteroTrojanGNN
from xai_shared.graph_data.pyg_converter import CircuitPyGConverter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DeepResearchExperiments')

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


# =========================================================================
# Model Architectures
# =========================================================================

class HomogeneousCellNetGNN(nn.Module):
    """Homogeneous Bipartite GraphSAGE with configurable hidden dimension."""
    def __init__(self, cell_in_dim: int = 34, net_in_dim: int = 20, hidden_dim: int = 64, num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.num_layers = num_layers
        self.hidden_dim = hidden_dim
        self.cell_in = Linear(cell_in_dim, hidden_dim)
        self.net_in = Linear(net_in_dim, hidden_dim)
        self.convs = nn.ModuleList([SAGEConv(hidden_dim, hidden_dim) for _ in range(num_layers)])
        self.norms = nn.ModuleList([nn.LayerNorm(hidden_dim) for _ in range(num_layers)])
        self.dropout = dropout
        self.classifier = nn.Sequential(
            Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            Linear(hidden_dim // 2, 1)
        )

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

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


class HeteroTrojanGNNGate(nn.Module):
    """
    Heterogeneous GNN with Learnable Control-Relation Gating.
    Computes relation-specific SAGE convolutions and applies a learnable
    soft gate g_r = sigmoid(theta_r) to each relation before aggregation:
    m_v = sum_{r} g_r * SAGE_r(h_u, r)
    """
    def __init__(
        self,
        cell_in_dim: int = 34,
        net_in_dim: int = 20,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        edge_types: Optional[List[Tuple[str, str, str]]] = None,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout

        self.cell_in = Linear(cell_in_dim, hidden_dim)
        self.net_in = Linear(net_in_dim, hidden_dim)

        if edge_types is None:
            edge_types = EDGE_TYPES_ALL
        self.edge_types = edge_types

        # Per-relation SAGEConv modules
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()

        for _ in range(num_layers):
            conv_dict = nn.ModuleDict()
            for src, rel, dst in edge_types:
                rel_key = f"{src}__{rel}__{dst}"
                conv_dict[rel_key] = SAGEConv((hidden_dim, hidden_dim), hidden_dim)
            self.convs.append(conv_dict)
            self.norms.append(nn.ModuleDict({
                'cell': nn.LayerNorm(hidden_dim),
                'net': nn.LayerNorm(hidden_dim),
            }))

        # Learnable relation gates (one scalar theta_r per relation, shared across layers)
        # Initialized to 0.0 so sigmoid(theta_r) = 0.5 initially
        self.relation_thetas = nn.ParameterDict({
            f"{src}__{rel}__{dst}": nn.Parameter(torch.zeros(1))
            for src, rel, dst in edge_types
        })

        self.classifier = nn.Sequential(
            Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            Linear(hidden_dim // 2, 1),
        )

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_learned_gates(self) -> Dict[str, float]:
        """Returns the current sigmoid gating weights g_r in [0, 1]."""
        with torch.no_grad():
            return {
                rel_key: float(torch.sigmoid(theta).item())
                for rel_key, theta in self.relation_thetas.items()
            }

    def forward(
        self,
        x_dict: Dict[str, torch.Tensor],
        edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor],
    ) -> torch.Tensor:
        h_dict = {
            'cell': F.relu(self.cell_in(x_dict['cell'])),
            'net': F.relu(self.net_in(x_dict['net'])),
        }

        for l in range(self.num_layers):
            conv_dict = self.convs[l]
            out_cell_msgs = []
            out_net_msgs = []

            for src, rel, dst in self.edge_types:
                et = (src, rel, dst)
                if et not in edge_index_dict:
                    continue
                edge_index = edge_index_dict[et]
                rel_key = f"{src}__{rel}__{dst}"
                conv_module = conv_dict[rel_key]
                gate_weight = torch.sigmoid(self.relation_thetas[rel_key])

                msg = conv_module((h_dict[src], h_dict[dst]), edge_index)
                gated_msg = gate_weight * msg

                if dst == 'cell':
                    out_cell_msgs.append(gated_msg)
                else:
                    out_net_msgs.append(gated_msg)

            h_cell_new = sum(out_cell_msgs) if out_cell_msgs else h_dict['cell']
            h_net_new = sum(out_net_msgs) if out_net_msgs else h_dict['net']

            h_dict = {
                'cell': self.norms[l]['cell'](F.relu(h_cell_new) + h_dict['cell']),
                'net': self.norms[l]['net'](F.relu(h_net_new) + h_dict['net']),
            }
            if self.dropout > 0:
                h_dict = {k: F.dropout(v, p=self.dropout, training=self.training) for k, v in h_dict.items()}

        return self.classifier(h_dict['cell'])


# =========================================================================
# Training and Evaluation Helpers
# =========================================================================

def train_homogeneous_model(
    batch_train: HeteroData,
    idx_tr: np.ndarray,
    idx_va: np.ndarray,
    hidden_dim: int,
    device: torch.device,
    epochs: int = 50,
    seed: int = 42
):
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = HomogeneousCellNetGNN(hidden_dim=hidden_dim, num_layers=2, dropout=0.2).to(device)
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


def train_gated_hetero_model(
    batch_train: HeteroData,
    idx_tr: np.ndarray,
    idx_va: np.ndarray,
    device: torch.device,
    epochs: int = 50,
    seed: int = 42
):
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = HeteroTrojanGNNGate(hidden_dim=64, num_layers=2, dropout=0.2, edge_types=EDGE_TYPES_ALL).to(device)
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
        logits = model(batch_train.x_dict, batch_train.edge_index_dict).view(-1)
        loss = criterion(logits[idx_tr], y_tr)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
            model.eval()
            with torch.no_grad():
                val_logits = model(batch_train.x_dict, batch_train.edge_index_dict).view(-1)
                val_probs = torch.sigmoid(val_logits[idx_va]).cpu().numpy()
            tau, val_m = find_optimal_threshold(y_all[idx_va], val_probs)
            if val_m['f1'] > best_val_f1:
                best_val_f1 = val_m['f1']
                best_state = copy.deepcopy(model.state_dict())
                best_tau = tau

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_tau


def train_hetero_model(
    batch_train: HeteroData,
    idx_tr: np.ndarray,
    idx_va: np.ndarray,
    edge_types: List[Tuple[str, str, str]],
    device: torch.device,
    epochs: int = 50,
    seed: int = 42
):
    torch.manual_seed(seed)
    np.random.seed(seed)
    batch_train = batch_train.to(device)
    sub_edges = {et: batch_train.edge_index_dict[et] for et in edge_types if et in batch_train.edge_index_dict}

    model = HeteroTrojanGNN(hidden_dim=64, num_layers=2, dropout=0.2, edge_types=edge_types).to(device)
    # Dummy forward pass to initialize lazy linear layers
    _ = model(batch_train.x_dict, sub_edges)

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
        logits = model(batch_train.x_dict, sub_edges).view(-1)
        loss = criterion(logits[idx_tr], y_tr)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
            model.eval()
            with torch.no_grad():
                val_logits = model(batch_train.x_dict, sub_edges).view(-1)
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
# Experiment 1: Parameter-Matched Architecture Control
# =========================================================================

def run_experiment_1_parameter_matched(het_graphs: List[HeteroData], device: torch.device) -> Dict:
    logger.info("=== Running Experiment 1: Parameter-Matched Architecture Control ===")
    
    model_b_std = HomogeneousCellNetGNN(cell_in_dim=34, net_in_dim=20, hidden_dim=64, num_layers=2)
    model_b_wide = HomogeneousCellNetGNN(cell_in_dim=34, net_in_dim=20, hidden_dim=160, num_layers=2)
    model_c_hetero = HeteroTrojanGNN(hidden_dim=64, num_layers=2, edge_types=EDGE_TYPES_ALL)
    # Initialize lazy linear modules in HeteroTrojanGNN with dummy pass
    dummy_x = {'cell': torch.zeros(1, 34), 'net': torch.zeros(1, 20)}
    dummy_edges = {et: torch.zeros((2, 0), dtype=torch.long) for et in EDGE_TYPES_ALL}
    model_c_hetero(dummy_x, dummy_edges)

    params_b_std = model_b_std.count_parameters()
    params_b_wide = model_b_wide.count_parameters()
    params_c = sum(p.numel() for p in model_c_hetero.parameters() if p.requires_grad)

    logger.info(f"Parameter counts: Config B (d=64) = {params_b_std:,} | Config B-Wide (d=160) = {params_b_wide:,} | Config C (HeteroConv) = {params_c:,}")

    results_b_wide = {}
    f1_list_b_wide = []

    # Map graphs to families
    fam_graphs = {fam: [] for fam in CIRCUIT_FAMILIES}
    for g in het_graphs:
        cname = g.circuit_name
        for fam, pats in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in pats):
                fam_graphs[fam].append(g)
                break

    for held_out_fam in CIRCUIT_FAMILIES:
        train_list = []
        for fam, glist in fam_graphs.items():
            if fam != held_out_fam:
                train_list.extend(glist)
        test_list = fam_graphs[held_out_fam]

        batch_train = Batch.from_data_list(train_list)
        batch_test = Batch.from_data_list(test_list)

        n_cells = batch_train['cell'].x.size(0)
        y_train = batch_train['cell'].y.numpy()
        idx_tr, idx_va = train_test_split(np.arange(n_cells), test_size=0.2, random_state=42, stratify=y_train)

        model, tau = train_homogeneous_model(batch_train, idx_tr, idx_va, hidden_dim=160, device=device, epochs=50, seed=42)

        model.eval()
        batch_test = batch_test.to(device)
        with torch.no_grad():
            test_logits = model(batch_test).view(-1)
            test_probs = torch.sigmoid(test_logits).cpu().numpy()

        y_test = batch_test['cell'].y.cpu().numpy()
        preds = (test_probs >= tau).astype(int)
        m = compute_metrics(y_test, preds, test_probs)
        results_b_wide[held_out_fam] = m
        f1_list_b_wide.append(m['f1'])
        logger.info(f"  [B-Wide LOFO -> {held_out_fam}]: F1 = {m['f1']:.4f}, PR-AUC = {m['pr_auc']:.4f}, MCC = {m['mcc']:.4f}")

    macro_f1_b_wide = float(np.mean(f1_list_b_wide))
    logger.info(f"==> Config B-Wide Macro-F1: {macro_f1_b_wide:.4f} (vs Config B = 0.2151, Config C = 0.3670)")

    return {
        'parameter_counts': {
            'Config_B_Standard_d64': params_b_std,
            'Config_B_Wide_d160': params_b_wide,
            'Config_C_HeteroConv_d64': params_c,
        },
        'per_family': results_b_wide,
        'macro_f1_b_wide': macro_f1_b_wide,
        'macro_f1_b_standard': 0.2151,
        'macro_f1_c_hetero': 0.3670,
    }


# =========================================================================
# Experiment 2: Learnable Control-Relation Gating
# =========================================================================

def run_experiment_2_learnable_control_gating(het_graphs: List[HeteroData], device: torch.device) -> Dict:
    logger.info("=== Running Experiment 2: Learnable Control-Relation Gating (HeteroTrojanGNN-Gate) ===")
    
    fam_graphs = {fam: [] for fam in CIRCUIT_FAMILIES}
    for g in het_graphs:
        cname = g.circuit_name
        for fam, pats in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in pats):
                fam_graphs[fam].append(g)
                break

    results_gate = {}
    f1_list_gate = []
    learned_gates_per_fold = {}

    for held_out_fam in CIRCUIT_FAMILIES:
        train_list = []
        for fam, glist in fam_graphs.items():
            if fam != held_out_fam:
                train_list.extend(glist)
        test_list = fam_graphs[held_out_fam]

        batch_train = Batch.from_data_list(train_list)
        batch_test = Batch.from_data_list(test_list)

        n_cells = batch_train['cell'].x.size(0)
        y_train = batch_train['cell'].y.numpy()
        idx_tr, idx_va = train_test_split(np.arange(n_cells), test_size=0.2, random_state=42, stratify=y_train)

        model, tau = train_gated_hetero_model(batch_train, idx_tr, idx_va, device=device, epochs=50, seed=42)

        model.eval()
        batch_test = batch_test.to(device)
        with torch.no_grad():
            test_logits = model(batch_test.x_dict, batch_test.edge_index_dict).view(-1)
            test_probs = torch.sigmoid(test_logits).cpu().numpy()

        y_test = batch_test['cell'].y.cpu().numpy()
        preds = (test_probs >= tau).astype(int)
        m = compute_metrics(y_test, preds, test_probs)
        results_gate[held_out_fam] = m
        f1_list_gate.append(m['f1'])

        gates = model.get_learned_gates()
        learned_gates_per_fold[held_out_fam] = gates
        logger.info(f"  [Gated LOFO -> {held_out_fam}]: F1 = {m['f1']:.4f}, Control Gate = {gates.get('net__control_input__cell', 0.0):.4f}, Data Gate = {gates.get('net__data_input__cell', 0.0):.4f}")

    macro_f1_gate = float(np.mean(f1_list_gate))
    
    # Average gating values across all folds
    avg_gates = {}
    for k in learned_gates_per_fold[list(learned_gates_per_fold.keys())[0]]:
        avg_gates[k] = float(np.mean([learned_gates_per_fold[f][k] for f in CIRCUIT_FAMILIES]))

    logger.info(f"==> HeteroTrojanGNN-Gate Macro-F1: {macro_f1_gate:.4f} (vs Control OFF = 0.5239, Control ON = 0.4556)")
    logger.info(f"==> Average Learned Gates: {avg_gates}")

    return {
        'macro_f1_gated': macro_f1_gate,
        'macro_f1_control_off': 0.5239,
        'macro_f1_control_on': 0.4556,
        'average_learned_gates': avg_gates,
        'learned_gates_per_fold': learned_gates_per_fold,
        'per_family': results_gate,
    }


# =========================================================================
# Experiment 3: Circuit-Family Probing (Domain Identity)
# =========================================================================

def run_experiment_3_family_probing(het_graphs_basic: List[HeteroData], het_graphs_full: List[HeteroData], device: torch.device) -> Dict:
    logger.info("=== Running Experiment 3: Circuit-Family Probing (Domain Identity Analysis) ===")
    
    # Extract cell features and family labels
    fam_keys = list(CIRCUIT_FAMILIES.keys())
    fam_to_id = {fam: i for i, fam in enumerate(fam_keys)}

    x_5_list = []
    x_13_list = []
    y_fam_list = []

    for g_b, g_f in zip(het_graphs_basic, het_graphs_full):
        cname = g_b.circuit_name
        fam_idx = -1
        for fam, pats in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in pats):
                fam_idx = fam_to_id[fam]
                break
        
        # 5 features: LGFi, ffi, ffo, PI, PO
        x_5 = g_b['cell'].x[:, 21:26].numpy()
        # 13 topological metrics
        x_13 = g_f['cell'].x[:, 21:34].numpy()

        n_nodes = x_5.shape[0]
        x_5_list.append(x_5)
        x_13_list.append(x_13)
        y_fam_list.append(np.full(n_nodes, fam_idx, dtype=int))

    X_5 = np.vstack(x_5_list)
    X_13 = np.vstack(x_13_list)
    Y_fam = np.concatenate(y_fam_list)

    # Train probe classifiers
    idx_tr, idx_te = train_test_split(np.arange(len(Y_fam)), test_size=0.3, random_state=42, stratify=Y_fam)

    # Probe on 5 Hasegawa features
    clf_5 = LogisticRegression(max_iter=500, class_weight='balanced', random_state=42)
    clf_5.fit(X_5[idx_tr], Y_fam[idx_tr])
    y_pred_5 = clf_5.predict(X_5[idx_te])
    acc_5 = float(accuracy_score(Y_fam[idx_te], y_pred_5))
    f1_5 = float(f1_score(Y_fam[idx_te], y_pred_5, average='macro'))

    # Probe on 13 Topological features
    clf_13 = LogisticRegression(max_iter=500, class_weight='balanced', random_state=42)
    clf_13.fit(X_13[idx_tr], Y_fam[idx_tr])
    y_pred_13 = clf_13.predict(X_13[idx_te])
    acc_13 = float(accuracy_score(Y_fam[idx_te], y_pred_13))
    f1_13 = float(f1_score(Y_fam[idx_te], y_pred_13, average='macro'))

    logger.info(f"  [Family Probe] 5 Basic Features: Accuracy = {acc_5*100:.2f}%, Macro-F1 = {f1_5:.4f}")
    logger.info(f"  [Family Probe] 13 Graph IR Features: Accuracy = {acc_13*100:.2f}%, Macro-F1 = {f1_13:.4f}")

    return {
        'probe_5_basic_features': {'accuracy': acc_5, 'macro_f1': f1_5},
        'probe_13_topological_features': {'accuracy': acc_13, 'macro_f1': f1_13},
        'num_evaluated_cells': int(len(Y_fam)),
        'num_classes': len(fam_keys),
    }


# =========================================================================
# Experiment 4: Structural Noise & Netlist Perturbation Robustness
# =========================================================================

def run_experiment_4_noise_robustness(het_graphs: List[HeteroData], device: torch.device) -> Dict:
    logger.info("=== Running Experiment 4: Structural Noise & Netlist Perturbation Robustness ===")
    
    # Train a reference Config F model on the first 4 families and test on RS232
    fam_graphs = {fam: [] for fam in CIRCUIT_FAMILIES}
    for g in het_graphs:
        cname = g.circuit_name
        for fam, pats in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in pats):
                fam_graphs[fam].append(g)
                break

    train_list = fam_graphs['s15850'] + fam_graphs['s35932'] + fam_graphs['s38417'] + fam_graphs['s38584']
    test_list = fam_graphs['RS232']

    batch_train = Batch.from_data_list(train_list)
    batch_test_clean = Batch.from_data_list(test_list)

    n_cells = batch_train['cell'].x.size(0)
    y_train = batch_train['cell'].y.numpy()
    idx_tr, idx_va = train_test_split(np.arange(n_cells), test_size=0.2, random_state=42, stratify=y_train)

    # Train Config F (Control OFF)
    model, tau = train_hetero_model(batch_train, idx_tr, idx_va, EDGE_TYPES_NO_CTRL, device=device, epochs=50, seed=42)
    model.eval()

    # Clean evaluation
    batch_test_clean = batch_test_clean.to(device)
    with torch.no_grad():
        clean_logits = model(batch_test_clean.x_dict, {et: batch_test_clean.edge_index_dict[et] for et in EDGE_TYPES_NO_CTRL}).view(-1)
        clean_probs = torch.sigmoid(clean_logits).cpu().numpy()
    y_test = batch_test_clean['cell'].y.cpu().numpy()
    clean_metrics = compute_metrics(y_test, (clean_probs >= tau).astype(int), clean_probs)
    f1_clean = clean_metrics['f1']
    logger.info(f"  Clean Baseline (RS232 LOFO): F1 = {f1_clean:.4f}, PR-AUC = {clean_metrics['pr_auc']:.4f}")

    perturbation_results = {'clean': clean_metrics}

    # 1. Random Edge Drop (5%, 10%, 20%)
    for drop_rate in [0.05, 0.10, 0.20]:
        perturbed_edges = {}
        for et in EDGE_TYPES_NO_CTRL:
            e_idx = batch_test_clean.edge_index_dict[et]
            n_edges = e_idx.size(1)
            keep_mask = torch.rand(n_edges, device=device) >= drop_rate
            perturbed_edges[et] = e_idx[:, keep_mask]

        with torch.no_grad():
            p_logits = model(batch_test_clean.x_dict, perturbed_edges).view(-1)
            p_probs = torch.sigmoid(p_logits).cpu().numpy()
        m_pert = compute_metrics(y_test, (p_probs >= tau).astype(int), p_probs)
        retention = float(m_pert['f1'] / max(1e-6, f1_clean))
        m_pert['retention_rate'] = retention
        perturbation_results[f'edge_drop_{int(drop_rate*100)}pct'] = m_pert
        logger.info(f"  Edge Drop {int(drop_rate*100)}%: F1 = {m_pert['f1']:.4f} (Retention R(p) = {retention*100:.1f}%)")

    # 2. Net Node Feature Masking (5%, 10%)
    for mask_rate in [0.05, 0.10]:
        perturbed_x_dict = {
            'cell': batch_test_clean.x_dict['cell'].clone(),
            'net': batch_test_clean.x_dict['net'].clone(),
        }
        n_nets = perturbed_x_dict['net'].size(0)
        mask = torch.rand(n_nets, device=device) < mask_rate
        perturbed_x_dict['net'][mask] = 0.0

        with torch.no_grad():
            p_logits = model(perturbed_x_dict, {et: batch_test_clean.edge_index_dict[et] for et in EDGE_TYPES_NO_CTRL}).view(-1)
            p_probs = torch.sigmoid(p_logits).cpu().numpy()
        m_pert = compute_metrics(y_test, (p_probs >= tau).astype(int), p_probs)
        retention = float(m_pert['f1'] / max(1e-6, f1_clean))
        m_pert['retention_rate'] = retention
        perturbation_results[f'net_mask_{int(mask_rate*100)}pct'] = m_pert
        logger.info(f"  Net Mask {int(mask_rate*100)}%: F1 = {m_pert['f1']:.4f} (Retention R(p) = {retention*100:.1f}%)")

    return perturbation_results


# =========================================================================
# Experiment 5: Dirichlet Energy on Constant Dataflow Reference Graph (G_data)
# =========================================================================

def run_experiment_5_constant_operator_dirichlet(het_graphs: List[HeteroData], device: torch.device) -> Dict:
    logger.info("=== Running Experiment 5: Dirichlet Energy on Constant Dataflow Operator (G_data) ===")
    
    eval_circuits = [
        'RS232-T1000_90nm',
        's15850-T100_generic-180nm',
        's35932-T100_generic-180nm',
        's38417-T100_generic-180nm',
    ]

    target_graphs = [g for g in het_graphs if g.circuit_name in eval_circuits]

    train_graphs = [g for g in het_graphs if g.circuit_name not in eval_circuits]
    batch_train = Batch.from_data_list(train_graphs)
    n_cells = batch_train['cell'].x.size(0)
    y_train = batch_train['cell'].y.numpy()
    idx_tr, idx_va = train_test_split(np.arange(n_cells), test_size=0.2, random_state=42, stratify=y_train)

    logger.info("  Training Config C (Control ON)...")
    model_c, _ = train_hetero_model(batch_train, idx_tr, idx_va, EDGE_TYPES_ALL, device=device, epochs=30, seed=42)

    logger.info("  Training Config D (Control OFF)...")
    model_d, _ = train_hetero_model(batch_train, idx_tr, idx_va, EDGE_TYPES_NO_CTRL, device=device, epochs=30, seed=42)

    results_dirichlet = {}

    for g in target_graphs:
        cname = g.circuit_name
        g = g.to(device)

        edge_out = g.edge_index_dict.get(('cell', 'outputs', 'net'))
        edge_data_in = g.edge_index_dict.get(('net', 'data_input', 'cell'))

        if edge_out is not None and edge_data_in is not None:
            net_to_cell = {}
            for src_cell, dst_net in zip(edge_out[0].cpu().numpy(), edge_out[1].cpu().numpy()):
                net_to_cell.setdefault(int(dst_net), []).append(int(src_cell))
            
            dataflow_pairs = []
            for src_net, dst_cell in zip(edge_data_in[0].cpu().numpy(), edge_data_in[1].cpu().numpy()):
                if int(src_net) in net_to_cell:
                    for driving_cell in net_to_cell[int(src_net)]:
                        dataflow_pairs.append((driving_cell, int(dst_cell)))
            
            if dataflow_pairs:
                dataflow_edges = torch.tensor(dataflow_pairs, dtype=torch.long, device=device).t()
            else:
                dataflow_edges = torch.empty((2, 0), dtype=torch.long, device=device)
        else:
            dataflow_edges = torch.empty((2, 0), dtype=torch.long, device=device)

        def get_model_embeddings(model, edges):
            model.eval()
            with torch.no_grad():
                h_cell = F.relu(model.cell_in(g.x_dict['cell']))
                h_net = F.relu(model.net_in(g.x_dict['net']))
                h_dict = {'cell': h_cell, 'net': h_net}
                
                layer_embeds = [h_cell]
                for l in range(model.num_layers):
                    h_new = model.convs[l](h_dict, edges)
                    h_dict = {
                        k: model.norms[l][k](F.relu(h_new[k]) + h_dict[k])
                        for k in h_dict.keys()
                    }
                    layer_embeds.append(h_dict['cell'])
            return layer_embeds

        embeds_c = get_model_embeddings(model_c, {et: g.edge_index_dict[et] for et in EDGE_TYPES_ALL if et in g.edge_index_dict})
        embeds_d = get_model_embeddings(model_d, {et: g.edge_index_dict[et] for et in EDGE_TYPES_NO_CTRL if et in g.edge_index_dict})

        def compute_constant_operator_dirichlet(h_cell, edges):
            if edges.size(1) == 0:
                return 0.0
            u_idx = edges[0]
            v_idx = edges[1]
            diff = h_cell[u_idx] - h_cell[v_idx]
            sq_diff = (diff ** 2).sum(dim=-1).mean().item()
            h_var = (h_cell ** 2).sum(dim=-1).mean().item()
            return float(sq_diff / (2.0 * max(h_var, 1e-8)))

        circuit_metrics = {
            'num_dataflow_edges': int(dataflow_edges.size(1)),
            'Config_C_Control_ON': [
                {'layer': l, 'dirichlet_on_Gdata': compute_constant_operator_dirichlet(embeds_c[l], dataflow_edges)}
                for l in range(3)
            ],
            'Config_D_Control_OFF': [
                {'layer': l, 'dirichlet_on_Gdata': compute_constant_operator_dirichlet(embeds_d[l], dataflow_edges)}
                for l in range(3)
            ],
        }
        results_dirichlet[cname] = circuit_metrics
        logger.info(f"  [{cname}] L2 Dirichlet on G_data: Control ON = {circuit_metrics['Config_C_Control_ON'][2]['dirichlet_on_Gdata']:.4f} vs Control OFF = {circuit_metrics['Config_D_Control_OFF'][2]['dirichlet_on_Gdata']:.4f}")

    return results_dirichlet


# =========================================================================
# Main Runner
# =========================================================================

def main():
    device = get_device()
    logger.info(f"Starting Deep Research Supplementary Experiments on device: {device}")
    start_time = time.time()

    logger.info("Loading 30 circuit graphs...")
    het_conv_full = CircuitPyGConverter()
    circuits = sorted([d.name for d in het_conv_full.graphs_dir.glob('*') if d.is_dir()])
    het_graphs_full = [het_conv_full.convert_circuit(c) for c in circuits]

    het_conv_basic = CircuitPyGConverter(feature_cols=BASIC_5_FEATURES)
    het_graphs_basic = [het_conv_basic.convert_circuit(c) for c in circuits]

    output_data = {}

    # Run Experiments
    output_data['param_matched_control'] = run_experiment_1_parameter_matched(het_graphs_full, device)
    output_data['learnable_control_gating'] = run_experiment_2_learnable_control_gating(het_graphs_full, device)
    output_data['family_probe'] = run_experiment_3_family_probing(het_graphs_basic, het_graphs_full, device)
    output_data['noise_robustness'] = run_experiment_4_noise_robustness(het_graphs_full, device)
    output_data['dirichlet_constant_operator'] = run_experiment_5_constant_operator_dirichlet(het_graphs_full, device)

    elapsed = time.time() - start_time
    output_data['elapsed_seconds'] = elapsed
    logger.info(f"All 5 experiments successfully finished in {elapsed:.2f} seconds.")

    out_file = OUTPUT_DIR / 'deep_research_experiments.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    logger.info(f"Results saved to {out_file}")


if __name__ == '__main__':
    main()
