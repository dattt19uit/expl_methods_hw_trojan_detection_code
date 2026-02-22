#!/usr/bin/env python3
"""
CLI interface for Method 4 SHAP explanations.
"""

import argparse
import sys
from pathlib import Path
from .shap_explainer import run_shap_explanations


def main():
    """CLI entry point for SHAP explanations."""
    parser = argparse.ArgumentParser(
        description='Generate SHAP explanations for Method 2 classifier',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate SHAP explanations for 100 samples
  method4-shap-explain \\
    --model data/models/method2/xgboost_model.pkl \\
    --training-data data/processed/train.csv \\
    --test-data data/processed/test.csv \\
    --output output/shap/explanations.json \\
    --max-test-samples 100

  # Process all test samples
  method4-shap-explain \\
    --model data/models/method2/xgboost_model.pkl \\
    --training-data data/processed/train.csv \\
    --test-data data/processed/test.csv \\
    --output output/shap/explanations.json
        """
    )
    
    parser.add_argument('--model', type=str, required=True,
                       help='Path to trained model pickle file')
    parser.add_argument('--training-data', type=str, required=True,
                       help='Path to training CSV file')
    parser.add_argument('--test-data', type=str, required=True,
                       help='Path to test CSV file')
    parser.add_argument('--output', type=str, required=True,
                       help='Output path for SHAP explanations JSON')
    parser.add_argument('--max-test-samples', type=int, default=None,
                       help='Maximum number of test samples to explain (default: all)')
    parser.add_argument('--background-size', type=int, default=100,
                       help='Number of background samples for KernelExplainer (default: 100)')
    parser.add_argument('--predictions', type=str, default=None,
                       help='Path to Method 2 predictions.json for intelligent sampling')
    parser.add_argument('--prioritize-critical', action='store_true',
                       help='Prioritize trojan samples and false positives over random sampling')
    
    args = parser.parse_args()
    
    try:
        run_shap_explanations(
            model_path=args.model,
            training_data_path=args.training_data,
            test_data_path=args.test_data,
            output_path=args.output,
            max_test_samples=args.max_test_samples,
            background_size=args.background_size,
            predictions_path=args.predictions,
            prioritize_critical=args.prioritize_critical
        )
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
