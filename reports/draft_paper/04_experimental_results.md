# SECTION 4: EXPERIMENTAL EVALUATION

## 4.1. Experimental Setup & Benchmarks

### 4.1.1. Dataset & Benchmark Circuits
We conduct all experiments on the widely adopted Trust-Hub gate-level benchmark suite [CITATION: trust-hub]. The dataset comprises 30 synthesized gate-level netlists spanning five distinct architectural families:
1. `RS232` (Serial UART communication cores, 35 Flip-Flops, sequential bitstream receiver)
2. `s15850` (ISCAS-89 sequential benchmark core, 180nm standard cell technology)
3. `s35932` (Parallel 32-bit datapath processing core, 1,728 Flip-Flops)
4. `s38417` (Deep sequential finite state machine core)
5. `s38584` (Large-scale sequential processing unit, 1,452 Flip-Flops, >15,000 gates)

In total, the benchmark contains **47,464 standard logic cells**, of which only **370 cells belong to Hardware Trojans** (both Trigger and Payload gates). This corresponds to an extreme class imbalance ratio of **~0.78%** (ranging from 1:127 to 1:247 across individual circuits).

### 4.1.2. Evaluation Protocols: In-Distribution vs. Cross-Family LOFO
To rigorously investigate model generalizability, we establish two distinct evaluation protocols:
* **In-Distribution (ID) Random Partitioning:** Logic gates are randomly split into 60% training, 20% validation, and 20% testing sets across all 30 netlists simultaneously. Crucially, gates from the same circuit design appear in both training and test sets.
* **Leave-One-Family-Out (LOFO) Cross-Family Protocol:** In each LOFO fold, all circuits belonging to one entire architectural family (e.g., all `s35932` circuits) are held out exclusively as the unseen test set, while the model is trained strictly on the remaining four families. This protocol strictly enforces out-of-distribution (OOD) structural generalization.

### 4.1.3. Evaluation Metrics
Given the extreme class imbalance (~0.78% positive samples), accuracy is completely non-informative. We report:
1. **Macro-$F_1$:** Unweighted arithmetic mean of $F_1$-scores across the 5 LOFO folds (penalizes catastrophic failure on any single family).
2. **Micro-$F_1$:** Global $F_1$-score aggregated over all 47,464 test instances.
3. **Trojan Coverage (Recall):** Percentage of ground-truth Trojan cells successfully localized ($\text{TP} / (\text{TP} + \text{FN})$).
4. **False Positive Rate:** Number of false alarms per 1,000 benign logic gates ($\text{FP} / 1,000 \text{ gates}$).

---

## 4.2. Handcrafted Feature Baselines: From 5F to 13F

**[Question]**
We first investigate whether the five widely adopted logic distance features proposed by Hasegawa et al. [CITATION: hasegawa2016, whitten2026] are sufficient to support gate-level Hardware Trojan localization across unseen circuit families under strict LOFO evaluation.

**[Setup]**
We evaluate an XGBoost tabular classifier trained on the 5 Hasegawa features ($LGFi, ffi, ffo, PI, PO$). We compare standard random 60/20/20 in-distribution (ID) partitioning against the leave-one-family-out (LOFO) cross-family protocol across the 30 Trust-Hub circuits.

**[Observation]**
Under in-distribution splitting, the 5-feature baseline achieves a seemingly strong performance with an $F_1$-score of $0.6376 \pm 0.0492$ (and ROC-AUC of $0.9530$). However, under LOFO evaluation, the performance undergoes a catastrophic collapse: the Macro-$F_1$ plummets to **$0.0300$** and Micro-$F_1$ drops to **$0.0330$**, with a Trojan recall of merely **$5.59\%$** (missing 94.4% of Trojan gates across unseen families). On the `RS232` family, the ROC-AUC degrades below random guessing to **$0.3715$** [EVIDENCE].

**[Next Hypothesis]**
A natural hypothesis is that five topological distances are simply too coarse, and expanding the feature space with global graph centrality metrics might resolve the domain shift. We thus augment the representation from 5 to 13 features (13F) by incorporating eight graph-theoretic descriptors (degree, betweenness, closeness, PageRank, clustering coefficient, and $k$-core centralities) [CITATION].

**[Observation & Limitation]**
The extended 13F representation dramatically boosts in-distribution fitting, pushing the ID $F_1$-score to **$0.9243 \pm 0.0241$**. Nevertheless, under cross-family LOFO evaluation, performance remains severely suppressed, reaching only Macro-$F_1 = \mathbf{0.1637}$ and Micro-$F_1 = \mathbf{0.1140}$, while Trojan recall remains at approximately $12.0\%$.

**[Interpretation & Conclusion]**
* [EVIDENCE] Merely increasing the dimensionality of handcrafted scalar features cannot bridge the cross-family generalization gap.
* [REASONING] The failure under LOFO is governed by **Host Coordinate Memorization** and **Feature Inversion**: static tabular descriptors capture absolute geometric scales of the training circuits rather than invariant structural relational patterns.
* [LIMITATION] However, this experiment alone does not prove that a graph neural network is strictly necessary; it only establishes that scalar feature enrichment within a tabular paradigm is fundamentally insufficient.

