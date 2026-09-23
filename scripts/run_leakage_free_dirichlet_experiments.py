#!/usr/bin/env python3
"""
Leakage-Free Relation-Specific Dirichlet Non-Conformity Experiments for Hardware Trojan Localization:
Addresses all core methodological issues from deep-research-report_20260923_02.md:

1. Zero-Label Leakage Protocol:
   - Supervised-Normal Calibration (M1_S): median/MAD fitted strictly on benign training fold cells.
   - Contamination-Robust Unsupervised Calibration (M1_U): median/MAD fitted on all training fold cells without labels.
   - Scalers and thresholds locked on internal validation fold (Zero Test Contamination).

2. Dirichlet Decomposition & Relation Ablations:
   - E_data, E_ctrl, E_clock, E_reset, E_data + E_ctrl
   - Signed residual (log e - mu)/MAD vs Absolute residual |log e - mu|/MAD
   - Layer 0 (Input raw) vs Layer 1 vs Layer 2 embeddings

3. Operator Semantics Ablation:
   - Co-control clique (M_in^T @ M_in) vs Directed control-flow (M_out @ M_in)

4. Multi-Seed 5-Detector LOFO Benchmark (M0, M1_S, M1_U, M2, M3) across 3 seeds (42, 123, 456):
   - Paired delta PR-AUC and F1 (M3 - M0) with 95% Confidence Intervals and paired p-values.
   - Explicit disaggregation of sigma_family (across 5 folds) vs sigma_seed (across seeds).
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
from scipy import sparse as sp
from scipy import stats
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
logger = logging.getLogger('DirichletLeakageFreeExperiments')

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
    torch.set_num_threads(min(4, os.cpu_count() or 2))
    return torch.device('cpu')


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

    fp_per_1k = (fp / max(1, (tn + fp))) * 1000.0
    crr = float(tn + fn) / max(1, len(y_true))

    return {
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
        'precision': float(prec), 'recall': float(rec), 'f1': float(f1),
        'mcc': float(mcc), 'roc_auc': float(roc_auc), 'pr_auc': float(pr_auc),
        'fp_per_1k': float(fp_per_1k), 'crr': float(crr),
    }


def compute_precision_recall_at_k(y_true: np.ndarray, y_prob: np.ndarray, k_list: List[int]) -> Dict:
    metrics = {}
    n_trojans = int(np.sum(y_true == 1))
    if len(y_prob) == 0:
        return metrics

    order = np.argsort(-y_prob)
    for k in k_list:
        k_clamped = min(k, len(y_true))
        top_k_indices = order[:k_clamped]
        tp_k = int(np.sum(y_true[top_k_indices] == 1))
        prec_k = tp_k / float(k_clamped) if k_clamped > 0 else 0.0
        rec_k = tp_k / float(n_trojans) if n_trojans > 0 else 0.0
        metrics[f'p@{k}'] = round(prec_k, 4)
        metrics[f'r@{k}'] = round(rec_k, 4)
    return metrics


def find_optimal_threshold(y_true: np.ndarray, y_prob: np.ndarray, steps: int = 100) -> Tuple[float, Dict]:
    if len(y_prob) == 0 or len(np.unique(y_true)) <= 1:
        return 0.5, {'f1': 0.0}

    best_tau = 0.5
    best_metrics = {'f1': -1.0}
    thresholds = np.linspace(0.01, 0.99, steps)

    for tau in thresholds:
        preds = (y_prob >= tau).astype(int)
        m = compute_metrics(y_true, preds, y_prob)
        if m['f1'] > best_metrics['f1']:
            best_metrics = m
            best_tau = float(tau)

    return best_tau, best_metrics


# =========================================================================
# Operator Extraction: Co-Control vs Control-Flow
# =========================================================================

class CircuitOperators:
    def __init__(self, circuit_dir: Path):
        self.circuit_dir = circuit_dir
        self.circuit_name = circuit_dir.name
        self._load_data()

    def _load_data(self):
        nodes_df = pd.read_csv(self.circuit_dir / 'nodes.csv')
        edges_df = pd.read_csv(self.circuit_dir / 'edges.csv')

        cell_nodes = nodes_df[nodes_df['kind'] == 'cell'].reset_index(drop=True)
        net_nodes = nodes_df[nodes_df['kind'] == 'net'].reset_index(drop=True)

        self.cell_to_idx = {name: i for i, name in enumerate(cell_nodes['node'])}
        self.net_to_idx = {name: i for i, name in enumerate(net_nodes['node'])}

        self.n_cells = len(cell_nodes)
        self.n_nets = len(net_nodes)
        self.y = cell_nodes['is_trojan'].values.astype(int)
        self.cell_names = cell_nodes['node'].values

        cell_types = cell_nodes['type'].str.upper().values
        self.is_sequential = np.array([
            1 if ('DFF' in t or 'LATCH' in t or 'FLIP' in t) else 0
            for t in cell_types
        ])

        # Incidence matrices:
        # M_out: cell -> net (cells driving nets)
        # M_in_data: net -> cell (data nets driving cell inputs)
        # M_in_ctrl: net -> cell (control nets driving cell inputs)
        # M_in_clk: net -> cell (clock nets)
        # M_in_rst: net -> cell (reset nets)

        def _make_incidence(df_sub, row_is_cell=True):
            rows, cols = [], []
            for _, r in df_sub.iterrows():
                src, tgt = r['source'], r['target']
                if row_is_cell:
                    if src in self.cell_to_idx and tgt in self.net_to_idx:
                        rows.append(self.cell_to_idx[src])
                        cols.append(self.net_to_idx[tgt])
                else:
                    if src in self.net_to_idx and tgt in self.cell_to_idx:
                        rows.append(self.net_to_idx[src])
                        cols.append(self.cell_to_idx[tgt])
            if row_is_cell:
                return sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(self.n_cells, self.n_nets))
            return sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(self.n_nets, self.n_cells))

        out_edges = edges_df[edges_df['direction'] == 'cell_to_net']
        data_in = edges_df[(edges_df['direction'] == 'net_to_cell') & (edges_df['is_control'] == 0)]
        ctrl_in = edges_df[(edges_df['direction'] == 'net_to_cell') & (edges_df['is_control'] == 1)]

        clk_ports = {'CLK', 'CK', 'CLOCK', 'CLK_IN'}
        rst_ports = {'RST', 'RSTB', 'RESET', 'RN', 'SN', 'SETB'}

        clk_in = edges_df[(edges_df['direction'] == 'net_to_cell') & (edges_df['port'].astype(str).str.upper().isin(clk_ports))]
        rst_in = edges_df[(edges_df['direction'] == 'net_to_cell') & (edges_df['port'].astype(str).str.upper().isin(rst_ports))]

        M_out = _make_incidence(out_edges, row_is_cell=True)
        M_in_data = _make_incidence(data_in, row_is_cell=False)
        M_in_ctrl = _make_incidence(ctrl_in, row_is_cell=False)
        M_in_clk = _make_incidence(clk_in, row_is_cell=False)
        M_in_rst = _make_incidence(rst_in, row_is_cell=False)

        # 1. Functional Dataflow Operator (driver -> net -> receiver)
        # A_data[i, j] = 1 if cell i drives net that feeds cell j
        A_data = (M_out @ M_in_data).tocsr()
        A_data.setdiag(0)
        A_data.eliminate_zeros()
        self.A_data_dir = A_data
        self.A_data_sym = (A_data + A_data.T).tocsr()
        self.A_data_sym.data = np.ones_like(self.A_data_sym.data)

        # 2. Co-Control Clique Operator (M_in^T @ M_in): flip-flops sharing a control net
        A_ctrl_co = (M_in_ctrl.T @ M_in_ctrl).tocsr()
        A_ctrl_co.setdiag(0)
        A_ctrl_co.eliminate_zeros()
        self.A_ctrl_co = A_ctrl_co

        # 3. Directed Control Flow Operator (M_out @ M_in_ctrl): driver -> receiver of control signal
        A_ctrl_flow = (M_out @ M_in_ctrl).tocsr()
        A_ctrl_flow.setdiag(0)
        A_ctrl_flow.eliminate_zeros()
        self.A_ctrl_flow_dir = A_ctrl_flow
        self.A_ctrl_flow_sym = (A_ctrl_flow + A_ctrl_flow.T).tocsr()
        self.A_ctrl_flow_sym.data = np.ones_like(self.A_ctrl_flow_sym.data)

        # 4. Clock and Reset Operators
        A_clock = (M_in_clk.T @ M_in_clk).tocsr()
        A_clock.setdiag(0)
        A_clock.eliminate_zeros()
        self.A_clock = A_clock

        A_reset = (M_in_rst.T @ M_in_rst).tocsr()
        A_reset.setdiag(0)
        A_reset.eliminate_zeros()
        self.A_reset = A_reset

        # Normalized Symmetric Laplacians
        self.L_data_sym = self._build_normalized_laplacian(self.A_data_sym)
        self.L_ctrl_sym = self._build_normalized_laplacian(self.A_ctrl_co)
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


def compute_local_edge_variation(H_np: np.ndarray, A_sp: sp.csr_matrix, eps: float = 1e-6) -> np.ndarray:
    """
    Computes local edge variation:
    e_i = (sum_j A(i,j) ||h_i - h_j||^2) / (deg_i + eps)
    """
    N = H_np.shape[0]
    if A_sp.nnz == 0:
        return np.zeros(N)
    e_local = np.zeros(N)
    for i in range(N):
        start = A_sp.indptr[i]
        end = A_sp.indptr[i + 1]
        if start == end:
            continue
        neighbors = A_sp.indices[start:end]
        diffs = H_np[neighbors] - H_np[i]
        sq_diffs = np.sum(diffs ** 2, axis=-1)
        weights = A_sp.data[start:end]
        e_local[i] = np.sum(weights * sq_diffs) / (np.sum(weights) + eps)
    return e_local


# =========================================================================
# LEAKAGE-FREE NORMALIZATION MODULE
# =========================================================================

class LeakageFreeDirichletNormalizer:
    """
    Fit normality statistics (median and MAD) strictly on TRAINING circuits.
    Provides two calibration modes:
    - supervised: uses benign training nodes
    - unsupervised: uses all training nodes (contamination-robust, breakdown point = 50%)
    """
    def __init__(self, mode: str = 'supervised', eps: float = 1e-6):
        self.mode = mode
        self.eps = eps
        self.stats = {}  # {relation: {seq_val: (median, mad)}}

    def fit(self, train_energies: Dict[str, np.ndarray], is_seq_all: np.ndarray, y_all: Optional[np.ndarray] = None):
        self.stats = {}
        for rel_name, e_arr in train_energies.items():
            log_e = np.log(e_arr + self.eps)
            self.stats[rel_name] = {}
            for seq_val in [0, 1]:
                mask = (is_seq_all == seq_val)
                if self.mode == 'supervised' and y_all is not None:
                    mask = mask & (y_all == 0)

                if np.sum(mask) < 5:
                    mask = (is_seq_all == seq_val)
                if np.sum(mask) < 2:
                    mask = np.ones(len(e_arr), dtype=bool)

                ref_vals = log_e[mask]
                med = float(np.median(ref_vals))
                mad = float(np.median(np.abs(ref_vals - med)))
                scale = float(1.4826 * mad + self.eps)
                self.stats[rel_name][seq_val] = (med, scale)

    def transform(self, e_arr: np.ndarray, is_seq: np.ndarray, rel_name: str, signed: bool = False) -> np.ndarray:
        N = len(e_arr)
        z = np.zeros(N)
        log_e = np.log(e_arr + self.eps)
        rel_stats = self.stats.get(rel_name, {})

        for seq_val in [0, 1]:
            mask = (is_seq == seq_val)
            med, scale = rel_stats.get(seq_val, (0.0, 1.0))
            if signed:
                z[mask] = (log_e[mask] - med) / scale
            else:
                z[mask] = np.abs(log_e[mask] - med) / scale
        return z


# =========================================================================
# EXPERIMENT 1 & 2: LEAKAGE-FREE DE ABLATIONS & OPERATOR COMPARISON
# =========================================================================

def run_dirichlet_detailed_ablations(
    fam_circuits: Dict[str, List[str]],
    device: torch.device
) -> Dict:
    logger.info("=== Running Experiment: Detailed Dirichlet Decomposition & Operator Ablations ===")
    
    graphs_dir = REPO_ROOT / 'data' / 'circuits' / 'graphs'
    conv = CircuitPyGConverter()

    circuit_ops = {}
    circuit_pyg = {}

    for fam, cnames in fam_circuits.items():
        for cname in cnames:
            cdir = graphs_dir / cname
            if cdir.exists():
                circuit_ops[cname] = CircuitOperators(cdir)
                circuit_pyg[cname] = conv.convert_circuit(cname)

    folds = list(fam_circuits.keys())

    # We evaluate across 5 LOFO folds using Leakage-Free calibration:
    # 1. Supervised vs Unsupervised calibration
    # 2. Relation breakdown: E_data, E_ctrl_co, E_ctrl_flow, E_clock, E_reset, E_data + E_ctrl
    # 3. Signed residual vs Absolute residual
    # 4. Layer 0 (Input features) vs Layer 1 vs Layer 2 embeddings

    ablation_results = {
        'M1_Supervised_Normal': [],
        'M1_Unsupervised_Robust': [],
        'E_data_only': [],
        'E_ctrl_co_only': [],
        'E_ctrl_flow_only': [],
        'E_clock_only': [],
        'E_reset_only': [],
        'E_data_plus_ctrl': [],
        'Signed_Residual': [],
        'Absolute_Residual': [],
        'Layer_0_Raw': [],
        'Layer_1_Conv': [],
        'Layer_2_Conv': []
    }

    for test_fam in folds:
        train_fams = [f for f in folds if f != test_fam]
        train_cnames = [c for f in train_fams for c in fam_circuits[f] if c in circuit_pyg]
        val_fam = train_fams[0]
        val_cnames = [c for c in fam_circuits[val_fam] if c in circuit_pyg]
        inner_train_cnames = [c for f in train_fams[1:] for c in fam_circuits[f] if c in circuit_pyg]
        test_cnames = [c for c in fam_circuits[test_fam] if c in circuit_pyg]

        # Extract features for train, val, test
        # We train a quick Config F GNN on inner train to get Layer 1 and 2 embeddings
        b_train = Batch.from_data_list([circuit_pyg[c] for c in inner_train_cnames]).to(device)
        b_val = Batch.from_data_list([circuit_pyg[c] for c in val_cnames]).to(device)
        b_test = Batch.from_data_list([circuit_pyg[c] for c in test_cnames]).to(device)

        y_train = b_train['cell'].y.cpu().numpy()
        y_val = b_val['cell'].y.cpu().numpy()
        y_test = b_test['cell'].y.cpu().numpy()

        edges_no_ctrl = {k: b_train.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in b_train.edge_index_dict}
        edges_no_ctrl_val = {k: b_val.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in b_val.edge_index_dict}
        edges_no_ctrl_test = {k: b_test.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in b_test.edge_index_dict}

        model = HeteroTrojanGNN(num_layers=2, hidden_dim=64, dropout=0.2).to(device)
        opt = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)
        pos_weight = torch.tensor([float((y_train == 0).sum() / max(1, (y_train == 1).sum()))], device=device)
        criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

        for _ in range(25):
            model.train()
            opt.zero_grad()
            logits = model(b_train.x_dict, edges_no_ctrl).view(-1)
            loss = criterion(logits, b_train['cell'].y.float())
            loss.backward()
            opt.step()

        model.eval()

        def _get_embs(cnames: List[str]):
            embs_l0, embs_l1, embs_l2 = [], [], []
            for c in cnames:
                g = circuit_pyg[c].to(device)
                with torch.no_grad():
                    h_c = F.relu(model.cell_in(g.x_dict['cell']))
                    h_n = F.relu(model.net_in(g.x_dict['net']))
                    h_d = {'cell': h_c, 'net': h_n}
                    embs_l0.append(g['cell'].x.cpu().numpy())
                    # Conv 1
                    h_new = model.convs[0](h_d, {k: g.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in g.edge_index_dict})
                    h_d = {k: model.norms[0][k](F.relu(h_new[k]) + h_d[k]) for k in h_d.keys()}
                    embs_l1.append(h_d['cell'].cpu().numpy())
                    # Conv 2
                    h_new = model.convs[1](h_d, {k: g.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in g.edge_index_dict})
                    h_d = {k: model.norms[1][k](F.relu(h_new[k]) + h_d[k]) for k in h_d.keys()}
                    embs_l2.append(h_d['cell'].cpu().numpy())
            return embs_l0, embs_l1, embs_l2

        train_l0, train_l1, train_l2 = _get_embs(inner_train_cnames)
        val_l0, val_l1, val_l2 = _get_embs(val_cnames)
        test_l0, test_l1, test_l2 = _get_embs(test_cnames)

        # Build training energy distribution across all training circuits for all operators
        def _calc_circuit_energies(cnames: List[str], embs_list: List[np.ndarray]):
            e_data, e_ctrl_co, e_ctrl_flow, e_clk, e_rst = [], [], [], [], []
            is_seq_list, y_list = [], []
            for c, H_np in zip(cnames, embs_list):
                ops = circuit_ops[c]
                e_data.append(compute_local_edge_variation(H_np, ops.A_data_sym))
                e_ctrl_co.append(compute_local_edge_variation(H_np, ops.A_ctrl_co))
                e_ctrl_flow.append(compute_local_edge_variation(H_np, ops.A_ctrl_flow_sym))
                e_clk.append(compute_local_edge_variation(H_np, ops.A_clock))
                e_rst.append(compute_local_edge_variation(H_np, ops.A_reset))
                is_seq_list.append(ops.is_sequential)
                y_list.append(ops.y)

            return {
                'data': np.concatenate(e_data),
                'ctrl_co': np.concatenate(e_ctrl_co),
                'ctrl_flow': np.concatenate(e_ctrl_flow),
                'clock': np.concatenate(e_clk),
                'reset': np.concatenate(e_rst),
            }, np.concatenate(is_seq_list), np.concatenate(y_list)

        tr_e_l2, tr_seq, tr_y = _calc_circuit_energies(inner_train_cnames, train_l2)
        va_e_l2, va_seq, va_y = _calc_circuit_energies(val_cnames, val_l2)
        te_e_l2, te_seq, te_y = _calc_circuit_energies(test_cnames, test_l2)

        # Layer 0 and Layer 1 test energies
        tr_e_l0, _, _ = _calc_circuit_energies(inner_train_cnames, train_l0)
        te_e_l0, _, _ = _calc_circuit_energies(test_cnames, test_l0)
        va_e_l0, _, _ = _calc_circuit_energies(val_cnames, val_l0)

        tr_e_l1, _, _ = _calc_circuit_energies(inner_train_cnames, train_l1)
        te_e_l1, _, _ = _calc_circuit_energies(test_cnames, test_l1)
        va_e_l1, _, _ = _calc_circuit_energies(val_cnames, val_l1)

        # Fit Normalizers STRICTLY ON TRAINING FOLDS
        norm_sup = LeakageFreeDirichletNormalizer(mode='supervised')
        norm_sup.fit(tr_e_l2, tr_seq, tr_y)

        norm_unsup = LeakageFreeDirichletNormalizer(mode='unsupervised')
        norm_unsup.fit(tr_e_l2, tr_seq, None)

        norm_l0 = LeakageFreeDirichletNormalizer(mode='supervised')
        norm_l0.fit(tr_e_l0, tr_seq, tr_y)

        norm_l1 = LeakageFreeDirichletNormalizer(mode='supervised')
        norm_l1.fit(tr_e_l1, tr_seq, tr_y)

        # Helper to score, find val tau, and evaluate on test
        def _eval_anomaly_signal(va_score: np.ndarray, te_score: np.ndarray) -> Dict:
            s_min, s_max = va_score.min(), va_score.max()
            va_norm = (va_score - s_min) / (s_max - s_min + 1e-8)
            # Use VALIDATION scale on test (Zero Test Contamination)
            te_norm = (te_score - s_min) / (s_max - s_min + 1e-8)
            tau, _ = find_optimal_threshold(va_y, va_norm)
            preds = (te_norm >= tau).astype(int)
            return compute_metrics(te_y, preds, te_norm)

        # 1. M1 Supervised (max of z_data, z_ctrl)
        z_da_va_s = norm_sup.transform(va_e_l2['data'], va_seq, 'data')
        z_ct_va_s = norm_sup.transform(va_e_l2['ctrl_co'], va_seq, 'ctrl_co')
        z_da_te_s = norm_sup.transform(te_e_l2['data'], te_seq, 'data')
        z_ct_te_s = norm_sup.transform(te_e_l2['ctrl_co'], te_seq, 'ctrl_co')
        ablation_results['M1_Supervised_Normal'].append(_eval_anomaly_signal(
            np.maximum(z_da_va_s, z_ct_va_s), np.maximum(z_da_te_s, z_ct_te_s)))

        # 2. M1 Unsupervised (zero labels used during fitting)
        z_da_va_u = norm_unsup.transform(va_e_l2['data'], va_seq, 'data')
        z_ct_va_u = norm_unsup.transform(va_e_l2['ctrl_co'], va_seq, 'ctrl_co')
        z_da_te_u = norm_unsup.transform(te_e_l2['data'], te_seq, 'data')
        z_ct_te_u = norm_unsup.transform(te_e_l2['ctrl_co'], te_seq, 'ctrl_co')
        ablation_results['M1_Unsupervised_Robust'].append(_eval_anomaly_signal(
            np.maximum(z_da_va_u, z_ct_va_u), np.maximum(z_da_te_u, z_ct_te_u)))

        # 3. E_data only
        ablation_results['E_data_only'].append(_eval_anomaly_signal(z_da_va_s, z_da_te_s))

        # 4. E_ctrl_co only (Clique co-control)
        ablation_results['E_ctrl_co_only'].append(_eval_anomaly_signal(z_ct_va_s, z_ct_te_s))

        # 5. E_ctrl_flow only (Directed control flow)
        z_fl_va = norm_sup.transform(va_e_l2['ctrl_flow'], va_seq, 'ctrl_flow')
        z_fl_te = norm_sup.transform(te_e_l2['ctrl_flow'], te_seq, 'ctrl_flow')
        ablation_results['E_ctrl_flow_only'].append(_eval_anomaly_signal(z_fl_va, z_fl_te))

        # 6. E_clock only
        z_ck_va = norm_sup.transform(va_e_l2['clock'], va_seq, 'clock')
        z_ck_te = norm_sup.transform(te_e_l2['clock'], te_seq, 'clock')
        ablation_results['E_clock_only'].append(_eval_anomaly_signal(z_ck_va, z_ck_te))

        # 7. E_reset only
        z_rs_va = norm_sup.transform(va_e_l2['reset'], va_seq, 'reset')
        z_rs_te = norm_sup.transform(te_e_l2['reset'], te_seq, 'reset')
        ablation_results['E_reset_only'].append(_eval_anomaly_signal(z_rs_va, z_rs_te))

        # 8. E_data + E_ctrl (additive fusion)
        ablation_results['E_data_plus_ctrl'].append(_eval_anomaly_signal(
            z_da_va_s + z_ct_va_s, z_da_te_s + z_ct_te_s))

        # 9. Signed residual vs Absolute residual
        z_da_va_sgn = norm_sup.transform(va_e_l2['data'], va_seq, 'data', signed=True)
        z_da_te_sgn = norm_sup.transform(te_e_l2['data'], te_seq, 'data', signed=True)
        ablation_results['Signed_Residual'].append(_eval_anomaly_signal(z_da_va_sgn, z_da_te_sgn))
        ablation_results['Absolute_Residual'].append(_eval_anomaly_signal(np.abs(z_da_va_sgn), np.abs(z_da_te_sgn)))

        # 10. Layer 0 vs Layer 1 vs Layer 2 embeddings
        z_l0_va = norm_l0.transform(va_e_l0['data'], va_seq, 'data')
        z_l0_te = norm_l0.transform(te_e_l0['data'], te_seq, 'data')
        ablation_results['Layer_0_Raw'].append(_eval_anomaly_signal(z_l0_va, z_l0_te))

        z_l1_va = norm_l1.transform(va_e_l1['data'], va_seq, 'data')
        z_l1_te = norm_l1.transform(te_e_l1['data'], te_seq, 'data')
        ablation_results['Layer_1_Conv'].append(_eval_anomaly_signal(z_l1_va, z_l1_te))

        ablation_results['Layer_2_Conv'].append(_eval_anomaly_signal(z_da_va_s, z_da_te_s))

    # Summarize ablation metrics across folds
    ablation_summary = {}
    for name, m_list in ablation_results.items():
        f1s = [m['f1'] for m in m_list]
        prs = [m['pr_auc'] for m in m_list]
        mccs = [m['mcc'] for m in m_list]
        fp1k = [m['fp_per_1k'] for m in m_list]
        ablation_summary[name] = {
            'macro_f1_mean': round(float(np.mean(f1s)), 4),
            'macro_f1_std': round(float(np.std(f1s)), 4),
            'macro_pr_auc_mean': round(float(np.mean(prs)), 4),
            'macro_pr_auc_std': round(float(np.std(prs)), 4),
            'macro_mcc_mean': round(float(np.mean(mccs)), 4),
            'fp_per_1k_mean': round(float(np.mean(fp1k)), 2),
            'worst_family_f1': round(float(np.min(f1s)), 4),
        }
        logger.info(f"Ablation [{name}]: Macro-F1 = {ablation_summary[name]['macro_f1_mean']} | PR-AUC = {ablation_summary[name]['macro_pr_auc_mean']}")

    return ablation_summary


# =========================================================================
# EXPERIMENT 3: MULTI-SEED 5-DETECTOR BENCHMARK WITH PAIRED SIGNIFICANCE
# =========================================================================

def run_multiseed_detector_benchmark(
    fam_circuits: Dict[str, List[str]],
    device: torch.device,
    seeds: List[int] = [42, 123, 456]
) -> Dict:
    logger.info(f"=== Running Multi-Seed 5-Detector LOFO Benchmark (Seeds: {seeds}) ===")

    graphs_dir = REPO_ROOT / 'data' / 'circuits' / 'graphs'
    conv = CircuitPyGConverter()

    circuit_ops = {}
    circuit_pyg = {}

    for fam, cnames in fam_circuits.items():
        for cname in cnames:
            cdir = graphs_dir / cname
            if cdir.exists():
                circuit_ops[cname] = CircuitOperators(cdir)
                circuit_pyg[cname] = conv.convert_circuit(cname)

    folds = list(fam_circuits.keys())
    detectors = ['M0_HeteroGNN', 'M1_Supervised_DE', 'M1_Unsupervised_DE', 'M2_Early_Fusion_DE', 'M3_Calibrated_Late_Fusion']

    # Structure: {det: {seed: {family: metrics}}}
    raw_results = {det: {s: {} for s in seeds} for det in detectors}

    for seed in seeds:
        torch.manual_seed(seed)
        np.random.seed(seed)

        for test_fam in folds:
            train_fams = [f for f in folds if f != test_fam]
            train_cnames = [c for f in train_fams for c in fam_circuits[f] if c in circuit_pyg]
            val_fam = train_fams[0]
            val_cnames = [c for c in fam_circuits[val_fam] if c in circuit_pyg]
            inner_train_cnames = [c for f in train_fams[1:] for c in fam_circuits[f] if c in circuit_pyg]
            test_cnames = [c for c in fam_circuits[test_fam] if c in circuit_pyg]

            b_train = Batch.from_data_list([circuit_pyg[c] for c in inner_train_cnames]).to(device)
            b_val = Batch.from_data_list([circuit_pyg[c] for c in val_cnames]).to(device)
            b_test = Batch.from_data_list([circuit_pyg[c] for c in test_cnames]).to(device)

            y_train = b_train['cell'].y.cpu().numpy()
            y_val = b_val['cell'].y.cpu().numpy()
            y_test = b_test['cell'].y.cpu().numpy()

            edges_no_ctrl = {k: b_train.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in b_train.edge_index_dict}
            edges_no_ctrl_val = {k: b_val.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in b_val.edge_index_dict}
            edges_no_ctrl_test = {k: b_test.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in b_test.edge_index_dict}

            # -------------------------------------------------------------
            # M0: Reference HeteroGNN
            # -------------------------------------------------------------
            model_m0 = HeteroTrojanGNN(num_layers=2, hidden_dim=64, dropout=0.2).to(device)
            opt_m0 = torch.optim.Adam(model_m0.parameters(), lr=0.005, weight_decay=1e-4)
            pos_weight = torch.tensor([float((y_train == 0).sum() / max(1, (y_train == 1).sum()))], device=device)
            criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

            best_val_f1_m0 = -1.0
            best_state_m0 = None
            best_tau_m0 = 0.5

            for epoch in range(35):
                model_m0.train()
                opt_m0.zero_grad()
                logits = model_m0(b_train.x_dict, edges_no_ctrl).view(-1)
                loss = criterion(logits, b_train['cell'].y.float())
                loss.backward()
                opt_m0.step()

                if (epoch + 1) % 5 == 0:
                    model_m0.eval()
                    with torch.no_grad():
                        val_logits = model_m0(b_val.x_dict, edges_no_ctrl_val).view(-1)
                        val_probs = torch.sigmoid(val_logits).cpu().numpy()
                    tau, vm = find_optimal_threshold(y_val, val_probs)
                    if vm['f1'] > best_val_f1_m0:
                        best_val_f1_m0 = vm['f1']
                        best_tau_m0 = tau
                        best_state_m0 = copy.deepcopy(model_m0.state_dict())

            if best_state_m0 is not None:
                model_m0.load_state_dict(best_state_m0)
            model_m0.eval()

            with torch.no_grad():
                te_logits_m0 = model_m0(b_test.x_dict, edges_no_ctrl_test).view(-1)
                te_probs_m0 = torch.sigmoid(te_logits_m0).cpu().numpy()
                va_logits_m0 = model_m0(b_val.x_dict, edges_no_ctrl_val).view(-1)
                va_probs_m0 = torch.sigmoid(va_logits_m0).cpu().numpy()

            preds_m0 = (te_probs_m0 >= best_tau_m0).astype(int)
            m0_m = compute_metrics(y_test, preds_m0, te_probs_m0)
            m0_m.update(compute_precision_recall_at_k(y_test, te_probs_m0, [10, 20, 50]))
            raw_results['M0_HeteroGNN'][seed][test_fam] = m0_m

            # -------------------------------------------------------------
            # Extract Representations & Leakage-Free Normalization
            # -------------------------------------------------------------
            def _get_cell_embs(cnames):
                embs = []
                for c in cnames:
                    g = circuit_pyg[c].to(device)
                    with torch.no_grad():
                        h_c = F.relu(model_m0.cell_in(g.x_dict['cell']))
                        h_n = F.relu(model_m0.net_in(g.x_dict['net']))
                        h_d = {'cell': h_c, 'net': h_n}
                        for i in range(model_m0.num_layers):
                            h_new = model_m0.convs[i](h_d, {k: g.edge_index_dict[k] for k in EDGE_TYPES_NO_CTRL if k in g.edge_index_dict})
                            h_d = {k: model_m0.norms[i][k](F.relu(h_new[k]) + h_d[k]) for k in h_d.keys()}
                        embs.append(h_d['cell'].cpu().numpy())
                return embs

            tr_embs = _get_cell_embs(inner_train_cnames)
            va_embs = _get_cell_embs(val_cnames)
            te_embs = _get_cell_embs(test_cnames)

            def _collect_energies(cnames, embs_list):
                e_data_list, e_ctrl_list = [], []
                seq_list, y_list = [], []
                for c, H in zip(cnames, embs_list):
                    ops = circuit_ops[c]
                    e_data_list.append(compute_local_edge_variation(H, ops.A_data_sym))
                    e_ctrl_list.append(compute_local_edge_variation(H, ops.A_ctrl_co))
                    seq_list.append(ops.is_sequential)
                    y_list.append(ops.y)
                return (np.concatenate(e_data_list), np.concatenate(e_ctrl_list),
                        np.concatenate(seq_list), np.concatenate(y_list))

            tr_ed, tr_ec, tr_seq, tr_y = _collect_energies(inner_train_cnames, tr_embs)
            va_ed, va_ec, va_seq, va_y = _collect_energies(val_cnames, va_embs)
            te_ed, te_ec, te_seq, te_y = _collect_energies(test_cnames, te_embs)

            # Fit Supervised Normalizer
            norm_sup = LeakageFreeDirichletNormalizer(mode='supervised')
            norm_sup.fit({'data': tr_ed, 'ctrl': tr_ec}, tr_seq, tr_y)

            # Fit Unsupervised Normalizer (NO LABELS)
            norm_unsup = LeakageFreeDirichletNormalizer(mode='unsupervised')
            norm_unsup.fit({'data': tr_ed, 'ctrl': tr_ec}, tr_seq, None)

            # Transform Val and Test
            z_da_va_s = norm_sup.transform(va_ed, va_seq, 'data')
            z_ct_va_s = norm_sup.transform(va_ec, va_seq, 'ctrl')
            z_da_te_s = norm_sup.transform(te_ed, te_seq, 'data')
            z_ct_te_s = norm_sup.transform(te_ec, te_seq, 'ctrl')

            z_da_va_u = norm_unsup.transform(va_ed, va_seq, 'data')
            z_ct_va_u = norm_unsup.transform(va_ec, va_seq, 'ctrl')
            z_da_te_u = norm_unsup.transform(te_ed, te_seq, 'data')
            z_ct_te_u = norm_unsup.transform(te_ec, te_seq, 'ctrl')

            # -------------------------------------------------------------
            # M1_S: Supervised Normal DE
            # -------------------------------------------------------------
            score_va_m1s = np.maximum(z_da_va_s, z_ct_va_s)
            score_te_m1s = np.maximum(z_da_te_s, z_ct_te_s)
            s_min, s_max = score_va_m1s.min(), score_va_m1s.max()
            score_va_m1s_n = (score_va_m1s - s_min) / (s_max - s_min + 1e-8)
            score_te_m1s_n = (score_te_m1s - s_min) / (s_max - s_min + 1e-8)
            tau_m1s, _ = find_optimal_threshold(va_y, score_va_m1s_n)
            preds_m1s = (score_te_m1s_n >= tau_m1s).astype(int)
            m1s_m = compute_metrics(y_test, preds_m1s, score_te_m1s_n)
            m1s_m.update(compute_precision_recall_at_k(y_test, score_te_m1s_n, [10, 20, 50]))
            raw_results['M1_Supervised_DE'][seed][test_fam] = m1s_m

            # -------------------------------------------------------------
            # M1_U: Contamination-Robust Unsupervised DE
            # -------------------------------------------------------------
            score_va_m1u = np.maximum(z_da_va_u, z_ct_va_u)
            score_te_m1u = np.maximum(z_da_te_u, z_ct_te_u)
            s_min_u, s_max_u = score_va_m1u.min(), score_va_m1u.max()
            score_va_m1u_n = (score_va_m1u - s_min_u) / (s_max_u - s_min_u + 1e-8)
            score_te_m1u_n = (score_te_m1u - s_min_u) / (s_max_u - s_min_u + 1e-8)
            tau_m1u, _ = find_optimal_threshold(va_y, score_va_m1u_n)
            preds_m1u = (score_te_m1u_n >= tau_m1u).astype(int)
            m1u_m = compute_metrics(y_test, preds_m1u, score_te_m1u_n)
            m1u_m.update(compute_precision_recall_at_k(y_test, score_te_m1u_n, [10, 20, 50]))
            raw_results['M1_Unsupervised_DE'][seed][test_fam] = m1u_m

            # -------------------------------------------------------------
            # M2: Early Fusion (GNN + DE input features)
            # -------------------------------------------------------------
            def _augment_graph(cname: str, z_da, z_ct):
                g = copy.deepcopy(circuit_pyg[cname])
                de_f = torch.tensor(np.stack([z_da, z_ct], axis=-1), dtype=torch.float32)
                g['cell'].x = torch.cat([g['cell'].x, de_f], dim=-1)
                return g

            # Partition z_da and z_ct per circuit for train/val/test
            def _split_per_circuit(cnames, z_da, z_ct):
                res = []
                idx = 0
                for c in cnames:
                    nc = circuit_ops[c].n_cells
                    res.append(_augment_graph(c, z_da[idx:idx+nc], z_ct[idx:idx+nc]))
                    idx += nc
                return res

            z_da_tr = norm_sup.transform(tr_ed, tr_seq, 'data')
            z_ct_tr = norm_sup.transform(tr_ec, tr_seq, 'ctrl')

            g_tr_m2 = _split_per_circuit(inner_train_cnames, z_da_tr, z_ct_tr)
            g_va_m2 = _split_per_circuit(val_cnames, z_da_va_s, z_ct_va_s)
            g_te_m2 = _split_per_circuit(test_cnames, z_da_te_s, z_ct_te_s)

            b_tr_m2 = Batch.from_data_list(g_tr_m2).to(device)
            b_va_m2 = Batch.from_data_list(g_va_m2).to(device)
            b_te_m2 = Batch.from_data_list(g_te_m2).to(device)

            model_m2 = HeteroTrojanGNN(num_layers=2, hidden_dim=64, dropout=0.2).to(device)
            model_m2.cell_in = Linear(36, 64).to(device)
            opt_m2 = torch.optim.Adam(model_m2.parameters(), lr=0.005, weight_decay=1e-4)

            best_val_f1_m2 = -1.0
            best_state_m2 = None
            best_tau_m2 = 0.5

            for epoch in range(35):
                model_m2.train()
                opt_m2.zero_grad()
                logits = model_m2(b_tr_m2.x_dict, edges_no_ctrl).view(-1)
                loss = criterion(logits, b_tr_m2['cell'].y.float())
                loss.backward()
                opt_m2.step()

                if (epoch + 1) % 5 == 0:
                    model_m2.eval()
                    with torch.no_grad():
                        val_logits = model_m2(b_va_m2.x_dict, edges_no_ctrl_val).view(-1)
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
                te_logits_m2 = model_m2(b_te_m2.x_dict, edges_no_ctrl_test).view(-1)
                te_probs_m2 = torch.sigmoid(te_logits_m2).cpu().numpy()

            preds_m2 = (te_probs_m2 >= best_tau_m2).astype(int)
            m2_m = compute_metrics(y_test, preds_m2, te_probs_m2)
            m2_m.update(compute_precision_recall_at_k(y_test, te_probs_m2, [10, 20, 50]))
            raw_results['M2_Early_Fusion_DE'][seed][test_fam] = m2_m

            # -------------------------------------------------------------
            # M3: Calibrated Late Fusion (GNN Logit + z_data + z_ctrl)
            # S_i = sigmoid(alpha * logit_GNN + beta * z_data + gamma * z_ctrl)
            # -------------------------------------------------------------
            val_logits_np = va_logits_m0.cpu().numpy()
            test_logits_np = te_logits_m0.cpu().numpy()

            best_alpha, best_beta, best_gamma, best_tau_m3 = 1.0, 0.3, 0.3, 0.5
            best_val_f1_m3 = -1.0

            # Normalize residuals with training scales
            z_da_va_norm = (z_da_va_s - z_da_va_s.min()) / (z_da_va_s.max() - z_da_va_s.min() + 1e-8)
            z_ct_va_norm = (z_ct_va_s - z_ct_va_s.min()) / (z_ct_va_s.max() - z_ct_va_s.min() + 1e-8)

            z_da_te_norm = (z_da_te_s - z_da_va_s.min()) / (z_da_va_s.max() - z_da_va_s.min() + 1e-8)
            z_ct_te_norm = (z_ct_te_s - z_ct_va_s.min()) / (z_ct_va_s.max() - z_ct_va_s.min() + 1e-8)

            for a in [0.7, 1.0, 1.3]:
                for b in [0.0, 0.2, 0.5]:
                    for c in [0.0, 0.2, 0.5]:
                        fused_val = 1.0 / (1.0 + np.exp(-(a * val_logits_np + b * z_da_va_norm + c * z_ct_va_norm)))
                        tau, vm = find_optimal_threshold(y_val, fused_val, steps=40)
                        if vm['f1'] > best_val_f1_m3:
                            best_val_f1_m3 = vm['f1']
                            best_alpha, best_beta, best_gamma, best_tau_m3 = a, b, c, tau

            fused_test = 1.0 / (1.0 + np.exp(-(best_alpha * test_logits_np + best_beta * z_da_te_norm + best_gamma * z_ct_te_norm)))
            preds_m3 = (fused_test >= best_tau_m3).astype(int)
            m3_m = compute_metrics(y_test, preds_m3, fused_test)
            m3_m.update(compute_precision_recall_at_k(y_test, fused_test, [10, 20, 50]))
            m3_m['calibrated_weights'] = {
                'alpha': best_alpha, 'beta': best_beta, 'gamma': best_gamma, 'tau': best_tau_m3
            }
            raw_results['M3_Calibrated_Late_Fusion'][seed][test_fam] = m3_m

            logger.info(f"  [Seed {seed} | {test_fam}] M0 F1={m0_m['f1']:.4f} | M1_S={m1s_m['f1']:.4f} | M1_U={m1u_m['f1']:.4f} | M3 F1={m3_m['f1']:.4f} (PR-AUC: M0={m0_m['pr_auc']:.4f}, M3={m3_m['pr_auc']:.4f})")

    # =====================================================================
    # STATISTICAL ANALYSIS & AGGREGATION
    # Disaggregate sigma_family vs sigma_seed
    # Compute paired delta (M3 - M0) across all (seed, family) pairs
    # =====================================================================
    logger.info("=== Computing Statistical Disaggregation & Paired Hypothesis Tests ===")

    paired_delta_pr = []
    paired_delta_f1 = []
    paired_delta_mcc = []

    for s in seeds:
        for f in folds:
            m0_f = raw_results['M0_HeteroGNN'][s][f]
            m3_f = raw_results['M3_Calibrated_Late_Fusion'][s][f]
            paired_delta_pr.append(m3_f['pr_auc'] - m0_f['pr_auc'])
            paired_delta_f1.append(m3_f['f1'] - m0_f['f1'])
            paired_delta_mcc.append(m3_f['mcc'] - m0_f['mcc'])

    # Paired Statistics
    def _paired_stats(delta_arr):
        arr = np.array(delta_arr)
        mean_d = float(np.mean(arr))
        std_d = float(np.std(arr, ddof=1))
        n = len(arr)
        se = std_d / math.sqrt(n)
        ci_95 = (mean_d - 1.96 * se, mean_d + 1.96 * se)
        # Paired t-test (H0: mean == 0)
        t_stat, p_val = stats.ttest_1samp(arr, 0.0)
        try:
            w_stat, p_wilcoxon = stats.wilcoxon(arr[arr != 0])
        except Exception:
            w_stat, p_wilcoxon = 0.0, 1.0

        return {
            'mean_delta': round(mean_d, 4),
            'std_delta': round(std_d, 4),
            'ci_95_low': round(float(ci_95[0]), 4),
            'ci_95_high': round(float(ci_95[1]), 4),
            't_stat': round(float(t_stat), 4),
            'p_value_parametric': round(float(p_val), 4),
            'p_value_wilcoxon': round(float(p_wilcoxon), 4)
        }

    stat_summary = {
        'delta_pr_auc': _paired_stats(paired_delta_pr),
        'delta_f1': _paired_stats(paired_delta_f1),
        'delta_mcc': _paired_stats(paired_delta_mcc)
    }

    # Macro summaries disaggregated
    final_detector_summary = {}

    for det in detectors:
        # F_s,f matrix of shape (n_seeds, n_families)
        f1_mat = np.zeros((len(seeds), len(folds)))
        pr_mat = np.zeros((len(seeds), len(folds)))
        mcc_mat = np.zeros((len(seeds), len(folds)))
        fp1k_mat = np.zeros((len(seeds), len(folds)))
        p10_mat = np.zeros((len(seeds), len(folds)))

        for i, s in enumerate(seeds):
            for j, f in enumerate(folds):
                f1_mat[i, j] = raw_results[det][s][f]['f1']
                pr_mat[i, j] = raw_results[det][s][f]['pr_auc']
                mcc_mat[i, j] = raw_results[det][s][f]['mcc']
                fp1k_mat[i, j] = raw_results[det][s][f]['fp_per_1k']
                p10_mat[i, j] = raw_results[det][s][f]['p@10']

        # 1. Macro-LOFO across 5 families per seed: shape (n_seeds,)
        macro_per_seed_f1 = np.mean(f1_mat, axis=1)
        macro_per_seed_pr = np.mean(pr_mat, axis=1)
        macro_per_seed_mcc = np.mean(mcc_mat, axis=1)

        # 2. Per-family average across seeds: shape (n_families,)
        family_avg_f1 = np.mean(f1_mat, axis=0)
        family_avg_pr = np.mean(pr_mat, axis=0)

        # 3. Overall pooled mean
        overall_mean_f1 = float(np.mean(f1_mat))
        sigma_seed_f1 = float(np.std(macro_per_seed_f1, ddof=1)) if len(seeds) > 1 else 0.0
        sigma_family_f1 = float(np.std(family_avg_f1, ddof=1))

        final_detector_summary[det] = {
            'overall_mean_f1': round(overall_mean_f1, 4),
            'sigma_seed_f1': round(sigma_seed_f1, 4),
            'sigma_family_f1': round(sigma_family_f1, 4),
            'overall_mean_pr_auc': round(float(np.mean(pr_mat)), 4),
            'sigma_seed_pr_auc': round(float(np.std(macro_per_seed_pr, ddof=1)) if len(seeds) > 1 else 0.0, 4),
            'sigma_family_pr_auc': round(float(np.std(family_avg_pr, ddof=1)), 4),
            'overall_mean_mcc': round(float(np.mean(mcc_mat)), 4),
            'overall_mean_fp_per_1k': round(float(np.mean(fp1k_mat)), 2),
            'overall_mean_p@10': round(float(np.mean(p10_mat)), 4),
            'worst_family_f1_avg': round(float(np.min(family_avg_f1)), 4),
            'per_family_f1_avg': {folds[j]: round(float(family_avg_f1[j]), 4) for j in range(len(folds))},
            'per_family_pr_auc_avg': {folds[j]: round(float(family_avg_pr[j]), 4) for j in range(len(folds))}
        }

        logger.info(f"==> [{det}]: F1 = {final_detector_summary[det]['overall_mean_f1']} (sigma_seed={sigma_seed_f1:.4f}, sigma_family={sigma_family_f1:.4f}) | PR-AUC = {final_detector_summary[det]['overall_mean_pr_auc']} | Worst-Family F1 = {final_detector_summary[det]['worst_family_f1_avg']}")

    return {
        'detector_summary': final_detector_summary,
        'paired_hypothesis_tests': stat_summary,
        'raw_results': raw_results
    }


# =========================================================================
# MAIN EXECUTION
# =========================================================================

def main():
    start_time = time.time()
    logger.info("Starting Leakage-Free Relation-Specific Dirichlet Non-Conformity Experiments...")
    device = get_device()
    logger.info(f"Using compute device: {device}")

    # Discover circuits by family from actual directory names on disk
    graphs_dir = REPO_ROOT / 'data' / 'circuits' / 'graphs'
    all_circuit_dirs = sorted([d.name for d in graphs_dir.glob('*') if d.is_dir()])

    fam_circuits = {fam: [] for fam in CIRCUIT_FAMILIES}
    for cname in all_circuit_dirs:
        for fam, pats in CIRCUIT_FAMILIES.items():
            if any(p in cname for p in pats):
                fam_circuits[fam].append(cname)
                break

    for fam, clist in fam_circuits.items():
        logger.info(f"Family {fam}: {len(clist)} circuits found")

    # 1. Run Detailed Dirichlet Ablations (Operator semantics, signed vs absolute, layer depth)
    ablation_summary = run_dirichlet_detailed_ablations(fam_circuits, device)

    # 2. Run Multi-Seed 5-Detector LOFO Benchmark (M0, M1_S, M1_U, M2, M3)
    benchmark_summary = run_multiseed_detector_benchmark(fam_circuits, device, seeds=[42, 123, 456])

    total_time = round(time.time() - start_time, 2)
    logger.info(f"All experiments completed successfully in {total_time}s!")

    final_payload = {
        'execution_time_seconds': total_time,
        'ablation_summary': ablation_summary,
        'benchmark_summary': benchmark_summary['detector_summary'],
        'paired_hypothesis_tests': benchmark_summary['paired_hypothesis_tests'],
        'raw_results': benchmark_summary['raw_results']
    }

    out_file = OUTPUT_DIR / 'dirichlet_leakage_free_experiments.json'
    with open(out_file, 'w') as f:
        json.dump(final_payload, f, indent=2)

    logger.info(f"Saved complete verified experimental data to: {out_file}")


if __name__ == '__main__':
    main()
