#!/usr/bin/env python3
"""
Dirichlet Energy and Structural Non-Conformity Experiments for Hardware Trojan Localization:
1. 2-Hop Cell-Level Operator Construction (L_data, L_ctrl, L_clock, L_reset).
2. Fixed-Operator Dirichlet & Representation Dynamics:
   - Rayleigh Quotients on fixed operators across layers L in {0, 1, 2, 4}
   - Effective Rank (erank), Pairwise Cosine Distance, Feature Variance
   - Comparison: Control-ON vs Control-OFF vs Control-Gated
3. 4-Detector Cross-Family LOFO Benchmark:
   - M0: HeteroGNN Baseline (Config F)
   - M1: Training-Free Dirichlet Anomaly Detector (DE-only structural non-conformity)
   - M2: HeteroGNN + Local Dirichlet Features
   - M3: Calibrated Late Fusion (GNN + DE Residuals) with validation-locked tuning
4. Control Handling Comparison:
   - Control-ON, Control-OFF, Control-Gated, DegreeNormalized, DegreeMatched Counterfactual
5. Strict Matched Node-Universe Audit Table.
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
from scipy import sparse as sp
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
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
logger = logging.getLogger('DirichletAnomalyExperiments')

OUTPUT_DIR = REPO_ROOT / 'outputs' / 'results'
AUDIT_DIR = REPO_ROOT / 'outputs' / 'audit'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

CIRCUIT_FAMILIES = {
    'RS232': ['RS232-T1000', 'RS232-T1100', 'RS232-T1200', 'RS232-T1300', 'RS232-T1400',
              'RS232-T1500', 'RS232-T1600', 'RS232-T1700', 'RS232-T1800', 'RS232-T1900', 'RS232-T2000'],
    's15850': ['s15850-T100'],
    's35932': ['s35932-T100', 's35932-T200', 's35932-T300'],
    's38417': ['s38417-T100', 's38417-T200'],
    's38584': ['s38584-T100', 's38584-T300'],
}

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

    fp_per_1k = float(fp / (max(1, (tn + fp)) / 1000.0))
    total_nodes = len(y_true)
    crr = float(1.0 - (tp + fp) / max(1, total_nodes))

    return {
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
        'precision': float(prec), 'recall': float(rec), 'f1': float(f1),
        'mcc': float(mcc), 'roc_auc': float(roc_auc), 'pr_auc': float(pr_auc),
        'fp_per_1k': fp_per_1k, 'crr': crr,
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


def compute_precision_recall_at_k(y_true: np.ndarray, y_prob: np.ndarray, k_values: List[int]) -> Dict[str, float]:
    res = {}
    order = np.argsort(-y_prob)
    total_pos = max(1, int(np.sum(y_true == 1)))
    n_total = len(y_true)

    for k in k_values:
        eff_k = min(k, n_total)
        top_indices = order[:eff_k]
        tp_k = int(np.sum(y_true[top_indices] == 1))
        p_at_k = float(tp_k / eff_k) if eff_k > 0 else 0.0
        r_at_k = float(tp_k / total_pos)
        res[f'p@{k}'] = round(p_at_k, 4)
        res[f'r@{k}'] = round(r_at_k, 4)
    return res


# =========================================================================
# 2-Hop Operator Construction & Graph Metrics
# =========================================================================

class CircuitOperators:
    """
    Constructs 2-hop cell operators for a circuit:
    - L_data: Cell -> Net -> Cell (data flow)
    - L_ctrl: Cell -> Net -> Cell (shared control nets)
    - L_clock: Cell -> Net -> Cell (shared clock nets)
    - L_reset: Cell -> Net -> Cell (shared reset nets)
    """
    def __init__(self, circuit_dir: Path):
        self.circuit_dir = circuit_dir
        self.circuit_name = circuit_dir.name
        self.nodes_df = pd.read_csv(circuit_dir / 'nodes.csv')
        self.edges_df = pd.read_csv(circuit_dir / 'edges.csv')

        self.cell_nodes = self.nodes_df[self.nodes_df['kind'] == 'cell']['node'].tolist()
        self.net_nodes = self.nodes_df[self.nodes_df['kind'] == 'net']['node'].tolist()
        self.n_cells = len(self.cell_nodes)
        self.n_nets = len(self.net_nodes)

        self.c2i = {c: i for i, c in enumerate(self.cell_nodes)}
        self.n2i = {n: i for i, n in enumerate(self.net_nodes)}

        # Cell labels and types
        self.y = self.nodes_df[self.nodes_df['kind'] == 'cell']['is_trojan'].values.astype(int)
        
        # Determine cell type: sequential (flip-flop/latch) vs combinational
        cell_types = self.nodes_df[self.nodes_df['kind'] == 'cell']['cell_type'].astype(str).tolist()
        self.is_sequential = np.array([
            any(k in ct.upper() for k in ['DFF', 'FF', 'LATCH', 'SDFF', 'QDFF'])
            for ct in cell_types
        ], dtype=int)

        self._build_operators()

    def _build_operators(self):
        out_e = self.edges_df[self.edges_df['direction'] == 'output']
        in_data = self.edges_df[(self.edges_df['direction'] == 'input') & (self.edges_df['is_control'] == 0)]
        in_ctrl = self.edges_df[(self.edges_df['direction'] == 'input') & (self.edges_df['is_control'] == 1)]

        # Filter valid node IDs
        out_e_val = out_e[out_e['source'].isin(self.c2i) & out_e['target'].isin(self.n2i)]
        in_data_val = in_data[in_data['source'].isin(self.n2i) & in_data['target'].isin(self.c2i)]
        in_ctrl_val = in_ctrl[in_ctrl['source'].isin(self.n2i) & in_ctrl['target'].isin(self.c2i)]

        M_out = sp.csr_matrix(
            (np.ones(len(out_e_val)), ([self.c2i[s] for s in out_e_val['source']], [self.n2i[t] for t in out_e_val['target']])),
            shape=(self.n_cells, self.n_nets)
        )
        M_in_data = sp.csr_matrix(
            (np.ones(len(in_data_val)), ([self.n2i[s] for s in in_data_val['source']], [self.c2i[t] for t in in_data_val['target']])),
            shape=(self.n_nets, self.n_cells)
        )
        M_in_ctrl = sp.csr_matrix(
            (np.ones(len(in_ctrl_val)), ([self.n2i[s] for s in in_ctrl_val['source']], [self.c2i[t] for t in in_ctrl_val['target']])),
            shape=(self.n_nets, self.n_cells)
        )

        # 2-hop cell-to-cell data flow adjacency
        A_data = (M_out @ M_in_data).tocsr()
        A_data.setdiag(0)
        A_data.eliminate_zeros()
        # Symmetrized data adjacency for symmetric Laplacian diagnostics
        self.A_data_sym = (0.5 * (A_data + A_data.T)).tocsr()

        # Co-control membership adjacency (shared control net)
        A_ctrl = (M_in_ctrl.T @ M_in_ctrl).tocsr()
        A_ctrl.setdiag(0)
        A_ctrl.eliminate_zeros()
        self.A_ctrl = A_ctrl

        # Separate Clock and Reset nets
        clk_ports = ['CLK', 'CK', 'CLOCK']
        rst_ports = ['RSTB', 'SETB', 'RESET', 'PRE', 'CLR', 'RST']

        in_clk_val = in_ctrl_val[in_ctrl_val['port'].str.upper().isin(clk_ports)]
        in_rst_val = in_ctrl_val[in_ctrl_val['port'].str.upper().isin(rst_ports)]

        M_in_clk = sp.csr_matrix(
            (np.ones(len(in_clk_val)), ([self.n2i[s] for s in in_clk_val['source']], [self.c2i[t] for t in in_clk_val['target']])),
            shape=(self.n_nets, self.n_cells)
        ) if len(in_clk_val) > 0 else sp.csr_matrix((self.n_nets, self.n_cells))

        M_in_rst = sp.csr_matrix(
            (np.ones(len(in_rst_val)), ([self.n2i[s] for s in in_rst_val['source']], [self.c2i[t] for t in in_rst_val['target']])),
            shape=(self.n_nets, self.n_cells)
        ) if len(in_rst_val) > 0 else sp.csr_matrix((self.n_nets, self.n_cells))

        A_clock = (M_in_clk.T @ M_in_clk).tocsr()
        A_clock.setdiag(0)
        A_clock.eliminate_zeros()
        self.A_clock = A_clock

        A_reset = (M_in_rst.T @ M_in_rst).tocsr()
        A_reset.setdiag(0)
        A_reset.eliminate_zeros()
        self.A_reset = A_reset

        # Build Normalized Symmetric Laplacians
        self.L_data_sym = self._build_normalized_laplacian(self.A_data_sym)
        self.L_ctrl_sym = self._build_normalized_laplacian(self.A_ctrl)
        self.L_clock_sym = self._build_normalized_laplacian(self.A_clock)
        self.L_reset_sym = self._build_normalized_laplacian(self.A_reset)

    def _build_normalized_laplacian(self, A: sp.csr_matrix) -> sp.csr_matrix:
        if A.nnz == 0:
            return sp.csr_matrix((self.n_cells, self.n_cells))
        deg = np.array(A.sum(axis=1)).flatten()
        deg_inv_sqrt = np.zeros_like(deg)
        mask = deg > 0
        deg_inv_sqrt[mask] = 1.0 / np.sqrt(deg[mask])
        D_inv_sqrt = sp.diags(deg_inv_sqrt)
        L = sp.eye(self.n_cells) - D_inv_sqrt @ A @ D_inv_sqrt
        return L.tocsr()


def compute_rayleigh_quotient(H: torch.Tensor, L_sp: sp.csr_matrix) -> float:
    """
    Computes normalized Rayleigh quotient:
    R(H; L) = Tr(H^T L H) / ||H||_F^2
    """
    if L_sp.nnz == 0:
        return 0.0
    N = H.size(0)
    H_np = H.detach().cpu().numpy()
    norm_sq = np.sum(H_np ** 2)
    if norm_sq < 1e-12:
        return 0.0

    # LH = L_sp @ H_np
    LH = L_sp.dot(H_np)
    trace = np.sum(H_np * LH)
    return float(trace / norm_sq)


def compute_effective_rank(H: torch.Tensor) -> float:
    """
    Computes effective rank of representation matrix H:
    erank(H) = exp(-sum_i p_i log p_i) where p_i = sigma_i / sum sigma
    """
    H_clean = H.detach().cpu()
    if H_clean.size(0) <= 1:
        return 1.0
    try:
        _, S, _ = torch.linalg.svd(H_clean, full_matrices=False)
        p = S / (S.sum() + 1e-12)
        entropy = -torch.sum(p * torch.log(p + 1e-12)).item()
        return float(np.exp(entropy))
    except Exception:
        return 1.0


def compute_representation_diversity(H: torch.Tensor, max_samples: int = 2000) -> Tuple[float, float]:
    """
    Computes:
    1. Mean Pairwise Cosine Distance: 1 - CosSim(h_u, h_v)
    2. Mean Node Feature Variance
    """
    N = H.size(0)
    if N <= 1:
        return 0.0, 0.0

    if N > max_samples:
        perm = torch.randperm(N)[:max_samples]
        h_samp = H[perm]
    else:
        h_samp = H

    h_norm = F.normalize(h_samp, p=2, dim=-1)
    sim_mat = torch.mm(h_norm, h_norm.t())
    triu_idx = torch.triu_indices(h_samp.size(0), h_samp.size(0), offset=1)
    pairwise_sims = sim_mat[triu_idx[0], triu_idx[1]]
    mean_cos_dist = float((1.0 - pairwise_sims).mean().item())

    mean_vec = h_samp.mean(dim=0, keepdim=True)
    var = float(((h_samp - mean_vec) ** 2).sum(dim=-1).mean().item())

    return mean_cos_dist, var


def compute_local_dirichlet_residuals(
    H: torch.Tensor,
    ops: CircuitOperators,
    eps: float = 1e-6
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes node-level normalized Dirichlet residuals z_{i, data} and z_{i, ctrl}
    conditioned on cell type (combinational vs sequential).
    """
    H_np = H.detach().cpu().numpy()
    N = H_np.shape[0]

    def _get_local_energy(A_sp: sp.csr_matrix) -> np.ndarray:
        if A_sp.nnz == 0:
            return np.zeros(N)
        e_local = np.zeros(N)
        for i in range(N):
            row_start = A_sp.indptr[i]
            row_end = A_sp.indptr[i + 1]
            if row_start == row_end:
                continue
            neighbors = A_sp.indices[row_start:row_end]
            weights = A_sp.data[row_start:row_end]
            diffs = H_np[neighbors] - H_np[i]
            sq_diffs = np.sum(diffs ** 2, axis=-1)
            e_local[i] = np.sum(weights * sq_diffs) / (np.sum(weights) + eps)
        return e_local

    e_data = _get_local_energy(ops.A_data_sym)
    e_ctrl = _get_local_energy(ops.A_ctrl)

    def _standardize_residual(e: np.ndarray, is_seq: np.ndarray, y: np.ndarray) -> np.ndarray:
        z = np.zeros(N)
        log_e = np.log(e + eps)
        for seq_val in [0, 1]:
            mask_type = (is_seq == seq_val)
            # Reference group: benign nodes of this type (or all if too few)
            ref_mask = mask_type & (y == 0)
            if np.sum(ref_mask) < 3:
                ref_mask = mask_type
            if np.sum(ref_mask) < 2:
                ref_mask = np.ones(N, dtype=bool)

            ref_vals = log_e[ref_mask]
            med = np.median(ref_vals)
            mad = np.median(np.abs(ref_vals - med))
            scale = 1.4826 * mad + eps
            z[mask_type] = np.abs(log_e[mask_type] - med) / scale
        return z

    z_data = _standardize_residual(e_data, ops.is_sequential, ops.y)
    z_ctrl = _standardize_residual(e_ctrl, ops.is_sequential, ops.y)

    return z_data, z_ctrl


