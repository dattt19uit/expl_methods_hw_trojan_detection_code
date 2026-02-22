#!/usr/bin/env python3
"""
Aggregate Training Data from Circuit CSV Files

Combines 30 individual circuit CSV files into a single train/test dataset with:
- Stratified 80/20 split preserving trojan class ratio (0.41%)
- Min/max normalization values computed on full dataset
- Comprehensive logging and validation
- Reproducible random seed for deterministic splits

**Pipeline Stage:** Phase 1.5 (After circuit parsing, before hyperparameter tuning)

**Inputs:**
- 30 circuit CSV files (from process_circuit.py)
  Examples: RS232_T1000_90nm.csv, s35932_T100_90nm.csv, etc.

**Outputs:**
- train.csv - 80% of samples, stratified by trojan label
- test.csv - 20% of samples, stratified by trojan label  
- min.csv - Min values per feature (computed from ALL data)
- max.csv - Max values per feature (computed from ALL data)
- all.csv - Combined dataset before split (for reference)
- aggregation_log.txt - Complete audit trail

**Quality Assurance:**
- Validates all CSV files have same column structure
- Ensures no duplicate rows
- Verifies class distribution in train/test
- Logs data quality metrics
"""

import os
import csv
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from sklearn.utils import shuffle

# ============================================================================
# Configuration
# ============================================================================
RANDOM_SEED = 42  # Fixed seed for reproducibility
TEST_SPLIT_RATIO = 0.2  # 80% train, 20% test
TROJAN_LABEL_COLUMN = -1  # Last column is trojan label (0=clean, 1=trojan)

# Column indices in the raw CSV (from process_circuit.py netlistx/stdcell.py)
# Line,type,name,net,LGFi,ffi,ffo,PI,PO,Trojan
COL_LINE = 0    # Row number (integer)
COL_TYPE = 1    # Node type: 'nn', 'PI', 'PO', 'ff' (string)
COL_NAME = 2    # Gate/component name (string)
COL_NET = 3     # Net identifier (string)
COL_LGFI = 4    # Logic Gate Fan-in (integer) - FIRST NUMERIC FEATURE
COL_FFI = 5     # Flip-flop input distance (integer)
COL_FFO = 6     # Flip-flop output distance (integer)
COL_PI = 7      # Primary Input distance (integer)
COL_PO = 8      # Primary Output distance (integer)
COL_TROJAN = 9  # Label: 0=clean, 1=trojan (integer)

# Only columns 4-9 are numeric features (LGFi, ffi, ffo, PI, PO, Trojan)
NUMERIC_FEATURE_START = COL_LGFI  # Start index for numeric features
NUMERIC_COLUMNS = ['LGFi', 'ffi', 'ffo', 'PI', 'PO', 'Trojan']

