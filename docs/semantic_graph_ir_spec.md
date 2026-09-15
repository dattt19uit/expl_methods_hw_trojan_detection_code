# Specification: Semantic Graph Intermediate Representation (Semantic Graph IR)

**Date:** 2026-09-15  
**Status:** Officially Audited and Frozen (Phase B Deliverable)  

## 1. Mathematical Formalism

A gate-level netlist is represented as a directed heterogeneous bipartite graph:
$$\mathcal{G} = (\mathcal{V}_{\text{cell}}, \mathcal{V}_{\text{net}}, \mathcal{E}, \Phi_{\mathcal{V}}, \Phi_{\mathcal{E}})$$

Where:
- $\mathcal{V}_{\text{cell}} \cap \mathcal{V}_{\text{net}} = \emptyset$ strictly enforces the bipartite boundary (no Cell connects directly to another Cell without an intermediary Net wire).
- $\Phi_{\mathcal{V}} = \{\text{'cell'}, \text{'net'}\}$ is the node type mapping.
- $\Phi_{\mathcal{E}}$ defines 6 directed edge types for forward physical flow and bidirectional GNN message passing:

| Canonical Triplet Relation | Direction | Source Type | Target Type | Physical Hardware Semantics |
| :--- | :---: | :---: | :---: | :--- |
| `('cell', 'outputs', 'net')` | Forward | Cell | Net | Standard cell logic gate driving an output wire/net. |
| `('net', 'data_input', 'cell')` | Forward | Net | Cell | Net carrying data operand signal into cell input pin. |
| `('net', 'control_input', 'cell')` | Forward | Net | Cell | Net driving clock/reset/enable control pins (`CLK`, `RST`, etc.). |
| `('net', 'rev_outputs', 'cell')` | Reverse | Net | Cell | Reverse message flow from driven net back to driver cell. |
| `('cell', 'rev_data_input', 'net')` | Reverse | Cell | Net | Reverse message flow from sink cell back to input data net. |
| `('cell', 'rev_control_input', 'net')` | Reverse | Cell | Net | Reverse message flow from sink cell back to control net. |

## 2. Control Signal Classification Rule

The classification of `control_input` vs `data_input` is enforced during Verilog netlist parsing in:
`packages/shared/xai_shared/circuitgraph/circuitgraph/parsing/verilog.py` (line 273, 286):

```python
CONTROL_PORTS = {'CLK', 'CK', 'RSTB', 'RN', 'SETB', 'SN', 'test_se'}
attributes['is_control'] = 1 if port_name in CONTROL_PORTS else 0
```

### Scientific Impact:
1. **Data Graph Isolation ($G_{\text{data}}$):** When calculating topological shortest path metrics (Dijkstra, Logic Depth, BFS) and in Config D ablation, edges with `is_control == 1` are removed. This prevents high-fanout global clock nets (`sys_clk`) from collapsing the shortest-path distance between un-related gates to 2 hops.
2. **Relation-Aware Convolutions:** In `HeteroTrojanGNN`, separate transformation weight matrices ($W_{\text{data}} \neq W_{\text{ctrl}} \neq W_{\text{out}}$) are applied per relation, preventing over-smoothing.

## 3. Node Attributes & Feature Dimensions

- **Cell Feature Vector $x_{\text{cell}} \in \mathbb{R}^{34}$:**
  - 20-dim one-hot gate family (`AND`, `NAND`, `OR`, `NOR`, `XOR`, `XNOR`, `INV`, `BUF`, `AOI`, `AO`, `OAI`, `OA`, `MUX`, `DFF`, `LSD`, `ISOL`, etc.)
  - 1-dim sequential flag (`is_sequential`)
  - 13-dim normalized topological metrics (`LGFi`, `ffi`, `ffo`, `PI`, `PO`, `in_degree`, `out_degree`, `pagerank`, `betweenness`, `closeness`, `clustering`, `core_number`, `logic_depth_ratio`)

- **Net Feature Vector $x_{\text{net}} \in \mathbb{R}^{20}$:**
  - 6-dim one-hot net type (`wire`, `input`, `output`, `inout`, `supply0`, `supply1`)
  - 1-dim Primary Output flag (`is_output`)
  - 13-dim topological metrics matching the cell schema.

## 4. Verification Samples

Audited 54 sampled edges from representative circuits (`RS232`, `s15850`, `s35932`). Detailed CSV log available at `outputs/audit/graph_edge_samples.csv`.
