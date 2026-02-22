#!/usr/bin/env python3
"""
CLI wrapper for data aggregation.

Combines individual circuit CSV files into train/test datasets.
"""

import sys


def main():
    """CLI entry point for xai-aggregate-data command."""
    # Import here to use the aggregator's main function directly
    from .aggregator import main as aggregator_main
    
    # Call the aggregator's main which has full argument parsing
    return aggregator_main()


if __name__ == '__main__':
    sys.exit(main())
