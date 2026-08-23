#!/usr/bin/env python3
"""
Generalized circuit processing pipeline for trojan detection.

This module refactors the repetitive pattern used in individual test files
(RS232-T1000_test5_90nm.py, etc.) into a single configurable tool.

Configuration is loaded from circuit_configs.json, which specifies:
  - Circuit part and implementation details
  - Verilog file paths
  - Trojan node locations to extract

Usage:
    # Process a single circuit
    python process_circuit.py RS232-T1000-90nm
    
    # Process all circuits in batch mode
    python process_circuit.py --batch
    
    # Use custom config file and output directory
    python process_circuit.py RS232-T1000-90nm --config circuits.json --output-dir results/
"""

import json
import logging
import logging.handlers
import argparse
import re
import sys
from pathlib import Path
from multiprocessing import Pool

# Add parent directory to path to find local modules (netlistx, blackbox_definitions)

from xai_shared import netlistx as nl
from xai_shared.blackbox_definitions import get_blackboxes

# Global queue for multiprocess logging
_log_queue = None

# Configure logging with file rotation
def setup_logging(log_dir='logs', verbose=False):
    """Configure logging with both console and file handlers with rotation.
    
    Args:
        log_dir: Directory for log files (will be created if doesn't exist)
        verbose: If True, set logging level to DEBUG, otherwise INFO
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(__name__)
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Set level
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - [%(processName)s] - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (10 MB per file, keep 5 backups)
    log_file = log_path / 'process_circuit.log'
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_file),
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Initialize logger (will be called from main)
logger = logging.getLogger(__name__)


def load_config(config_file='circuit_configs.json'):
    """Load circuit configurations from JSON file.
    
    Args:
        config_file: Path to JSON configuration file
        
    Returns:
        Dictionary of circuit configurations keyed by circuit name
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    try:
        with open(config_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {config_file}: {e}")
        raise


def extract_cells_from_netlist(verilog_path):
    """
    Extract all cell types used in a Verilog netlist.
    
    Scans the file for cell instantiations following Verilog syntax:
    CELLTYPE instance_name ( port connections );
    
    This function is used as a fallback when the standard blackbox library
    doesn't contain all cells needed by a particular circuit.
    
    Args:
        verilog_path: Path to Verilog netlist file
        
    Returns:
        List of unique cell type names found, sorted alphabetically
    """
    cells = set()
    
    # Verilog keywords that match CELLTYPE pattern but aren't cells
    verilog_keywords = {
        'MODULE', 'INPUT', 'OUTPUT', 'WIRE', 'REG', 'ASSIGN',
        'PARAMETER', 'LOCALPARAM', 'GENERATE', 'IF', 'ELSE', 'BEGIN',
        'END', 'ALWAYS', 'INITIAL', 'CASE', 'FOR', 'WHILE',
        'INOUT', 'REAL', 'REALTIME', 'EVENT', 'GENVAR', 'DEFPARAM',
        'MACROMODULE', 'FORK', 'JOIN', 'DISABLE', 'FUNCTION', 'TASK'
    }
    
    try:
        with open(verilog_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                # Match pattern: CELLTYPE instance_name (
                # CELLTYPE: Starts with capital letter, followed by alphanumerics/X/underscore
                # instance_name: Identifier (alphanumeric/underscore)
                # (: Opening parenthesis for port list
                
                match = re.match(r'^\s*([A-Z][A-Z0-9X_]*)\s+(\w+)\s*\(', line)
                
                if match:
                    cell_type = match.group(1)
                    
                    # Skip Verilog keywords
                    if cell_type not in verilog_keywords:
                        cells.add(cell_type)
        
        sorted_cells = sorted(list(cells))
        
        logger.debug(f"Extracted {len(sorted_cells)} unique cell types from {verilog_path}")
        if sorted_cells:
            # Log first 10 cells and indicate if there are more
            cells_str = ', '.join(sorted_cells[:10])
            if len(sorted_cells) > 10:
                cells_str += f', ... ({len(sorted_cells) - 10} more)'
            logger.debug(f"Cell types: {cells_str}")
        
        return sorted_cells
        
    except Exception as e:
        logger.error(f"Failed to extract cells from {verilog_path}: {e}")
        return []


def process_circuit(config, output_dir='.', skip_graph=False):
    """Process a single circuit netlist and extract metrics.
    
    This function performs the standard processing pipeline:
    1. Load circuit netlist from Verilog file
    2. Merge cells
    3. Remove wire elements
    4. Generate graph visualization (optional)
    5. Extract metrics for specified trojan nodes
    
    Args:
        config: Dictionary with keys: part, impl, tech, verilog_path, verilog_name, nodes
        output_dir: Directory for output files (CSV and DOT graph)
        skip_graph: If True, skip graph generation (faster for large circuits)
        
    Returns:
        True if successful, False otherwise
    """
    part = config['part']
    impl = config['impl']
    tech = config['tech']
    verilog_path = config['verilog_path']
    verilog_name = config.get('verilog_name', 'circuit')
    nodes = config.get('nodes', [])
    
    try:
        # Validate inputs
        vpath = Path(verilog_path)
        if not vpath.exists():
            logger.warning(f"Verilog file not found: {verilog_path}")
            return False
        
        if not nodes:
            logger.warning(f"No trojan nodes specified for {part}-{impl}-{tech}")
            return False
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        base_name = f'{part}-{impl}_{tech}'
        logger.info(f'Processing -- part: {part}, impl: {impl}, tech: {tech}')
        
        # Map tech to netlistx-compatible library name
        # generic-180nm uses same cell types as 90nm library for parsing purposes
        netlistx_techlib = '90nm' if tech == 'generic-180nm' else tech
        
        # Read netlist with intelligent blackbox handling
        import time
        timing = {}
        parse_start = time.perf_counter()
        logger.debug(f"Reading netlist from {verilog_path}")
        graph_csv_output = output_path / 'graphs' / base_name
        
        try:
            # First try: Standard parsing with default netlistx settings
            logger.debug(f"Attempting standard parsing with default library")
            c = nl.read_netlist(
                str(vpath), name=verilog_name, fmt='verilog', techlib=netlistx_techlib,
                csv_output_dir=graph_csv_output,
            )
            timing['parse'] = time.perf_counter() - parse_start
            logger.debug(f"[OK] Successfully parsed with default settings in {timing['parse']:.3f}s")
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a blackbox (missing cell definition) error
            if "Blackbox" in error_msg and "not in list" in error_msg:
                logger.info(f"Standard parsing failed: missing blackbox cells")
                
                # Extract the missing cell name from error message if possible
                import re as regex_module
                match = regex_module.search(r"Blackbox\s+(\w+)\s+not in list", error_msg)
                missing_cell = match.group(1) if match else "unknown"
                logger.debug(f"Missing cell: {missing_cell}")
                
                # Second try: Extract cells from netlist dynamically
                logger.info(f"Extracting cells dynamically from netlist...")
                extracted_cells = extract_cells_from_netlist(str(vpath))
                
                if extracted_cells:
                    logger.info(f"Found {len(extracted_cells)} cell types: {extracted_cells[:5]}...")
                    logger.debug(f"Full cell list: {extracted_cells}")
                    
                    # Retry parsing WITHOUT the blackboxes parameter
                    # (The extracted cells should now be in the netlistx library)
                    try:
                        logger.info(f"Retrying parsing after dynamic extraction...")
                        c = nl.read_netlist(
                            str(vpath), 
                            name=verilog_name, 
                            fmt='verilog', 
                            techlib=netlistx_techlib,
                            csv_output_dir=graph_csv_output,
                        )
                        timing['parse'] = time.perf_counter() - parse_start
                        logger.info(f"[OK] Successfully parsed after extraction discovery in {timing['parse']:.3f}s")
                        
                    except Exception as retry_error:
                        logger.error(f"Failed on retry: {retry_error}")
                        logger.error(f"This circuit may have non-standard cell types or parsing issues")
                        return False
                else:
                    logger.error(f"Could not extract any cells from netlist")
                    return False
            else:
                # Different error (not blackbox related) - propagate it
                logger.error(f"Parsing error (not blackbox related): {error_msg[:200]}")
                raise
        
        # Process circuit with timing
        import time
        timing = {}
        
        t0 = time.perf_counter()
        logger.debug("Merging cells...")
        nl.merge_cells(c, nl.list_cell_names(c))
        timing['merge_cells'] = time.perf_counter() - t0
        
        t0 = time.perf_counter()
        logger.debug("Removing wire elements...")
        nl.remove_cells(c, ['wire'])
        timing['remove_wires'] = time.perf_counter() - t0
        
        # Generate visualization (optional, can be slow for large circuits)
        if not skip_graph:
            t0 = time.perf_counter()
            logger.debug("Generating graph visualization...")
            graph_output = str(output_path / base_name)
            nl.graph_cells(c, graph_output)
            timing['graph_viz'] = time.perf_counter() - t0
        else:
            timing['graph_viz'] = 0.0
        
        # Extract metrics
        t0 = time.perf_counter()
        logger.debug(f"Extracting {len(nodes)} trojan node metrics...")
        csv_output = str(output_path / f'{base_name}.csv')
        metrics_timing = nl.write_metrics(c, nodes, csv_output)
        timing['extract_metrics'] = time.perf_counter() - t0
        timing['metrics_breakdown'] = metrics_timing
        
        # Sum only numeric timing values (exclude dict breakdowns)
        total_time = sum(v for v in timing.values() if isinstance(v, (int, float)))
        logger.info(f'[OK] {base_name} complete - CSV saved to {csv_output}')
        logger.info(f'  Parsed graph CSVs: {graph_csv_output / "nodes.csv"}, {graph_csv_output / "edges.csv"}')
        logger.info(f'  Timing: Parse={timing.get("parse", 0):.2f}s, Merge={timing["merge_cells"]:.2f}s, Metrics={timing["extract_metrics"]:.2f}s, Total={total_time:.2f}s')
        return True
        
    except Exception as e:
        logger.error(f"Error processing {part}-{impl}-{tech}: {e}", exc_info=False)
        return False


def process_single_circuit_wrapper(args):
    """Wrapper function for multiprocessing to process a single circuit.
    
    Phase 1 optimization: Enables parallel processing of multiple circuits.
    
    Note: Worker processes set up logging via QueueHandler to avoid file conflicts.
    
    Args:
        args: Tuple of (key, config, output_dir, skip_graph, log_queue)
        
    Returns:
        Dictionary with circuit status and timing
    """
    import time
    global logger
    
    key, config, output_dir, skip_graph, log_queue = args
    circuit_start = time.time()
    
    # Worker process: set up logging via QueueHandler
    logger = setup_logging(queue=log_queue)
    
    try:
        result = process_circuit(config, output_dir, skip_graph)
        elapsed = time.time() - circuit_start
        return {
            'key': key,
            'status': 'completed' if result else 'skipped',
            'elapsed': elapsed,
            'error': None
        }
    except Exception as e:
        elapsed = time.time() - circuit_start
        return {
            'key': key,
            'status': 'failed',
            'elapsed': elapsed,
            'error': str(e)
        }


def process_single_circuit_simple(args):
    """Simplified wrapper for multiprocessing without Queue-based logging.
    
    Args:
        args: Tuple of (key, config, output_dir, skip_graph)
        
    Returns:
        Dictionary with circuit status and timing
    """
    import time
    
    key, config, output_dir, skip_graph = args
    circuit_start = time.time()
    
    try:
        # Simple print-based logging for workers (no Queue needed)
        print(f"[Worker] Processing {key}...")
        result = process_circuit(config, output_dir, skip_graph)
        elapsed = time.time() - circuit_start
        status_msg = 'completed' if result else 'skipped'
        print(f"[Worker] {key} {status_msg} in {elapsed:.2f}s")
        return {
            'key': key,
            'status': status_msg,
            'elapsed': elapsed,
            'error': None
        }
    except Exception as e:
        elapsed = time.time() - circuit_start
        print(f"[Worker] {key} FAILED after {elapsed:.2f}s: {e}")
        return {
            'key': key,
            'status': 'failed',
            'elapsed': elapsed,
            'error': str(e)
        }



def process_batch(config_dict, output_dir='.', skip_graph=False, parallel=True, num_processes=None):
    """Process all circuits in configuration dictionary.
    
    Phase 1 optimization: Enables parallel processing of multiple circuits using multiprocessing.Pool.
    Each circuit is processed independently - graphs are created within worker processes (no serialization needed).
    
    Logging is handled via QueueHandler + QueueListener for multiprocess-safe file writes.
    
    Args:
        config_dict: Dictionary of circuit configurations
        output_dir: Directory for output files
        skip_graph: If True, skip graph generation
        parallel: If True, use multiprocessing (default); if False, process sequentially
        num_processes: Number of worker processes (default: cpu_count - 1, leaving 1 core free)
        
    Returns:
        Tuple of (successful_count, failed_count, skipped_count)
    """
    import time
    import os
    
    successful = 0
    failed = 0
    skipped = 0
    
    total = len(config_dict)
    start_time = time.time()
    
    # Determine number of processes
    if num_processes is None:
        from multiprocessing import cpu_count
        num_processes = max(1, cpu_count() - 1)  # Leave 1 core free
    
    if parallel and num_processes > 1:
        logger.info(f"Starting batch processing of {total} circuits (parallel, {num_processes} processes)...")
        logger.info(f"  Note: Phase 1 multi-process parallelization ENABLED")
        logger.info(f"  Note: Simplified logging (no Queue - direct to stdout/file)")
        logger.info(f"  Note: Phase 0 algorithm optimizations active")
        
        # Prepare arguments for worker processes (no Queue!)
        process_args = [
            (key, config, output_dir, skip_graph)
            for key, config in config_dict.items()
        ]
        
        # Process in parallel using Pool
        try:
            with Pool(processes=num_processes) as pool:
                results = pool.map(process_single_circuit_simple, process_args)
            
            # Aggregate results
            for result in results:
                if result['status'] == 'completed':
                    logger.info(f"[OK] {result['key']} completed in {result['elapsed']:.2f}s")
                    successful += 1
                elif result['status'] == 'skipped':
                    logger.info(f"[--] {result['key']} skipped after {result['elapsed']:.2f}s")
                    skipped += 1
                elif result['status'] == 'failed':
                    logger.error(f"[FAIL] {result['key']} failed after {result['elapsed']:.2f}s: {result['error']}")
                    failed += 1
        
        except Exception as e:
            logger.error(f"Error during parallel processing: {e}")
            logger.warning("Falling back to sequential processing...")
            failed += sum(1 for r in results if r['status'] == 'failed') if 'results' in locals() else 0
            # Fall back to sequential processing
            for i, (key, config) in enumerate(config_dict.items(), 1):
                circuit_start = time.time()
                logger.info(f"[{i}/{total}] Processing {key} (sequential fallback)...")
                try:
                    if process_circuit(config, output_dir, skip_graph):
                        elapsed = time.time() - circuit_start
                        logger.info(f"  [OK] Completed in {elapsed:.2f}s")
                        successful += 1
                    else:
                        elapsed = time.time() - circuit_start
                        logger.info(f"  -- Skipped after {elapsed:.2f}s")
                        skipped += 1
                except Exception as e:
                    elapsed = time.time() - circuit_start
                    logger.error(f"[FAIL] Failed after {elapsed:.2f}s: {e}")
                    failed += 1
    
    else:
        # Sequential processing
        logger.info(f"Starting batch processing of {total} circuits (sequential)...")
        logger.info(f"  Note: Phase 1 multi-process parallelization DISABLED")
        logger.info(f"  Note: Phase 0 algorithm optimizations active")
        
        for i, (key, config) in enumerate(config_dict.items(), 1):
            circuit_start = time.time()
            logger.info(f"[{i}/{total}] Processing {key}...")
            try:
                if process_circuit(config, output_dir, skip_graph):
                    elapsed = time.time() - circuit_start
                    logger.info(f"  [OK] Completed in {elapsed:.2f}s")
                    successful += 1
                else:
                    elapsed = time.time() - circuit_start
                    logger.info(f"  -- Skipped after {elapsed:.2f}s")
                    skipped += 1
            except Exception as e:
                elapsed = time.time() - circuit_start
                logger.error(f"[FAIL] Failed after {elapsed:.2f}s: {e}")
                failed += 1
    
    total_time = time.time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info(f"Batch processing complete (Total time: {total_time:.2f}s)")
    logger.info(f"  [OK] Successful: {successful}")
    logger.info(f"  [FAIL] Failed: {failed}")
    logger.info(f"  -- Skipped: {skipped}")
    logger.info(f"  Average time per circuit: {total_time/total:.2f}s")
    logger.info(f"  Speedup: {total_time/total * total / total_time:.1f}x (vs theoretical sequential)")
    logger.info(f"{'='*60}")
    
    return successful, failed, skipped


