# Research Execution Plan --- Semantic Graph IR for Hardware Trojan Detection

> **Purpose:** This document is intended to be given to Google
> Antigravity (or another coding/research agent) together with the
> current research repository.\
> The agent should use this document as an execution plan to **inspect,
> verify, improve, and automate the existing experimental pipeline**.
>
> **Important:** Do not blindly rewrite the project. Inspect the
> existing implementation first, preserve working behavior, and make
> small, reviewable changes.

------------------------------------------------------------------------

## 1. Research Context

The research topic is currently:

**Graph-based Representation and Learning for Hardware Trojan Detection
and Structural Localization in Netlists**

The project studies Hardware Trojan (HT) detection on gate-level
netlists, primarily using the Trust-Hub benchmark.

The current research direction is based on:

1.  A tabular baseline using XGBoost and five Hasegawa structural
    features.
2.  A richer graph-based intermediate representation (Semantic Graph
    IR).
3.  A heterogeneous Cell--Net graph representation.
4.  A heterogeneous GNN for cell-level Trojan classification.
5.  Leave-One-Family-Out (LOFO) evaluation for cross-family
    generalization.
6.  Graph explainability/localization as a secondary research direction.

The main goal now is **not to add more model complexity**.

The immediate goal is to make the experimental evidence scientifically
reliable enough for a Master's thesis and a possible international
research paper.

------------------------------------------------------------------------

# 2. Current Research Question

The current working hypothesis is:

> A typed heterogeneous Cell--Net representation combined with
> relation-aware graph learning may improve Hardware Trojan detection
> generalization to circuit families unseen during training.

This is a hypothesis, **not yet a proven claim**.

The experiments must determine whether the hypothesis is supported.

## RQ1 --- Representation

Does an explicit Cell--Net representation improve Hardware Trojan
detection compared with a compressed graph representation when other
experimental factors are controlled as much as possible?

## RQ2 --- Cross-Family Generalization

How does the proposed Semantic Graph + heterogeneous GNN perform on
unseen circuit families under Leave-One-Family-Out evaluation compared
with tabular XGBoost and graph baselines?

## RQ3 --- Component Contribution

Which components contribute to performance?

Specifically:

-   explicit Net nodes;
-   heterogeneous/relation-aware message passing;
-   control relations;
-   topology features.

## Secondary Question --- Explainability

Can graph explanations provide useful structural localization/evidence
for Trojan predictions?

**This is currently secondary. Do not prioritize XAI over the core
detection/generalization experiments.**

------------------------------------------------------------------------

# 3. Existing Preliminary Results

Current preliminary experiments suggest:

  Experiment   Description                                        Random Split F1
  ------------ ------------------------------------------------ -----------------
  Exp1         XGBoost + 5 Hasegawa                                       \~0.657
  Exp2         XGBoost + 13 handcrafted features                          \~0.924
  Exp3         Graph IR XGBoost + 5 features                              \~0.744
  Exp4         Graph IR XGBoost + 13 features                             \~0.873
  Exp5         Homogeneous GNN on compressed representation               \~0.655
  Exp6         Proposed heterogeneous GNN + Semantic Graph IR             \~0.806

Preliminary single-seed LOFO macro-F1:

  Experiment     Macro F1
  ------------ ----------
  Exp1           \~0.0297
  Exp2           \~0.1637
  Exp3           \~0.1346
  Exp4           \~0.1369
  Exp5           \~0.1487
  Exp6           \~0.3950

These results are **preliminary**.

Do not encode statements such as "Semantic Graph definitely improves
generalization" into documentation or code comments.

The purpose of the next experiments is to determine **why** Exp6
performs better and whether the result is stable.

------------------------------------------------------------------------

# 4. General Instructions for the Coding Agent

Before changing anything:

1.  Inspect the repository structure.
2.  Identify:
    -   Verilog/netlist parsing pipeline;
    -   graph construction;
    -   feature extraction;
    -   dataset splitting;
    -   model definitions;
    -   training loop;
    -   threshold selection;
    -   evaluation code;
    -   LOFO implementation;
    -   result storage;
    -   XAI code.
3.  Produce a short audit describing how the existing implementation
    works.
