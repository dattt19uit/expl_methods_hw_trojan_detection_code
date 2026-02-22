#!/usr/bin/env python3
"""CLI entry point for XGBoost model training (Method 1)"""

import argparse
from pathlib import Path
from method1.training.train_xgboost import train_models


def main():
    parser = argparse.ArgumentParser(
        description='Train 31 property-based XGBoost models (no hyperparameter tuning needed)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with default settings
  method1-train-xgboost --data-folder ../../data/aggregate --output ../../data/outputs/method1_xgboost

  # Train with custom parallelism
  method1-train-xgboost --data-folder ../../data/aggregate --output ../../data/outputs/method1_xgboost --jobs 8

  # Train serially (for debugging)
  method1-train-xgboost --data-folder ../../data/aggregate --output ../../data/outputs/method1_xgboost --no-parallel

Note: XGBoost trains 350x faster than SVM (60 seconds vs 5.7 hours)
      No hyperparameter tuning required - works well with defaults
      No feature scaling needed - XGBoost handles raw features
        """
    )
    
    parser.add_argument(
        '--data-folder',
        required=True,
        help='Folder containing train.csv, test.csv, min.csv, max.csv'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='Output folder for models and results'
    )
    
    parser.add_argument(
        '--jobs',
        type=int,
        default=None,
        help='Number of parallel processes (default: cpu_count - 2)'
    )
    
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing (for debugging)'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    data_folder = Path(args.data_folder)
    if not data_folder.exists():
        parser.error(f"Data folder does not exist: {data_folder}")
    
    # Run training
    print("="*80)
    print("Property-Based XGBoost Training")
    print("="*80)
    print(f"Data folder: {args.data_folder}")
    print(f"Output: {args.output}")
    print(f"Jobs: {args.jobs if args.jobs else 'auto (cpu_count - 2)'}")
    print(f"Parallel: {'No' if args.no_parallel else 'Yes'}")
    print("="*80)
    print()
    
    results = train_models(
        data_folder=args.data_folder,
        output_folder=args.output,
        jobs=args.jobs,
        no_parallel=args.no_parallel
    )
    
    print()
    print("="*80)
    print("[OK] Training Complete!")
    print("="*80)
    print(f"Models saved to: {args.output}/models/")
    print(f"Predictions saved to: {args.output}/")
    print(f"Logs saved to: {args.output}/logs/")
    print()


if __name__ == '__main__':
    main()
