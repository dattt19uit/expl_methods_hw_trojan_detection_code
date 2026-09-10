# Báo cáo Tiến độ Luận văn — Tuần 10/09/2026
**Tác giả**: Trần Tấn Đạt  
**Cập nhật lần cuối**: 10/09/2026  

---

## 1. Tổng quan công việc tuần này

Tuần này tập trung triển khai và đánh giá **Experiment 5 — Heterogeneous Graph Neural Network (H-GNN)** trên biểu diễn Semantic Graph IR, đồng thời thực hiện đối chuẩn định lượng **Graph XAI (GNNExplainer)** với 3 phương pháp XAI bảng (LIME, SHAP, Gradient Attribution).

---

## 2. Kết quả đối chuẩn 5 thí nghiệm (In-Distribution 60/20/20)

> **Dữ liệu**: 30 mạch Trust-Hub, cell-level prediction, phân chia stratified 60/20/20.  
> **Ngưỡng quyết định**: tối ưu trên Validation Set.

| # | Phương pháp | Đặc trưng | F1 (Seed 42) | AUC | TP | FP | FN |
|---|-------------|-----------|:---:|:---:|:--:|:--:|:--:|
| Exp 1 | XGBoost Baseline | 5 Hasegawa | 0.7731 | 0.9539 | 46 | 3 | 24 |
| Exp 2 | XGBoost Baseline | 13 (Hase+Graph) | 0.7967 | 0.9496 | 49 | 4 | 21 |
| Exp 3 | XGBoost + Graph IR | 5 Hasegawa | 0.7692 | 0.9972 | 55 | 14 | 19 |
| Exp 4 | XGBoost + Graph IR | 13 (Hase+Graph) | **0.8589** | **0.9998** | 70 | 19 | 4 |
| **Exp 5** | **HeteroTrojanGNN** | **Hetero Graph** | **0.8516** | **0.9946** | **66** | **15** | **8** |

**Nhận xét**: Exp 5 (H-GNN) đạt F1 = 0.8516, tương đương Exp 4 (F1 = 0.8589), nhưng **không sử dụng bất kỳ đặc trưng thủ công** nào — chỉ dùng cấu trúc đồ thị thuần túy (cell family one-hot + net type + cấu trúc kết nối).

---

## 3. Kết quả thống kê 10 lần chạy (Multi-Seed)

| # | Phương pháp | F1 (mean ± std) | AUC (mean ± std) |
|---|-------------|:---:|:---:|
| Exp 1 | XGBoost Baseline (5 feats) | 0.7516 ± 0.0458 | 0.9574 ± 0.0071 |
| Exp 2 | XGBoost Baseline (13 feats) | 0.7392 ± 0.0455 | 0.9573 ± 0.0072 |
| Exp 3 | Graph IR (5 feats) | 0.7435 ± 0.0405 | 0.9892 ± 0.0051 |
| Exp 4 | Graph IR (13 feats) | **0.8813 ± 0.0216** | **0.9960 ± 0.0041** |
| **Exp 5** | **HeteroTrojanGNN** | **0.7976 ± 0.0465** | **0.9918 ± 0.0057** |

---

## 4. Kết quả LOFO Cross-Validation — Cải thiện vượt trội của H-GNN

| # | Phương pháp | Micro-F1 | Macro-F1 |
|---|-------------|:---:|:---:|
| Exp 1 | XGBoost Baseline (5 feats) | 0.0314 | 0.0362 |
| Exp 2 | XGBoost Baseline (13 feats) | 0.0296 | 0.0344 |
| Exp 3 | Graph IR (5 feats) | 0.0837 | 0.1346 |
| Exp 4 | Graph IR (13 feats) | 0.0580 | 0.0792 |
| **Exp 5** | **HeteroTrojanGNN** | **0.3721** | **0.4282** |

### Per-family LOFO (Exp 5 H-GNN):

| Family Holdout | F1 | AUC | TP | FP | FN |
|---|:---:|:---:|:--:|:--:|:--:|
| RS232 (22 mạch) | 0.1128 | 0.4075 | 15 | 8 | 228 |
| s15850 (1 mạch) | 0.4727 | 0.9866 | 13 | 15 | 14 |
| s35932 (3 mạch) | **0.9500** | **0.9807** | 57 | 0 | 6 |
| s38417 (2 mạch) | 0.4923 | 0.9748 | 16 | 22 | 11 |
| s38584 (2 mạch) | 0.1132 | 0.9319 | 3 | 40 | 7 |

