"""
PyTorch Geometric (PyG) HeteroData Converter for Hardware Trojan Detection.

Converts Semantic Graph IR (nodes.csv, edges.csv) and tabular features into
HeteroData objects suitable for Heterogeneous Graph Neural Networks (H-GNN).
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import torch
from torch_geometric.data import HeteroData

# Standard gate cell families for 70 technology library cells
CELL_FAMILIES = [
    'AND', 'NAND', 'OR', 'NOR', 'XOR', 'XNOR',
    'INV', 'BUF', 'DFF', 'SDFF', 'AO', 'AOI',
    'OA', 'OAI', 'MUX', 'MX', 'LSD', 'ISOL', 'SPECIAL', 'OTHER'
]
CELL_FAMILY_TO_IDX = {fam: idx for idx, fam in enumerate(CELL_FAMILIES)}

NET_TYPES = ['wire', 'input', 'buf', '0', '1', 'other']
NET_TYPE_TO_IDX = {t: idx for idx, t in enumerate(NET_TYPES)}


def get_cell_family(cell_type: str) -> str:
    """Categorize standard cell type into functional logic family."""
    if not isinstance(cell_type, str) or not cell_type:
        return 'OTHER'
    ct = cell_type.upper()
    if ct.startswith('SDFF'):
        return 'SDFF'
    if ct.startswith('DFF'):
        return 'DFF'
    if ct.startswith('NAND'):
        return 'NAND'
    if ct.startswith('AND'):
        return 'AND'
    if ct.startswith('NOR'):
        return 'NOR'
    if ct.startswith('OR'):
        return 'OR'
    if ct.startswith('XNOR'):
        return 'XNOR'
    if ct.startswith('XOR'):
        return 'XOR'
    if ct.startswith('INV'):
        return 'INV'
    if ct.startswith('BUF') or ct.startswith('NBUFF'):
        return 'BUF'
    if ct.startswith('AOI'):
        return 'AOI'
    if ct.startswith('AO'):
        return 'AO'
    if ct.startswith('OAI'):
        return 'OAI'
    if ct.startswith('OA'):
        return 'OA'
    if ct.startswith('MUX') or ct.startswith('MX'):
        return 'MUX'
    if ct.startswith('LSD'):
        return 'LSD'
    if ct.startswith('ISOL'):
        return 'ISOL'
    return 'OTHER'


class CircuitPyGConverter:
    """
    Converts graph CSVs (nodes.csv, edges.csv) and tabular features
    into PyTorch Geometric HeteroData graphs.
    """

    def __init__(
        self,
        graphs_dir: Union[str, Path] = 'data/circuits/graphs',
        circuits_feature_dir: Optional[Union[str, Path]] = 'data/circuits_graph_ir',
        feature_cols: Optional[List[str]] = None,
    ):
        self.graphs_dir = Path(graphs_dir)
        self.circuits_feature_dir = Path(circuits_feature_dir) if circuits_feature_dir else None
        
        if feature_cols is None:
            # 13 features: 5 Hasegawa + 8 Graph IR
            self.feature_cols = [
                'LGFi', 'ffi', 'ffo', 'PI', 'PO',
                'in_degree', 'out_degree', 'pagerank', 'betweenness',
                'closeness', 'clustering', 'core_number', 'logic_depth_ratio'
            ]
        else:
            self.feature_cols = feature_cols

    def convert_circuit(
        self,
        circuit_name: str,
        scaler_mean: Optional[np.ndarray] = None,
        scaler_std: Optional[np.ndarray] = None,
    ) -> HeteroData:
        """
        Convert a single circuit into a HeteroData object.
        """
        circuit_graph_dir = self.graphs_dir / circuit_name
        nodes_file = circuit_graph_dir / 'nodes.csv'
        edges_file = circuit_graph_dir / 'edges.csv'

        if not nodes_file.exists() or not edges_file.exists():
            raise FileNotFoundError(f"Missing nodes.csv or edges.csv in {circuit_graph_dir}")

        df_nodes = pd.read_csv(nodes_file)
        df_edges = pd.read_csv(edges_file)

        # Tabular features if available
        df_features = None
        if self.circuits_feature_dir:
            feat_file = self.circuits_feature_dir / f"{circuit_name}.csv"
            if feat_file.exists():
                df_features = pd.read_csv(feat_file).set_index('net')

        # Separate cell and net nodes
        cell_mask = df_nodes['kind'] == 'cell'
        net_mask = df_nodes['kind'] == 'net'

        cell_nodes = df_nodes[cell_mask].copy().reset_index(drop=True)
        net_nodes = df_nodes[net_mask].copy().reset_index(drop=True)

        cell_to_idx = {name: i for i, name in enumerate(cell_nodes['node'])}
        net_to_idx = {name: i for i, name in enumerate(net_nodes['node'])}

        num_cells = len(cell_nodes)
        num_nets = len(net_nodes)

        # 1. Cell features:
        # - One-hot logic family (20 dim)
        # - Sequential flag (1 dim)
        # - Tabular features (len(feature_cols) dim, e.g. 13 dim)
        cell_fam_indices = [
            CELL_FAMILY_TO_IDX.get(get_cell_family(ct), CELL_FAMILY_TO_IDX['OTHER'])
            for ct in cell_nodes['cell_type']
        ]
        cell_fam_onehot = np.zeros((num_cells, len(CELL_FAMILIES)), dtype=np.float32)
        cell_fam_onehot[np.arange(num_cells), cell_fam_indices] = 1.0

        is_seq = np.array([
            1.0 if 'DFF' in get_cell_family(ct) else 0.0
            for ct in cell_nodes['cell_type']
        ], dtype=np.float32).reshape(-1, 1)

        # Tabular features for cells
        if df_features is not None:
            cell_feats = []
            for name in cell_nodes['node']:
                if name in df_features.index:
                    row = df_features.loc[name]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                    vals = [float(row.get(col, 0.0) or 0.0) for col in self.feature_cols]
                else:
                    vals = [0.0] * len(self.feature_cols)
                cell_feats.append(vals)
            cell_feats = np.array(cell_feats, dtype=np.float32)
            if scaler_mean is not None and scaler_std is not None:
                cell_feats = (cell_feats - scaler_mean) / (scaler_std + 1e-8)
        else:
            cell_feats = np.zeros((num_cells, len(self.feature_cols)), dtype=np.float32)

        x_cell = np.hstack([cell_fam_onehot, is_seq, cell_feats])

        # Cell Labels
        y_cell = cell_nodes['is_trojan'].astype(int).values

        # 2. Net features:
        # - One-hot net type (6 dim)
        # - Is output flag (1 dim)
        # - Tabular features (len(feature_cols) dim)
        net_type_indices = [
            NET_TYPE_TO_IDX.get(str(t).strip().lower(), NET_TYPE_TO_IDX['other'])
            for t in net_nodes['type']
        ]
        net_type_onehot = np.zeros((num_nets, len(NET_TYPES)), dtype=np.float32)
        net_type_onehot[np.arange(num_nets), net_type_indices] = 1.0

        is_out = np.array([
            1.0 if (str(out).strip().lower() == 'true') else 0.0
            for out in net_nodes['output']
        ], dtype=np.float32).reshape(-1, 1)

        if df_features is not None:
            net_feats = []
            for name in net_nodes['node']:
                if name in df_features.index:
                    row = df_features.loc[name]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                    vals = [float(row.get(col, 0.0) or 0.0) for col in self.feature_cols]
                else:
                    vals = [0.0] * len(self.feature_cols)
                net_feats.append(vals)
            net_feats = np.array(net_feats, dtype=np.float32)
            if scaler_mean is not None and scaler_std is not None:
                net_feats = (net_feats - scaler_mean) / (scaler_std + 1e-8)
        else:
            net_feats = np.zeros((num_nets, len(self.feature_cols)), dtype=np.float32)

        x_net = np.hstack([net_type_onehot, is_out, net_feats])

        # 3. Build Edges:
        # data_input: net -> cell (is_control == 0)
        # control_input: net -> cell (is_control == 1)
        # outputs: cell -> net
        edge_data_in_src, edge_data_in_dst = [], []
        edge_ctrl_in_src, edge_ctrl_in_dst = [], []
        edge_out_src, edge_out_dst = [], []

        for _, row in df_edges.iterrows():
            src_name = row['source']
            dst_name = row['target']
            direction = str(row['direction']).strip().lower()
            is_ctrl = int(row.get('is_control', 0) or 0)

            if direction == 'input':
                # net -> cell
                if src_name in net_to_idx and dst_name in cell_to_idx:
                    s_idx = net_to_idx[src_name]
                    d_idx = cell_to_idx[dst_name]
                    if is_ctrl == 1:
                        edge_ctrl_in_src.append(s_idx)
                        edge_ctrl_in_dst.append(d_idx)
                    else:
                        edge_data_in_src.append(s_idx)
                        edge_data_in_dst.append(d_idx)
            elif direction == 'output':
                # cell -> net
                if src_name in cell_to_idx and dst_name in net_to_idx:
                    s_idx = cell_to_idx[src_name]
                    d_idx = net_to_idx[dst_name]
                    edge_out_src.append(s_idx)
                    edge_out_dst.append(d_idx)

        # Construct HeteroData
        data = HeteroData()
        data['cell'].x = torch.tensor(x_cell, dtype=torch.float32)
        data['cell'].y = torch.tensor(y_cell, dtype=torch.float32)
        data['cell'].node_names = list(cell_nodes['node'])

        data['net'].x = torch.tensor(x_net, dtype=torch.float32)
        data['net'].node_names = list(net_nodes['node'])

        # Forward edges
        def _to_tensor(srcs, dsts):
            if len(srcs) == 0:
                return torch.empty((2, 0), dtype=torch.long)
            return torch.tensor([srcs, dsts], dtype=torch.long)

        data['net', 'data_input', 'cell'].edge_index = _to_tensor(edge_data_in_src, edge_data_in_dst)
        data['net', 'control_input', 'cell'].edge_index = _to_tensor(edge_ctrl_in_src, edge_ctrl_in_dst)
        data['cell', 'outputs', 'net'].edge_index = _to_tensor(edge_out_src, edge_out_dst)

        # Reverse edges (to allow bidirectional message passing)
        data['cell', 'rev_data_input', 'net'].edge_index = _to_tensor(edge_data_in_dst, edge_data_in_src)
        data['cell', 'rev_control_input', 'net'].edge_index = _to_tensor(edge_ctrl_in_dst, edge_ctrl_in_src)
        data['net', 'rev_outputs', 'cell'].edge_index = _to_tensor(edge_out_dst, edge_out_src)

        data.circuit_name = circuit_name
        return data

