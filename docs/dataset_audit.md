# Dataset Audit Report: Trust-Hub Benchmark Suite

**Date:** 2026-09-15  
**Scope:** Trust-Hub Gate-Level Netlist Benchmarks (Phase A Audit)  
**Total Circuits Audited:** 30 across 5 distinct circuit families  

## 1. Executive Summary & Aggregate Statistics

- **Total Standard Cell Gates (Nodes):** 47,464
- **Total Nets (Wires):** 61,067
- **Total Directed Bipartite Edges:** 202,415
- **Total Trojan Cells:** 370
- **Total Clean Cells:** 47,094
- **Overall Trojan Prevalence:** **0.7795%** (Extreme class imbalance: 1 Trojan cell per ~247 clean cells)

## 2. Family-Level Breakdown

| Family | Circuits | Total Cells | Total Nets | Total Edges | Trojan Cells | Clean Cells | Trojan % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `RS232` | 22 | 5,299 | 6,257 | 22,039 | 243 | 5,056 | 4.586% |
| `s15850` | 1 | 2,182 | 2,798 | 8,981 | 27 | 2,155 | 1.237% |
| `s35932` | 3 | 16,341 | 21,993 | 68,135 | 63 | 16,278 | 0.386% |
| `s38417` | 2 | 10,685 | 14,091 | 48,945 | 27 | 10,658 | 0.253% |
| `s38584` | 2 | 12,957 | 15,928 | 54,315 | 10 | 12,947 | 0.077% |
| **TOTAL** | **30** | **47,464** | **61,067** | **202,415** | **370** | **47,094** | **0.780%** |

## 3. Detailed Circuit-Level Audit

| Circuit | Family | Cells | Nets | Edges | Trojans | Ratio | Parse | Label Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `RS232-T1000-90nm` | RS232 | 268 | 312 | 1030 | 12 | 0.0448 | OK | MISMATCH |
| `RS232-T1000-180nm` | RS232 | 215 | 259 | 983 | 13 | 0.0605 | OK | VERIFIED |
| `RS232-T1100-90nm` | RS232 | 271 | 314 | 1036 | 12 | 0.0443 | OK | VERIFIED |
| `RS232-T1200-90nm` | RS232 | 273 | 316 | 1042 | 14 | 0.0513 | OK | VERIFIED |
| `RS232-T1300-90nm` | RS232 | 267 | 308 | 1017 | 9 | 0.0337 | OK | VERIFIED |
| `RS232-T1300-180nm` | RS232 | 213 | 254 | 967 | 9 | 0.0423 | OK | VERIFIED |
| `RS232-T1400-90nm` | RS232 | 269 | 312 | 1036 | 13 | 0.0483 | OK | VERIFIED |
| `RS232-T1500-90nm` | RS232 | 270 | 315 | 1037 | 13 | 0.0481 | OK | MISMATCH |
| `RS232-T1600-90nm` | RS232 | 265 | 309 | 1013 | 9 | 0.0340 | OK | MISMATCH |
| `s15850-T100-generic` | s15850 | 2182 | 2798 | 8981 | 27 | 0.0124 | OK | VERIFIED |
| `s35932-T100-generic` | s35932 | 5441 | 7325 | 22699 | 15 | 0.0028 | OK | VERIFIED |
| `s35932-T200-generic` | s35932 | 5438 | 7321 | 22692 | 12 | 0.0022 | OK | VERIFIED |
| `s35932-T300-generic` | s35932 | 5462 | 7347 | 22744 | 36 | 0.0066 | OK | VERIFIED |
| `s38417-T100-generic` | s38417 | 5341 | 7044 | 24468 | 12 | 0.0022 | OK | VERIFIED |
| `s38417-T200-generic` | s38417 | 5344 | 7047 | 24477 | 15 | 0.0028 | OK | VERIFIED |
| `s38584-T100-generic` | s38584 | 6482 | 7967 | 27165 | 8 | 0.0012 | OK | VERIFIED |
| `s38584-T300-generic` | s38584 | 6475 | 7961 | 27150 | 2 | 0.0003 | OK | VERIFIED |
| `RS232-T1100-180nm` | RS232 | 216 | 258 | 986 | 12 | 0.0556 | OK | VERIFIED |
| `RS232-T1200-180nm` | RS232 | 216 | 259 | 998 | 14 | 0.0648 | OK | VERIFIED |
| `RS232-T1400-180nm` | RS232 | 215 | 258 | 989 | 13 | 0.0605 | OK | VERIFIED |
| `RS232-T1500-180nm` | RS232 | 216 | 261 | 991 | 14 | 0.0648 | OK | VERIFIED |
| `RS232-T1600-180nm` | RS232 | 214 | 259 | 980 | 12 | 0.0561 | OK | VERIFIED |
| `RS232-T1700-90nm` | RS232 | 264 | 308 | 1012 | 8 | 0.0303 | OK | VERIFIED |
| `RS232-T1700-180nm` | RS232 | 210 | 254 | 962 | 8 | 0.0381 | OK | VERIFIED |
| `RS232-T1800-90nm` | RS232 | 256 | 300 | 976 | 0 | 0.0000 | OK | MISMATCH |
| `RS232-T1800-180nm` | RS232 | 206 | 250 | 935 | 4 | 0.0194 | OK | VERIFIED |
| `RS232-T1900-90nm` | RS232 | 276 | 320 | 1053 | 16 | 0.0580 | OK | VERIFIED |
| `RS232-T1900-180nm` | RS232 | 218 | 262 | 999 | 16 | 0.0734 | OK | VERIFIED |
| `RS232-T2000-90nm` | RS232 | 268 | 312 | 1024 | 11 | 0.0410 | OK | VERIFIED |
| `RS232-T2000-180nm` | RS232 | 213 | 257 | 973 | 11 | 0.0516 | OK | VERIFIED |

## 4. Integrity and Leakage Checks

1. **Duplication Check:** All 30 circuit configuration keys and underlying directories are unique.
2. **Parsing Completeness:** 30/30 circuits successfully parsed into valid bipartite graph structures (`nodes.csv` and `edges.csv`).
3. **Label Consistency:** Trojan annotations were cross-referenced against `circuit_configs.json`. Any differences in hierarchical naming prefixes (e.g. escaped identifiers) have been verified to match the netlist instances.
4. **Noted Observations:**
   - [RS232-T1000-90nm] Label mismatch: Annotated=13, Graph=12. Missing: ['U304'], Extra: []
   - [RS232-T1500-90nm] Label mismatch: Annotated=14, Graph=13. Missing: ['U304'], Extra: []
   - [RS232-T1600-90nm] Label mismatch: Annotated=12, Graph=9. Missing: ['iDatasend_reg_2', 'U300', 'iDatasend_reg_1'], Extra: []
   - [RS232-T1800-90nm] Label mismatch: Annotated=4, Graph=0. Missing: ['U301', 'U300', 'U303'], Extra: []
