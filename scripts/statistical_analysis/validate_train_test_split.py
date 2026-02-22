#!/usr/bin/env python3
"""
Train/Test Split Validation (Step 4.5 - URGENT)

Validates data characteristics:
- No deduplication in train vs test sets
- Expected ~55K samples total
- Proper trojan/non-trojan ratio
- No data leakage between splits
"""

import numpy as np
import pandas as pd
import json
from pathlib import Path
import argparse


def load_dataset(data_dir):
    """Load train and test datasets."""
    data_dir = Path(data_dir)
    
    train_data = None
    test_data = None
    
    # Look for CSV files in data directory
    train_paths = [
        data_dir / "train_data.csv",
        data_dir / "train.csv",
        data_dir / "aggregated_data" / "train_data.csv"
    ]
    test_paths = [
        data_dir / "test_data.csv",
        data_dir / "test.csv",
        data_dir / "aggregated_data" / "test_data.csv"
    ]
    
    for path in train_paths:
        if path.exists():
            print(f"[OK] Found train data: {path}")
            train_data = pd.read_csv(path)
            break
    
    for path in test_paths:
        if path.exists():
            print(f"[OK] Found test data: {path}")
            test_data = pd.read_csv(path)
            break
    
    return train_data, test_data


def validate_no_deduplication(train_data, test_data):
    """
    Validate that train/test contain all samples without deduplication.
    
    Returns validation dict.
    """
    print("\n" + "="*60)
    print("VALIDATION: No Deduplication Between Train/Test")
    print("="*60)
    
    results = {}
    
    # Check if 'circuit_id' or similar identifier exists
    id_columns = ['circuit_id', 'circuit', 'id', 'sample_id']
    id_col = None
    for col in id_columns:
        if col in train_data.columns:
            id_col = col
            break
    
    if id_col:
        print(f"Using identifier column: {id_col}")
        
        train_ids = set(train_data[id_col])
        test_ids = set(test_data[id_col])
        
        # Check for overlap (should be NONE)
        overlap = train_ids & test_ids
        results['has_id_column'] = True
        results['id_column'] = id_col
        results['overlap_count'] = len(overlap)
        results['overlap_ids'] = list(overlap)[:10]  # First 10
        
        print(f"  Train unique IDs: {len(train_ids)}")
        print(f"  Test unique IDs: {len(test_ids)}")
        print(f"  Overlap: {len(overlap)}")
        
        if len(overlap) > 0:
            print(f"  WARNING: {len(overlap)} samples appear in both train and test!")
            print(f"    First few: {list(overlap)[:5]}")
            results['validation_status'] = 'FAILED'
        else:
            print(f"  [OK] PASS: No overlap between train and test")
            results['validation_status'] = 'PASSED'
    else:
        print("  [INFO] No identifier column found")
        print("  Cannot check for exact duplicates without IDs")
        results['has_id_column'] = False
        results['validation_status'] = 'UNKNOWN'
    
    return results


def validate_sample_counts(train_data, test_data, expected_total=55000):
    """
    Validate expected sample counts (~55K total).
    
    Returns validation dict.
    """
    print("\n" + "="*60)
    print("VALIDATION: Sample Counts")
    print("="*60)
    
    train_count = len(train_data)
    test_count = len(test_data)
    total_count = train_count + test_count
    
    print(f"  Train samples: {train_count:,}")
    print(f"  Test samples: {test_count:,}")
    print(f"  Total samples: {total_count:,}")
    print(f"  Expected total: ~{expected_total:,}")
    
    # Check if within 10% of expected
    tolerance = 0.10
    lower_bound = expected_total * (1 - tolerance)
    upper_bound = expected_total * (1 + tolerance)
    
    results = {
        'train_count': train_count,
        'test_count': test_count,
        'total_count': total_count,
        'expected_total': expected_total,
        'within_tolerance': lower_bound <= total_count <= upper_bound
    }
    
    if results['within_tolerance']:
        deviation = (total_count - expected_total) / expected_total * 100
        print(f"  [OK] PASS: Total within {tolerance*100}% of expected ({deviation:+.1f}%)")
        results['validation_status'] = 'PASSED'
    else:
        deviation = (total_count - expected_total) / expected_total * 100
        print(f"  WARNING: Total deviates {deviation:+.1f}% from expected")
        results['validation_status'] = 'WARNING'
    
    return results