---

## 4.3. Compressed Homogeneous Graph vs. Explicit Cell-Net Graph (Config A ➔ Config B)

**[Question]**
When transitioning from tabular vectors to graph representations, does preserving explicit net (wire) nodes improve Trojan localization over flattened gate-level graphs?

**[Setup]**
* **Config A (CircuitGraph Homogeneous GNN):** GraphSAGE 2-layer on a homogeneous gate graph where nets are compressed into direct gate-to-gate edges (resulting in 12 Trojan cells being dropped due to missing net-connectivity).
* **Config B (Explicit Cell-Net Homogeneous GNN):** GraphSAGE 2-layer on an explicit bipartite Cell–Net graph preserving 100% of cells (47,464) and nets (54,000+), but applying a single shared weight matrix $W$ across all edge types.

**[Observation]**
Config A achieves a LOFO Macro-$F_1$ of **$0.3518$**. Surprisingly, Config B experiences a severe performance degradation, dropping by $-38.9\%$ to a Macro-$F_1$ of **$0.2151$** [EVIDENCE].

**[Interpretation & Conclusion]**
* [REASONING] Explicitly introducing net nodes triples the total graph diameter and node count. When a homogeneous GNN aggregates over both cell and net nodes with a shared transformation matrix $W$, it conflates functional logic gates with passive routing wires, causing severe semantic dilution.
* [LIMITATION] Topology completeness alone is not sufficient; the model must explicitly discriminate between distinct physical semantic relations.

---

## 4.4. The Necessity of Relational Message Passing (Config B ➔ Config C)

**[Question]**
Does decoupling relation-specific transformations via Heterogeneous Graph Convolution (HeteroConv) recover representation fidelity on the bipartite Cell–Net graph?

**[Setup]**
* **Config C (`HeteroTrojanGNN` + Control-ON):** Retains the bipartite Cell–Net topology but applies heterogeneous message passing with distinct weight matrices $W_r$ for each of the 6 physical relation types (`cell-to-net`, `net-to-cell`, `driver`, `load`, etc.) with basic 5 features.

**[Observation]**
Heterogeneous relational learning triggers an immediate performance rebound: Macro-$F_1$ surges from **$0.2151$** (Config B) to **$0.3258$** (Config C), representing a **$+51.5\%$ relative recovery** [EVIDENCE].

**[Interpretation]**
[REASONING] HeteroConv successfully decouples semantic relations, allowing the model to learn distinct directional dependencies between logic cells and driving nets.

---

## 4.5. Which Relations Matter? Decoupling the Global Control Infrastructure (Config C/D & E/F)

**[Question]**
Do all physical circuit relations contribute positively to cross-family generalization, or do global control infrastructures (clock and reset distribution networks) impede transferability?

**[Setup]**
We systematically contrast **Control-ON** (retaining clock/reset edges in message passing) against **Control-OFF** (pruning clock and reset distribution trees during neighborhood aggregation):
* Config C (5F, Control-ON) vs. Config D (5F, Control-OFF)
* Config E (13F, Control-ON) vs. Config F (13F, Control-OFF)

**[Observation]**
* Under 5 features: Config D (`Control-OFF`) achieves Macro-$F_1 = \mathbf{0.4032}$, outperforming Config C ($0.3258$) by **$+23.8\%$** [EVIDENCE].
* Under 13 features: Config F (`Control-OFF`) attains the peak performance of Macro-$F_1 = \mathbf{0.5239}$ (and Micro-$F_1 = 0.5180$, Recall $= 61.22\%$), significantly superior to Config E (`Control-ON`, $0.4570$) [EVIDENCE].
* On `RS232`, Config F eliminates false alarms entirely ($\text{FP} = 0.00$) [EVIDENCE].

**[Interpretation]**
[REASONING] Global clock networks connect simultaneously to thousands of sequential storage elements, acting as high-degree artificial shortcut superhighways. During graph message passing, these shortcuts diffuse and oversmooth localized rare-trigger signals across the entire circuit.

---

## 4.6. Representation Geometry & Smoothness Analysis (Dirichlet Energy & Effective Rank)

**[Question]**
Can we geometrically explain why decoupling control relations prevents representation oversmoothing and preserves rare-trigger discrimination?

**[Setup]**
We compute relation-specific Dirichlet Energy $E_D(\mathbf{H}) = \text{Tr}(\mathbf{H}^T \mathbf{\tilde{L}}_r \mathbf{H})$ and Effective Rank across hidden representations under Control-ON and Control-OFF configurations.

**[Observation]**
* Under Control-ON: Dirichlet Energy along control edges collapses to near zero ($E_D \to 0$), indicating extreme node representation homogeneity across sequential elements.
* Under Control-OFF: Dirichlet Energy along datapath relations remains preserved at non-degenerate levels, and Effective Rank increases from $k_{eff} = 4.2$ to $k_{eff} = 11.8$ [EVIDENCE].

**[Conclusion]**
[REASONING] Relation-specific representation analysis provides evidence consistent with the hypothesis that Control-OFF preserves the spectral contrast of Trojan trigger motifs, preventing them from being swallowed by global clock tree oversmoothing.
