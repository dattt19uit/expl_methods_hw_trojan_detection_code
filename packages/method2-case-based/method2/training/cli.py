"""CLI wrapper for method2 KNN training"""
import argparse
from .train import train_knn_model


def main():
    parser = argparse.ArgumentParser(
        description='Train KNN classifier for case-based trojan detection (Method 2)'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Path to training CSV file'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for model and metadata'
    )
    parser.add_argument(
        '--k',
        type=int,
        default=5,
        help='Number of neighbors (default: 5)'
    )
    parser.add_argument(
        '--metric',
        default='euclidean',
        choices=['euclidean', 'manhattan', 'chebyshev', 'minkowski'],
        help='Distance metric (default: euclidean)'
    )
    parser.add_argument(
        '--weights',
        default='distance',
        choices=['uniform', 'distance'],
        help='Weight function (default: distance)'
    )
    
    args = parser.parse_args()
    
    # Train model
    train_knn_model(
        train_csv=args.input,
        output_dir=args.output,
        k=args.k,
        metric=args.metric,
        weights=args.weights
    )
    
    print("\n[OK] KNN training complete!")


if __name__ == '__main__':
    main()
