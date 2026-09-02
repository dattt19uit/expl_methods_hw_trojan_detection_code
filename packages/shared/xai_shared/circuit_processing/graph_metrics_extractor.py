#!/usr/bin/env python3
"""
Graph Metrics Extractor

Computes 5 Hasegawa topological features (LGFi, ffi, ffo, PI, PO) + 8 advanced
graph topological features directly from structural graph CSV files (nodes.csv and edges.csv).
"""

import os
import csv
import math
import time
import logging
from pathlib import Path
import networkx as nx

logger = logging.getLogger(__name__)

# Standard Flip-Flop and Latch cell types across libraries
FF_TYPES = {
    'SDFFSRX1', 'DFFARX1', 'DFFASX1', 'DFFNX2', 'DFFX2', 'SDFFX1',
    'LSDNENX1', 'LSDNX1', 'ff', 'flopd', 'fflopd', 'flopdrs', 'fflopdrs',
    'GTECH_FD1', 'GTECH_FD2', 'GTECH_FD3'
}

BASE_5_FEATURES = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']
GRAPH_8_FEATURES = [
    'in_degree', 'out_degree', 'pagerank', 'betweenness',
    'closeness', 'clustering', 'core_number', 'logic_depth_ratio'
]
ALL_13_NUMERIC_FEATURES = BASE_5_FEATURES + GRAPH_8_FEATURES