4.  Identify discrepancies between the implementation and this research
    plan.
5.  Do **not** silently fix scientifically meaningful behavior.
6.  For meaningful changes, explain:
    -   current behavior;
    -   problem/risk;
    -   proposed modification;
    -   expected effect.
7.  Prefer configuration-driven experiments over duplicated scripts.
8.  Preserve reproducibility.
9.  Never optimize hyperparameters using the held-out LOFO test family.
10. Never use test labels for threshold selection.

------------------------------------------------------------------------

# 5. Phase A --- Dataset Audit

## Objective

Verify exactly what data is being used before running additional
experiments.

## Tasks

Inspect the Trust-Hub dataset processing pipeline and generate a dataset
summary containing:

-   family name;
-   circuit name;
-   number of cell nodes;
-   number of net nodes;
-   number of edges;
-   number of Trojan cells;
-   number of clean cells;
-   Trojan prevalence;
-   parser success/failure;
-   missing labels, if any.

Expected output:

``` text
outputs/audit/dataset_summary.csv
```

Suggested columns:

``` text
family
circuit
num_cells
num_nets
num_edges
num_trojan
num_clean
trojan_ratio
parse_status
label_status
```

## Checks

Verify:

-   no unintended duplicated circuits;
-   all expected circuits are present;
-   no circuit silently failed parsing;
-   labels align with graph nodes;
-   family assignments are correct;
-   reported total counts match the actual generated dataset.

## Deliverable

Create:

``` text
docs/dataset_audit.md
```

Document discovered issues instead of hiding them.

------------------------------------------------------------------------

# 6. Phase B --- Semantic Graph IR Verification

## Objective

Verify that the generated graph actually corresponds to the source
gate-level netlist.

The graph is expected to be a directed heterogeneous bipartite graph:

``` text
Cell -> Net : outputs
Net  -> Cell: data_input
Net  -> Cell: control_input
```

Reverse relations may also exist for message passing.

## Tasks

Select at least three representative circuits.

For each circuit:

1.  Sample Cell nodes.
2.  Sample Net nodes.
3.  Sample connections.
4.  Trace them back to the original netlist.
5.  Verify node type and relation type.
6.  Verify reverse-edge construction.

Generate a machine-readable verification report where possible.

Example:

``` text
outputs/audit/graph_edge_samples.csv
```

Suggested columns:

``` text
family
circuit
source
source_type
target
target_type
relation
source_netlist_reference
verification_status
notes
```

## Critical Check --- Control Signals

Inspect exactly how the implementation determines:

``` text
data_input
vs
control_input
```

Document the rule.

If it is based on:

-   pin names;
-   signal names;
-   regex;
-   gate type;
-   hard-coded lists;

state that explicitly.

Do not assume names such as `CLK`, `RST`, `RESET`, `SET`, etc. are
universally reliable.

## Deliverable

Create:

``` text
docs/semantic_graph_ir_spec.md
```

It should define:

-   node types;
-   edge types;
-   reverse relations;
-   control/data classification;
-   treatment of constants;
-   primary inputs/outputs;
-   sequential cells;
-   assumptions and limitations.

------------------------------------------------------------------------

# 7. Phase C --- Feature Audit

## Objective

Document every feature used by the models and detect possible leakage.

Current expected dimensions are approximately:

``` text
Cell features: 34D
Net features : 20D
```

Do not assume these dimensions are correct. Verify them from the source.

## Tasks

Generate a feature specification.

For every feature record:

``` text
name
node_type
dimension
definition
implementation_location
requires_graph_topology
requires_training_statistics
uses_label
normalization
```

At minimum inspect:

### Cell features

-   gate-family encoding;
-   sequential flag;
-   LGFi;
-   FFi;
-   FFo;
-   PI distance;
-   PO distance;
-   topology features.

### Net features

-   net-type encoding;
-   primary-output flag;
-   topology features.

## Leakage Checks

Verify that:

-   no feature directly uses Trojan labels;
-   feature selection does not use test labels;
-   normalization fitted from data uses training data only;
-   LOFO held-out family does not contribute learned preprocessing
    statistics;
-   validation is used for threshold/hyperparameter selection;
-   test data is evaluation-only.

## Deliverable

