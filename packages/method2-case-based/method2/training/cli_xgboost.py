#!/usr/bin/env python3
"""CLI entry point for XGBoost model training (Method 2)"""

import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(
        description='Train XGBoost classifier for case-based trojan detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with default settings
  method2-train-xgboost --train-data ../../data/aggregate/train.csv --output-dir ../../data/outputs/method2_xgboost

  # Train with custom hyperparameters
  method2-train-xgboost --train-data ../../data/aggregate/train.csv --output-dir ../../data/outputs/method2_xgboost --max-depth 8 --learning-rate 0.1

Note: XGBoost trains 350x faster than SVM (58 seconds vs 5.7 hours)
      Achieves 2x better recall (87.5% vs 41.7%)
      No feature scaling needed - XGBoost handles raw features
        """
    )
    
    parser.add_argument(
        '--train-data',
        required=True,
        help='Path to training CSV file'
    )
    
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Output directory for model and metadata'
    )
    
    parser.add_argument(
        '--max-depth',
        type=int,
        default=6,
        help='Maximum tree depth (default: 6)'
    )
    
    parser.add_argument(
        '--learning-rate',
        type=float,
        default=0.3,
        help='Learning rate (default: 0.3)'
    )
    
    parser.add_argument(
        '--n-estimators',
        type=int,
        default=100,
        help='Number of boosting rounds (default: 100)'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    train_data = Path(args.train_data)
    if not train_data.exists():
        parser.error(f"Training data file does not exist: {train_data}")
    
    # Import here to avoid circular imports
    from method2.training.train_xgboost import train_xgboost_model
    
    # Run training
    print("="*80)
    print("Case-Based XGBoost Training")
    print("="*80)
    print(f"Training data: {args.train_data}")
    print(f"Output directory: {args.output_dir}")
    print(f"Max depth: {args.max_depth}")
    print(f"Learning rate: {args.learning_rate}")
    print(f"N estimators: {args.n_estimators}")
    print("="*80)
    print()
    
    model, metadata = train_xgboost_model(
        train_csv=args.train_data,
        output_dir=args.output_dir,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
        n_estimators=args.n_estimators
    )
    
    print()
    print("="*80)
    print("[OK] Training Complete!")
    print("="*80)
    print(f"Model saved to: {args.output_dir}/xgboost_model.pkl")
    print(f"Metadata saved to: {args.output_dir}/xgboost_metadata.json")
    print()


if __name__ == '__main__':
    main()
