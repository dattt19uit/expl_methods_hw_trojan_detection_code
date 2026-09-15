# Experimental Protocol & Evaluation Guidelines

**Date:** 2026-09-15  
**Status:** Officially Audited and Frozen (Phase E Deliverable)  

---

## 1. Research Protocol Principles

All experiments in this research must adhere to two distinct evaluation protocols with strict isolation to prevent scientific misinterpretation.

---

## 2. Protocol 1: In-Distribution Evaluation (Node-Level Split)

### Setup:
- **Partition Ratio:** 60% Train, 20% Validation, 20% Test.
- **Stratification:** Stratified by cell label (`is_trojan`).
- **Repetitions:** 10 independent runs across pre-defined seeds:
  `[42, 101, 2024, 777, 888, 999, 1234, 5678, 9999, 31415]`.

### Scientific Meaning & Constraints:
- Cells from the **same circuit** may appear in both Train and Test partitions.
- **Constraint:** This experiment measures **in-distribution learning capacity** under severe class imbalance. It MUST NOT be used or reported as evidence of cross-family generalization or zero-day Trojan localization.

---

## 3. Protocol 2: Cross-Family Leave-One-Family-Out (LOFO) Evaluation

### Setup:
- Evaluates out-of-distribution transferability across 5 Trust-Hub circuit families:
  1. `RS232` (22 circuits: T1000 - T2000, 90nm and 180nm)
  2. `s15850` (1 circuit: s15850-T100)
  3. `s35932` (3 circuits: s35932-T100, T200, T300)
  4. `s38417` (2 circuits: s38417-T100, T200)
  5. `s38584` (2 circuits: s38584-T100, T300)
- In each fold $k$:
  - **TEST Set:** All circuits belonging to held-out family $F_k$.
  - **TRAIN / VAL Set:** All circuits belonging to the remaining 4 families (85% Train, 15% Validation).

### Strict Anti-Leakage Constraints:
1. **Zero Test Knowledge:** The held-out family $F_k$ is NEVER seen during training, feature normalization fitting (`StandardScaler`), hyperparameter tuning, or threshold selection.
2. **Threshold Tuning ($\tau^*$):** The optimal decision threshold $\tau^*$ is selected strictly via 100-step grid search optimizing $F_1$ on the validation partition of the training families. The selected $\tau^*$ is then applied blindly to the test family.
3. **Evaluation Metrics:**
   - **Primary Metric:** Macro-$F_1$ across the 5 held-out families:
     $$\text{Macro } F_1 = \frac{1}{5} \sum_{k=1}^{5} F_1(F_k)$$
   - **Secondary Metrics:** Per-family Precision, Recall, $F_1$, ROC-AUC, PR-AUC, and Micro-$F_1$.

---

## 4. Controlled Ablation Suite (Configs A–E)

To isolate the contribution of each architectural factor, the ablation suite evaluates:
- **Config A:** Compressed homogeneous graph + baseline GraphSAGE (Exp 5 baseline).
- **Config B:** Explicit Bipartite Cell--Net graph + homogeneous GraphSAGE (evaluates explicit Net wire nodes).
- **Config C:** Explicit Bipartite Cell--Net graph + HeteroConv SAGE + Control Edges (evaluates relation-aware message passing).
- **Config D:** Explicit Bipartite Cell--Net graph + HeteroConv SAGE - Control Edges (evaluates Clock Bottleneck hypothesis).
- **Config E:** Full HeteroTrojanGNN with all 13 topological Graph IR features (evaluates topological feature enrichment).

