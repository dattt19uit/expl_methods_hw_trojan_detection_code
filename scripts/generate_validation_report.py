#!/usr/bin/env python3
"""
Auto-generate Statistical Validation Report

Reads all statistical analysis output files and generates a
standardized markdown report with all tables auto-populated.

Usage:
    python3 scripts/generate_validation_report.py --output REPORT.md
"""

import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import platform


def load_json_safe(filepath):
    """Load JSON file safely, return empty dict if not found."""
    try:
        with open(filepath) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"WARNING: Could not load {filepath}: {e}")
        return {}


def parse_analysis_report_txt(filepath='analysis_report.txt'):
    """Parse the text analysis report for detailed metrics."""
    try:
        with open(filepath) as f:
            content = f.read()
        
        data = {
            'dataset': {},
            'method1': {},
            'method2': {},
            'method3': {},
            'method4': {},
            'method5': {}
        }
        
        # Parse dataset info
        if 'Test Set Size:' in content:
            for line in content.split('\n'):
                if 'Test Set Size:' in line:
                    data['dataset']['test_samples'] = line.split(':')[1].strip()
                elif 'Total Trojans:' in line:
                    data['dataset']['total_trojans'] = line.split(':')[1].strip()
                elif 'Trojan Rate:' in line:
                    data['dataset']['trojan_rate'] = line.split(':')[1].strip()
        
        # Parse Method 1
        if 'METHOD 1:' in content:
            m1_section = content.split('METHOD 1:')[1].split('METHOD 2:')[0]
            data['method1']['confusion_matrix'] = {}
            
            for line in m1_section.split('\n'):
                if 'Accuracy:' in line and '%' in line:
                    data['method1']['accuracy'] = line.split(':')[1].strip()
                elif 'Precision:' in line and '%' in line:
                    data['method1']['precision'] = line.split(':')[1].strip()
                elif 'Recall:' in line and '%' in line:
                    data['method1']['recall'] = line.split(':')[1].strip()
                elif 'F1 Score:' in line:
                    data['method1']['f1'] = line.split(':')[1].strip()
                elif 'Avg Confidence:' in line:
                    data['method1']['avg_confidence'] = line.split(':')[1].strip()
                elif 'Coverage:' in line and '%' in line:
                    data['method1']['coverage'] = line.split(':')[1].strip().split('(')[0].strip()
                elif 'TN=' in line:
                    # Parse confusion matrix: TN=9,585  FP=1,761
                    parts = line.strip().split()
                    for part in parts:
                        if '=' in part:
                            key, val = part.split('=')
                            data['method1']['confusion_matrix'][key.lower()] = val.replace(',', '')
                elif 'FN=' in line and 'TP=' in line:
                    # Parse: FN=10  TP=36
                    parts = line.strip().split()
                    for part in parts:
                        if '=' in part:
                            key, val = part.split('=')
                            data['method1']['confusion_matrix'][key.lower()] = val.replace(',', '')
        
        # Parse Method 2
        if 'METHOD 2:' in content:
            m2_section = content.split('METHOD 2:')[1].split('METHOD 3:')[0]
            data['method2']['threshold'] = None
            data['method2']['confusion_matrix'] = {}
            data['method2']['baseline'] = {}
            
            # Split into subsections
            lines = m2_section.split('\n')
            in_optimized = False
            in_baseline = False
            in_confusion = False
            
            for i, line in enumerate(lines):
                # Detect sections
                if 'THRESHOLD:' in line:
                    data['method2']['threshold'] = line.split(':')[1].strip()
                elif 'Optimized Performance:' in line:
                    in_optimized = True
                    in_baseline = False
                    in_confusion = False
                elif 'Improvement vs Baseline' in line:
                    in_optimized = False
                    in_baseline = True
                    in_confusion = False
                elif 'Confusion Matrix:' in line:
                    in_optimized = False
                    in_baseline = False
                    in_confusion = True
                
                # Parse optimized performance section
                elif in_optimized:
                    if 'Accuracy:' in line and '%' in line:
                        data['method2']['accuracy'] = line.split(':')[1].strip()
                    elif 'Precision:' in line and '%' in line and '->' not in line:
                        data['method2']['precision'] = line.split(':')[1].strip()
                    elif 'Recall:' in line and '%' in line and '->' not in line:
                        data['method2']['recall'] = line.split(':')[1].strip()
                    elif 'F1 Score:' in line and '->' not in line:
                        data['method2']['f1'] = line.split(':')[1].strip()
                
                # Parse baseline improvement section
                elif in_baseline:
                    if 'Precision:' in line and '->' in line:
                        parts = line.split(':')[1].strip().split('->')
                        data['method2']['baseline']['precision'] = parts[0].strip()
                    elif 'Recall:' in line and '->' in line:
                        parts = line.split(':')[1].strip().split('->')
                        data['method2']['baseline']['recall'] = parts[0].strip()
                    elif 'False Positives Reduced:' in line:
                        data['method2']['fp_reduced'] = line.split(':')[1].strip()
                
                # Parse confusion matrix
                elif in_confusion:
                    if 'TN=' in line:
                        # Parse: TN=11,318  FP=28
                        parts = line.strip().split()
                        for part in parts:
                            if '=' in part:
                                key, val = part.split('=')
                                data['method2']['confusion_matrix'][key.lower()] = val.replace(',', '')
                    elif 'FN=' in line and 'TP=' in line:
                        # Parse: FN=22  TP=24
                        parts = line.strip().split()
                        for part in parts:
                            if '=' in part:
                                key, val = part.split('=')
                                data['method2']['confusion_matrix'][key.lower()] = val.replace(',', '')
        
        # Parse Method 3 (LIME)
        if 'METHOD 3:' in content:
            m3_section = content.split('METHOD 3:')[1].split('METHOD 4:')[0]
            for line in m3_section.split('\n'):
                if 'Total explanations:' in line:
                    data['method3']['total_explanations'] = line.split(':')[1].strip()
                elif 'Avg time per sample:' in line:
                    data['method3']['avg_time'] = line.split(':')[1].strip()
                elif 'Coverage:' in line and '%' in line:
                    data['method3']['coverage'] = line.split(':')[1].split('of')[0].strip()
        
        # Parse Method 4 (SHAP)
        if 'METHOD 4:' in content:
            m4_section = content.split('METHOD 4:')[1].split('METHOD 5:')[0]
            for line in m4_section.split('\n'):
                if 'Total explanations:' in line:
                    data['method4']['total_explanations'] = line.split(':')[1].strip()
                elif 'Avg time per sample:' in line:
                    data['method4']['avg_time'] = line.split(':')[1].strip()
                elif 'Speed advantage:' in line:
                    data['method4']['speed_vs_lime'] = line.split(':')[1].strip()
                elif 'Coverage:' in line and '%' in line:
                    data['method4']['coverage'] = line.split(':')[1].split('of')[0].strip()
        
        # Parse Method 5 (Gradient)
        if 'METHOD 5:' in content:
            m5_section = content.split('METHOD 5:')[1]
            for line in m5_section.split('\n'):
                if 'Total explanations:' in line:
                    data['method5']['total_explanations'] = line.split(':')[1].strip()
                elif 'Avg time per sample:' in line:
                    data['method5']['avg_time'] = line.split(':')[1].strip()
                elif 'Speed vs LIME:' in line:
                    data['method5']['speed_vs_lime'] = line.split(':')[1].strip()
                elif 'Speed vs SHAP:' in line:
                    data['method5']['speed_vs_shap'] = line.split(':')[1].strip()
                elif 'Coverage:' in line and '%' in line:
                    data['method5']['coverage'] = line.split(':')[1].split('of')[0].strip()
        
        return data
    except Exception as e:
        print(f"WARNING: Could not parse analysis_report.txt: {e}")
        return {}


