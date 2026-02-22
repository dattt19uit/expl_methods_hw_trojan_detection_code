"""
Case-based KNN Classifier for Hardware Trojan Detection (Method 2)

This implementation uses scikit-learn's KNeighborsClassifier with legacy-style
weighted explanations. Based on the original case-based method but modernized
with mainstream ML libraries.

Key Features:
- Scikit-learn KNN classifier (efficient, well-tested)
- Weighted correspondence scoring: weight = 1 / (distance + 1)^3
- Configurable trojan multiplier for imbalanced data
- Case-based explanations with similar training samples
- Compatible output format for Phase 4 integration
"""

import os
import json
import pickle
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, matthews_corrcoef, cohen_kappa_score
)


def train_knn_model(train_csv, output_dir, k=5, metric='euclidean', weights='distance'):
    """
    Train KNN classifier on circuit data.
    
    Args:
        train_csv: Path to training CSV file
        output_dir: Directory to save model and metadata
        k: Number of neighbors (default: 5)
        metric: Distance metric (default: 'euclidean')
        weights: Weight function ('uniform' or 'distance')
    
    Returns:
        model: Trained KNeighborsClassifier
        scaler: Fitted StandardScaler
        metadata: Training metadata dictionary
    """
    print(f"Loading training data from {train_csv}...")
    df = pd.read_csv(train_csv)
    
    # Extract features and labels
    X_train = df.iloc[:, :-1].values  # All columns except last
    y_train = df.iloc[:, -1].values.astype(int)  # Last column is label
    
    print(f"Training samples: {len(X_train)}")
    print(f"Features: {X_train.shape[1]}")
    print(f"Class distribution: {np.bincount(y_train)}")
    
    # Normalize features
    print("Normalizing features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    # Train KNN classifier
    print(f"Training KNN classifier (k={k}, metric={metric}, weights={weights})...")
    start_time = datetime.now()
    
    knn = KNeighborsClassifier(
        n_neighbors=k,
        metric=metric,
        weights=weights,
        algorithm='auto',  # Let sklearn choose best algorithm
        n_jobs=-1  # Use all CPU cores
    )
    knn.fit(X_train_scaled, y_train)
    
    end_time = datetime.now()
    print(f"Training completed in {end_time - start_time}")
    
    # Create metadata
    metadata = {
        'k': k,
        'metric': metric,
        'weights': weights,
        'n_samples': len(X_train),
        'n_features': X_train.shape[1],
        'class_distribution': np.bincount(y_train).tolist(),
        'training_time': str(end_time - start_time),
        'timestamp': datetime.now().isoformat()
    }
    
    # Save model, scaler, and training data (needed for explanations)
    os.makedirs(output_dir, exist_ok=True)
    
    model_path = os.path.join(output_dir, 'knn_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': knn,
            'scaler': scaler,
            'X_train_scaled': X_train_scaled,
            'y_train': y_train,
            'metadata': metadata
        }, f)
    print(f"Model saved to {model_path}")
    
    # Save metadata separately as JSON
    metadata_path = os.path.join(output_dir, 'knn_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved to {metadata_path}")
    
    return knn, scaler, metadata


def main():
    parser = argparse.ArgumentParser(
        description='Train KNN classifier for case-based trojan detection'
    )
    parser.add_argument(
        '--train-data',
        required=True,
        help='Path to training CSV file'
    )
    parser.add_argument(
        '--output-dir',
        default='../../data/outputs/case_based',
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
        train_csv=args.train_data,
        output_dir=args.output_dir,
        k=args.k,
        metric=args.metric,
        weights=args.weights
    )
    
    print("\n[OK] KNN training complete!")


if __name__ == '__main__':
    main()
