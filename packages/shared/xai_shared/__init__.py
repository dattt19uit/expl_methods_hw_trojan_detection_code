"""
xai_shared - Shared Infrastructure for XAI Hardware Trojan Detection

This package provides common utilities used across all XAI methods.
"""

__version__ = "1.0.0"
__author__ = "Paul Whitten, Francis Wolff, Chris Papachristou"

# Export threshold optimization utilities
from .threshold_optimizer import ThresholdOptimizer, ThresholdMetrics

__all__ = ['ThresholdOptimizer', 'ThresholdMetrics']