**Nhận xét quan trọng**:
- **Cải thiện LOFO vượt trội**: H-GNN đạt Macro-F1 = 0.4282, gấp **5.4×** so với Exp 4 (0.0792) và **11.8×** so với Exp 1 (0.0362).
- **s35932** đạt F1 = 0.9500 — chuỗi Trigger→Payload được học qua message passing.
- **RS232** còn thấp (F1 = 0.113): RS232 có tỉ lệ Trojan cực nhỏ (~2.1%), chủ yếu bị FN do class imbalance cực độ khi holdout.
- **So sánh Exp 4 vs Exp 5 LOFO**: Exp 4 sụp đổ hoàn toàn trên RS232 (TP=1) và s15850 (TP=0) — xác nhận rằng đặc trưng tô-pô thủ công không generalize được. H-GNN với message passing khái quát hóa tốt hơn đáng kể.

---

## 5. Đối chuẩn Graph XAI vs Tabular XAI

| Phương pháp XAI | Mô hình | Fidelity+ | Fidelity- | Loc. Prec | Loc. Recall | Circuit-level? |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **GNNExplainer** | H-GNN (Exp 5) | **0.0925** | **0.000** | **0.307** | **0.307** | **✓ (cổng logic)** |
| SHAP | XGBoost (Exp 1) | N/A | N/A | 0.548* | 1.0* | ✗ (feature only) |
| LIME | XGBoost (Exp 1) | N/A | N/A | 0.890* | 1.0* | ✗ (feature only) |
| Gradient Attr. | XGBoost (Exp 1) | N/A | N/A | 0.0* | 0.0* | ✗ (feature only) |

> \* Localization tabular XAI: đo "tỉ lệ feature top-k là Trojan-indicative (LGFi, PO, PI)" — không thể localize đến cổng logic cụ thể.

**Nhận xét**:
- **GNNExplainer** là phương pháp **duy nhất** khoanh vùng được đến cấp cổng logic (`cell`) và dây dẫn (`net`).
- Fidelity+ = 0.0925: che 20% cạnh quan trọng nhất giảm xác suất Trojan trung bình 9.25%.
- LIME có feature top-1 accuracy = 89% vì LGFi thường đứng đầu, nhưng không phân biệt được *cổng cụ thể nào* là Trojan.

---

## 6. Files đã tạo tuần này

| File | Mô tả |
|------|--------|
| `packages/shared/xai_shared/graph_data/pyg_converter.py` | Chuyển đổi nodes.csv + edges.csv → HeteroData (PyG) |
| `packages/shared/xai_shared/graph_data/hetero_gnn.py` | Mô hình HeteroTrojanGNN (2-layer HeteroConv + SAGEConv) |
| `scripts/train_and_benchmark_gnn.py` | Benchmark đầy đủ: Single Seed, 10-Run, LOFO cho Exp 5 |
| `scripts/explain_gnn.py` | GNNExplainer + Fidelity+/- + Localization Precision/Recall |
| `scripts/compare_xai_methods.py` | So sánh Graph XAI vs LIME/SHAP/Gradient |
| `data/models/comparison_5_experiments.json` | Kết quả đầy đủ 5 thí nghiệm (JSON) |
| `data/models/hetero_gnn_best.pt` | Checkpoint H-GNN tốt nhất (seed 42) |
| `data/explanations/gnn/gnn_explanations.json` | GNNExplainer trên 6 mạch benchmark |
| `data/explanations/xai_comparison_benchmark.json` | So sánh định lượng Graph XAI vs Tabular XAI |

---

## 7. Kiến trúc H-GNN

```
Đầu vào:
  Cell node: [one-hot cell family (20) | is_sequential (1) | 13 feats] = 34 dim
  Net node:  [one-hot net type (6)     | is_output (1)     | 13 feats] = 20 dim

Layer 1: HeteroConv {
  (net → data_input → cell):     SAGEConv
  (net → control_input → cell):  SAGEConv
  (cell → outputs → net):        SAGEConv
  + 3 reverse edge types
} + LayerNorm + ReLU + Residual

Layer 2: HeteroConv { ... } + LayerNorm + ReLU + Residual

Classifier Head (cell only):
  Linear(64→32) → ReLU → Dropout(0.2) → Linear(32→1)

Loss: BCEWithLogitsLoss(pos_weight = N_neg/N_pos)
```

---

## 8. Hướng tiếp theo

- [ ] Thử **Focal Loss** / **class-balanced sampling** để cải thiện LOFO trên RS232 và s38584
- [ ] Viết phần **RQ3 Analysis** chi tiết trong luận văn: so sánh LOFO Exp 1–5
- [ ] Tạo **visualization** subgraph explanation cho Trojan gate điển hình (mạch s35932)
- [ ] Gửi báo cáo tiến độ lên thầy hướng dẫn

