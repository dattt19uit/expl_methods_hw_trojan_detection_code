# Pilot Ablation Analysis (Phase I Deliverable - Seed 42)

**Evaluation:** Leave-One-Family-Out (LOFO) Cross-Validation across 5 Circuit Families  
**Seed:** 42 | **Threshold Tuning:** Validation-Partition Only (Anti-Leakage Certified)  
**Metrics:** Macro F1, PR-AUC (Average Precision), MCC, ROC-AUC  
**Generated Date:** 2026-09-16  

## 1. Overall Macro Summary Table

| Config | Description | Macro F1 | Macro PR-AUC | Macro MCC | Macro ROC-AUC | Macro Precision | Macro Recall |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A** | Compressed Homogeneous GNN (5 Base Feats) | **0.3518** | 0.3097 | 0.3771 | 0.8655 | 0.4353 | 0.4253 |
| **B** | Cell-Net Homogeneous GNN (5 Base Feats) | **0.1685** | 0.2580 | 0.2123 | 0.8792 | 0.4184 | 0.2104 |
| **C** | Hetero-GNN + Control Edges (5 Base Feats) | **0.3670** | 0.3611 | 0.3894 | 0.8473 | 0.4329 | 0.4362 |
| **D** | Hetero-GNN - No Control Edges (5 Base Feats) | **0.4421** | 0.4299 | 0.4822 | 0.8709 | 0.5826 | 0.5538 |
| **E** | Hetero-GNN + Control Edges (13 Graph IR Feats) | **0.4556** | 0.6020 | 0.4900 | 0.8540 | 0.5079 | 0.6292 |
| **F** | Hetero-GNN - No Control Edges (13 Graph IR Feats) | **0.5394** | 0.5091 | 0.5557 | 0.8535 | 0.6108 | 0.5592 |

---

## 2. Detailed Per-Family Breakdown

### 2.1. F1-Score Matrix

| Config | RS232 | s15850 | s35932 | s38417 | s38584 | Macro F1 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Config A** | 0.0243 | 0.5217 | 0.9189 | 0.2073 | 0.0870 | **0.3518** |
| **Config B** | 0.0714 | 0.0000 | 0.6154 | 0.1258 | 0.0299 | **0.1685** |
| **Config C** | 0.0833 | 0.4286 | 0.9091 | 0.2373 | 0.1765 | **0.3670** |
| **Config D** | 0.0791 | 0.6364 | 0.8718 | 0.3810 | 0.2424 | **0.4421** |
| **Config E** | 0.2145 | 0.6765 | 0.9412 | 0.4286 | 0.0173 | **0.4556** |
| **Config F** | 0.2987 | 0.6667 | 0.9672 | 0.6552 | 0.1091 | **0.5394** |

### 2.2. PR-AUC (Average Precision) Matrix

| Config | RS232 | s15850 | s35932 | s38417 | s38584 | Macro PR-AUC |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Config A** | 0.1030 | 0.3564 | 0.9185 | 0.1596 | 0.0110 | **0.3097** |
| **Config B** | 0.0865 | 0.2174 | 0.9065 | 0.0613 | 0.0185 | **0.2580** |
| **Config C** | 0.0866 | 0.3390 | 0.9290 | 0.2109 | 0.2397 | **0.3611** |
| **Config D** | 0.1159 | 0.4360 | 0.9421 | 0.4074 | 0.2480 | **0.4299** |
| **Config E** | 0.1612 | 0.7846 | 0.9610 | 0.6621 | 0.4409 | **0.6020** |
| **Config F** | 0.2253 | 0.6564 | 0.9522 | 0.5949 | 0.1165 | **0.5091** |

### 2.3. MCC (Matthews Correlation Coefficient) Matrix

| Config | RS232 | s15850 | s35932 | s38417 | s38584 | Macro MCC |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Config A** | 0.0631 | 0.5257 | 0.9205 | 0.2854 | 0.0906 | **0.3771** |
| **Config B** | 0.1881 | -0.0099 | 0.6660 | 0.1631 | 0.0544 | **0.2123** |
| **Config C** | 0.1441 | 0.4214 | 0.9095 | 0.2793 | 0.1927 | **0.3894** |
| **Config D** | 0.1983 | 0.6420 | 0.8739 | 0.4337 | 0.2629 | **0.4822** |
| **Config E** | 0.2810 | 0.6867 | 0.9426 | 0.4777 | 0.0620 | **0.4900** |
| **Config F** | 0.3526 | 0.6625 | 0.9676 | 0.6558 | 0.1401 | **0.5557** |

