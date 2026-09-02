#!/usr/bin/env python3
"""
CLI Tool: xai-compute-graph-metrics

Batch computes 5 Hasegawa metrics for all circuit graphs in data/circuits/graphs/
and exports to data/circuits_graph_ir/*.csv
"""

import sys
import argparse
import logging
from pathlib import Path
from multiprocessing import Pool, cpu_count
from .graph_metrics_extractor import extract_metrics_from_graph_csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ComputeGraphMetricsCLI')


def _process_single_graph(args):
    graph_dir, output_file = args
    logger.info(f"Processing {graph_dir.name} -> {output_file.name}...")
    try:
        success = extract_metrics_from_graph_csv(graph_dir, output_file)
        if success:
            logger.info(f"  [OK] {graph_dir.name} completed successfully.")
            return (graph_dir.name, True, None)
        else:
            logger.error(f"  [FAILED] {graph_dir.name} extraction failed.")
            return (graph_dir.name, False, "Extraction error")
    except Exception as e:
        logger.error(f"  [ERROR] {graph_dir.name}: {e}")
        return (graph_dir.name, False, str(e))


def main():
    parser = argparse.ArgumentParser(description="Compute 5 Hasegawa metrics from nodes.csv & edges.csv")
    parser.add_argument('--graphs-dir', type=str, default='data/circuits/graphs',
                        help="Directory containing graph folders with nodes.csv and edges.csv")
    parser.add_argument('--output-dir', type=str, default='data/circuits_graph_ir',
                        help="Output directory to save computed feature CSV files")
    parser.add_argument('-j', '--jobs', type=int, default=max(1, cpu_count() - 1),
                        help="Number of parallel processes")
    parser.add_argument('--circuit', type=str, default=None,
                        help="Process only a specific circuit by folder name")

    args = parser.parse_args()

    graphs_dir = Path(args.graphs_dir)
    output_dir = Path(args.output_dir)

    if not graphs_dir.exists():
        logger.error(f"Graphs directory not found: {graphs_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    if args.circuit:
        subdirs = [graphs_dir / args.circuit]
    else:
        subdirs = sorted([d for d in graphs_dir.iterdir() if d.is_dir() and (d / 'nodes.csv').exists()])

    if not subdirs:
        logger.warning(f"No valid graph directories found in {graphs_dir}")
        return 0

    logger.info(f"Found {len(subdirs)} circuit graphs to process with {args.jobs} workers.")

    tasks = [(d, output_dir / f"{d.name}.csv") for d in subdirs]

    if args.jobs <= 1:
        results = [_process_single_graph(task) for task in tasks]
    else:
        with Pool(processes=args.jobs) as pool:
            results = pool.map(_process_single_graph, tasks)

    success_count = sum(1 for _, ok, _ in results if ok)
    logger.info(f"All done: {success_count}/{len(tasks)} circuits processed successfully.")
    return 0 if success_count == len(tasks) else 1


if __name__ == '__main__':
    sys.exit(main())