Create:

``` text
docs/feature_spec.md
```

and, if useful:

``` text
outputs/audit/feature_schema.csv
```

------------------------------------------------------------------------

# 8. Phase D --- Verify GNN Implementation

## Objective

Make sure the mathematical description used in the thesis can accurately
describe the actual source code.

## Inspect

-   PyTorch version;
-   PyTorch Geometric version;
-   `HeteroConv`;
-   `SAGEConv`;
-   `root_weight`;
-   aggregation inside each relation;
-   aggregation across relations;
-   reverse relations;
-   residual connections;
-   LayerNorm;
-   dropout;
-   hidden dimension;
-   number of message-passing layers;
-   classifier architecture.

## Important

Do not claim the thesis equation is an "exact implementation" unless it
really matches the source.

If the source contains implementation-specific behavior that would make
the equation cumbersome, recommend describing the equation as a
**simplified formulation**.

## Deliverable

Create:

``` text
docs/model_implementation_audit.md
```

------------------------------------------------------------------------

# 9. Phase E --- Freeze Evaluation Protocol

Create one central experimental protocol rather than allowing individual
scripts to define their own evaluation logic.

## In-Distribution Protocol

Current intended protocol:

``` text
60% train
20% validation
20% test
stratified node-level split
```

This must explicitly be described as:

**in-distribution node-level evaluation**

Nodes belonging to the same circuit may occur across
train/validation/test.

Therefore this experiment must **not** be used as evidence of
independent circuit-family generalization.

## LOFO Protocol

For each family `F`:

``` text
TEST = all circuits belonging to F

TRAIN + VALIDATION =
all permitted circuits belonging to the remaining families
```

The held-out family must not influence:

-   training;
-   validation;
-   threshold selection;
-   hyperparameter selection;
-   learned normalization;
-   feature selection.

## Threshold

Threshold must be selected using validation data only.

Record the selected threshold for every run.

## Metrics

Primary:

``` text
macro F1 across held-out families
```

Secondary:

``` text
precision
recall
F1
PR-AUC / Average Precision
MCC
ROC-AUC
micro F1
```

Always record class support.

## Deliverable

Create:

``` text
docs/experimental_protocol.md
```

------------------------------------------------------------------------

# 10. Phase F --- Refactor Experiment Runner

## Objective

Experiments should be reproducible from configuration rather than
source-code edits.

Desired conceptual configuration:

``` yaml
experiment: C
representation: semantic_cell_net
model: hetero_sage
feature_set: basic
control_edges: true
seed: 42
held_out_family: RS232
```

The exact format can follow the existing project's architecture.

## Required Parameters

At minimum experiments should be selectable by:

``` text
representation
model
feature_set
control_edges
seed
held_out_family
```

## Result Schema

Every run should save:

``` text
experiment_id
timestamp
git_commit_if_available

representation
model
feature_set
control_edges

seed
held_out_family

num_train
num_validation
num_test

num_test_positive
num_test_negative

threshold

TP
FP
TN
FN

precision
recall
f1
pr_auc
roc_auc
mcc

training_time
inference_time
```

Where practical, also save raw predictions:

``` text
circuit
node_id
ground_truth
probability
prediction
```

Suggested structure:

``` text
results/
  <experiment>/
    seed_<seed>/
      <held_out_family>/
        metrics.json
        predictions.csv
        run_config.yaml
```

------------------------------------------------------------------------

# 11. Phase G --- Controlled Ablation Experiments

This is the **highest-priority experimental task**.

The goal is to isolate components rather than simply compare the old
Exp5 and Exp6.

## Configuration A --- Compressed Representation

``` text
Representation: compressed
Model: homogeneous GraphSAGE
Features: common/basic
Control handling: baseline-compatible
```

## Configuration B --- Explicit Cell--Net Representation

``` text
Representation: Semantic Cell-Net
Model: homogeneous GraphSAGE
Features: same/common basic information as A where scientifically possible
```

### Comparison

``` text
A vs B
```

Research purpose:

> Estimate the contribution of explicit Cell--Net representation.

**Important:** Inspect whether A and B can genuinely be made comparable.
If the representations make identical features impossible, document the
confound instead of pretending it is a perfectly controlled comparison.

