# Model Implementation Audit: HeteroTrojanGNN vs Theoretical Formulation

**Date:** 2026-09-15  
**Status:** Officially Audited and Frozen (Phase D Deliverable)  
**Implementation Source:** `packages/shared/xai_shared/graph_data/hetero_gnn.py`

---

## 1. Environment & Framework Stack
- **PyTorch Version:** 2.6.0+cpu
- **PyTorch Geometric (PyG) Version:** 2.6.1
- **Device Support:** Auto-detected CUDA GPU or optimized multi-threaded CPU (`torch.set_num_threads`)

---

## 2. Mathematical Mapping vs Source Code Verification

### 2.1. Initial Feature Projections
In the thesis formulation:
$$h_{\text{cell}}^{(0)} = \text{ReLU}\left(W_{\text{proj, cell}} \cdot x_{\text{cell}} + b_{\text{proj, cell}}\right) \in \mathbb{R}^{64}$$
$$h_{\text{net}}^{(0)} = \text{ReLU}\left(W_{\text{proj, net}} \cdot x_{\text{net}} + b_{\text{proj, net}}\right) \in \mathbb{R}^{64}$$

**Source Code Match (`hetero_gnn.py:53-56`):**
```python
self.cell_proj = nn.Sequential(nn.Linear(cell_in_dim, hidden_dim), nn.ReLU())
self.net_proj = nn.Sequential(nn.Linear(net_in_dim, hidden_dim), nn.ReLU())
```
- `cell_in_dim = 34`, `net_in_dim = 20`, `hidden_dim = 64`. Exactly matches.

---

### 2.2. Heterogeneous Message Passing (Layer $l \in \{1, 2\}$)
For node $v \in \mathcal{V}_{\text{cell}}$ and edge relation $r = (s, \text{rel}, \text{cell}) \in \Phi_{\mathcal{E}}$:
$$m_{v, r}^{(l)} = \text{SAGEConv}_{r}\left(\{h_u^{(l-1)} \mid u \in \mathcal{N}_r(v)\}, h_v^{(l-1)}\right)$$
$$h_v^{(l)} = \text{LayerNorm}\left(h_v^{(l-1)} + \text{Dropout}\left(\text{ReLU}\left(\sum_{r} m_{v, r}^{(l)}\right), p=0.2\right)\right)$$

**Source Code Match (`hetero_gnn.py:60-84`):**
```python
# SAGEConv per relation with sum aggregation across relations
conv_dict = {
    rel: SAGEConv(in_dim, hidden_dim, aggr='mean')
    for rel in relations
}
self.convs.append(HeteroConv(conv_dict, aggr='sum'))
self.norms_cell.append(nn.LayerNorm(hidden_dim))
self.norms_net.append(nn.LayerNorm(hidden_dim))
```
- Intra-relation aggregation: `aggr='mean'` (GraphSAGE mean aggregator).
- Inter-relation aggregation: `aggr='sum'` (Summing contributions across relations).
- Residual Connections: `h_cell = h_cell + F.dropout(F.relu(h_new['cell']), p=self.dropout, training=self.training)`
- Normalization: `LayerNorm(hidden_dim=64)` applied post-residual.
- Exactly matches.

---

### 2.3. Classification Head (MLP Head)
Final embedding $h_v^{(2)}$ of cell $v$ is passed through a 2-layer MLP to produce logit $z_v$:
$$z_v = W_2 \cdot \text{ReLU}\left(W_1 \cdot h_v^{(2)} + b_1\right) + b_2$$
$$\hat{p}_v = \sigma(z_v) = \frac{1}{1 + e^{-z_v}}$$

**Source Code Match (`hetero_gnn.py:92-96`):**
```python
self.classifier = nn.Sequential(
    nn.Linear(hidden_dim, hidden_dim // 2), # 64 -> 32
    nn.ReLU(),
    nn.Dropout(dropout),                   # p = 0.2
    nn.Linear(hidden_dim // 2, 1)          # 32 -> 1
)
```
- Output logit is strictly 1-dimensional scalar per cell node.
- Loss function: `nn.BCEWithLogitsLoss(pos_weight=w_pos)` where $w_{\text{pos}} = \frac{N_{\text{clean}}}{N_{\text{trojan}}}$.

---

## 3. Audit Conclusion
The PyG implementation in `hetero_gnn.py` is fully faithful to the mathematical formulation presented in the thesis. No hidden approximations or non-standard operations are present.

