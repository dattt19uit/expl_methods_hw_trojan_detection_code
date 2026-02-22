#!/usr/bin/env python3
"""
CLI tool for processing hardware circuits.
"""

import argparse
import logging
import sys
from pathlib import Path

from .processor import process_circuit, process_batch, load_config, setup_logging


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Process hardware circuits for trojan detection'
    )
    
    parser.add_argument(
        'circuit',
        nargs='?',
        help='Circuit identifier (e.g., RS232-T1000-90nm)'
    )
    parser.add_argument('--config', default='circuit_configs.json')
    parser.add_argument('--batch', action='store_true')
    parser.add_argument('--output-dir', default='data/circuits/')
    parser.add_argument('--skip-graph', action='store_true')
    parser.add_argument('--log-dir', default='logs')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--num-processes', '-j', type=int, default=None)
    
    args = parser.parse_args()
    
    logger = setup_logging(args.log_dir, args.verbose)
    logger.info(f"Config: {args.config}, Output: {args.output_dir}")
    
    try:
        configs = load_config(args.config)
        
        if args.batch:
            num_processes = None if (args.num_processes is None or args.num_processes == 0) else args.num_processes
            process_batch(configs, args.output_dir, args.skip_graph, parallel=True, num_processes=num_processes)
        else:
            if not args.circuit:
                logger.error("Specify a circuit name or use --batch")
                return 1
            if args.circuit not in configs:
                logger.error(f"Circuit '{args.circuit}' not found")
                return 1
            success = process_circuit(configs[args.circuit], args.output_dir, args.skip_graph)
            return 0 if success else 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