------------------------------------------------------------------------

## Configuration C --- Relation-Aware Heterogeneous GNN

``` text
Representation: Semantic Cell-Net
Model: heterogeneous/relation-aware GraphSAGE
Features: same basic feature setting as B
Control edges: enabled
```

### Comparison

``` text
B vs C
```

Research purpose:

> Estimate the contribution of heterogeneous/relation-aware message
> passing.

------------------------------------------------------------------------

## Configuration D --- Remove Control Relations

Same as C except:

``` text
control_edges: false
```

### Comparison

``` text
C vs D
```

Research purpose:

> Determine empirically whether control relations help or hurt
> cross-family detection.

Do not encode the assumption that control edges necessarily cause
over-smoothing or contamination.

------------------------------------------------------------------------

## Configuration E --- Full Features

Same architecture/representation as C, but use the full proposed
topology feature set.

### Comparison

``` text
C vs E
```

Research purpose:

> Estimate how much final performance comes from richer features.

------------------------------------------------------------------------

# 12. Phase H --- Pilot Ablation First

Do **not** immediately run every configuration across many seeds.

First use:

``` text
seed = 42
```

Run:

``` text
A
B
C
D
E
```

across all five LOFO families.

Expected total:

``` text
5 configurations × 5 held-out families = 25 runs
```

Generate:

``` text
outputs/results/ablation_seed42.csv
```

Required summary:

  Config     RS232   s15850   s35932   s38417   s38584   Macro F1
  -------- ------- -------- -------- -------- -------- ----------
  A                                                    
  B                                                    
  C                                                    
  D                                                    
  E                                                    

## STOP CONDITION

After the 25 pilot runs:

**Do not automatically launch multi-seed experiments.**

First produce an analysis report.

------------------------------------------------------------------------

# 13. Phase I --- Analyze Pilot Ablation

Create:

``` text
docs/ablation_pilot_analysis.md
```

Answer:

## A vs B

``` text
delta_representation = F1_B - F1_A
```

Does explicit Cell--Net representation appear useful?

Check:

-   macro delta;
-   per-family delta;
-   precision/recall behavior;
-   whether one family dominates the result.

## B vs C

``` text
delta_relation_model = F1_C - F1_B
```

Does relation-aware heterogeneous message passing appear useful?

## C vs D

``` text
delta_control = F1_C - F1_D
```

Do control relations help or hurt?

Do not over-interpret.

## C vs E

``` text
delta_features = F1_E - F1_C
```

How much performance comes from feature engineering?

## Decision

At the end, recommend which configurations deserve expensive multi-seed
evaluation.

------------------------------------------------------------------------

# 14. Phase J --- Multi-Seed LOFO

Only after the pilot is verified.

Initial seed set:

``` text
42
123
456
789
2026
```

For each selected configuration:

``` text
5 seeds × 5 held-out families
```

Do not rerun unnecessary configurations if pilot results show they do
not answer an important research question.

## Required Outputs

Generate:

``` text
outputs/results/lofo_multiseed.csv
outputs/results/lofo_per_family.csv
outputs/results/paired_deltas.csv
```

Report:

``` text
mean
standard deviation
median
confidence interval where appropriate
```

for the important metrics.

------------------------------------------------------------------------

# 15. Phase K --- Statistical Analysis

For key paired comparisons:

``` text
A vs B
B vs C
C vs D
C vs E
```

compute:

``` text
absolute F1 delta
per-family delta
per-seed delta
win/loss counts
confidence intervals
```

A paired Wilcoxon signed-rank test may be considered where appropriate.

However:

> Do not blindly treat all seed × fold measurements as fully independent
> observations.

The report should emphasize:

-   effect size;
-   consistency across families;
-   uncertainty;
-   practical significance;

rather than relying only on `p < 0.05`.

------------------------------------------------------------------------

# 16. Phase L --- Error Analysis

## Objective

Understand why performance differs substantially across circuit
families.

For each family inspect:

``` text
Trojan prevalence
number of circuits
graph size
cell-type distribution
degree distribution
control-edge distribution
Trojan topology where ground truth permits
false positives
false negatives
prediction confidence
```

Select:

