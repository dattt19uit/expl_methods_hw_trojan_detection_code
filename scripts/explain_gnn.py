#!/usr/bin/env python3
"""
Graph Explainable AI (Graph XAI) for Hardware Trojan Detection.

Uses GNNExplainer on HeteroTrojanGNN to discover the computational subgraph
connecting trigger nets, payload gates, and control signals.
Computes quantitative XAI metrics:
- Fidelity+ (Prediction drop when explaining subgraph is masked)
- Fidelity- (Prediction drop when only explaining subgraph is retained)
- Subgraph Sparsity (Fraction of irrelevant circuit pruned)
- Trojan Subgraph Localization Precision & Recall against ground-truth netlist.
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch_geometric.explain import Explainer, GNNExplainer

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.shared.xai_shared.graph_data.hetero_gnn import HeteroTrojanGNN
from packages.shared.xai_shared.graph_data.pyg_converter import CELL_FAMILIES, CircuitPyGConverter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GraphXAI')


def compute_fidelity_metrics(
    model: HeteroTrojanGNN,
    data,
    target_node_idx: int,
    edge_mask_dict: Dict,
    top_k_ratio: float = 0.20,
) -> Tuple[float, float, float]:
    """
    Computes Fidelity+, Fidelity-, and Sparsity.
    - Fidelity+: f(G) - f(G \ G_sub)  (Higher is better, shows necessity)
    - Fidelity-: f(G) - f(G_sub)      (Lower is better, shows sufficiency)
    - Sparsity: 1 - (|E_sub| / |E|)
    """
    model.eval()
    with torch.no_grad():
        # Baseline probability on original graph
        orig_logits = model(data.x_dict, data.edge_index_dict).view(-1)
        orig_prob = torch.sigmoid(orig_logits[target_node_idx]).item()

        # Build masked edge dictionaries
        masked_edge_index_dict = {}
        subgraph_edge_index_dict = {}

        total_edges = 0
        kept_subgraph_edges = 0

        for et, edge_index in data.edge_index_dict.items():
            num_e = edge_index.size(1)
            total_edges += num_e
            if num_e == 0:
                masked_edge_index_dict[et] = edge_index
                subgraph_edge_index_dict[et] = edge_index
                continue

            mask = edge_mask_dict.get(et)
            if mask is None or mask.numel() == 0:
                mask = torch.zeros(num_e)

            # Determine top-k threshold
            k = max(1, int(num_e * top_k_ratio))
            _, top_indices = torch.topk(mask, k=k)
            top_mask = torch.zeros(num_e, dtype=torch.bool)
            top_mask[top_indices] = True

            # G \ G_sub (remove top-k important edges)
            masked_edge_index_dict[et] = edge_index[:, ~top_mask]
            # G_sub (keep only top-k important edges)
            subgraph_edge_index_dict[et] = edge_index[:, top_mask]
            kept_subgraph_edges += k

        # Prediction without explaining subgraph
        masked_logits = model(data.x_dict, masked_edge_index_dict).view(-1)
        masked_prob = torch.sigmoid(masked_logits[target_node_idx]).item()

        # Prediction with only explaining subgraph
        subgraph_logits = model(data.x_dict, subgraph_edge_index_dict).view(-1)
        subgraph_prob = torch.sigmoid(subgraph_logits[target_node_idx]).item()

    fid_plus = float(orig_prob - masked_prob)
    fid_minus = float(orig_prob - subgraph_prob)
    sparsity = float(1.0 - (kept_subgraph_edges / max(1, total_edges)))

    return fid_plus, fid_minus, sparsity


def evaluate_trojan_localization(
    data,
    circuit_name: str,
    target_node_idx: int,
    edge_mask_dict: Dict,
    top_k_edges: int = 20,
) -> Tuple[float, float]:
    """
    Evaluates how accurately the GNNExplainer edge mask localizes ground-truth Trojan elements.
    Ground truth Trojan edges and cells are checked against edges.csv and nodes.csv.
    """
    edges_csv = Path('data/circuits/graphs') / circuit_name / 'edges.csv'
    if not edges_csv.exists():
        return 0.0, 0.0

    df_edges = pd.read_csv(edges_csv)
    # Ground truth trojan context in edges.csv
    trojan_edges = df_edges[df_edges['trojan_context'] == 'trojan']
    if len(trojan_edges) == 0:
        # Fallback: edges incident to is_trojan cells
        df_nodes = pd.read_csv(Path('data/circuits/graphs') / circuit_name / 'nodes.csv')
        trojan_nodes = set(df_nodes[df_nodes['is_trojan'] == 1]['node'])
        trojan_edges = df_edges[df_edges['source'].isin(trojan_nodes) | df_edges['target'].isin(trojan_nodes)]

    gt_trojan_pairs = set(zip(trojan_edges['source'], trojan_edges['target']))
    if len(gt_trojan_pairs) == 0:
        return 1.0, 1.0

    cell_names = data['cell'].node_names
    net_names = data['net'].node_names

    # Collect all edges with their explanation weights
    scored_edges = []
    for et, edge_index in data.edge_index_dict.items():
        src_type, rel, dst_type = et
        if rel.startswith('rev_'):
            continue  # ignore reverse auxiliary edges for reporting

        mask = edge_mask_dict.get(et)
        if mask is None or mask.numel() == 0:
            continue

        mask_np = mask.cpu().numpy()
        for e_idx in range(edge_index.size(1)):
            s = edge_index[0, e_idx].item()
            d = edge_index[1, e_idx].item()
            s_name = cell_names[s] if src_type == 'cell' else net_names[s]
            d_name = cell_names[d] if dst_type == 'cell' else net_names[d]
            w = float(mask_np[e_idx])
            scored_edges.append((s_name, d_name, w, rel))

    scored_edges.sort(key=lambda x: x[2], reverse=True)
    top_edges = scored_edges[:top_k_edges]

    hits = sum(1 for s, d, _, _ in top_edges if (s, d) in gt_trojan_pairs or (d, s) in gt_trojan_pairs)
    loc_prec = hits / max(1, len(top_edges))
    loc_rec = hits / max(1, min(len(gt_trojan_pairs), top_k_edges))

    return float(loc_prec), float(loc_rec)


def run_graph_xai_benchmark(
    circuits_to_explain: List[str] = [
        'RS232-T1000_90nm',
        'RS232-T1200_90nm',
        's15850-T100_generic-180nm',
        's35932-T100_generic-180nm',
        's38417-T100_generic-180nm',
        's38584-T100_generic-180nm',
    ],
    model_path: str = 'data/models/hetero_gnn_best.pt',
    output_path: str = 'data/explanations/gnn/gnn_explanations.json',
) -> Dict:
    """
    Runs GNNExplainer on trained HeteroTrojanGNN across benchmark circuits.
    """
    logger.info("Initializing Graph XAI Benchmark with GNNExplainer...")
    converter = CircuitPyGConverter()

    model = HeteroTrojanGNN(hidden_dim=64, num_layers=2)
    ckpt = torch.load(model_path, map_location='cpu')
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()

    explainer = Explainer(
        model=model,
        algorithm=GNNExplainer(epochs=30),
        explanation_type='model',
        node_mask_type='attributes',
        edge_mask_type='object',
        model_config=dict(
            mode='binary_classification',
            task_level='node',
            return_type='raw'
        )
    )

    all_results = {}
    aggregate_fid_plus = []
    aggregate_fid_minus = []
    aggregate_sparsity = []
    aggregate_loc_prec = []
    aggregate_loc_rec = []

    for cname in circuits_to_explain:
        logger.info(f"Explaining circuit: {cname}...")
        try:
            data = converter.convert_circuit(cname)
        except Exception as e:
            logger.warning(f"Could not load circuit {cname}: {e}")
            continue

        trojan_indices = (data['cell'].y == 1).nonzero(as_tuple=True)[0].cpu().numpy()
        if len(trojan_indices) == 0:
            logger.info(f"No trojan cells found in {cname}. Skipping.")
            continue

        circuit_explanations = []
        # Explain up to 5 trojan gates per circuit
        targets = trojan_indices[:5]
        for t_idx in targets:
            cell_name = data['cell'].node_names[t_idx]
            t0 = time.time()
            expl = explainer(data.x_dict, data.edge_index_dict, index=int(t_idx))
            dt = time.time() - t0

            # Compute fidelity metrics
            fid_p, fid_m, sp = compute_fidelity_metrics(model, data, int(t_idx), expl.edge_mask_dict)
            # Compute ground-truth localization
            loc_p, loc_r = evaluate_trojan_localization(data, cname, int(t_idx), expl.edge_mask_dict)

            # Node feature attribution (cell)
            cell_feat_mask = expl.node_mask_dict['cell'][t_idx].cpu().numpy()
            top_cell_feat_indices = np.argsort(cell_feat_mask)[::-1][:5]

            feat_names = CELL_FAMILIES + ['is_sequential'] + converter.feature_cols
            top_features = [
                {'feature': feat_names[idx] if idx < len(feat_names) else f'feat_{idx}', 'importance': float(cell_feat_mask[idx])}
                for idx in top_cell_feat_indices
            ]

            circuit_explanations.append({
                'cell_index': int(t_idx),
                'cell_name': cell_name,
                'time_seconds': float(dt),
                'fidelity_plus': fid_p,
                'fidelity_minus': fid_m,
                'sparsity': sp,
                'localization_precision': loc_p,
                'localization_recall': loc_r,
                'top_node_features': top_features,
            })

            aggregate_fid_plus.append(fid_p)
            aggregate_fid_minus.append(fid_m)
            aggregate_sparsity.append(sp)
            aggregate_loc_prec.append(loc_p)
            aggregate_loc_rec.append(loc_r)

        all_results[cname] = circuit_explanations

    summary = {
        'method': 'GNNExplainer (HeteroTrojanGNN)',
        'fidelity_plus_mean': float(np.mean(aggregate_fid_plus)) if aggregate_fid_plus else 0.0,
        'fidelity_minus_mean': float(np.mean(aggregate_fid_minus)) if aggregate_fid_minus else 0.0,
        'sparsity_mean': float(np.mean(aggregate_sparsity)) if aggregate_sparsity else 0.0,
        'localization_precision_mean': float(np.mean(aggregate_loc_prec)) if aggregate_loc_prec else 0.0,
        'localization_recall_mean': float(np.mean(aggregate_loc_rec)) if aggregate_loc_rec else 0.0,
        'circuits_explained': list(all_results.keys()),
        'circuit_details': all_results,
    }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Graph XAI Benchmark complete. Results saved to {output_path}")
    logger.info(f"Fidelity+: {summary['fidelity_plus_mean']:.4f}, Fidelity-: {summary['fidelity_minus_mean']:.4f}, "
                f"Localization Precision: {summary['localization_precision_mean']:.4f}, Recall: {summary['localization_recall_mean']:.4f}")
    return summary


if __name__ == '__main__':
    run_graph_xai_benchmark()