def get_git_info():
    """Get git repository information."""
    try:
        commit = subprocess.check_output(['git', 'log', '-1', '--oneline'], 
                                        stderr=subprocess.DEVNULL).decode().strip()
        branch = subprocess.check_output(['git', 'branch', '--show-current'],
                                        stderr=subprocess.DEVNULL).decode().strip()
        return {'commit': commit, 'branch': branch}
    except:
        return {'commit': 'unknown', 'branch': 'unknown'}


def get_system_info():
    """Get system information."""
    try:
        hostname = subprocess.check_output(['hostname']).decode().strip()
    except:
        hostname = 'unknown'
    
    return {
        'hostname': hostname,
        'os': platform.system(),
        'python': platform.python_version()
    }


def format_percentage(value):
    """Format value as percentage."""
    if isinstance(value, (int, float)):
        return f"{value*100:.2f}%"
    return str(value)


def format_ci(metric_data):
    """Format confidence interval string."""
    if not metric_data:
        return "N/A"
    mean = metric_data.get('mean', 0)
    lower = metric_data.get('lower', 0)
    upper = metric_data.get('upper', 0)
    return f"{mean*100:.2f}% [95% CI: {lower*100:.2f}%, {upper*100:.2f}%]"


def format_pvalue_stars(p_value):
    """Convert p-value to significance stars."""
    if p_value < 0.001:
        return "***"
    elif p_value < 0.01:
        return "**"
    elif p_value < 0.05:
        return "*"
    else:
        return "ns"