1.  best-performing family;
2.  worst-performing family.

Compare them.

Do not invent a causal explanation.

If the data only supports correlation, state that.

## Deliverable

Create:

``` text
docs/error_analysis.md
```

------------------------------------------------------------------------

# 17. Phase M --- Related Work Support

This is partly a literature/research task rather than a coding task.

If external literature access is available, build a related-work matrix.

Focus on:

1.  ML-based Hardware Trojan detection;
2.  graph/GNN-based Hardware Trojan detection;
3.  netlist/Verilog graph representations for security;
4.  cross-design/cross-family/OOD evaluation;
5.  graph explainability for hardware/security where relevant.

Suggested schema:

``` text
paper
year
dataset
representation
cell_nodes
net_nodes
heterogeneous
relation_types
model
task_level
split_protocol
cross_family_or_ood
xai
main_contribution
limitations
difference_from_current_work
```

The purpose is to identify the **3--5 papers closest to this work**.

Do not generate novelty claims such as:

> "No previous work has..."

unless the literature evidence actually supports them.

------------------------------------------------------------------------

# 18. Phase N --- Hardware Knowledge Support

Because the researcher comes primarily from Computer Science/ML rather
than hardware design, create documentation that connects hardware
concepts directly to this implementation.

Create:

``` text
docs/hardware_knowledge_for_thesis.md
```

Cover, at minimum:

``` text
RTL vs gate-level netlist
module
port
pin
cell / gate
net / wire
combinational logic
sequential logic
flip-flop
primary input/output
fan-in
fan-out
clock
reset
control signal
data signal
synthesis
Hardware Trojan
trigger
payload
Trust-Hub labels
```

For every concept, explain:

1.  concise definition;
2.  small example;
3.  where it appears in this repository;
4.  how it maps to Semantic Graph IR;
5.  why it matters for the research.

The goal is not to teach all of digital design.

The goal is to make the researcher capable of defending every
hardware-related design decision in the thesis.

------------------------------------------------------------------------

# 19. XAI --- HOLD Until Core Detection Is Stable

Do not prioritize new XAI experiments yet.

There are methodological questions that must be resolved first.

## Critical Issue --- Localization Ground Truth

The proposed graph is bipartite:

``` text
Cell <-> Net <-> Cell
```

Therefore an edge directly connecting:

``` text
TrojanCell -> TrojanCell
```

does not normally exist in the graph.

The localization evaluation must define ground truth in the same graph
space.

Possible choices to investigate:

1.  Trojan-cell localization;
2.  Cell--Net edges incident to Trojan cells;
3.  canonicalized structural motifs involving Trojan cells and
    connecting nets;
4.  explicitly annotated Trojan nets, if reliable metadata exists.

Do not choose silently.

Document the scientific meaning of the selected definition.

## Recall

If reporting standard recall:

``` text
recall = hits / |ground_truth|
```

Do not use:

``` text
hits / min(|ground_truth|, k)
```

and call it standard recall.

If another top-k metric is desired, give it a distinct name and
definition.

## XGBoost Gradient Attribution

Inspect the current implementation.

Because tree ensembles are piecewise-constant models, a method called
"Gradient Attribution" requires careful justification.

If the implementation is actually finite-difference
perturbation/sensitivity, rename it accordingly.

## XAI Deliverable

Only after the core experiments are stable, propose a scientifically
defensible XAI evaluation plan.

------------------------------------------------------------------------

# 20. Paper-Oriented Outputs

The project should eventually be able to produce the following artifacts
automatically:

``` text
paper_artifacts/
├── dataset_statistics.csv
├── in_distribution_results.csv
├── lofo_results.csv
├── ablation_results.csv
├── per_family_results.csv
├── statistical_comparisons.csv
├── error_analysis.csv
└── figures/
```

Suggested paper structure:

``` text
1. Introduction
2. Related Work
3. Problem Formulation
4. Proposed Typed Cell-Net Representation
5. Heterogeneous GNN
6. Experimental Setup
7. Results
   7.1 In-distribution
   7.2 Cross-family LOFO
   7.3 Controlled Ablation
   7.4 Per-family/Error Analysis
8. Discussion
9. Explainability (optional/secondary)
10. Threats to Validity
11. Conclusion
```

