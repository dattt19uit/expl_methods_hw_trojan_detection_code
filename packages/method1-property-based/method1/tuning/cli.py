#!/usr/bin/env python3
"""CLI wrapper for hyperparameter tuning"""

import argparse
from multiprocessing import cpu_count
from .tune import tune_hyperparameters


def main():
    """Main entry point for method1-tune command"""
    parser = argparse.ArgumentParser(
        description='Tune hyperparameters on aggregated/deduplicated training data'
    )
    parser.add_argument('-i', '--input', required=True,
                       help='Input train.csv from aggregate_training_data.py')
    parser.add_argument('-o', '--output', default='logs/hyperparameter_tuning_aggregate.json',
                       help='Output file for tuning results')
    parser.add_argument('-l', '--log-file', default=None,
                       help='Log file path (default: output file with .log extension)')
    parser.add_argument('-p', '--progress-file', default=None,
                       help='Progress tracking file (default: output file with _progress.txt)')
    parser.add_argument('-j', '--jobs', type=int, default=None,
                       help='Number of parallel jobs (default: cpu_count - 1)')
    parser.add_argument('--grid-size', type=int, default=50,
                       help='Grid size for C and gamma (default: 50, creates 50x50=2500 combinations)')
    parser.add_argument('--progress-dir', default=None,
                       help='Directory for per-property progress files')
    parser.add_argument('--property-start', type=int, default=0,
                       help='Starting property index (inclusive, default: 0)')
    parser.add_argument('--property-end', type=int, default=30,
                       help='Ending property index (inclusive, default: 30)')
    
    args = parser.parse_args()
    
    tune_hyperparameters(
        input_csv=args.input,
        output_file=args.output,
        log_file=args.log_file,
        progress_file=args.progress_file,
        jobs=args.jobs,
        grid_size=args.grid_size,
        progress_dir=args.progress_dir,
        property_start=args.property_start,
        property_end=args.property_end
    )


if __name__ == '__main__':
    main()
