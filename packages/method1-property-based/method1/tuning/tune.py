#!/usr/bin/env python3
"""
Tune SVM hyperparameters for aggregated/deduplicated training data

This script is optimized for the smaller deduplicated dataset from
aggregate_training_data.py (2,020 training samples vs 55,487 raw samples).

Key differences from tune_hyperparameters_fast.py:
- No subsampling needed (already deduplicated)
- Loads single train.csv file (not 30 circuit CSVs)
- No duplicate handling
- Single-stage fine-grained grid search (no adaptive refinement)
- Simpler, cleaner code for aggregate data pipeline

Expected runtime: ~2 hours for all 31 properties on 20-core machine
(50x50x5 = 12,500 fits per property, 31 properties = 387,500 total fits)
"""

import os
import csv
import json
import numpy as np
import logging
import sys
from pathlib import Path
from datetime import datetime
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, StratifiedShuffleSplit
from multiprocessing import Pool, cpu_count
from itertools import combinations
import threading

# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging(log_file):
    """Configure logging to both file and console
    
    Args:
        log_file: Path to log file
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('TuneHyperparametersAggregate')
    logger.handlers = []
    logger.setLevel(logging.DEBUG)
    
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh_format = logging.Formatter('%(asctime)s - [%(levelname)8s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(fh_format)
    logger.addHandler(fh)
    
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch_format = logging.Formatter('%(asctime)s - [%(levelname)8s] - %(message)s', datefmt='%H:%M:%S')
    ch.setFormatter(ch_format)
    logger.addHandler(ch)
    
    return logger

logger = None

# ============================================================================
# Progress Tracking
# ============================================================================
class ProgressTracker:
    """Track progress across parallel workers"""
    def __init__(self, progress_file):
        self.progress_file = progress_file
        self.lock = threading.Lock()
        with open(progress_file, 'w') as f:
            f.write("0\n")
    
    def log_property_complete(self, property_idx, property_names, f1_score, elapsed_sec):
        """Called when a property tuning completes"""
        with self.lock:
            with open(self.progress_file, 'a') as f:
                f.write(f"Property {property_idx:2d}: {str(property_names):35s} | F1: {f1_score:.4f} | {elapsed_sec/60:.1f} min\n")
                f.flush()

class ProgressTrackingSVC(SVC):
    """SVC wrapper that tracks each fit call"""
    _progress_tracker = None
    
    def fit(self, X, y, **kwargs):
        result = super().fit(X, y, **kwargs)
        if ProgressTrackingSVC._progress_tracker is not None:
            ProgressTrackingSVC._progress_tracker.increment()
        return result

class FitProgressTracker:
    """Track individual SVM fits"""
    def __init__(self, progress_file, property_idx, property_names, total_fits=1000):
        self.progress_file = progress_file
        self.property_idx = property_idx
        self.property_names = property_names
        self.total_fits = total_fits
        self.current_fits = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()
        self.last_log_fits = 0
        self.log_interval = 25
        
        with open(progress_file, 'w') as f:
            f.write(f"Property {property_idx:2d}: {str(property_names)} - Starting\n")
            f.flush()
    
    def increment(self):
        """Called after each SVM fit completes"""
        with self.lock:
            self.current_fits += 1
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            if self.current_fits - self.last_log_fits >= self.log_interval or self.current_fits == self.total_fits:
                pct = (self.current_fits / self.total_fits) * 100
                rate = self.current_fits / elapsed if elapsed > 0 else 0
                eta_sec = (self.total_fits - self.current_fits) / rate if rate > 0 else 0
                
                with open(self.progress_file, 'a') as f:
                    f.write(f"  [{self.current_fits:5d}/{self.total_fits}] {pct:5.1f}% | Rate: {rate:5.1f} fits/sec | ETA: {eta_sec/60:.1f} min\n")
                    f.flush()
                
                self.last_log_fits = self.current_fits

# ============================================================================
# Data Loading
# ============================================================================
def load_train_csv(csv_file):
    """Load aggregate training CSV file (deduplicated)"""
    rows = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics = [
                float(row['LGFi']),
                float(row['ffi']),
                float(row['ffo']),
                float(row['PI']),
                float(row['PO']),
            ]
            rows.append((metrics, int(row['Trojan'])))
    return rows

# ============================================================================
# Tuning Function
# ============================================================================
def tune_single_property(args):
    """Tune hyperparameters for a single property - single stage fine grid"""
    train_data, train_labels, property_idx, property_names, progress_dir, grid_size = args
    
    start_time = datetime.now()
    
    # Single fine-grained grid search (no coarse/refine stages needed with small dataset)
    C_range = np.logspace(-2, 4, num=grid_size)
    gamma_range = np.logspace(-5, 3, num=grid_size)
    param_grid = {'C': C_range, 'gamma': gamma_range}
    cv = StratifiedShuffleSplit(n_splits=5, test_size=0.2, random_state=42)
    
    ProgressTrackingSVC._progress_tracker = FitProgressTracker(
        f'{progress_dir}/tune_property_{property_idx:02d}_progress.txt',
        property_idx,
        property_names,
        total_fits=grid_size*grid_size*5
    )
    
    grid = GridSearchCV(
        ProgressTrackingSVC(kernel='rbf', probability=True, class_weight='balanced'),
        param_grid=param_grid,
        cv=cv,
        scoring='f1',
        n_jobs=1,
        verbose=0
    )
    grid.fit(train_data, train_labels)
    ProgressTrackingSVC._progress_tracker = None
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    result = {
        'property_idx': property_idx,
        'property_names': property_names,
        'best_params': grid.best_params_,
        'best_score': grid.best_score_,
        'elapsed_seconds': elapsed,
    }
    return result

# ============================================================================
# Tuner Class
# ============================================================================
class AggregateHyperparameterTuner:
    """Tuner for aggregated/deduplicated training data"""
    
    def __init__(self, log_file='tune_hyperparameters_aggregate.log', progress_file='tune_hyperparameters_aggregate_progress.txt'):
        self.scaler = StandardScaler()
        self.results = []
        global logger
        logger = setup_logging(log_file)
        self.logger = logger
        self.progress_tracker = ProgressTracker(progress_file)
        self.grid_size = 50  # Single fine-grained grid (default 50x50)
    
    def generate_properties(self, num_features=5):
        """Generate property combinations"""
        self.logger.info("")
        self.logger.info("="*70)
        self.logger.info("GENERATING PROPERTIES")
        self.logger.info("="*70)
        
        properties = []
        feature_names = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']
        
        for i in range(1, num_features + 1):
            for combo in combinations(range(num_features), i):
                prop_names = [feature_names[j] for j in combo]
                properties.append({'indices': combo, 'names': prop_names})
        
        self.logger.info(f"[OK] Generated {len(properties)} property combinations")
        self.logger.info("")
        return properties
    
    def load_data(self, train_csv):
        """Load aggregated training data (already deduplicated)"""
        self.logger.info("="*70)
        self.logger.info("LOADING AGGREGATED TRAINING DATA")
        self.logger.info("="*70)
        self.logger.info(f"Input file: {train_csv}")
        
        rows = load_train_csv(train_csv)
        
        all_metrics = []
        all_labels = []
        for metrics, label in rows:
            all_metrics.append(metrics)
            all_labels.append(label)
        
        X = np.array(all_metrics)
        y = np.array(all_labels)
        
        trojan_count = np.sum(y == 1)
        clean_count = np.sum(y == 0)
        
        self.logger.info(f"[OK] Loaded {len(X)} samples")
        self.logger.info(f"   Class distribution: {clean_count} clean, {trojan_count} trojans ({trojan_count/len(y)*100:.2f}%)")
        self.logger.info(f"   Note: Data already deduplicated by aggregate_training_data.py")
        
        # Scale data
        X_scaled = self.scaler.fit_transform(X)
        
        self.logger.info("")
        return X_scaled, y
    
    def extract_property_data(self, X, property_indices):
        """Extract data for a specific property"""
        return X[:, property_indices]
    
    def tune_parallel(self, X, y, properties, progress_dir='logs/tune_progress_aggregate', n_jobs=None):
        """Tune hyperparameters for all properties in parallel"""
        if n_jobs is None:
            n_jobs = max(1, cpu_count() - 1)
        
        self.logger.info("")
        self.logger.info("="*70)
        self.logger.info(f"HYPERPARAMETER TUNING (Parallel, {n_jobs} processes)")
        self.logger.info("="*70)
        self.logger.info(f"Using F1-score optimization with 5-fold stratified CV")
        self.logger.info(f"Class weighting: BALANCED (accounts for class imbalance)")
        self.logger.info(f"Grid: C in [2^-2, 2^4], gamma in [2^-5, 2^3]")
        self.logger.info(f"Grid size: {self.grid_size}x{self.grid_size} = {self.grid_size*self.grid_size} combinations")
        self.logger.info(f"Total SVM fits per property: {self.grid_size*self.grid_size} x 5 folds = {self.grid_size*self.grid_size*5}")
        self.logger.info(f"Total SVM fits (all properties): {len(properties)} x {self.grid_size*self.grid_size*5} = {len(properties)*self.grid_size*self.grid_size*5:,}")
        self.logger.info("")
        
        tune_args = []
        start_time = datetime.now()
        
        for prop_idx, prop in enumerate(properties):
            X_prop = self.extract_property_data(X, prop['indices'])
            tune_args.append((X_prop, y, prop_idx, prop['names'], progress_dir, self.grid_size))
        
        self.logger.info(f"Starting {len(properties)} property tuning jobs...")
        self.logger.info(f"Start time: {start_time.strftime('%H:%M:%S')}")
        self.logger.info(f"Watch progress: tail -f {self.progress_tracker.progress_file}")
        self.logger.info("")
        
        results = []
        with Pool(n_jobs) as pool:
            for i, result in enumerate(pool.imap_unordered(tune_single_property, tune_args), 1):
                prop_idx = result['property_idx']
                prop_names = result['property_names']
                elapsed = result['elapsed_seconds']
                score = result['best_score']
                
                self.logger.info(f"[{i:2d}/{len(properties)}] Property {prop_idx:2d}: {str(prop_names):35s} | F1: {score:.4f} | Time: {elapsed/60:.1f} min")
                self.progress_tracker.log_property_complete(prop_idx, prop_names, score, elapsed)
                results.append(result)
        
        end_time = datetime.now()
        total_elapsed = (end_time - start_time).total_seconds() / 60
        
        self.logger.info("")
        self.logger.info(f"[OK] All {len(properties)} properties tuned")
        self.logger.info(f"Total time: {total_elapsed:.1f} minutes ({total_elapsed/60:.2f} hours)")
        
        sorted_results = sorted(results, key=lambda x: x['best_score'], reverse=True)
        
        median_c = np.median([r['best_params']['C'] for r in results])
        median_gamma = np.median([r['best_params']['gamma'] for r in results])
        
        return {
            'all_results': sorted_results,
            'recommended': {
                'C': median_c,
                'gamma': median_gamma,
            }
        }
    
    def save_results(self, tuning_results, output_file):
        """Save tuning results to file"""
        self.logger.info("="*70)
        self.logger.info("SAVING RESULTS")
        self.logger.info("="*70)
        
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'data_source': 'aggregate_training_data.py (deduplicated)',
            'recommended_params': {
                'C': float(tuning_results['recommended']['C']),
                'gamma': float(tuning_results['recommended']['gamma']),
            },
            'all_properties': [
                {
                    'property_idx': r['property_idx'],
                    'property_names': r['property_names'],
                    'best_C': float(r['best_params']['C']),
                    'best_gamma': float(r['best_params']['gamma']),
                    'best_f1_score': float(r['best_score']),
                }
                for r in tuning_results['all_results']
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        self.logger.info(f"[OK] Results saved to {output_file}")
        self.logger.info("")


def tune_hyperparameters(input_csv, output_file, log_file=None, progress_file=None, 
                        jobs=None, grid_size=50, progress_dir=None,
                        property_start=0, property_end=30):
    """
    Main function to tune hyperparameters
    
    Args:
        input_csv: Path to train.csv from aggregate_training_data.py
        output_file: Path to save tuning results JSON
        log_file: Path to log file (default: auto-generated)
        progress_file: Path to progress file (default: auto-generated)
        jobs: Number of parallel jobs (default: cpu_count - 1)
        grid_size: Grid size for C and gamma (default: 50)
        progress_dir: Directory for per-property progress files
        property_start: Starting property index (inclusive)
        property_end: Ending property index (inclusive)
    """
    # Set defaults
    if log_file is None:
        log_file = output_file.replace('.json', '.log')
    if progress_file is None:
        progress_file = output_file.replace('.json', '_progress.txt')
    if progress_dir is None:
        progress_dir = os.path.join(os.path.dirname(output_file) or 'logs', 'tune_progress_aggregate')
    
    # Create directories
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    os.makedirs(os.path.dirname(log_file) or '.', exist_ok=True)
    os.makedirs(progress_dir, exist_ok=True)
    
    # Initialize tuner
    tuner = AggregateHyperparameterTuner(log_file, progress_file)
    tuner.grid_size = grid_size
    
    # Log configuration
    tuner.logger.info("="*70)
    tuner.logger.info("CONFIGURATION")
    tuner.logger.info("="*70)
    tuner.logger.info(f"  Input CSV:            {input_csv}")
    tuner.logger.info(f"  Output file:          {output_file}")
    tuner.logger.info(f"  Log file:             {log_file}")
    tuner.logger.info(f"  Progress file:        {progress_file}")
    tuner.logger.info(f"  Progress directory:   {progress_dir}")
    tuner.logger.info(f"  Grid size:            {grid_size}x{grid_size} = {grid_size*grid_size} combinations")
    tuner.logger.info(f"  Property range:       {property_start}-{property_end}")
    tuner.logger.info(f"  Parallel jobs:        {jobs or cpu_count()-1}")
    
    # Generate properties
    all_properties = tuner.generate_properties(num_features=5)
    
    # Filter properties
    properties = all_properties[property_start:property_end+1]
    tuner.logger.info(f"Selected {len(properties)} properties for tuning (indices {property_start}-{property_end})")
    tuner.logger.info("")
    
    # Load data
    X, y = tuner.load_data(input_csv)
    
    # Tune hyperparameters
    tuning_results = tuner.tune_parallel(X, y, properties, progress_dir, jobs)
    
    # Save results
    tuner.save_results(tuning_results, output_file)
    
    tuner.logger.info("="*70)
    tuner.logger.info("[OK] TUNING COMPLETE")
    tuner.logger.info("="*70)
    
    return tuning_results
