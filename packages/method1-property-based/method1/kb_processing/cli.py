#!/usr/bin/env python3
"""CLI wrapper for KB processing"""

import argparse
from .process import process_kb


def main():
    """Main entry point for method1-kb command"""
    parser = argparse.ArgumentParser(
        prog='method1-kb',
        description='Process knowledge base from trained model predictions',
        epilog='Computes voting ensemble and effectiveness metrics'
    )
    parser.add_argument('-i', '--input', required=True, 
                       help='Folder with prediction JSONs from training')
    parser.add_argument('-o', '--output', required=True, 
                       help='Output folder for processed KB')
    
    args = parser.parse_args()
    
    process_kb(
        input_folder=args.input,
        output_folder=args.output
    )


if __name__ == '__main__':
    main()