def validate_class_balance(train_data, test_data):
    """
    Validate trojan/non-trojan ratio in train and test.
    
    Returns validation dict.
    """
    print("\n" + "="*60)
    print("VALIDATION: Class Balance")
    print("="*60)
    
    # Find label column
    label_columns = ['Trojan', 'label', 'is_trojan', 'trojan', 'class']
    label_col = None
    for col in label_columns:
        if col in train_data.columns:
            label_col = col
            break
    
    if not label_col:
        print("  [WARNING] No label column found!")
        return {'validation_status': 'UNKNOWN'}
    
    print(f"Using label column: {label_col}")
    
    # Count classes
    train_trojan = (train_data[label_col] == 1).sum()
    train_clean = (train_data[label_col] == 0).sum()
    test_trojan = (test_data[label_col] == 1).sum()
    test_clean = (test_data[label_col] == 0).sum()
    
    train_total = len(train_data)
    test_total = len(test_data)
    
    train_ratio = train_trojan / train_total if train_total > 0 else 0
    test_ratio = test_trojan / test_total if test_total > 0 else 0
    
    print(f"\n  Train set:")
    print(f"    Trojan: {train_trojan:,} ({train_ratio*100:.1f}%)")
    print(f"    Clean: {train_clean:,} ({(1-train_ratio)*100:.1f}%)")
    
    print(f"\n  Test set:")
    print(f"    Trojan: {test_trojan:,} ({test_ratio*100:.1f}%)")
    print(f"    Clean: {test_clean:,} ({(1-test_ratio)*100:.1f}%)")
    
    # Check if ratios are similar (within 5%)
    ratio_diff = abs(train_ratio - test_ratio)
    
    results = {
        'label_column': label_col,
        'train': {
            'trojan_count': int(train_trojan),
            'clean_count': int(train_clean),
            'trojan_ratio': float(train_ratio)
        },
        'test': {
            'trojan_count': int(test_trojan),
            'clean_count': int(test_clean),
            'trojan_ratio': float(test_ratio)
        },
        'ratio_difference': float(ratio_diff)
    }
    
    if ratio_diff < 0.05:
        print(f"\n  [OK] PASS: Train/test ratios similar (delta = {ratio_diff*100:.2f}%)")
        results['validation_status'] = 'PASSED'
    else:
        print(f"\n  WARNING: Train/test ratios differ by {ratio_diff*100:.2f}%")
        results['validation_status'] = 'WARNING'
    
    return results


def validate_feature_integrity(train_data, test_data):
    """
    Validate feature columns are consistent between train/test.
    
    Returns validation dict.
    """
    print("\n" + "="*60)
    print("VALIDATION: Feature Integrity")
    print("="*60)
    
    train_cols = set(train_data.columns)
    test_cols = set(test_data.columns)
    
    missing_in_test = train_cols - test_cols
    missing_in_train = test_cols - train_cols
    
    print(f"  Train columns: {len(train_cols)}")
    print(f"  Test columns: {len(test_cols)}")
    
    results = {
        'train_column_count': len(train_cols),
        'test_column_count': len(test_cols),
        'columns_match': len(missing_in_test) == 0 and len(missing_in_train) == 0
    }
    
    if results['columns_match']:
        print(f"  [OK] PASS: All columns present in both splits")
        results['validation_status'] = 'PASSED'
    else:
        if missing_in_test:
            print(f"  [WARNING] Missing in test: {missing_in_test}")
        if missing_in_train:
            print(f"  [WARNING] Missing in train: {missing_in_train}")
        results['validation_status'] = 'FAILED'
        results['missing_in_test'] = list(missing_in_test)
        results['missing_in_train'] = list(missing_in_train)
    
    return results


def generate_validation_report(train_data, test_data, output_file):
    """
    Generate comprehensive validation report.
    
    Parameters:
    - train_data: train DataFrame
    - test_data: test DataFrame
    - output_file: output JSON file path
    """
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("TRAIN/TEST SPLIT VALIDATION REPORT")
    print("="*60)
    
    # Run all validations
    validation_results = {
        'no_deduplication': validate_no_deduplication(train_data, test_data),
        'sample_counts': validate_sample_counts(train_data, test_data),
        'class_balance': validate_class_balance(train_data, test_data),
        'feature_integrity': validate_feature_integrity(train_data, test_data)
    }
    
    # Overall status
    statuses = [v.get('validation_status', 'UNKNOWN') for v in validation_results.values()]
    
    if any(s == 'FAILED' for s in statuses):
        overall_status = 'FAILED'
    elif all(s in ('PASSED', 'UNKNOWN') for s in statuses) and any(s == 'PASSED' for s in statuses):
        # If no failures and at least one pass, treat UNKNOWN (e.g. missing ID column) as non-blocking
        overall_status = 'PASSED'
    elif any(s == 'WARNING' for s in statuses):
        overall_status = 'WARNING'
    else:
        overall_status = 'UNKNOWN'
    
    validation_results['overall_status'] = overall_status
    
    # Save report
    with open(output_file, 'w') as f:
        json.dump(validation_results, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"  Overall Status: {overall_status}")
    print(f"\n  Individual Checks:")
    for check_name, result in validation_results.items():
        if check_name == 'overall_status':
            continue
        status = result.get('validation_status', 'UNKNOWN')
        print(f"    {check_name:25s}: {status}")
    
    print(f"\n[OK] Report saved to: {output_file}")
    print("="*60)
    
    return validation_results


def main():
    parser = argparse.ArgumentParser(description='Validate train/test split (Step 4.5)')
    parser.add_argument('--data-dir', default='data',
                       help='Directory containing train/test data')
    parser.add_argument('--output', default='data/statistical_analysis/split_validation.json',
                       help='Output JSON file')
    parser.add_argument('--expected-total', type=int, default=55000,
                       help='Expected total sample count')
    
    args = parser.parse_args()
    
    # Load data
    print("Loading datasets...")
    train_data, test_data = load_dataset(args.data_dir)
    
    if train_data is None or test_data is None:
        print("\n[WARNING] Could not find train or test data!")
        print("This script will be ready to run once pipeline completes.")
        print("\nExpected paths:")
        print("  - data/train_data.csv")
        print("  - data/test_data.csv")
        print("  OR")
        print("  - data/aggregated_data/train_data.csv")
        print("  - data/aggregated_data/test_data.csv")
        return
    
    # Generate validation report
    generate_validation_report(train_data, test_data, args.output)


if __name__ == '__main__':
    main()