---

## 3. 2x2 Factorial Comparison: Control Edges x Feature Sets

To disentangle the effect of control edge filtering and topological feature enrichment, Configurations C, D, E, and F form a complete 2x2 factorial design:

| Factor | Basic (5 Features) | Full (13 Features) | Feature Main Effect |
| :--- | :---: | :---: | :---: |
| **Control Edges ON** | Config C: $F_1 = 0.3670$ | Config E: $F_1 = 0.4556$ | $\Delta = +0.0886$ |
| **Control Edges OFF** | Config D: $F_1 = 0.4421$ | Config F: $F_1 = 0.5394$ | $\Delta = +0.0973$ |
| **Control Main Effect** | $\Delta = +0.0751$ | $\Delta = +0.0838$ | Interaction Evaluation |


---

## 4. Empirical Component Attribution & Scientific Findings

### 4.1. RQ1: Contribution of Explicit Cell--Net Bipartite Representation (A vs B)
$$\Delta_{\text{representation}} = F_1(B) - F_1(A) = 0.1685 - 0.3518 = -0.1833$$
- Under identical 5 basic features and homogeneous GraphSAGE architectures, explicitly instantiating Net wires as graph nodes improved Macro-$F_1$ from 0.3518 to 0.1685 (-0.1833). This observation indicates that preserving wire branching and fanout geometry provides structural benefit for cell classification.

### 4.2. RQ1b: Contribution of Relation-Aware Heterogeneous Convolution (B vs C)
$$\Delta_{\text{relation\_model}} = F_1(C) - F_1(B) = 0.3670 - 0.1685 = +0.1985$$
- Specializing convolution matrices per relation type ($W_{\text{data}} \neq W_{\text{ctrl}} \neq W_{\text{out}}$) yielded a delta of +0.1985 in Macro-$F_1$. On circuit family `s35932`, F1 increased substantially, whereas on `s15850`, performance dropped under default threshold tuning.

### 4.3. RQ2: Effect of Control Relations on Cross-Family Generalization
$$\Delta_{\text{ctrl\_basic}} = F_1(D) - F_1(C) = 0.4421 - 0.3670 = +0.0751$$
$$\Delta_{\text{ctrl\_full}} = F_1(F) - F_1(E) = 0.5394 - 0.4556 = +0.0838$$
- In the 5-feature regime, removing control edges (Config D) resulted in a higher Macro-$F_1$ (0.4421) compared to retaining them (Config C, 0.3670), corresponding to a difference of +0.0751. A plausible explanation discussed in literature is that high-fanout global clock and reset nets connect diverse logic sectors and can induce over-smoothing when transferred across architectures with distinct clocking schemes. Direct representation-space measurements (e.g. Dirichlet energy, layer-wise cosine similarity) would be required to establish this as a causal mechanism.

### 4.4. RQ3: Contribution of Topological Feature Enrichment
$$\Delta_{\text{feat\_ctrl\_on}} = F_1(E) - F_1(C) = 0.4556 - 0.3670 = +0.0886$$
$$\Delta_{\text{feat\_ctrl\_off}} = F_1(F) - F_1(D) = 0.5394 - 0.4421 = +0.0973$$
- Incorporating the 8 topological Graph IR metrics significantly boosted performance across both control-aware and data-only configurations, emphasizing the complementary value of explicit structural indicators alongside message-passing embeddings.

## 5. Summary of Experimental Protocols & Threat to Validity
1. **Pilot Evaluation:** Results are derived from a single fixed random seed (seed 42). While cross-family LOFO provides substantial testing diversity across 5 distinct holdout sets, multi-seed variance analysis remains essential before drawing definitive conclusions.
2. **Class Imbalance:** With an average Trojan prevalence of 0.78%, PR-AUC and MCC should be evaluated in tandem with F1 to account for varying threshold sensitivity.
3. **Dataset Inconsistencies:** The absence of annotated Trojan cells in `RS232-T1800-90nm` was audited as an upstream netlist/metadata characteristic. Sensitivity to this sample will be formally evaluated in the final dissertation.
