"""
PyTorch Geometric (PyG) Converter for Baseline NetlistX Circuit Graphs.

Converts the author's original graph representation (c.graph from netlistx
after merge_cells and remove_cells(['wire'])) along with the 13 baseline
tabular features into homogeneous PyG Data objects.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data

import xai_shared.netlistx as nl

logger = logging.getLogger(__name__)

BASELINE_FEATURE_COLS = [
    'LGFi', 'ffi', 'ffo', 'PI', 'PO',
    'in_degree', 'out_degree', 'pagerank', 'betweenness',
    'closeness', 'clustering', 'core_number', 'logic_depth_ratio'
]


class BaselinePyGConverter:
    """
    Converts NetlistX baseline graphs and tabular features into PyTorch Geometric Data graphs.
    Caches parsed graphs to data/circuits/baseline_pyg/ for fast loading.
    """

    def __init__(
        self,
        circuits_csv_dir: Union[str, Path] = 'data/circuits',
        circuit_configs_path: Union[str, Path] = 'configs/circuit_configs.json',
        cache_dir: Union[str, Path] = 'data/circuits/baseline_pyg',
        edges_dir: Union[str, Path] = 'data/circuits/baseline_graphs',
        feature_cols: Optional[List[str]] = None,
        bidirectional: bool = True,
    ):
        self.circuits_csv_dir = Path(circuits_csv_dir)
        self.circuit_configs_path = Path(circuit_configs_path)
        self.cache_dir = Path(cache_dir)
        self.edges_dir = Path(edges_dir)
        self.feature_cols = feature_cols or BASELINE_FEATURE_COLS
        self.bidirectional = bidirectional

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.edges_dir.mkdir(parents=True, exist_ok=True)

        self._configs_by_basename = self._load_configs()

    def _load_configs(self) -> Dict[str, Dict]:
        """Map base circuit name (e.g. RS232-T1000_90nm) to its config."""
        if not self.circuit_configs_path.exists():
            return {}
        with open(self.circuit_configs_path, 'r', encoding='utf-8') as f:
            raw_configs = json.load(f)

        mapping = {}
        for key, cfg in raw_configs.items():
            base_name = f"{cfg['part']}-{cfg['impl']}_{cfg['tech']}"
            mapping[base_name] = cfg
        return mapping

    def extract_and_save_edges(self, circuit_name: str) -> Path:
        """
        Extract edges from NetlistX c.graph for a circuit and save to CSV.
        """
        circuit_edges_dir = self.edges_dir / circuit_name
        circuit_edges_dir.mkdir(parents=True, exist_ok=True)
        edges_file = circuit_edges_dir / 'edges.csv'

        if edges_file.exists():
            return edges_file

        if circuit_name not in self._configs_by_basename:
            raise KeyError(f"Circuit {circuit_name} not found in {self.circuit_configs_path}")

        cfg = self._configs_by_basename[circuit_name]
        vpath = cfg['verilog_path']
        vname = cfg.get('verilog_name', 'circuit')
        tech = cfg['tech']
        # Map generic-180nm to 90nm compatible library
        netlistx_techlib = '90nm' if tech == 'generic-180nm' else tech

        logger.debug(f"Parsing baseline graph for {circuit_name} from {vpath}...")
        c = nl.read_netlist(vpath, name=vname, fmt='verilog', techlib=netlistx_techlib)
        nl.merge_cells(c, nl.list_cell_names(c))
        nl.remove_cells(c, ['wire'])

        edge_list = list(c.graph.edges)
        df_edges = pd.DataFrame(edge_list, columns=['source', 'target'])
        df_edges.to_csv(edges_file, index=False)
        logger.debug(f"Saved {len(df_edges)} edges to {edges_file}")

        # Also ensure nodes.csv is saved in the baseline_graphs directory
        nodes_file = circuit_edges_dir / 'nodes.csv'
        if not nodes_file.exists():
            csv_file = self.circuits_csv_dir / f"{circuit_name}.csv"
            if csv_file.exists():
                df_c = pd.read_csv(csv_file)
                df_nodes = pd.DataFrame({
                    'node': df_c['net'],
                    'type': df_c['type'],
                    'name': df_c['name'],
                    'is_trojan': df_c['Trojan'],
                })
                for col in self.feature_cols:
                    if col in df_c.columns:
                        df_nodes[col] = df_c[col]
                df_nodes.to_csv(nodes_file, index=False)

        return edges_file

    def convert_circuit(
        self,
        circuit_name: str,
        scaler_mean: Optional[np.ndarray] = None,
        scaler_std: Optional[np.ndarray] = None,
        force_recompute: bool = False,
    ) -> Data:
        """
        Convert a single circuit to PyG Data object.
        Uses cached .pt file if available.
        """
        cached_pt = self.cache_dir / f"{circuit_name}.pt"
        if not force_recompute and cached_pt.exists():
            try:
                return torch.load(cached_pt, weights_only=False)
            except Exception as e:
                logger.warning(f"Failed to load cached {cached_pt}: {e}. Recomputing...")

        # 1. Load node features and labels from data/circuits/{circuit_name}.csv
        csv_file = self.circuits_csv_dir / f"{circuit_name}.csv"
        if not csv_file.exists():
            raise FileNotFoundError(f"Missing node CSV file: {csv_file}")

        df_nodes = pd.read_csv(csv_file)
        node_names = df_nodes['net'].astype(str).tolist()
        node_to_idx = {name: i for i, name in enumerate(node_names)}
        num_nodes = len(node_names)

        # Extract 13 numerical features
        features = df_nodes[self.feature_cols].fillna(0.0).values.astype(np.float32)
        if scaler_mean is not None and scaler_std is not None:
            features = (features - scaler_mean) / (scaler_std + 1e-8)

        x = torch.tensor(features, dtype=torch.float32)

        # Labels
        y = torch.tensor(df_nodes['Trojan'].fillna(0).astype(int).values, dtype=torch.float32)

        # 2. Load or extract edges
        edges_file = self.extract_and_save_edges(circuit_name)
        df_edges = pd.read_csv(edges_file)

        src_indices = []
        dst_indices = []
        for src, dst in zip(df_edges['source'].astype(str), df_edges['target'].astype(str)):
            if src in node_to_idx and dst in node_to_idx:
                src_indices.append(node_to_idx[src])
                dst_indices.append(node_to_idx[dst])

        if len(src_indices) > 0:
            edge_index_fwd = torch.tensor([src_indices, dst_indices], dtype=torch.long)
            if self.bidirectional:
                # Add reverse edges for two-way message passing (matching HeteroTrojanGNN)
                edge_index_rev = edge_index_fwd.flip(0)
                edge_index = torch.cat([edge_index_fwd, edge_index_rev], dim=1)
                # Remove duplicate edges if any
                edge_index = torch.unique(edge_index, dim=1)
            else:
                edge_index = edge_index_fwd
        else:
            edge_index = torch.empty((2, 0), dtype=torch.long)

        data = Data(
            x=x,
            edge_index=edge_index,
            y=y,
            circuit_name=circuit_name,
            num_nodes=num_nodes,
        )

        # Cache to disk
        try:
            torch.save(data, cached_pt)
        except Exception as e:
            logger.warning(f"Could not cache PyG data to {cached_pt}: {e}")

        return data

    def convert_all(
        self,
        force_recompute: bool = False,
    ) -> List[Data]:
        """Convert all 30 benchmark circuits."""
        circuits = sorted([f.stem for f in self.circuits_csv_dir.glob('*.csv')])
        logger.info(f"Converting/loading {len(circuits)} baseline circuit graphs...")
        graphs = []
        for cname in circuits:
            graphs.append(self.convert_circuit(cname, force_recompute=force_recompute))
        return graphs