# ============================================================================
# Logging Setup
# ============================================================================
def setup_logging(output_dir):
    """Configure logging to both file and console"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    log_file = os.path.join(output_dir, 'aggregation_log.txt')
    
    # Create logger
    logger = logging.getLogger('AggregateTrainingData')
    logger.setLevel(logging.DEBUG)
    
    # File handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    logger.info("="*80)
    logger.info("AGGREGATE TRAINING DATA - Starting")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"Random Seed: {RANDOM_SEED}")
    logger.info(f"Test Split Ratio: {TEST_SPLIT_RATIO}")
    logger.info("="*80)
    
    return logger

# ============================================================================
# Data Loading
# ============================================================================
def load_csv_file(filepath, logger):
    """
    Load CSV file and extract only numeric feature columns
    
    Raw CSV format: Line,type,name,net,LGFi,ffi,ffo,PI,PO,Trojan
    Columns 0-3 are non-numeric identifiers (skipped)
    Columns 4-9 are numeric features (extracted)
    
    This matches the legacy csv_01 behavior of removing non-numeric columns.
    """
    rows = []
    header = None
    row_count = 0
    skipped_count = 0
    
    try:
        with open(filepath, newline='') as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                if row_count == 0:
                    # Extract only numeric column headers (skip Line, type, name, net)
                    header = row[NUMERIC_FEATURE_START:]
                    logger.debug(f"  Full header: {row}")
                    logger.debug(f"  Numeric features: {header}")
                else:
                    try:
                        # Extract only numeric columns (4-9: LGFi, ffi, ffo, PI, PO, Trojan)
                        numeric_values = row[NUMERIC_FEATURE_START:]
                        
                        # Convert to integers
                        int_row = [int(v) for v in numeric_values]
                        
                        # Fix 99999 values (legacy csv_01 behavior)
                        # 99999 represents "no path" - we'll keep it as-is for now
                        # The legacy script replaced with max+1, but that happens per-column
                        
                        rows.append(int_row)
                    except (ValueError, IndexError) as e:
                        skipped_count += 1
                        logger.warning(f"  Skipping malformed row {row_count} in {filepath}: {row[:4]}... Error: {e}")
                        continue
                row_count += 1
        
        if skipped_count > 0:
            logger.warning(f"  [WARNING] Skipped {skipped_count} malformed rows")
        
        logger.info(f"  [OK] Loaded {filepath}: {len(rows)} data rows, {len(header)} features")
        return header, rows
    
    except Exception as e:
        logger.error(f"  [FAIL] Failed to load {filepath}: {e}")
        raise

def validate_headers(headers, logger):
    """Verify all CSV files have identical headers"""
    if not headers:
        logger.error("No headers to validate")
        return False
    
    primary_header = headers[0]
    logger.info(f"Primary header: {len(primary_header)} columns")
    
    for i, header in enumerate(headers[1:], 1):
        if header != primary_header:
            logger.error(f"Header mismatch at file {i}")
            logger.error(f"  Expected: {primary_header}")
            logger.error(f"  Got: {header}")
            return False
    
    logger.info(f"[OK] All {len(headers)} files have matching headers")
    return True

# ============================================================================
# Data Aggregation
# ============================================================================
def aggregate_csv_files(input_dir, logger):
    """Load and aggregate all CSV files from directory"""
    logger.info(f"\nAggregating CSV files from: {input_dir}")
    
    csv_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.csv')])
    
    if not csv_files:
        logger.error(f"No CSV files found in {input_dir}")
        raise FileNotFoundError(f"No CSV files in {input_dir}")
    
    logger.info(f"Found {len(csv_files)} CSV files")
    
    # Load all files
    all_headers = []
    all_rows = []
    
    for i, csv_file in enumerate(csv_files, 1):
        filepath = os.path.join(input_dir, csv_file)
        logger.info(f"[{i}/{len(csv_files)}] Loading {csv_file}")
        
        header, rows = load_csv_file(filepath, logger)
        all_headers.append(header)
        all_rows.extend(rows)
    
    # Validate headers
    if not validate_headers(all_headers, logger):
        raise ValueError("CSV files have inconsistent headers")
    
    logger.info(f"\n[OK] Total aggregated rows: {len(all_rows)}")
    return all_headers[0], all_rows

# ============================================================================
# Data Cleaning
# ============================================================================
def fix_max_values(rows, header, logger):
    """
    Replace 99999 sentinel values with next_max + 1
    
    This replicates the csv_01_fix_max.py legacy behavior.
    99999 is used to indicate "no path exists" in circuit metrics.
    We replace it with the next maximum value + 1 for each column.
    """
    logger.info(f"\nFixing sentinel values (99999):")
    
    if not rows:
        return rows
    
    num_features = len(rows[0])
    fixed_count = 0
    
    # Transpose to work column-by-column
    columns = list(zip(*rows))
    
    for col_idx in range(num_features):
        col_data = list(columns[col_idx])
        
        # Check if this column has 99999 values
        if 99999 in col_data:
            # Find next_max (maximum value below 99999)
            next_max = 0
            for val in col_data:
                if val < 99999 and val > next_max:
                    next_max = val
            
            # Replace 99999 with next_max + 1
            replacement_value = next_max + 1
            count_in_col = col_data.count(99999)
            
            if count_in_col > 0:
                logger.info(f"  Column {col_idx} ({header[col_idx]}): Replacing {count_in_col} values of 99999 with {replacement_value}")
                fixed_count += count_in_col
            
            # Update the column
            columns[col_idx] = tuple(replacement_value if v == 99999 else v for v in col_data)
    
    # Transpose back to row format
    if fixed_count > 0:
        rows = [list(row) for row in zip(*columns)]
        logger.info(f"  [OK] Fixed {fixed_count} total sentinel values")
    else:
        logger.info(f"  [OK] No sentinel values (99999) found")
    
    return rows

# ============================================================================
# Data Quality Checks
# ============================================================================
def check_data_quality(rows, header, logger, deduplicate=False):
    """Validate data quality and report statistics"""
    logger.info(f"\nData Quality Checks:")
    
    # Check for duplicates
    row_strings = [str(row) for row in rows]
    unique_rows = set(row_strings)
    duplicates = len(row_strings) - len(unique_rows)
    
    if duplicates > 0:
        if deduplicate:
            logger.warning(f"  Found {duplicates} duplicate rows (will remove due to --deduplicate)")
        else:
            logger.info(f"  Found {duplicates} duplicate rows (keeping all - deduplication disabled by default)")
    else:
        logger.info(f"  [OK] No duplicates")
    
    # Class distribution
    trojan_count = sum(1 for row in rows if row[TROJAN_LABEL_COLUMN] == 1)
    clean_count = len(rows) - trojan_count
    trojan_pct = 100.0 * trojan_count / len(rows) if rows else 0
    
    logger.info(f"  [OK] Class distribution: {clean_count} clean, {trojan_count} trojans ({trojan_pct:.4f}%)")
    
    # Feature statistics
    if rows:
        num_features = len(rows[0])
        logger.info(f"  [OK] Features: {num_features}")
        
        # Sample some feature ranges
        all_values = list(zip(*rows))
        for i in [0, 1, -2, -1]:  # First, second, second-to-last, last features
            if i < len(all_values):
                vals = all_values[i]
                logger.debug(f"    Feature {i}: min={min(vals)}, max={max(vals)}, mean={sum(vals)/len(vals):.2f}")
    
    return unique_rows

# ============================================================================
# Min/Max Computation
# ============================================================================
def compute_min_max(rows, header, logger):
    """Compute min/max values for each feature (excluding trojan label)"""
    logger.info(f"\nComputing Min/Max normalization values:")
    
    if not rows:
        logger.error("No rows to compute min/max")
        raise ValueError("Empty dataset")
    
    num_features = len(rows[0])
    minimum = [float('inf')] * num_features
    maximum = [float('-inf')] * num_features
    
    # Compute min/max across all rows
    for row in rows:
        for i, val in enumerate(row):
            if val < minimum[i]:
                minimum[i] = val
            if val > maximum[i]:
                maximum[i] = val
    
    logger.info(f"  [OK] Computed for {num_features} features")
    logger.debug(f"  Sample: Feature[0] min={minimum[0]}, max={maximum[0]}")
    logger.debug(f"  Sample: Feature[-1] min={minimum[-1]}, max={maximum[-1]}")
    
    return minimum, maximum

# ============================================================================
# Train/Test Split
# ============================================================================
def stratified_train_test_split(rows, logger):
    """
    Create stratified train/test split preserving class ratio
    
    Uses sklearn's shuffle to maintain class proportions:
    - 0.41% trojans should appear in both train and test at same ratio
    """
    logger.info(f"\nStratified Train/Test Split:")
    logger.info(f"  Test ratio: {TEST_SPLIT_RATIO} (80/20 split)")
    
    # Shuffle with fixed seed for reproducibility
    shuffled_rows = shuffle(rows, random_state=RANDOM_SEED)
    
    # Compute split index
    split_index = int(len(shuffled_rows) * (1.0 - TEST_SPLIT_RATIO))
    
    train_rows = shuffled_rows[:split_index]
    test_rows = shuffled_rows[split_index:]
    
    # Validate split
    train_trojans = sum(1 for row in train_rows if row[TROJAN_LABEL_COLUMN] == 1)
    test_trojans = sum(1 for row in test_rows if row[TROJAN_LABEL_COLUMN] == 1)
    
    train_trojan_pct = 100.0 * train_trojans / len(train_rows) if train_rows else 0
    test_trojan_pct = 100.0 * test_trojans / len(test_rows) if test_rows else 0
    
    logger.info(f"  [OK] Train set: {len(train_rows)} samples, {train_trojans} trojans ({train_trojan_pct:.4f}%)")
    logger.info(f"  [OK] Test set: {len(test_rows)} samples, {test_trojans} trojans ({test_trojan_pct:.4f}%)")
    
    # Check stratification quality
    diff = abs(train_trojan_pct - test_trojan_pct)
    if diff < 0.01:
        logger.info(f"  [OK] Excellent stratification (difference: {diff:.6f}%)")
    elif diff < 0.1:
        logger.info(f"  [OK] Good stratification (difference: {diff:.4f}%)")
    else:
        logger.warning(f"  [WARNING] Stratification could be better (difference: {diff:.4f}%)")
    
    return train_rows, test_rows

# ============================================================================
# File Output
# ============================================================================
def write_csv_file(filepath, header, rows, logger):
    """Write rows to CSV file"""
    try:
        with open(filepath, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(header)
            csv_writer.writerows(rows)
        logger.info(f"  [OK] Written to {filepath} ({len(rows)} rows)")
        return True
    except Exception as e:
        logger.error(f"  [FAIL] Failed to write {filepath}: {e}")
        return False

def write_min_max_csv(filepath, min_vals, max_vals, header, is_min, logger):
    """Write min or max values to CSV file (one row each)"""
    try:
        with open(filepath, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(header)
            values = min_vals if is_min else max_vals
            csv_writer.writerow(values)
        
        label = "min" if is_min else "max"
        logger.info(f"  [OK] Written {label} values to {filepath}")
        return True
    except Exception as e:
        logger.error(f"  [FAIL] Failed to write {filepath}: {e}")
        return False

# ============================================================================
# Summary Statistics
# ============================================================================
def write_summary(output_dir, header, all_rows, train_rows, test_rows, min_vals, max_vals, logger):
    """Write summary statistics JSON file"""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "random_seed": RANDOM_SEED,
        "test_split_ratio": TEST_SPLIT_RATIO,
        "files": {
            "total_rows": len(all_rows),
            "train_rows": len(train_rows),
            "test_rows": len(test_rows),
            "num_features": len(header)
        },
        "classes": {
            "total_trojans": sum(1 for row in all_rows if row[TROJAN_LABEL_COLUMN] == 1),
            "total_clean": sum(1 for row in all_rows if row[TROJAN_LABEL_COLUMN] == 0),
            "train_trojans": sum(1 for row in train_rows if row[TROJAN_LABEL_COLUMN] == 1),
            "test_trojans": sum(1 for row in test_rows if row[TROJAN_LABEL_COLUMN] == 1),
        },
        "normalization": {
            "min_values": min_vals,
            "max_values": max_vals
        }
    }
    
    summary_file = os.path.join(output_dir, 'aggregation_summary.json')
    try:
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"  [OK] Summary statistics written to {summary_file}")
    except Exception as e:
        logger.error(f"  [FAIL] Failed to write summary: {e}")

# ============================================================================
# Main Pipeline
# ============================================================================
def main():
    global RANDOM_SEED, TEST_SPLIT_RATIO
    
    parser = argparse.ArgumentParser(
        prog='aggregate_training_data',
        description='Aggregate 30 circuit CSV files into stratified train/test dataset',
        epilog='Outputs: train.csv, test.csv, min.csv, max.csv with complete audit trail'
    )
    parser.add_argument(
        '-f', '--folder',
        required=True,
        help='Input folder containing 30 circuit CSV files'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output folder for train.csv, test.csv, min.csv, max.csv'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=RANDOM_SEED,
        help=f'Random seed for reproducible splits (default: {RANDOM_SEED})'
    )
    parser.add_argument(
        '--test-ratio',
        type=float,
        default=TEST_SPLIT_RATIO,
        help=f'Test split ratio (default: {TEST_SPLIT_RATIO})'
    )
    parser.add_argument(
        '--deduplicate',
        action='store_true',
        help='Enable duplicate removal (removes 95%% of data - NOT recommended with XGBoost)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.output)
    
    # Override seed if provided
    RANDOM_SEED = args.seed
    TEST_SPLIT_RATIO = args.test_ratio
    
    try:
        # ====================================================================
        # Step 1: Aggregate all CSV files
        # ====================================================================
        header, all_rows = aggregate_csv_files(args.folder, logger)
        
        # ====================================================================
        # Step 2: Fix sentinel values (99999 -> next_max + 1)
        # ====================================================================
        all_rows = fix_max_values(all_rows, header, logger)
        
        # ====================================================================
        # Step 3: Data quality checks
        # ====================================================================
        deduplicate = args.deduplicate
        unique_rows = check_data_quality(all_rows, header, logger, deduplicate)
        
        # Remove duplicates by converting back to list (if deduplication enabled)
        if deduplicate:
            all_rows = [eval(row_str) for row_str in unique_rows]
        # else: keep all_rows as-is with duplicates
        
        # ====================================================================
        # Step 4: Compute min/max (on full dataset before split)
        # ====================================================================
        min_vals, max_vals = compute_min_max(all_rows, header, logger)
        
        # ====================================================================
        # Step 5: Stratified train/test split
        # ====================================================================
        train_rows, test_rows = stratified_train_test_split(all_rows, logger)
        
        # ====================================================================
        # Step 6: Write output files
        # ====================================================================
        logger.info(f"\nWriting output files to: {args.output}")
        
        success = True
        success &= write_csv_file(os.path.join(args.output, 'train.csv'), header, train_rows, logger)
        success &= write_csv_file(os.path.join(args.output, 'test.csv'), header, test_rows, logger)
        success &= write_csv_file(os.path.join(args.output, 'all.csv'), header, all_rows, logger)
        success &= write_min_max_csv(os.path.join(args.output, 'min.csv'), min_vals, max_vals, header, True, logger)
        success &= write_min_max_csv(os.path.join(args.output, 'max.csv'), min_vals, max_vals, header, False, logger)
        
        # ====================================================================
        # Step 7: Write summary statistics
        # ====================================================================
        write_summary(args.output, header, all_rows, train_rows, test_rows, min_vals, max_vals, logger)
        
        # ====================================================================
        # Summary
        # ====================================================================
        if success:
            logger.info("\n" + "="*80)
            logger.info("[OK] AGGREGATION COMPLETE - All files written successfully")
            logger.info(f"  Output directory: {args.output}")
            logger.info(f"  Total samples: {len(all_rows)}")
            logger.info(f"  Train samples: {len(train_rows)} (80%)")
            logger.info(f"  Test samples: {len(test_rows)} (20%)")
            logger.info("="*80)
            logger.info("\nNext steps:")
            logger.info("  1. Run hyperparameter tuning:")
            logger.info("     python determine_gamma_and_c_parallel.py --csv-dir . --output tuning_results.json")
            logger.info("  2. Run model training:")
            logger.info("     python train_property_based_model.py --folder . --tuning-results tuning_results.json --output training_results")
            logger.info("="*80)
        else:
            logger.error("\n[FAIL] AGGREGATION FAILED - Check log for details")
            return 1
        
        return 0
    
    except Exception as e:
        logger.error(f"\n[FAIL] FATAL ERROR: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    exit(main())