def extract_metrics_from_graph_csv(graph_dir: Path, output_file: Path) -> bool:
    """
    Read nodes.csv and edges.csv from graph_dir, compute 13 topological features
    (5 Hasegawa + 8 advanced graph features), and save to output_file in CSV format.
    """
    nodes_csv = graph_dir / 'nodes.csv'
    edges_csv = graph_dir / 'edges.csv'

    if not nodes_csv.exists() or not edges_csv.exists():
        logger.error(f"Missing nodes.csv or edges.csv in {graph_dir}")
        return False

    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load nodes and classify node types
    G = nx.DiGraph()
    G_data = nx.DiGraph()  # Graph filtering out clock/reset control nets
    raw_nodes = {}
    PI = set()
    PO = set()
    FF = set()
    trojan_nodes = set()

    with open(nodes_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            node = row['node']
            kind = row.get('kind', '')
            cell_type = row.get('cell_type', '')
            node_type = row.get('type', '')
            is_output = row.get('output', '').lower() in ('true', '1')
            is_trojan = row.get('is_trojan', '0') == '1' or row.get('trojan', '0') == '1'

            raw_nodes[node] = row
            G.add_node(node, kind=kind, cell_type=cell_type, type=node_type, is_trojan=is_trojan)
            G_data.add_node(node, kind=kind, cell_type=cell_type, type=node_type, is_trojan=is_trojan)

            if is_trojan:
                trojan_nodes.add(node)

            # Check Primary Inputs
            if node_type == 'input' or (kind == 'net' and node_type == 'input'):
                PI.add(node)
            # Check Primary Outputs
            if is_output or node_type == 'output' or (kind == 'net' and node_type == 'output'):
                PO.add(node)
            # Check Flip-Flops
            if cell_type in FF_TYPES:
                FF.add(node)

    # 2. Load edges and construct both full graph and clean data graph (is_control == 0)
    with open(edges_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = row['source']
            dst = row['target']
            port = row.get('port', '')
            direction = row.get('direction', '')
            is_ctrl = row.get('is_control', '0') == '1'
            G.add_edge(src, dst, port=port, direction=direction, is_control=is_ctrl)
            if not is_ctrl:
                G_data.add_edge(src, dst, port=port, direction=direction)

    # 3. High-performance multi-source Dijkstra shortest path computations
    GC = G
    GR = nx.DiGraph.reverse(G)

    dist_to_PI = dict(nx.multi_source_dijkstra_path_length(GC, PI)) if PI else {}
    dist_to_PO = dict(nx.multi_source_dijkstra_path_length(GR, PO)) if PO else {}
    dist_to_FF_in = dict(nx.multi_source_dijkstra_path_length(GC, FF)) if FF else {}
    dist_to_FF_out = dict(nx.multi_source_dijkstra_path_length(GR, FF)) if FF else {}

    # 4. Advanced Graph Topological Features computed on clean data-flow graph (G_data)
    # PageRank (data flow importance without clock noise)
    try:
        pr_scores = nx.pagerank(G_data, alpha=0.85, max_iter=200, tol=1e-6)
    except Exception:
        pr_scores = {n: 1.0 / max(1, len(G_data)) for n in G_data}

    # In/Out Degree
    in_degrees = dict(G_data.in_degree())
    out_degrees = dict(G_data.out_degree())

    # Undirected projection for clustering and core number
    G_undir = G_data.to_undirected()
    clustering_coeffs = nx.clustering(G_undir)
    core_numbers = nx.core_number(G_undir)

    # Approximate Betweenness Centrality using sampling on large graphs for speed
    n_nodes = len(G_data)
    k_samples = min(n_nodes, 150) if n_nodes > 500 else None
    try:
        betweenness_scores = nx.betweenness_centrality(G_data, k=k_samples, normalized=True, weight=None)
    except Exception:
        betweenness_scores = {n: 0.0 for n in G_data}

    # Closeness Centrality
    try:
        closeness_scores = nx.closeness_centrality(G_data)
    except Exception:
        closeness_scores = {n: 0.0 for n in G_data}

    # 5. Compute metrics for each node and write output CSV
    header = ["Line", "type", "name", "net"] + ALL_13_NUMERIC_FEATURES + ["Trojan"]
    with open(output_file, 'w', encoding='utf-8', newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow(header)

        line_num = 0
        for net in sorted(G.nodes()):
            line_num += 1
            meta = raw_nodes.get(net, {})
            cell_type = meta.get('cell_type', '')
            kind = meta.get('kind', '')

            # Logic Gate Fanin level 2 (LGFi)
            gates = list(G.predecessors(net))
            fanin = []
            for g in gates:
                fanin.extend(list(G.predecessors(g)))
            LGFi = len(fanin)

            # Distance to Flip-Flop Input (ffi)
            if net in FF:
                preds = list(G.predecessors(net))
                ffi_dist = min([dist_to_FF_in.get(p, 99999) + 1 for p in preds], default=99999)
            else:
                ffi_dist = dist_to_FF_in.get(net, 99999)

            # Distance to Flip-Flop Output (ffo)
            if net in FF:
                succs = list(G.successors(net))
                ffo_dist = min([dist_to_FF_out.get(s, 99999) + 1 for s in succs], default=99999)
            else:
                ffo_dist = dist_to_FF_out.get(net, 99999)

            # Distance to Primary Inputs / Outputs
            nPI_dist = dist_to_PI.get(net, 99999)
            nPO_dist = dist_to_PO.get(net, 99999)

            # Convert to hops (distance - 1)
            nPO = 0 if net in PO else (99999 if nPO_dist >= 99999 else max(0, nPO_dist - 1))
            nPI = 0 if net in PI else (99999 if nPI_dist >= 99999 else max(0, nPI_dist - 1))

            ffi = nPI if ffi_dist >= 99999 else (0 if ffi_dist <= 1 else ffi_dist - 1)
            ffo = nPO if ffo_dist >= 99999 else (0 if ffo_dist <= 1 else ffo_dist - 1)

            if net in ['tie_0', 'tie_1', 'tie_x']:
                nPI = 0
                ffi = 0

            # Scale-invariant Logic Depth Ratio
            finite_pi = nPI if nPI < 99999 else 0
            finite_po = nPO if nPO < 99999 else 0
            depth_ratio = finite_pi / (finite_pi + finite_po + 1e-5)

            # Advanced Graph Features
            in_deg = in_degrees.get(net, 0)
            out_deg = out_degrees.get(net, 0)
            pr = pr_scores.get(net, 0.0)
            btw = betweenness_scores.get(net, 0.0)
            cls_cent = closeness_scores.get(net, 0.0)
            clust = clustering_coeffs.get(net, 0.0)
            k_core = core_numbers.get(net, 0)

            # Trojan label
            Trojan = 1 if net in trojan_nodes else 0

            # Node category type
            ctype = 'PI' if net in PI else 'PO' if net in PO else 'ff' if net in FF else 'nn'
            cname = cell_type if kind == 'cell' and cell_type else 'net'

            row_data = [
                f"{line_num:07}", ctype, cname, net,
                LGFi, ffi, ffo, nPI, nPO,
                in_deg, out_deg, f"{pr:.6f}", f"{btw:.6f}",
                f"{cls_cent:.6f}", f"{clust:.6f}", k_core, f"{depth_ratio:.6f}",
                Trojan
            ]
            writer.writerow(row_data)

    return True
