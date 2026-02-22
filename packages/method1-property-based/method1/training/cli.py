#!/usr/bin/env python3
"""CLI wrapper for model training"""

import argparse
from multiprocessing import cpu_count
from .train import train_models


def main():
    """Main entry point for method1-train command"""
    parser = argparse.ArgumentParser(
        prog='method1-train',
        description='Train 31 property-based models with tuned hyperparameters and class weighting',
        epilog='Uses tuning results and applies balanced class weights for trojan detection'
    )
    parser.add_argument('-i', '--input', required=True, 
                       help='Input folder with CSV files (train.csv, test.csv, min.csv, max.csv)')
    parser.add_argument('-p', '--params', required=True, 
                       help='Path to tuning results JSON (from hyperparameter tuning)')
    parser.add_argument('-o', '--output', required=True, 
                       help='Output folder for models and results')
    parser.add_argument('-j', '--jobs', type=int, default=None, 
                       help='Number of parallel processes (default: cpu_count - 2)')
    parser.add_argument('--no-parallel', action='store_true', 
                       help='Disable parallelism (for debugging)')
    
    args = parser.parse_args()
    
    train_models(
        data_folder=args.input,
        tuning_results_file=args.params,
        output_folder=args.output,
        jobs=args.jobs,
        no_parallel=args.no_parallel
    )


if __name__ == '__main__':
    main()