------------------------------------------------------------------------

# 21. What NOT to Do

Unless evidence later justifies it, do not:

-   add GAT/Transformer/new architectures simply to increase model
    count;
-   perform extensive hyperparameter searching on the LOFO test family;
-   tune thresholds on test data;
-   claim random 60/20/20 node split demonstrates cross-family
    generalization;
-   claim Semantic Graph is responsible for Exp6 improvement before
    controlled ablation;
-   claim control edges cause over-smoothing without measuring it;
-   claim relation typing eliminates control-edge contamination;
-   claim Graph XAI is superior to SHAP/LIME from incomparable models;
-   claim graph localization works before defining correct graph-space
    ground truth;
-   claim novelty before checking related work;
-   optimize only for the highest possible F1;
-   rewrite the working repository unnecessarily.

------------------------------------------------------------------------

# 22. Priority Order

Use this order unless repository inspection reveals a blocking issue:

``` text
P0  Inspect repository
 |
P1  Dataset audit
 |
P2  Semantic Graph IR verification
 |
P3  Feature + leakage audit
 |
P4  GNN implementation audit
 |
P5  Freeze evaluation protocol
 |
P6  Build/refactor experiment runner
 |
P7  A–E ablation, seed 42
 |
P8  Analyze pilot ablation
 |
P9  Multi-seed LOFO
 |
P10 Statistical + error analysis
 |
P11 Finalize research claims
 |
P12 XAI, only if core research is stable
```

Related-work review and hardware-domain documentation can proceed in
parallel with P6--P10.

------------------------------------------------------------------------

# 23. Definition of Done for the Core Research

The core research can be considered mature enough for paper/thesis
writing when the following are satisfied:

-   [ ] Dataset statistics verified.
-   [ ] Family/circuit mapping verified.
-   [ ] Graph construction manually validated.
-   [ ] Control/data edge rules documented.
-   [ ] Feature schema documented.
-   [ ] No obvious label/test leakage.
-   [ ] Model implementation matches documented architecture.
-   [ ] In-distribution protocol documented.
-   [ ] LOFO protocol documented.
-   [ ] Validation-only threshold selection verified.
-   [ ] Controlled A--E ablation completed.
-   [ ] Important ablations repeated across multiple seeds.
-   [ ] Multi-seed LOFO completed.
-   [ ] Per-family metrics reported.
-   [ ] F1 + Precision + Recall + PR-AUC + MCC reported.
-   [ ] Mean/uncertainty reported.
-   [ ] Important paired deltas analyzed.
-   [ ] Error analysis completed.
-   [ ] Closest related works identified.
-   [ ] Research gap revised based on literature.
-   [ ] Main claim matches experimental evidence.
-   [ ] Limitations explicitly documented.
-   [ ] Hardware concepts used in the thesis can be explained and
    defended.

XAI is **not required** for this checklist.

------------------------------------------------------------------------

# 24. First Task for Google Antigravity

Do **not** begin by modifying the models.

Start with:

> **Repository Audit**

Please inspect the entire repository and return:

1.  repository structure relevant to the research pipeline;
2.  end-to-end data flow from netlist to prediction;
3.  where graph construction is implemented;
4.  where Cell/Net types and edge relations are defined;
5.  where features are computed;
6.  where train/validation/test splits are created;
7.  where LOFO is implemented;
8.  where thresholds are selected;
9.  where models are defined;
10. where metrics/results are saved;
11. potential leakage or reproducibility risks;
12. differences between the current implementation and this plan;
13. a proposed minimal sequence of code changes.

**Do not implement major changes until this audit is complete.**

After the audit, proceed in priority order starting from dataset/graph
verification.

------------------------------------------------------------------------

# 25. Desired Working Style

For each task:

``` text
1. Inspect
2. Explain current behavior
3. Identify risk/problem
4. Propose minimal change
5. Implement
6. Add/check tests where feasible
7. Run verification
8. Save output
9. Summarize what changed
10. State what remains uncertain
```

Scientific correctness is more important than producing a better-looking
metric.

A negative ablation result is valid.

If an experiment contradicts the current hypothesis, report it rather
than changing the protocol to recover the expected result.