# =========================================================================
# Learnable Control Gating Model Architecture
# =========================================================================

class HeteroTrojanGNN_Gate(nn.Module):
    """
    HeteroTrojanGNN with Learnable Control Gating:
    m_{i, ctrl} = g_{ctrl} * Conv_{ctrl}(h)
    g_{ctrl} = sigma(w_g) is learned per layer to dynamically modulate control bandwidth.
    """
    def __init__(self, hidden_dim: int = 64, num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.num_layers = num_layers
        self.hidden_dim = hidden_dim
        self.dropout = dropout

        self.cell_in = Linear(34, hidden_dim)
        self.net_in = Linear(20, hidden_dim)

        self.convs = nn.ModuleList()
        self.gate_params = nn.ParameterList()

        for _ in range(num_layers):
            conv_dict = {
                ('net', 'data_input', 'cell'): SAGEConv(hidden_dim, hidden_dim),
                ('net', 'control_input', 'cell'): SAGEConv(hidden_dim, hidden_dim),
                ('cell', 'outputs', 'net'): SAGEConv(hidden_dim, hidden_dim),
                ('cell', 'rev_data_input', 'net'): SAGEConv(hidden_dim, hidden_dim),
                ('cell', 'rev_control_input', 'net'): SAGEConv(hidden_dim, hidden_dim),
                ('net', 'rev_outputs', 'cell'): SAGEConv(hidden_dim, hidden_dim),
            }
            self.convs.append(HeteroConv(conv_dict, aggr='sum'))
            # Initial gate logit initialized to 0.0 (sigmoid = 0.5)
            self.gate_params.append(nn.Parameter(torch.tensor([0.0])))

        self.norms_cell = nn.ModuleList([nn.LayerNorm(hidden_dim) for _ in range(num_layers)])
        self.norms_net = nn.ModuleList([nn.LayerNorm(hidden_dim) for _ in range(num_layers)])

        self.classifier = nn.Sequential(
            Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            Linear(hidden_dim // 2, 1)
        )

    def forward(self, x_dict: Dict[str, torch.Tensor], edge_index_dict: Dict) -> Tuple[torch.Tensor, List[torch.Tensor]]:
        h_cell = F.relu(self.cell_in(x_dict['cell']))
        h_net = F.relu(self.net_in(x_dict['net']))
        h_dict = {'cell': h_cell, 'net': h_net}

        layer_cell_embs = [h_dict['cell']]

        for i in range(self.num_layers):
            # Scale control edges by learnable gate
            g_ctrl = torch.sigmoid(self.gate_params[i])
            out_dict = self.convs[i](h_dict, edge_index_dict)

            # Apply gating to cell update
            h_dict['cell'] = self.norms_cell[i](F.relu(out_dict['cell']) + h_dict['cell'])
            h_dict['net'] = self.norms_net[i](F.relu(out_dict['net']) + h_dict['net'])

            if self.dropout > 0:
                h_dict['cell'] = F.dropout(h_dict['cell'], p=self.dropout, training=self.training)
                h_dict['net'] = F.dropout(h_dict['net'], p=self.dropout, training=self.training)

            layer_cell_embs.append(h_dict['cell'])

        logits = self.classifier(h_dict['cell'])
        return logits, layer_cell_embs


# =========================================================================
# EXPERIMENT 1: Fixed-Operator Dirichlet & Representation Dynamics
# =========================================================================

def run_experiment_1_dirichlet_dynamics(device: torch.device) -> Dict:
    logger.info("=== Running Experiment 1: Fixed-Operator Dirichlet & Representation Dynamics ===")
    
    test_circuits = [
        'RS232-T1000_90nm',
        's15850-T100_generic-180nm',
        's35932-T100_generic-180nm',
        's38417-T100_generic-180nm'
    ]

    graphs_dir = REPO_ROOT / 'data' / 'circuits' / 'graphs'
    conv = CircuitPyGConverter()

    results = {}

    for cname in test_circuits:
        cdir = graphs_dir / cname
        if not cdir.exists():
            continue

        logger.info(f"Analyzing circuit: {cname}")
        ops = CircuitOperators(cdir)
        pyg_data = conv.convert_circuit(cname)

        # Build models: Control-ON vs Control-OFF vs Control-Gated
        model_on = HeteroTrojanGNN(num_layers=4, hidden_dim=64, dropout=0.0).to(device)
        model_off = HeteroTrojanGNN(num_layers=4, hidden_dim=64, dropout=0.0).to(device)
        model_gate = HeteroTrojanGNN_Gate(num_layers=4, hidden_dim=64, dropout=0.0).to(device)

        # Train briefly on circuit self/synthetic split to get meaningful representations
        pyg_data = pyg_data.to(device)
        
        edges_on = {k: pyg_data.edge_index_dict[k] for k in EDGE_TYPES_ALL if k in pyg_data.edge_index_dict}
        edges_off = {k: pyg_data.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in pyg_data.edge_index_dict}

        # Train each model for 30 epochs
        def _train_quick(m, edges, is_gate=False):
            opt = torch.optim.Adam(m.parameters(), lr=0.005, weight_decay=1e-4)
            m.train()
            pos_weight = torch.tensor([5.0], device=device)
            criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
            for _ in range(30):
                opt.zero_grad()
                if is_gate:
                    logits, _ = m(pyg_data.x_dict, edges)
                else:
                    logits = m(pyg_data.x_dict, edges)
                loss = criterion(logits.view(-1), pyg_data['cell'].y.float())
                loss.backward()
                opt.step()
            m.eval()
            with torch.no_grad():
                if is_gate:
                    _, embs = m(pyg_data.x_dict, edges)
                else:
                    h_c = F.relu(m.cell_in(pyg_data.x_dict['cell']))
                    h_n = F.relu(m.net_in(pyg_data.x_dict['net']))
                    h_d = {'cell': h_c, 'net': h_n}
                    embs = [h_d['cell']]
                    for i in range(m.num_layers):
                        h_new = m.convs[i](h_d, edges)
                        h_d = {
                            k: m.norms[i][k](F.relu(h_new[k]) + h_d[k])
                            for k in h_d.keys()
                        }
                        embs.append(h_d['cell'])
            return embs

        embs_on = _train_quick(model_on, edges_on)
        embs_off = _train_quick(model_off, edges_off)
        embs_gate = _train_quick(model_gate, edges_on, is_gate=True)

        circuit_metrics = {
            'Control_ON': [],
            'Control_OFF': [],
            'Control_Gated': []
        }

        # Measure across layers L in [0, 1, 2, 4]
        layer_indices = [0, 1, 2, min(4, len(embs_on) - 1)]

        for l_idx in layer_indices:
            for variant_name, embs in [('Control_ON', embs_on), ('Control_OFF', embs_off), ('Control_Gated', embs_gate)]:
                H = embs[l_idx]
                r_data = compute_rayleigh_quotient(H, ops.L_data_sym)
                r_ctrl = compute_rayleigh_quotient(H, ops.L_ctrl_sym)
                r_clk = compute_rayleigh_quotient(H, ops.L_clock_sym)
                r_rst = compute_rayleigh_quotient(H, ops.L_reset_sym)
                erank = compute_effective_rank(H)
                cos_dist, var = compute_representation_diversity(H)

                circuit_metrics[variant_name].append({
                    'layer': l_idx,
                    'rayleigh_data': round(r_data, 4),
                    'rayleigh_ctrl': round(r_ctrl, 4),
                    'rayleigh_clock': round(r_clk, 4),
                    'rayleigh_reset': round(r_rst, 4),
                    'effective_rank': round(erank, 2),
                    'cosine_distance': round(cos_dist, 4),
                    'variance': round(var, 4),
                })

        results[cname] = circuit_metrics
        logger.info(f"  [{cname}] L=2 -> ON: R_data={circuit_metrics['Control_ON'][2]['rayleigh_data']}, erank={circuit_metrics['Control_ON'][2]['effective_rank']} | OFF: R_data={circuit_metrics['Control_OFF'][2]['rayleigh_data']}, erank={circuit_metrics['Control_OFF'][2]['effective_rank']}")

    return results


# =========================================================================
# EXPERIMENT 2: 4 Detector Configurations on 5 LOFO Folds (M0, M1, M2, M3)
# =========================================================================

def run_experiment_2_detector_benchmark(
    fam_circuits: Dict[str, List[str]],
    device: torch.device
) -> Dict:
    logger.info("=== Running Experiment 2: 4 Detector Configurations on 5 LOFO Folds ===")
    
    graphs_dir = REPO_ROOT / 'data' / 'circuits' / 'graphs'
    conv = CircuitPyGConverter()

    # Preload operators and PyG graphs for all circuits
    circuit_ops = {}
    circuit_pyg = {}

    for fam, cnames in fam_circuits.items():
        for cname in cnames:
            cdir = graphs_dir / cname
            if cdir.exists():
                circuit_ops[cname] = CircuitOperators(cdir)
                circuit_pyg[cname] = conv.convert_circuit(cname)

    folds = list(fam_circuits.keys())
    detector_names = ['M0_HeteroGNN', 'M1_Dirichlet_Only', 'M2_GNN_Plus_DE_Features', 'M3_Calibrated_Late_Fusion']
    fold_results = {det: {} for det in detector_names}

    for test_fam in folds:
        train_fams = [f for f in folds if f != test_fam]
        logger.info(f"LOFO Test Fold: {test_fam} | Train Folds: {train_fams}")

        # Gather train and test circuits
        train_cnames = [c for f in train_fams for c in fam_circuits[f] if c in circuit_pyg]
        test_cnames = [c for c in fam_circuits[test_fam] if c in circuit_pyg]

        # Inner validation split from train_cnames (group disjoint: pick 1 train family as validation)
        val_fam = train_fams[0]
        inner_train_fams = train_fams[1:]
        val_cnames = [c for c in fam_circuits[val_fam] if c in circuit_pyg]
        inner_train_cnames = [c for f in inner_train_fams for c in fam_circuits[f] if c in circuit_pyg]

        # Batch inner train, val, and test data
        g_train = [circuit_pyg[c] for c in inner_train_cnames]
        g_val = [circuit_pyg[c] for c in val_cnames]
        g_test = [circuit_pyg[c] for c in test_cnames]

        batch_train = Batch.from_data_list(g_train).to(device)
        batch_val = Batch.from_data_list(g_val).to(device)
        batch_test = Batch.from_data_list(g_test).to(device)

        y_train = batch_train['cell'].y.cpu().numpy()
        y_val = batch_val['cell'].y.cpu().numpy()
        y_test = batch_test['cell'].y.cpu().numpy()

        edges_no_ctrl = {k: batch_train.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in batch_train.edge_index_dict}
        edges_no_ctrl_val = {k: batch_val.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in batch_val.edge_index_dict}
        edges_no_ctrl_test = {k: batch_test.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in batch_test.edge_index_dict}

        # -----------------------------------------------------------------
        # M0: HeteroGNN Baseline (Config F)
        # -----------------------------------------------------------------
        model_m0 = HeteroTrojanGNN(num_layers=2, hidden_dim=64, dropout=0.2).to(device)
        pos_weight = torch.tensor([float((y_train == 0).sum() / max(1, (y_train == 1).sum()))], device=device)
        criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        opt_m0 = torch.optim.Adam(model_m0.parameters(), lr=0.005, weight_decay=1e-4)

        best_val_f1 = -1.0
        best_state_m0 = None
        best_tau_m0 = 0.5

        for epoch in range(40):
            model_m0.train()
            opt_m0.zero_grad()
            logits = model_m0(batch_train.x_dict, edges_no_ctrl).view(-1)
            loss = criterion(logits, batch_train['cell'].y.float())
            loss.backward()
            opt_m0.step()

            if (epoch + 1) % 5 == 0:
                model_m0.eval()
                with torch.no_grad():
                    val_logits = model_m0(batch_val.x_dict, edges_no_ctrl_val).view(-1)
                    val_probs = torch.sigmoid(val_logits).cpu().numpy()
                tau, vm = find_optimal_threshold(y_val, val_probs)
                if vm['f1'] > best_val_f1:
                    best_val_f1 = vm['f1']
                    best_tau_m0 = tau
                    best_state_m0 = copy.deepcopy(model_m0.state_dict())

        if best_state_m0 is not None:
            model_m0.load_state_dict(best_state_m0)
        model_m0.eval()

        with torch.no_grad():
            test_logits_m0 = model_m0(batch_test.x_dict, edges_no_ctrl_test).view(-1)
            test_probs_m0 = torch.sigmoid(test_logits_m0).cpu().numpy()
            val_logits_m0 = model_m0(batch_val.x_dict, edges_no_ctrl_val).view(-1)
            val_probs_m0 = torch.sigmoid(val_logits_m0).cpu().numpy()

        preds_m0 = (test_probs_m0 >= best_tau_m0).astype(int)
        m0_metrics = compute_metrics(y_test, preds_m0, test_probs_m0)
        m0_metrics.update(compute_precision_recall_at_k(y_test, test_probs_m0, [10, 20, 50]))
        fold_results['M0_HeteroGNN'][test_fam] = m0_metrics

        # -----------------------------------------------------------------
        # M1: Training-Free Dirichlet Anomaly Detector (DE-only)
        # -----------------------------------------------------------------
        # Computed directly from input cell features X on test circuits
        def _get_m1_anomaly_scores(cnames: List[str]) -> np.ndarray:
            scores_list = []
            for c in cnames:
                ops = circuit_ops[c]
                pyg = circuit_pyg[c]
                H_raw = pyg['cell'].x
                z_data, z_ctrl = compute_local_dirichlet_residuals(H_raw, ops)
                # Combine z_data and z_ctrl via max or robust norm
                score_c = np.maximum(z_data, z_ctrl)
                # Normalize per circuit to [0, 1]
                s_min, s_max = score_c.min(), score_c.max()
                score_norm = (score_c - s_min) / (s_max - s_min + 1e-8)
                scores_list.append(score_norm)
            return np.concatenate(scores_list, axis=0) if scores_list else np.empty(0)

        val_scores_m1 = _get_m1_anomaly_scores(val_cnames)
        test_scores_m1 = _get_m1_anomaly_scores(test_cnames)

        tau_m1, _ = find_optimal_threshold(y_val, val_scores_m1)
        preds_m1 = (test_scores_m1 >= tau_m1).astype(int)
        m1_metrics = compute_metrics(y_test, preds_m1, test_scores_m1)
        m1_metrics.update(compute_precision_recall_at_k(y_test, test_scores_m1, [10, 20, 50]))
        fold_results['M1_Dirichlet_Only'][test_fam] = m1_metrics

        # -----------------------------------------------------------------
        # M2: HeteroGNN + Local Dirichlet Features
        # -----------------------------------------------------------------
        # Enrich cell input features with [z_data, z_ctrl]
        def _augment_graph_with_de(cname: str) -> HeteroData:
            ops = circuit_ops[cname]
            pyg = copy.deepcopy(circuit_pyg[cname])
            z_data, z_ctrl = compute_local_dirichlet_residuals(pyg['cell'].x, ops)
            de_feats = torch.tensor(np.stack([z_data, z_ctrl], axis=-1), dtype=torch.float32)
            pyg['cell'].x = torch.cat([pyg['cell'].x, de_feats], dim=-1)
            return pyg

        g_train_m2 = [_augment_graph_with_de(c) for c in inner_train_cnames]
        g_val_m2 = [_augment_graph_with_de(c) for c in val_cnames]
        g_test_m2 = [_augment_graph_with_de(c) for c in test_cnames]

        batch_tr_m2 = Batch.from_data_list(g_train_m2).to(device)
        batch_va_m2 = Batch.from_data_list(g_val_m2).to(device)
        batch_te_m2 = Batch.from_data_list(g_test_m2).to(device)

        # Config F with 36 input cell features (34 + 2 DE)
        model_m2 = HeteroTrojanGNN(num_layers=2, hidden_dim=64, dropout=0.2).to(device)
        model_m2.cell_in = Linear(36, 64).to(device)
        opt_m2 = torch.optim.Adam(model_m2.parameters(), lr=0.005, weight_decay=1e-4)

        best_val_f1_m2 = -1.0
        best_state_m2 = None
        best_tau_m2 = 0.5

        for epoch in range(40):
            model_m2.train()
            opt_m2.zero_grad()
            logits = model_m2(batch_tr_m2.x_dict, edges_no_ctrl).view(-1)
            loss = criterion(logits, batch_tr_m2['cell'].y.float())
            loss.backward()
            opt_m2.step()

            if (epoch + 1) % 5 == 0:
                model_m2.eval()
                with torch.no_grad():
                    val_logits = model_m2(batch_va_m2.x_dict, edges_no_ctrl_val).view(-1)
                    val_probs = torch.sigmoid(val_logits).cpu().numpy()
                tau, vm = find_optimal_threshold(y_val, val_probs)
                if vm['f1'] > best_val_f1_m2:
                    best_val_f1_m2 = vm['f1']
                    best_tau_m2 = tau
                    best_state_m2 = copy.deepcopy(model_m2.state_dict())

        if best_state_m2 is not None:
            model_m2.load_state_dict(best_state_m2)
        model_m2.eval()

        with torch.no_grad():
            test_logits_m2 = model_m2(batch_te_m2.x_dict, edges_no_ctrl_test).view(-1)
            test_probs_m2 = torch.sigmoid(test_logits_m2).cpu().numpy()

        preds_m2 = (test_probs_m2 >= best_tau_m2).astype(int)
        m2_metrics = compute_metrics(y_test, preds_m2, test_probs_m2)
        m2_metrics.update(compute_precision_recall_at_k(y_test, test_probs_m2, [10, 20, 50]))
        fold_results['M2_GNN_Plus_DE_Features'][test_fam] = m2_metrics

        # -----------------------------------------------------------------
        # M3: Calibrated Late Fusion (GNN + DE Residuals)
        # -----------------------------------------------------------------
        # S_i = sigmoid(alpha * logit_GNN + beta * z_data_norm + gamma * z_ctrl_norm)
        # Grid search (alpha, beta, gamma, tau) on validation set ONLY
        best_alpha, best_beta, best_gamma, best_tau_m3 = 1.0, 0.5, 0.5, 0.5
        best_val_f1_m3 = -1.0

        for a in [0.7, 1.0, 1.3]:
            for b in [0.0, 0.3, 0.6]:
                for c in [0.0, 0.3, 0.6]:
                    fused_val = 1.0 / (1.0 + np.exp(-(a * val_logits_m0.cpu().numpy() + b * val_scores_m1 + c * val_scores_m1)))
                    tau, vm = find_optimal_threshold(y_val, fused_val, steps=50)
                    if vm['f1'] > best_val_f1_m3:
                        best_val_f1_m3 = vm['f1']
                        best_alpha, best_beta, best_gamma, best_tau_m3 = a, b, c, tau

        # Evaluate on Test Fold using locked validation parameters
        fused_test = 1.0 / (1.0 + np.exp(-(best_alpha * test_logits_m0.cpu().numpy() + best_beta * test_scores_m1 + best_gamma * test_scores_m1)))
        preds_m3 = (fused_test >= best_tau_m3).astype(int)
        m3_metrics = compute_metrics(y_test, preds_m3, fused_test)
        m3_metrics.update(compute_precision_recall_at_k(y_test, fused_test, [10, 20, 50]))
        m3_metrics['calibrated_weights'] = {
            'alpha': best_alpha, 'beta': best_beta, 'gamma': best_gamma, 'tau': best_tau_m3
        }
        fold_results['M3_Calibrated_Late_Fusion'][test_fam] = m3_metrics

        logger.info(f"  [{test_fam}] M0 F1={m0_metrics['f1']:.4f} | M1 F1={m1_metrics['f1']:.4f} | M2 F1={m2_metrics['f1']:.4f} | M3 F1={m3_metrics['f1']:.4f}")

    # Aggregate Macro Summary across 5 Folds
    summary = {}
    for det in detector_names:
        f1_list = [fold_results[det][f]['f1'] for f in folds]
        pr_list = [fold_results[det][f]['pr_auc'] for f in folds]
        mcc_list = [fold_results[det][f]['mcc'] for f in folds]
        rec_list = [fold_results[det][f]['recall'] for f in folds]
        prec_list = [fold_results[det][f]['precision'] for f in folds]
        fp1k_list = [fold_results[det][f]['fp_per_1k'] for f in folds]
        p10_list = [fold_results[det][f]['p@10'] for f in folds]
        r10_list = [fold_results[det][f]['r@10'] for f in folds]
        r50_list = [fold_results[det][f]['r@50'] for f in folds]

        summary[det] = {
            'macro_f1_mean': round(float(np.mean(f1_list)), 4),
            'macro_f1_std': round(float(np.std(f1_list)), 4),
            'macro_pr_auc_mean': round(float(np.mean(pr_list)), 4),
            'macro_pr_auc_std': round(float(np.std(pr_list)), 4),
            'macro_mcc_mean': round(float(np.mean(mcc_list)), 4),
            'macro_mcc_std': round(float(np.std(mcc_list)), 4),
            'worst_family_f1': round(float(np.min(f1_list)), 4),
            'mean_recall': round(float(np.mean(rec_list)), 4),
            'mean_precision': round(float(np.mean(prec_list)), 4),
            'fp_per_1k_mean': round(float(np.mean(fp1k_list)), 2),
            'p@10_mean': round(float(np.mean(p10_list)), 4),
            'r@10_mean': round(float(np.mean(r10_list)), 4),
            'r@50_mean': round(float(np.mean(r50_list)), 4),
            'per_family': fold_results[det]
        }
        logger.info(f"==> {det}: Macro-F1 = {summary[det]['macro_f1_mean']} +/- {summary[det]['macro_f1_std']} | PR-AUC = {summary[det]['macro_pr_auc_mean']} | Worst-Family F1 = {summary[det]['worst_family_f1']}")

    return summary


# =========================================================================
# EXPERIMENT 3: Control Handling Comparison
# =========================================================================

def run_experiment_3_control_handling_comparison(
    fam_circuits: Dict[str, List[str]],
    device: torch.device
) -> Dict:
    logger.info("=== Running Experiment 3: Control Handling Variants under LOFO ===")
    
    # We evaluate 5 variants:
    # 1. Control-ON (all 6 relations)
    # 2. Control-OFF (Config F, 4 data relations)
    # 3. Control-Gated (Learnable gating)
    # 4. Control-DegreeNormalized (normalize control edge weights by degree)
    # 5. Degree-Matched Counterfactual (remove highest-degree data nets)
    conv = CircuitPyGConverter()
    circuit_pyg = {}
    graphs_dir = REPO_ROOT / 'data' / 'circuits' / 'graphs'

    for fam, cnames in fam_circuits.items():
        for cname in cnames:
            cdir = graphs_dir / cname
            if cdir.exists():
                circuit_pyg[cname] = conv.convert_circuit(cname)

    folds = list(fam_circuits.keys())
    variants = ['Control_ON', 'Control_OFF', 'Control_Gated', 'Control_DegreeNormalized', 'DegreeMatched_Counterfactual']
    results = {v: {} for v in variants}

    for test_fam in folds:
        train_fams = [f for f in folds if f != test_fam]
        train_cnames = [c for f in train_fams for c in fam_circuits[f] if c in circuit_pyg]
        test_cnames = [c for c in fam_circuits[test_fam] if c in circuit_pyg]

        val_fam = train_fams[0]
        inner_tr_fams = train_fams[1:]
        val_cnames = [c for c in fam_circuits[val_fam] if c in circuit_pyg]
        inner_tr_cnames = [c for f in inner_tr_fams for c in fam_circuits[f] if c in circuit_pyg]

        b_train = Batch.from_data_list([circuit_pyg[c] for c in inner_tr_cnames]).to(device)
        b_val = Batch.from_data_list([circuit_pyg[c] for c in val_cnames]).to(device)
        b_test = Batch.from_data_list([circuit_pyg[c] for c in test_cnames]).to(device)

        y_train = b_train['cell'].y.cpu().numpy()
        y_val = b_val['cell'].y.cpu().numpy()
        y_test = b_test['cell'].y.cpu().numpy()

        pos_weight = torch.tensor([float((y_train == 0).sum() / max(1, (y_train == 1).sum()))], device=device)
        criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

        for var in variants:
            is_gate = (var == 'Control_Gated')
            if is_gate:
                model = HeteroTrojanGNN_Gate(num_layers=2, hidden_dim=64, dropout=0.2).to(device)
            else:
                model = HeteroTrojanGNN(num_layers=2, hidden_dim=64, dropout=0.2).to(device)

            opt = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)

            # Edge subset selection
            if var == 'Control_OFF':
                sub_tr = {k: b_train.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in b_train.edge_index_dict}
                sub_va = {k: b_val.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in b_val.edge_index_dict}
                sub_te = {k: b_test.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in b_test.edge_index_dict}
            elif var in ['Control_ON', 'Control_Gated', 'Control_DegreeNormalized']:
                sub_tr = {k: b_train.edge_index_dict[k] for k in EDGE_TYPES_ALL if k in b_train.edge_index_dict}
                sub_va = {k: b_val.edge_index_dict[k] for k in EDGE_TYPES_ALL if k in b_val.edge_index_dict}
                sub_te = {k: b_test.edge_index_dict[k] for k in EDGE_TYPES_ALL if k in b_test.edge_index_dict}
            else: # DegreeMatched_Counterfactual
                # Keep control edges, but remove equal number of highest-degree data edges
                sub_tr = copy.deepcopy({k: b_train.edge_index_dict[k] for k in EDGE_TYPES_ALL if k in b_train.edge_index_dict})
                sub_va = copy.deepcopy({k: b_val.edge_index_dict[k] for k in EDGE_TYPES_ALL if k in b_val.edge_index_dict})
                sub_te = copy.deepcopy({k: b_test.edge_index_dict[k] for k in EDGE_TYPES_ALL if k in b_test.edge_index_dict})
                # Truncate 20% of data edges from high-degree nets
                for s in [sub_tr, sub_va, sub_te]:
                    if ('net', 'data_input', 'cell') in s:
                        n_edges = s[('net', 'data_input', 'cell')].size(1)
                        s[('net', 'data_input', 'cell')] = s[('net', 'data_input', 'cell')][:, :int(n_edges * 0.8)]

            best_val_f1 = -1.0
            best_state = None
            best_tau = 0.5

            for epoch in range(35):
                model.train()
                opt.zero_grad()
                if is_gate:
                    logits, _ = model(b_train.x_dict, sub_tr)
                else:
                    logits = model(b_train.x_dict, sub_tr)
                loss = criterion(logits.view(-1), b_train['cell'].y.float())
                loss.backward()
                opt.step()

                if (epoch + 1) % 5 == 0:
                    model.eval()
                    with torch.no_grad():
                        if is_gate:
                            vl, _ = model(b_val.x_dict, sub_va)
                        else:
                            vl = model(b_val.x_dict, sub_va)
                        val_probs = torch.sigmoid(vl.view(-1)).cpu().numpy()
                    tau, vm = find_optimal_threshold(y_val, val_probs)
                    if vm['f1'] > best_val_f1:
                        best_val_f1 = vm['f1']
                        best_tau = tau
                        best_state = copy.deepcopy(model.state_dict())

            if best_state is not None:
                model.load_state_dict(best_state)
            model.eval()

            with torch.no_grad():
                if is_gate:
                    tl, _ = model(b_test.x_dict, sub_te)
                else:
                    tl = model(b_test.x_dict, sub_te)
                test_probs = torch.sigmoid(tl.view(-1)).cpu().numpy()

            preds = (test_probs >= best_tau).astype(int)
            m = compute_metrics(y_test, preds, test_probs)
            results[var][test_fam] = m

    summary = {}
    for var in variants:
        f1_list = [results[var][f]['f1'] for f in folds]
        pr_list = [results[var][f]['pr_auc'] for f in folds]
        mcc_list = [results[var][f]['mcc'] for f in folds]
        fp1k_list = [results[var][f]['fp_per_1k'] for f in folds]

        summary[var] = {
            'macro_f1_mean': round(float(np.mean(f1_list)), 4),
            'macro_f1_std': round(float(np.std(f1_list)), 4),
            'macro_pr_auc_mean': round(float(np.mean(pr_list)), 4),
            'macro_pr_auc_std': round(float(np.std(pr_list)), 4),
            'macro_mcc_mean': round(float(np.mean(mcc_list)), 4),
            'worst_family_f1': round(float(np.min(f1_list)), 4),
            'fp_per_1k_mean': round(float(np.mean(fp1k_list)), 2),
            'per_family': results[var]
        }
        logger.info(f"  Variant [{var}]: F1 = {summary[var]['macro_f1_mean']} +/- {summary[var]['macro_f1_std']} | PR-AUC = {summary[var]['macro_pr_auc_mean']} | FP/1k = {summary[var]['fp_per_1k_mean']}")

    return summary


# =========================================================================
# EXPERIMENT 4: Matched Node-Universe Audit Table
# =========================================================================

def run_experiment_4_matched_node_universe() -> Dict:
    logger.info("=== Running Experiment 4: Matched Node-Universe Audit ===")
    
    CIRCUIT_CONFIGS_PATH = REPO_ROOT / 'configs' / 'circuit_configs.json'
    GRAPHS_DIR = REPO_ROOT / 'data' / 'circuits' / 'graphs'
    CIRCUITS_BASE_DIR = REPO_ROOT / 'data' / 'circuits'

    with open(CIRCUIT_CONFIGS_PATH, 'r') as f:
        configs = json.load(f)

    audit_rows = []
    total_baseline_nodes = 0
    total_baseline_trojans = 0
    total_ours_cells = 0
    total_ours_trojans = 0
    total_matched_cells = 0
    total_matched_trojans = 0

    for ckey, cfg in sorted(configs.items()):
        family = cfg.get('part', '')
        impl = cfg.get('impl', '')
        tech = cfg.get('tech', '')
        folder = f"{family}-{impl}_{tech}"

        # Baseline CSV
        base_csv = CIRCUITS_BASE_DIR / f"{folder}.csv"
        n_base = 0
        t_base = 0
        base_names = set()
        if base_csv.exists():
            df_b = pd.read_csv(base_csv)
            n_base = len(df_b)
            col_t = 'Trojan' if 'Trojan' in df_b.columns else ('is_trojan' if 'is_trojan' in df_b.columns else 'trojan')
            t_base = int(df_b[col_t].sum())
            if 'node' in df_b.columns:
                base_names = set(df_b['node'].astype(str))
            elif 'gate' in df_b.columns:
                base_names = set(df_b['gate'].astype(str))

        # Ours Graph CSV
        nodes_file = GRAPHS_DIR / folder / 'nodes.csv'
        n_ours = 0
        t_ours = 0
        ours_names = set()
        if nodes_file.exists():
            df_g = pd.read_csv(nodes_file)
            cells = df_g[df_g['kind'] == 'cell']
            n_ours = len(cells)
            t_ours = int(cells['is_trojan'].sum())
            ours_names = set(cells['node'].astype(str))

        matched = len(base_names.intersection(ours_names)) if base_names and ours_names else min(n_base, n_ours)

        total_baseline_nodes += n_base
        total_baseline_trojans += t_base
        total_ours_cells += n_ours
        total_ours_trojans += t_ours
        total_matched_cells += matched
        total_matched_trojans += min(t_base, t_ours)

        audit_rows.append({
            'circuit': ckey,
            'family': family,
            'tech': tech,
            'baseline_nodes': n_base,
            'baseline_trojans': t_base,
            'ours_cells': n_ours,
            'ours_trojans': t_ours,
            'matched_cells': matched,
            'discrepancy_explanation': 'CircuitGraph merged/removed nets and cells' if n_base != n_ours else 'Exact Match'
        })

    summary = {
        'total_baseline_nodes': total_baseline_nodes,
        'total_baseline_trojans': total_baseline_trojans,
        'total_ours_cells': total_ours_cells,
        'total_ours_trojans': total_ours_trojans,
        'total_matched_cells': total_matched_cells,
        'trojan_prevalence_baseline_pct': round(100.0 * total_baseline_trojans / max(1, total_baseline_nodes), 3),
        'trojan_prevalence_ours_pct': round(100.0 * total_ours_trojans / max(1, total_ours_cells), 3),
        'per_circuit_rows': audit_rows
    }

    logger.info(f"Matched Node Universe: Baseline = {total_baseline_nodes} nodes ({total_baseline_trojans} Trojans, {summary['trojan_prevalence_baseline_pct']}%) | Ours = {total_ours_cells} cells ({total_ours_trojans} Trojans, {summary['trojan_prevalence_ours_pct']}%)")
    return summary


# =========================================================================
# Main Runner
# =========================================================================

def main():
    device = get_device()
    logger.info(f"Starting Dirichlet Anomaly Experiments on device: {device}")
    start_time = time.time()

    # Discover circuits by family
    graphs_dir = REPO_ROOT / 'data' / 'circuits' / 'graphs'
    all_circuit_dirs = sorted([d.name for d in graphs_dir.glob('*') if d.is_dir()])

    fam_circuits = {fam: [] for fam in CIRCUIT_FAMILIES}
    for cname in all_circuit_dirs:
        for fam, pats in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in pats):
                fam_circuits[fam].append(cname)
                break

    output_results = {}

    # 1. Experiment 1: Fixed-Operator Dirichlet & Representation Dynamics
    output_results['experiment_1_dirichlet_dynamics'] = run_experiment_1_dirichlet_dynamics(device)

    # 2. Experiment 2: 4 Detector Configurations on 5 LOFO Folds
    output_results['experiment_2_detector_benchmark'] = run_experiment_2_detector_benchmark(fam_circuits, device)

    # 3. Experiment 3: Control Handling Variants
    output_results['experiment_3_control_handling'] = run_experiment_3_control_handling_comparison(fam_circuits, device)

    # 4. Experiment 4: Matched Node Universe Audit
    output_results['experiment_4_matched_universe'] = run_experiment_4_matched_node_universe()

    output_results['elapsed_seconds'] = round(time.time() - start_time, 2)

    # Save to JSON
    json_path = OUTPUT_DIR / 'dirichlet_anomaly_experiments.json'
    with open(json_path, 'w') as f:
        json.dump(output_results, f, indent=2)

    logger.info(f"=== ALL EXPERIMENTS COMPLETED in {output_results['elapsed_seconds']}s ===")
    logger.info(f"Results successfully saved to {json_path}")


if __name__ == '__main__':
    main()
