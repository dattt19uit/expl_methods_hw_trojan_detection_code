"""CLI wrapper for method2 classification (KNN or XGBoost)"""
import argparse
from .classify import classify_and_explain


def main():
    parser = argparse.ArgumentParser(
        description='Run classification with case-based explanations (Method 2 - KNN or XGBoost)'
    )
    parser.add_argument(
        '--model',
        required=True,
        help='Path to trained model pickle file (KNN or XGBoost)'
    )
    parser.add_argument(
        '--input',
        '--test-data',
        dest='input',
        required=True,
        help='Path to test CSV file'
    )
    parser.add_argument(
        '--output',
        '--output-dir',
        dest='output',
        required=True,
        help='Output directory for predictions and explanations'
    )
    parser.add_argument(
        '--trojan-weight',
        type=float,
        default=1.0,
        help='Weight multiplier for trojan samples (default: 1.0)'
    )
    parser.add_argument(
        '--k',
        type=int,
        default=5,
        help='Number of nearest neighbors for explanations (XGBoost only, default: 5)'
    )
    
    args = parser.parse_args()
    
    # Run classification with auto model detection
    classify_and_explain(
        model_path=args.model,
        test_csv=args.input,
        output_dir=args.output,
        trojan_weight=args.trojan_weight,
        k=args.k
    )
    
    print("\n[OK] Classification and explanation generation complete!")


if __name__ == '__main__':
    main()
