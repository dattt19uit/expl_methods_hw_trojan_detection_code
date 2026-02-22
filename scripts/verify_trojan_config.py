#!/usr/bin/env python3
"""Verify trojan node configuration against Verilog source files.

Compares TjFree (trojan-free) vs TjIn (trojan-injected) Verilog netlists
to discover which cell instances were added by the trojan insertion, then
verifies those match the nodes listed in circuit_configs.json.

Strategy per circuit type:
  - Non-RS232 (s15850, s35932, s38417, s38584): Have TjFree and TjIn files.
    Diff to find all added instances; filter to trojan-named ones.
  - RS232 (90nm/180nm): No TjFree baseline. Verify each configured trojan
    instance exists in the Verilog file.

Usage:
    python scripts/verify_trojan_config.py            # summary view
    python scripts/verify_trojan_config.py --verbose   # show discovered nodes

Run from the pipeline root directory.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return json.load(f)


def extract_instances_from_verilog(verilog_path: str) -> dict[str, str]:
    """Extract cell instance names and their cell types from a Verilog netlist.

    Returns dict mapping instance_name -> cell_type.
    Matches: CellType InstanceName ( ...
    """
    instances = {}
    with open(verilog_path) as f:
        content = f.read()
    skip = {'module', 'wire', 'assign', 'input', 'output', 'inout', 'reg', 'endmodule'}
    for match in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\(', content, re.MULTILINE):
        cell_type, inst_name = match.group(1), match.group(2)
        if cell_type not in skip:
            instances[inst_name] = cell_type
    return instances


def diff_instances(tj_free_path: str, tj_in_path: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Diff TjFree vs TjIn to find added, removed, and common instances.

    Returns (added, removed, common) where each is {instance_name: cell_type}.
    """
    free = extract_instances_from_verilog(tj_free_path)
    tjin = extract_instances_from_verilog(tj_in_path)

    added = {k: tjin[k] for k in tjin if k not in free}
    removed = {k: free[k] for k in free if k not in tjin}
    common = {k: tjin[k] for k in tjin if k in free}

    return added, removed, common


def is_trojan_name(name: str) -> bool:
    """Check if an instance name looks like a trojan-related component."""
    pattern = re.compile(
        r'Trojan|Tg\d_|TjPayload|Trigger|Payload|INVtest|INV_test',
        re.IGNORECASE
    )
    return bool(pattern.search(name))


def verify_educational(key: str, entry: dict, base_dir: str, verbose: bool) -> dict:
    """Verify non-RS232 circuit using TjFree/TjIn diff."""
    config_nodes = set(entry['nodes'])
    tj_in_path = os.path.join(base_dir, entry['verilog_path'])
    tj_free_path = tj_in_path.replace('/TjIn/', '/TjFree/')

    result = {'key': key, 'config_count': len(config_nodes), 'method': 'diff'}

    if not os.path.exists(tj_in_path):
        result['status'] = 'MISSING_TJIN'
        return result
    if not os.path.exists(tj_free_path):
        result['status'] = 'MISSING_TJFREE'
        return result

    added, removed, common = diff_instances(tj_free_path, tj_in_path)

    # Separate trojan-named instances from infrastructure changes (DFF rewiring etc.)
    trojan_added = {k: v for k, v in added.items() if is_trojan_name(k)}
    infra_added = {k: v for k, v in added.items() if not is_trojan_name(k)}

    missing_from_config = set(trojan_added.keys()) - config_nodes
    extra_in_config = config_nodes - set(trojan_added.keys())

    result['trojan_added'] = trojan_added
    result['infra_added'] = infra_added
    result['removed'] = removed
    result['missing_from_config'] = missing_from_config
    result['extra_in_config'] = extra_in_config

    if not missing_from_config and not extra_in_config:
        result['status'] = 'OK'
    else:
        result['status'] = 'MISMATCH'

    if verbose:
        print(f"\n{'='*80}")
        print(f"  {key}")
        print(f"  TjFree: {os.path.relpath(tj_free_path, base_dir)}")
        print(f"  TjIn:   {os.path.relpath(tj_in_path, base_dir)}")
        print(f"{'='*80}")
        print(f"  Instances in TjFree: {len(common) + len(removed):>5}")
        print(f"  Instances in TjIn:   {len(common) + len(added):>5}")
        print(f"  Added (total):       {len(added):>5}")
        print(f"    Trojan-named:      {len(trojan_added):>5}")
        print(f"    Infrastructure:    {len(infra_added):>5}  (DFF scan-chain rewiring, etc.)")
        if removed:
            print(f"  Removed:             {len(removed):>5}  (replaced by trojan-modified versions)")

        print(f"\n  Trojan instances discovered from diff:")
        for inst in sorted(trojan_added.keys()):
            in_config = "OK" if inst in config_nodes else "NOT IN CONFIG"
            print(f"    {trojan_added[inst]:<20} {inst:<30} [{in_config}]")

        if missing_from_config:
            print(f"\n  ** Missing from config (in Verilog but not configured):")
            for inst in sorted(missing_from_config):
                print(f"       {inst}")
        if extra_in_config:
            print(f"\n  ** Extra in config (configured but not in Verilog diff):")
            for inst in sorted(extra_in_config):
                print(f"       {inst}")

        if infra_added and len(infra_added) <= 15:
            print(f"\n  Infrastructure additions (not trojans, just scan-chain changes):")
            for inst in sorted(infra_added.keys()):
                print(f"    {infra_added[inst]:<20} {inst}")
        elif infra_added:
            print(f"\n  Infrastructure additions: {len(infra_added)} instances (DFF/SDFFX1 scan-chain rewiring)")

    return result


def verify_rs232(key: str, entry: dict, base_dir: str, verbose: bool) -> dict:
    """Verify RS232 circuit -- check configured trojan instances exist in Verilog."""
    config_nodes = set(entry['nodes'])
    verilog_path = os.path.join(base_dir, entry['verilog_path'])

    result = {'key': key, 'config_count': len(config_nodes), 'method': 'parse'}

    if not os.path.exists(verilog_path):
        result['status'] = 'MISSING_VERILOG'
        return result

    all_instances = extract_instances_from_verilog(verilog_path)
    found = config_nodes & set(all_instances.keys())
    missing = config_nodes - set(all_instances.keys())

    result['found_count'] = len(found)
    result['missing'] = missing
    result['status'] = 'OK' if not missing else 'NOT_FOUND'

    if verbose:
        tech = entry.get('tech', '?')
        print(f"\n  {key} ({tech}): {len(found)}/{len(config_nodes)} nodes found in Verilog")
        if missing:
            print(f"    Missing: {sorted(missing)}")
            print(f"    (Likely optimized away during synthesis for this tech node)")

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed diff results per circuit')
    args = parser.parse_args()

    # Determine base directory
    base_dir = os.getcwd()
    config_path = os.path.join(base_dir, 'configs', 'circuit_configs.json')
    if not os.path.exists(config_path):
        base_dir = str(Path(__file__).parent.parent)
        config_path = os.path.join(base_dir, 'configs', 'circuit_configs.json')
    if not os.path.exists(config_path):
        print("ERROR: Cannot find configs/circuit_configs.json")
        print("  Run from pipeline root directory.")
        sys.exit(1)

    config = load_config(config_path)
    print(f"Loaded {len(config)} circuit configurations\n")

    if args.verbose:
        print("=" * 80)
        print("  NON-RS232 CIRCUITS: TjFree vs TjIn Diff Analysis")
        print("=" * 80)

    results = []
    for key in sorted(config.keys()):
        entry = config[key]
        if entry.get('library_type') == 'educational':
            results.append(verify_educational(key, entry, base_dir, args.verbose))

    if args.verbose:
        print(f"\n\n{'='*80}")
        print("  RS232 CIRCUITS: Instance Existence Check")
        print("=" * 80)

    for key in sorted(config.keys()):
        entry = config[key]
        if not entry.get('library_type') == 'educational':
            results.append(verify_rs232(key, entry, base_dir, args.verbose))

    # Summary table
    print(f"\n\n{'Circuit':<28} {'Method':<6} {'Status':<12} {'Nodes':>5}  Details")
    print("-" * 95)

    ok_count = 0
    issue_count = 0

    for r in results:
        status = r['status']
        details = ""

        if status == 'OK':
            ok_count += 1
            if r['method'] == 'diff':
                n = len(r['trojan_added'])
                details = f"{n} trojan instances confirmed via TjFree/TjIn diff"
            else:
                details = f"{r['found_count']}/{r['config_count']} found in Verilog"
        elif status == 'MISMATCH':
            issue_count += 1
            parts = []
            if r['missing_from_config']:
                parts.append(f"not in config: {sorted(r['missing_from_config'])}")
            if r['extra_in_config']:
                parts.append(f"not in diff: {sorted(r['extra_in_config'])}")
            details = "; ".join(parts)
        elif status == 'NOT_FOUND':
            issue_count += 1
            details = f"missing from Verilog: {sorted(r['missing'])}"
        else:
            issue_count += 1
            details = status

        marker = "OK" if status == 'OK' else "**"
        print(f"{r['key']:<28} {r['method']:<6} {marker:<12} {r['config_count']:>5}  {details}")

    print(f"\n{'='*95}")
    print(f"Summary: {ok_count} OK, {issue_count} issues out of {len(results)} circuits")

    if issue_count > 0:
        sys.exit(1)
    else:
        print("All trojan node configurations verified!")
        sys.exit(0)


if __name__ == '__main__':
    main()
