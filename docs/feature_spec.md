# Feature Specification & Data Leakage Audit

**Date:** 2026-09-15  
**Status:** Officially Audited and Frozen (Phase C Deliverable)  

## 1. Feature Dimension Verification

- **Total Cell Feature Dimension ($x_{\text{cell}}$):** **34D**
  - 20D One-Hot Logic Gate Family
  - 1D Sequential Flip-Flop Flag (`is_sequential`)
  - 13D Topological & Hop Distance Metrics on $G_{\text{data}}$

- **Total Net Feature Dimension ($x_{\text{net}}$):** **20D**
  - 6D One-Hot Wire/Port Type
  - 1D Primary Output Port Flag (`is_output`)
  - 13D Topological & Hop Distance Metrics on $G_{\text{data}}$

## 2. Complete Feature Schema Table

| Feature Name | Node Type | Dim | Definition | Topology Dependent | Requires Train Stats | Uses Label | Normalization |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| `cell_family_onehot` | `cell` | 20 | One-hot encoding of logic gate type (AND, NAND, OR, NOR, XOR, XNOR, INV, BUF, AOI, AO, OAI, OA, MUX, DFF, LSD, ISOL, etc.) | False | False | False | One-hot (binary 0/1) |
| `is_sequential` | `cell` | 1 | Binary indicator if cell is a flip-flop/latch (DFF/SDFF) | False | False | False | Binary (0.0 or 1.0) |
| `LGFi` | `cell` | 1 | Logic Gate Fan-in (in-degree of gate) | True | True | False | StandardScaler (z-score on train fold) |
| `ffi` | `cell` | 1 | Shortest logic hop distance from nearest Flip-Flop to gate via G_data | True | True | False | StandardScaler (z-score on train fold) |
| `ffo` | `cell` | 1 | Shortest logic hop distance from gate to nearest downstream Flip-Flop via G_data | True | True | False | StandardScaler (z-score on train fold) |
| `PI` | `cell` | 1 | Shortest logic hop distance from Primary Inputs to gate via G_data | True | True | False | StandardScaler (z-score on train fold) |
| `PO` | `cell` | 1 | Shortest logic hop distance from gate to Primary Outputs via G_data | True | True | False | StandardScaler (z-score on train fold) |
| `in_degree` | `cell` | 1 | Directed in-degree on bipartite netlist graph | True | True | False | StandardScaler (z-score on train fold) |
| `out_degree` | `cell` | 1 | Directed out-degree on bipartite netlist graph | True | True | False | StandardScaler (z-score on train fold) |
| `pagerank` | `cell` | 1 | NetworkX PageRank centrality on G_data | True | True | False | StandardScaler (z-score on train fold) |
| `betweenness` | `cell` | 1 | NetworkX betweenness centrality on G_data | True | True | False | StandardScaler (z-score on train fold) |
| `closeness` | `cell` | 1 | NetworkX closeness centrality on G_data | True | True | False | StandardScaler (z-score on train fold) |
| `clustering` | `cell` | 1 | Local clustering coefficient on undirected projection of G_data | True | True | False | StandardScaler (z-score on train fold) |
| `core_number` | `cell` | 1 | k-core decomposition shell number on G_data | True | True | False | StandardScaler (z-score on train fold) |
| `logic_depth_ratio` | `cell` | 1 | Relative depth position: PI / (PI + PO + 1e-6) | True | True | False | StandardScaler (z-score on train fold) |
| `net_type_onehot` | `net` | 6 | One-hot encoding of Verilog net type (wire, input, output, inout, supply0, supply1) | False | False | False | One-hot (binary 0/1) |
| `is_output` | `net` | 1 | Binary indicator if net is a primary output port of the top module | False | False | False | Binary (0.0 or 1.0) |
| `net_topological_metrics` | `net` | 13 | 13 topological metrics calculated for net nodes on G_data (matching cell feature schema) | True | True | False | StandardScaler (z-score on train fold) |

## 3. Data Leakage & Independence Verification

1. **Label Isolation (`uses_label = False`):** Verified that ZERO features compute or access the ground truth `is_trojan` label. Features are derived purely from Verilog AST syntax and directed bipartite graph topology.
2. **LOFO Preprocessing Isolation:** In cross-family LOFO experiments, feature standard scalers (`scaler_mean`, `scaler_std`) are computed exclusively across training circuits. The held-out circuit family does NOT contribute to z-score normalization statistics.
3. **Threshold Selection Independence:** GNN decision thresholds $\tau^*$ are determined via 100-step grid search on the validation partition only (`val_idx`), completely isolated from the evaluation test set.
