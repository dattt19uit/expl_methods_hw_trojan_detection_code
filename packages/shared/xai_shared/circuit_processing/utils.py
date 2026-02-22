"""
Circuit processing utilities - helper functions for circuit validation.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_circuit_verilog_path(config, base_path='.'):
    """Get the full path to a circuit's Verilog file.
    
    Args:
        config: Circuit configuration dictionary
        base_path: Base directory for relative paths
        
    Returns:
        Absolute path to Verilog file
    """
    verilog_path = Path(config['verilog_path'])
    
    if not verilog_path.is_absolute():
        verilog_path = Path(base_path) / verilog_path
    
    return verilog_path.resolve()


def validate_circuit_config(config):
    """Validate that a circuit configuration has all required fields.
    
    Args:
        config: Circuit configuration dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['part', 'impl', 'tech', 'verilog_path', 'nodes']
    
    for field in required_fields:
        if field not in config:
            return False, f"Missing required field: {field}"
    
    if not isinstance(config['nodes'], list):
        return False, "Field 'nodes' must be a list"
    
    if len(config['nodes']) == 0:
        return False, "Field 'nodes' cannot be empty"
    
    return True, None