def generate_report(output_file, seed=None, iterations=None, confidence=None):
    """Generate complete validation report."""
    
    # Load all results
    split_validation = load_json_safe('data/statistical_analysis/split_validation.json')
    confidence_intervals = load_json_safe('data/statistical_analysis/confidence_intervals.json')
    mcnemar_tests = load_json_safe('data/statistical_analysis/mcnemar_tests.json')
    effect_sizes = load_json_safe('data/statistical_analysis/effect_sizes.json')
    correlation_tests = load_json_safe('data/statistical_analysis/correlation_tests.json')
    analysis_data = load_json_safe('analysis_report.json')
    
    # Parse text analysis report for detailed metrics
    analysis_parsed = parse_analysis_report_txt('analysis_report.txt')
    
    # Load optimal threshold file
    optimal_threshold = load_json_safe('data/models/method2/optimal_threshold.json')
    
    # Get system info
    git_info = get_git_info()
    sys_info = get_system_info()
    
    # Read text analysis report if available
    analysis_text = ""
    if Path('analysis_report.txt').exists():
        with open('analysis_report.txt') as f:
            analysis_text = f.read()
    
    # Build report
    report_lines = []
    
    # Header
    report_lines.extend([
        "# Statistical Validation Report",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Hostname:** {sys_info['hostname']}",
        f"**Git Branch:** {git_info['branch']}",
        f"**Git Commit:** {git_info['commit']}",
        f"**Python Version:** {sys_info['python']}",
        f"**OS:** {sys_info['os']}",
        ""
    ])
    
    if seed is not None:
        report_lines.append(f"**Random Seed:** {seed} (for exact reproducibility)")
    if iterations is not None:
        report_lines.append(f"**Bootstrap Iterations:** {iterations}")
    if confidence is not None:
        report_lines.append(f"**Confidence Level:** {confidence*100:.0f}%")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 1. DATA VALIDATION",
        ""
    ])
    
    # Data validation results
    if split_validation:
        status = split_validation.get('overall_status', split_validation.get('status', 'UNKNOWN'))
        status_icon = "[OK]" if status == "PASSED" else "[WARNING]" if status == "WARNING" else "[ERROR]"
        report_lines.append(f"**Status:** {status_icon} {status}")
        report_lines.append("")
        report_lines.append("| Check | Status | Details |")
        report_lines.append("|-------|--------|---------|")
        
        # Handle both formats: top-level check keys or nested 'checks' dict
        checks = split_validation.get('checks', {})
        if not checks:
            # Top-level format: each check is a top-level key with 'validation_status'
            skip_keys = {'overall_status', 'status', 'checks'}
            for check_name, check_data in split_validation.items():
                if check_name in skip_keys or not isinstance(check_data, dict):
                    continue
                check_status = check_data.get('validation_status', check_data.get('status', 'UNKNOWN'))
                check_icon = "[OK]" if check_status == "PASSED" else "[WARNING]" if check_status in ("WARNING", "UNKNOWN") else "[ERROR]"
                # Build details from available fields
                details_parts = []
                if 'total_count' in check_data:
                    details_parts.append(f"Total: {check_data['total_count']:,}")
                if 'trojan_ratio' in check_data.get('test', {}):
                    details_parts.append(f"Test trojan rate: {check_data['test']['trojan_ratio']*100:.2f}%")
                if 'columns_match' in check_data:
                    details_parts.append(f"Columns match: {check_data['columns_match']}")
                if not details_parts and check_status == "UNKNOWN":
                    details_parts.append("No ID column available")
                details = "; ".join(details_parts) if details_parts else ""
                report_lines.append(f"| {check_name} | {check_icon} {check_status} | {details} |")
        else:
            for check_name, check_data in checks.items():
                check_status = check_data.get('status', 'UNKNOWN')
                check_icon = "[OK]" if check_status == "PASSED" else "[ERROR]"
                details = check_data.get('message', '')
                report_lines.append(f"| {check_name} | {check_icon} {check_status} | {details} |")
        
        report_lines.append("")
        report_lines.append(f"**File:** `data/statistical_analysis/split_validation.json`")
    else:
        report_lines.append("**Status:** [WARNING] Data validation file not found")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 2. METHODS EXPLAINABILITY ANALYSIS",
        ""
    ])
    
    # Dataset summary from parsed report
    if analysis_parsed.get('dataset'):
        dataset = analysis_parsed['dataset']
        report_lines.extend([
            "### Dataset Summary",
            "",
            f"- **Test Set:** {dataset.get('test_samples', 'N/A')} samples",
            f"- **Total Trojans:** {dataset.get('total_trojans', 'N/A')}",
            f"- **Trojan Rate:** {dataset.get('trojan_rate', 'N/A')}",
            "",
            "---",
            ""
        ])
    
    # Method 1: Property-Based
    if analysis_parsed.get('method1'):
        m1 = analysis_parsed['method1']
        report_lines.extend([
            "### Method 1: Property-Based Ensemble",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Accuracy | {m1.get('accuracy', 'N/A')} |"
        ])
        
        # Add precision/recall/F1 if available
        if m1.get('precision'):
            report_lines.append(f"| Precision | {m1.get('precision', 'N/A')} |")
        if m1.get('recall'):
            report_lines.append(f"| Recall | {m1.get('recall', 'N/A')} |")
        if m1.get('f1'):
            report_lines.append(f"| F1 Score | {m1.get('f1', 'N/A')} |")
        
        report_lines.extend([
            f"| Avg Confidence | {m1.get('avg_confidence', 'N/A')} |",
            f"| Explainability Coverage | {m1.get('coverage', 'N/A')} |",
            ""
        ])
        
        # Add confusion matrix if available
        if m1.get('confusion_matrix') and m1['confusion_matrix']:
            cm = m1['confusion_matrix']
            report_lines.extend([
                "#### Confusion Matrix",
                "",
                f"- **True Negatives (TN):** {cm.get('tn', 'N/A')}",
                f"- **False Positives (FP):** {cm.get('fp', 'N/A')}",
                f"- **False Negatives (FN):** {cm.get('fn', 'N/A')}",
                f"- **True Positives (TP):** {cm.get('tp', 'N/A')}",
                ""
            ])
    
    # Method 2: XGBoost Classification (main classification method)
    if analysis_parsed.get('method2') or optimal_threshold:
        report_lines.extend([
            "### Method 2: XGBoost Classification",
            ""
        ])
        
        # Get data from parsed report and optimal_threshold.json
        m2 = analysis_parsed.get('method2', {})
        opt_data = optimal_threshold.get('optimal', {}) if optimal_threshold else {}
        baseline_data = optimal_threshold.get('baseline', {}) if optimal_threshold else {}
        
        if m2.get('threshold'):
            report_lines.append(f"**Optimized Threshold:** {m2.get('threshold')}")
            report_lines.append("")
        
        # Performance table - format values first to avoid nested f-string issues
        accuracy_val = m2.get('accuracy') or (f"{opt_data.get('accuracy', 0)*100:.2f}%" if opt_data.get('accuracy') else 'N/A')
        precision_val = m2.get('precision') or (f"{opt_data.get('precision', 0)*100:.2f}%" if opt_data.get('precision') else 'N/A')
        recall_val = m2.get('recall') or (f"{opt_data.get('recall', 0)*100:.2f}%" if opt_data.get('recall') else 'N/A')
        f1_val = m2.get('f1') or (f"{opt_data.get('f1_score', 0):.4f}" if opt_data.get('f1_score') else 'N/A')
        
        report_lines.extend([
            "#### Optimized Performance",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Accuracy | {accuracy_val} |",
            f"| Precision | {precision_val} |",
            f"| Recall | {recall_val} |",
            f"| F1 Score | {f1_val} |",
            ""
        ])
        
        # Confusion matrix
        if m2.get('confusion_matrix') or opt_data.get('confusion_matrix'):
            cm = m2.get('confusion_matrix', opt_data.get('confusion_matrix', {}))
            report_lines.extend([
                "#### Confusion Matrix",
                "",
                f"- **True Negatives (TN):** {cm.get('tn', 'N/A')}",
                f"- **False Positives (FP):** {cm.get('fp', 'N/A')}",
                f"- **False Negatives (FN):** {cm.get('fn', 'N/A')}",
                f"- **True Positives (TP):** {cm.get('tp', 'N/A')}",
                ""
            ])
        
        # Threshold optimization impact
        if baseline_data and opt_data:
            baseline_precision = baseline_data.get('precision', 0)
            opt_precision = opt_data.get('precision', 0)
            baseline_recall = baseline_data.get('recall', 0)
            opt_recall = opt_data.get('recall', 0)
            
            if baseline_precision and opt_precision:
                precision_improvement = ((opt_precision - baseline_precision) / baseline_precision) * 100
                report_lines.extend([
                    "#### Threshold Optimization Impact",
                    "",
                    "| Metric | Baseline (0.5) | Optimized | Improvement |",
                    "|--------|----------------|-----------|-------------|",
                    f"| Precision | {baseline_precision*100:.2f}% | {opt_precision*100:.2f}% | **+{precision_improvement:.1f}%** |",
                    f"| Recall | {baseline_recall*100:.2f}% | {opt_recall*100:.2f}% | {((opt_recall - baseline_recall) / baseline_recall) * 100:.1f}% |",
                    ""
                ])
        
        if m2.get('fp_reduced'):
            report_lines.extend([
                f"**False Positives Reduced:** {m2.get('fp_reduced')}",
                ""
            ])
    
    # Method 3, 4, 5: XAI methods
    for method_num, method_name in [(3, 'LIME'), (4, 'SHAP'), (5, 'Gradient Attribution')]:
        method_key = f'method{method_num}'
        if analysis_parsed.get(method_key):
            md = analysis_parsed[method_key]
            report_lines.extend([
                f"### Method {method_num}: {method_name}",
                "",
                f"- **Explanations Generated:** {md.get('total_explanations', 'N/A')}",
                f"- **Coverage:** {md.get('coverage', 'N/A')}",
                f"- **Avg Time per Sample:** {md.get('avg_time', 'N/A')}",
            ])
            
            if method_num == 4 and md.get('speed_vs_lime'):
                report_lines.append(f"- **Speed vs LIME:** {md.get('speed_vs_lime')}")
            elif method_num == 5:
                if md.get('speed_vs_lime'):
                    report_lines.append(f"- **Speed vs LIME:** {md.get('speed_vs_lime')}")
                if md.get('speed_vs_shap'):
                    report_lines.append(f"- **Speed vs SHAP:** {md.get('speed_vs_shap')}")
            
            report_lines.append("")
    
    report_lines.extend([
        "**Full Analysis:** `analysis_report.txt`",
        ""
    ])
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 3. BOOTSTRAP CONFIDENCE INTERVALS",
        ""
    ])
    
    # Confidence intervals
    if confidence_intervals:
        for method_name, metrics in confidence_intervals.items():
            # Skip non-method keys (e.g. 'metadata' added by optimized CI computation)
            if not isinstance(metrics, dict) or 'mean' in metrics or method_name == 'metadata':
                continue
            report_lines.append(f"### {method_name.upper()}")
            report_lines.append("")
            report_lines.append("| Metric | Mean | 95% CI | Std Error |")
            report_lines.append("|--------|------|--------|-----------|")
            
            for metric_name, ci_data in metrics.items():
                mean = ci_data.get('mean', 0)
                lower = ci_data.get('lower', 0)
                upper = ci_data.get('upper', 0)
                std_err = ci_data.get('std_error', 0)
                report_lines.append(
                    f"| {metric_name.capitalize()} | "
                    f"{mean*100:.2f}% | "
                    f"[{lower*100:.2f}%, {upper*100:.2f}%] | "
                    f"{std_err*100:.3f}% |"
                )
            report_lines.append("")
        
        report_lines.append(f"**Iterations:** {iterations if iterations else 'N/A'}")
        report_lines.append("**File:** `data/statistical_analysis/confidence_intervals.json`")
    else:
        report_lines.append("[WARNING] Confidence intervals not computed")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 4. STATISTICAL SIGNIFICANCE TESTS (McNemar's)",
        ""
    ])
    
    # McNemar tests
    if mcnemar_tests:
        report_lines.append("| Comparison | Statistic | P-Value | Significance | Interpretation |")
        report_lines.append("|------------|-----------|---------|--------------|----------------|")
        
        for comparison, result in mcnemar_tests.items():
            statistic = result.get('statistic', 0)
            p_value = result.get('p_value', 1.0)
            sig = format_pvalue_stars(p_value)
            test_type = result.get('test_type', 'unknown')
            
            interpretation = "Highly significant" if sig == "***" else \
                           "Very significant" if sig == "**" else \
                           "Significant" if sig == "*" else \
                           "Not significant"
            
            report_lines.append(
                f"| {comparison} | {statistic:.2f} | {p_value:.4f} | {sig} | {interpretation} ({test_type}) |"
            )
        
        report_lines.extend([
            "",
            "**Significance levels:**",
            "- `***` p < 0.001 (highly significant)",
            "- `**` p < 0.01 (very significant)",
            "- `*` p < 0.05 (significant)",
            "- `ns` p >= 0.05 (not significant)",
            "",
            "**File:** `data/statistical_analysis/mcnemar_tests.json`"
        ])
    else:
        report_lines.append("[WARNING] McNemar tests not computed")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 5. EFFECT SIZES (Cohen's d)",
        ""
    ])
    
    # Effect sizes - handle nested format {metric: {comparison: {cohens_d, magnitude, ...}}}
    if effect_sizes:
        report_lines.append("| Metric | Comparison | Cohen's d | Magnitude | Means |")
        report_lines.append("|--------|------------|-----------|-----------|-------|")
        
        for metric_or_comparison, value in effect_sizes.items():
            if isinstance(value, dict) and any(isinstance(v, dict) and 'cohens_d' in v for v in value.values()):
                # Nested format: {metric: {comparison: {cohens_d, magnitude, ...}}}
                for comparison, result in value.items():
                    d = result.get('cohens_d', 0)
                    magnitude = result.get('magnitude', 'unknown')
                    mean1 = result.get('mean1', 0)
                    mean2 = result.get('mean2', 0)
                    report_lines.append(
                        f"| {metric_or_comparison} | {comparison.replace('_', ' ')} | {d:+.3f} | {magnitude.capitalize()} | {mean1:.3f} vs {mean2:.3f} |"
                    )
            elif isinstance(value, dict) and 'cohens_d' in value:
                # Flat format: {comparison: {cohens_d, magnitude, direction}}
                d = value.get('cohens_d', 0)
                magnitude = value.get('magnitude', 'unknown')
                direction = value.get('direction', '')
                report_lines.append(
                    f"| - | {metric_or_comparison} | {d:+.3f} | {magnitude.capitalize()} | {direction} |"
                )
        
        report_lines.extend([
            "",
            "**Effect size interpretation:**",
            "- |d| < 0.2: negligible",
            "- 0.2 <= |d| < 0.5: small",
            "- 0.5 <= |d| < 0.8: medium",
            "- |d| >= 0.8: large",
            "",
            "**File:** `data/statistical_analysis/effect_sizes.json`"
        ])
    else:
        report_lines.append("[WARNING] Effect sizes not computed")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 6. CORRELATION TESTS",
        ""
    ])
    
    # Correlation tests - handle new format with 'correlations' sub-key
    corr_data = correlation_tests
    if isinstance(corr_data, dict) and 'correlations' in corr_data:
        corr_data = corr_data['correlations']
    
    if corr_data and len(corr_data) > 0:
        report_lines.append("| Method Pair | Spearman rho | P-Value | Significance |")
        report_lines.append("|-------------|------------|---------|--------------|")
        
        for pair, result in corr_data.items():
            if not isinstance(result, dict):
                continue
            rho = result.get('rho', 0)
            p_value = result.get('p_value', 1.0)
            sig = format_pvalue_stars(p_value)
            
            report_lines.append(
                f"| {pair.replace('_', ' ')} | {rho:.3f} | {p_value:.4f} | {sig} |"
            )
        
        # Add feature ranking table if available
        if isinstance(correlation_tests, dict) and 'rankings' in correlation_tests:
            feature_order = correlation_tests.get('feature_order', [])
            rankings = correlation_tests.get('rankings', {})
            importance_values = correlation_tests.get('importance_values', {})
            
            if feature_order and rankings:
                report_lines.extend(["", "### Feature Rankings (1=most important)", ""])
                header = "| Feature | " + " | ".join(rankings.keys()) + " |"
                sep = "|---------|" + "|".join(["--------"] * len(rankings)) + "|"
                report_lines.append(header)
                report_lines.append(sep)
                for i, feat in enumerate(feature_order):
                    row = f"| {feat} | " + " | ".join(str(int(r[i])) for r in rankings.values()) + " |"
                    report_lines.append(row)
        
        report_lines.extend([
            "",
            "### Paper Claim Verification",
            ""
        ])
        
        # Check LIME vs SHAP correlation
        lime_shap_key = None
        for key in corr_data.keys():
            if 'lime' in key.lower() and 'shap' in key.lower():
                lime_shap_key = key
                break
        
        if lime_shap_key:
            result = corr_data[lime_shap_key]
            actual_rho = result.get('rho', 0)
            actual_p = result.get('p_value', 1.0)
            
            paper_claim_rho = 0.94
            paper_claim_p = 0.001
            
            rho_diff = abs(actual_rho - paper_claim_rho)
            rho_verified = rho_diff < 0.05  # Within 5% tolerance
            p_verified = actual_p < paper_claim_p
            
            report_lines.extend([
                "**LIME vs SHAP Correlation:**",
                f"- Paper claims: rho=0.94, p<0.001",
                f"- Actual result: rho={actual_rho:.3f}, p={actual_p:.4f}",
                f"- **Verification Status:** {'[OK] VERIFIED' if rho_verified and p_verified else '[ERROR] DISCREPANCY'}",
                ""
            ])
            
            if not rho_verified:
                report_lines.append(f"[WARNING] **WARNING:** Correlation differs from paper claim by {rho_diff:.3f}")
                report_lines.append("")
        
        report_lines.append("**File:** `data/statistical_analysis/correlation_tests.json`")
    else:
        report_lines.append("[WARNING] Correlation tests not computed or no results")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 7. REPRODUCIBILITY INFORMATION",
        "",
        "### Commands Executed",
        "",
        "```bash",
        "# Methods explainability analysis",
        "python3 scripts/analyze_methods_explainability.py --output-txt analysis_report.txt --output-json analysis_report.json",
        "",
        "# Data validation",
        "python3 scripts/statistical_analysis/validate_train_test_split.py --data-dir data --expected-total 56961 --output data/statistical_analysis/split_validation.json",
        "",
        "# Bootstrap confidence intervals"
    ])
    
    if seed is not None and iterations is not None:
        report_lines.append(f"python3 scripts/statistical_analysis/compute_confidence_intervals.py --results-dir data/models --n-iterations {iterations} --seed {seed} --output data/statistical_analysis/confidence_intervals.json")
    else:
        report_lines.append("python3 scripts/statistical_analysis/compute_confidence_intervals.py --results-dir data/models --n-iterations 10000 --output data/statistical_analysis/confidence_intervals.json")
    
    report_lines.extend([
        "",
        "# McNemar paired comparison tests",
        "python3 scripts/statistical_analysis/mcnemar_tests.py --results-dir data/models --output data/statistical_analysis/mcnemar_tests.json",
        "",
        "# Effect sizes",
        "python3 scripts/statistical_analysis/effect_size_calculations.py --ci-file data/statistical_analysis/confidence_intervals.json --output data/statistical_analysis/effect_sizes.json",
        "",
        "# Correlation tests",
        "python3 scripts/statistical_analysis/correlation_significance.py --results-dir data/models --output data/statistical_analysis/correlation_tests.json",
        "```",
        "",
        "### Environment",
        "",
        f"- **Python Version:** {sys_info['python']}",
        f"- **Operating System:** {sys_info['os']}",
        f"- **Git Commit:** {git_info['commit']}",
        f"- **Git Branch:** {git_info['branch']}",
        ""
    ])
    
    if seed is not None:
        report_lines.extend([
            "### Reproducibility Notes",
            "",
            f"This analysis was run with **random seed {seed}** for exact reproducibility.",
            "Re-running with the same seed and data will produce bitwise identical results.",
            ""
        ])
    
    report_lines.extend([
        "---",
        "",
        "## 8. SUMMARY",
        "",
        "### Data Quality",
        f"- Data validation: {split_validation.get('overall_status', split_validation.get('status', 'UNKNOWN'))}",
        f"- Total samples: {split_validation.get('sample_counts', {}).get('total_count', split_validation.get('total_samples', 'N/A'))}",
        "",
        "### Statistical Validation",
        f"- Bootstrap CIs computed: {'[OK] Yes' if confidence_intervals else '[ERROR] No'}",
        f"- McNemar tests completed: {'[OK] Yes' if mcnemar_tests else '[ERROR] No'}",
        f"- Effect sizes calculated: {'[OK] Yes' if effect_sizes else '[ERROR] No'}",
        f"- Correlation tests completed: {'[OK] Yes' if correlation_tests else '[ERROR] No'}",
        "",
        "### Files Generated",
        "- `analysis_report.txt` - Human-readable methods analysis",
        "- `analysis_report.json` - Machine-readable methods analysis",
        "- `data/statistical_analysis/split_validation.json` - Data validation results",
        "- `data/statistical_analysis/confidence_intervals.json` - Bootstrap CIs",
        "- `data/statistical_analysis/mcnemar_tests.json` - Statistical significance tests",
        "- `data/statistical_analysis/effect_sizes.json` - Effect size calculations",
        "- `data/statistical_analysis/correlation_tests.json` - Correlation tests",
        "",
        "---",
        "",
        f"**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Hostname:** {sys_info['hostname']}",
        ""
    ])
    
    # Write report
    report_content = "\n".join(report_lines)
    with open(output_file, 'w') as f:
        f.write(report_content)
    
    print(f"[OK] Validation report generated: {output_file}")
    print(f"   Lines: {len(report_lines)}")
    print(f"   Size: {len(report_content)} bytes")
    
    return report_content


def main():
    parser = argparse.ArgumentParser(description='Generate statistical validation report')
    parser.add_argument('--output', required=True, help='Output markdown file')
    parser.add_argument('--seed', type=int, default=None, help='Random seed used (for documentation)')
    parser.add_argument('--iterations', type=int, default=None, help='Bootstrap iterations used')
    parser.add_argument('--confidence', type=float, default=None, help='Confidence level used')
    
    args = parser.parse_args()
    
    generate_report(args.output, args.seed, args.iterations, args.confidence)


if __name__ == '__main__':
    main()
