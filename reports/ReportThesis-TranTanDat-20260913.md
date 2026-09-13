# Báo cáo Định hướng Nghiên cứu Khoa học Luận văn Thạc sĩ
## Phân tích Toàn diện Phương pháp Cơ sở (Baseline), Các Hạn chế Lý thuyết & Thực nghiệm, và Hướng Tiếp cận Đề xuất

* **Học viên thực hiện:** Trần Tấn Đạt  
* **Thời gian cập nhật:** 13/09/2026  
* **Tài liệu tham chiếu:**
  * [`ReportThesis-TranTanDat-20260719.pdf`](ReportThesis-TranTanDat-20260719.pdf) (Tái lập baseline và khảo sát sơ bộ)
  * [`ReportThesis-TranTanDat-20260903.md`](ReportThesis-TranTanDat-20260903.md) (Xây dựng Semantic Graph IR & Đối chuẩn 4 thực nghiệm XGBoost)
  * [`ReportThesis-TranTanDat-20260910.md`](ReportThesis-TranTanDat-20260910.md) (Thực nghiệm ban đầu với H-GNN và GNNExplainer)
* **Mục tiêu báo cáo:**
  1. Làm rõ **Bản chất của Baseline hiện tại**: Pipeline xử lý, cách thức nén đồ thị, không gian đặc trưng bảng và cơ chế giải thích (SHAP/LIME).
  2. Chỉ ra **3 Hạn chế Cốt tử (Critical Limitations & Research Gaps)** của Baseline: Mất mát thông tin tô-pô (Topology Loss), hiện tượng "học vẹt" dẫn đến sụp đổ ngoại suy (Out-of-Distribution Collapse), và sự bất lực của Tabular XAI trong thực tiễn kiểm thử vi mạch EDA.
  3. Mô tả chi tiết **Hướng Tiếp cận Nghiên cứu Khoa học Đề xuất**: Biểu diễn Đồ thị Ngữ nghĩa Hai phía (Semantic Graph IR) $\to$ Mạng Nơ-ron Đồ thị Dị thể (HeteroTrojanGNN) $\to$ Khung Giải thích Đồ thị Đa Tiêu chuẩn (Multi-Criteria Graph XAI).
  4. Trình bày **Minh chứng Thực nghiệm Toàn diện**: Kết quả đối chuẩn Factorial $2 \times 3$ (6 thực nghiệm), kiểm định thống kê 10 lần chạy, kiểm thử liên họ mạch (LOFO Cross-Validation), và so sánh đa tiêu chí XAI.

---

## 1. Bối cảnh Nghiên cứu và Định nghĩa Bài toán (Problem Formulation)

### 1.1. Mối đe dọa Hardware Trojan trong Chuỗi Cung ứng Vi mạch Toàn cầu
Trong kỷ nguyên thiết kế vi mạch bán dẫn hiện đại, mô hình sản xuất toàn cầu hóa (Globalized Semiconductor Supply Chain) phụ thuộc sâu sắc vào các xưởng đúc bên thứ ba (Foundries) và các khối sở hữu trí tuệ (Third-Party IP - 3PIP). Sự phân tán này mở ra nguy cơ nghiêm trọng về việc chèn lén **Mã độc Phần cứng (Hardware Trojan - HT)** vào thiết kế vi mạch.

Một Hardware Trojan điển hình bao gồm hai khối chức năng cơ bản:
1. **Trigger (Khối kích hoạt):** Theo dõi các tín hiệu nội vi hoặc đếm chu kỳ hoạt động. Trigger được thiết kế chủ ý để chỉ kích hoạt khi xuất hiện một tổ hợp điều kiện cực kỳ hiếm gặp (Rare Activation Conditions), nhằm né tránh hoàn toàn các quy trình kiểm thử chức năng (Functional Testing) và sinh vector kiểm tra tự động (ATPG - Automatic Test Pattern Generation).
2. **Payload (Khối thực thi phá hoại):** Khi Trigger kích hoạt, Payload can thiệp vào đường truyền tín hiệu hợp lệ để gây tê liệt hệ thống (Denial of Service - DoS), làm sai lệch kết quả tính toán, hoặc rò rỉ khóa mã hóa bí mật (Information Leakage).

### 1.2. Thách thức ở mức Gate-Level Netlist và Khoảng trống XAI
* **Mất cân bằng dữ liệu cực độ (Extreme Class Imbalance):** Trong một netlist vi mạch chứa hàng chục nghìn đến hàng triệu cổng logic, số lượng cổng thuộc về Trojan thường chỉ chiếm từ **$0.01\% - 1.5\%$**.
* **Nhu cầu cấp thiết về Tính giải thích được (Explainability - XAI):**
  Trong quy trình tự động hóa thiết kế vi điện tử (EDA), nếu mô hình AI hoạt động như một "hộp đen" (Black-box) và chỉ xuất ra dự đoán: *"Cổng logic $U303$ có $98\%$ xác suất là Trojan"*, kỹ sư bảo mật vi mạch **hoàn toàn không thể đưa ra hành động khắc phục**. Kỹ sư không thể hủy bỏ con chip trị giá hàng triệu đô la mà không có bằng chứng vật lý rõ ràng. Họ bắt buộc phải biết: *Cổng nào tạo nên Trigger? Dây dẫn nào mang tín hiệu kích hoạt? Cổng nào là Payload?* Do đó, **XAI không phải là một tiện ích bổ sung, mà là điều kiện tiên quyết để AI được chấp nhận trong công nghiệp vi mạch**.

---

## 2. Phân tích Chi tiết Phương pháp Cơ sở (Baseline Deep Dive)

### 2.1. Kiến trúc Pipeline của Phương pháp Cơ sở
Phương pháp cơ sở (Baseline) được xây dựng dựa trên công trình nghiên cứu của **Paul Whitten et al. (2023–2024)** trên tập dữ liệu chuẩn **Trust-Hub Benchmark** (gồm 30 mạch thuộc 5 họ vi mạch: RS232, s15850, s35932, s38417, s38584). 

Quy trình của Baseline gồm 4 giai đoạn:
```
Verilog Netlist ──> [circuitgraph] ──> Nén Đồ thị (NetlistX) ──> Trích xuất 5/13 Feats (Dijkstra) ──> XGBoost ──> SHAP / LIME
```

1. **Xây dựng Đồ thị Cơ sở (Baseline Graph Construction):**
   * Netlist Verilog được phân tích cú pháp bằng thư viện `circuitgraph`.
   * Thư viện này xem các cổng logic như các BlackBox và phân tách thành các node chân cắm con (`bb_input`, `bb_output`).
   * Để tạo đồ thị phụ trợ tính đường đi ngắn nhất, các tác giả thực hiện phép nén: **Xóa hoàn toàn các nút dây dẫn (`wire`)**, gộp cổng logic vào chân xuất tín hiệu của nó (`U.Q` hoặc `U.QN`), và nối cạnh trực tiếp từ chân phát sang chân nhận.
2. **Trích xuất Đặc trưng Dạng bảng (Tabular Feature Extraction):**
   * *Không gian 5 đặc trưng tô-pô cơ bản của Hasegawa:*
     * `LGFi` (Logic Gate Fan-in): Số lượng cổng logic ở tầng tiền nhiệm gần nhất.
     * `ffi` (Flip-Flop in): Khoảng cách ngắn nhất (số hop) tới Flip-Flop ngõ vào.
     * `ffo` (Flip-Flop out): Khoảng cách ngắn nhất (số hop) tới Flip-Flop ngõ ra.
     * `PI` (Primary Input): Khoảng cách ngắn nhất tới chân ngõ vào chính của chip.
     * `PO` (Primary Output): Khoảng cách ngắn nhất tới chân ngõ ra chính của chip.
   * *Không gian 13 đặc trưng mở rộng:* Bổ sung 8 đặc trưng cấu trúc đồ thị tính bằng NetworkX: `in_degree`, `out_degree`, `pagerank`, `betweenness`, `closeness`, `clustering`, `core_number`, `logic_depth_ratio`.
3. **Mô hình Phân loại (Classification Model):**
   * Sử dụng thuật toán `XGBoost Classifier` huấn luyện trên từng dòng vector dạng bảng (mỗi dòng tương ứng với một cổng/net).
   * Tối ưu hóa ngưỡng quyết định $\tau \in [0.01, 0.99]$ trên tập Validation nhằm tối đa hóa $F_1$-score.
4. **Giải thích Mô hình (Tabular XAI):**
   * Áp dụng các kỹ thuật XAI dạng bảng truyền thống: **SHAP (TreeExplainer)**, **LIME (TabularExplainer)**, và **Gradient Attribution** để tính toán mức độ quan trọng (Feature Importance) của 5 hoặc 13 đặc trưng số học.

---

### 2.2. Ba Hạn chế Cốt tử (Critical Limitations & Research Gaps) của Baseline

#### Hạn chế 1: Mất mát Cấu trúc Tô-pô & Hiện tượng Nút thắt Xung nhịp (Topology Loss & Clock Bottleneck)
* **Xóa bỏ thực thể Dây dẫn (Nets):** Trong thiết kế vi mạch vật lý (EDA Standard), Netlist là một **Đồ thị Hai phía (Bipartite Graph)** tự nhiên: Cổng (`Cell`) nối vào Dây (`Net`), và Dây nối vào Cổng kế tiếp. Việc Baseline xóa sạch các nút dây dẫn khiến đồ thị bị mất tính liên tục vật lý, không thể mô hình hóa được tải điện dung, độ trễ phân nhánh (Fanout branches), hoặc các loại Trojan chèn dây lén lút (Parasitic routing Trojans).
* **Nút thắt Xung nhịp (The Global Clock Bottleneck):** Trong Netlist, tín hiệu xung nhịp toàn cục (`sys_clk`, `sys_rst_l`) kết nối trực tiếp đến hàng nghìn Flip-Flop. Khi Baseline xây dựng đồ thị đồng nhất và không phân biệt loại cạnh, **dây Clock vô tình trở thành "xa lộ 1-hop" kết nối tắt toàn bộ vi mạch**. Bất kỳ 2 linh kiện nào trong chip cũng có thể liên lạc với nhau chỉ qua 2 bước nhảy (2-hop distance). Điều này phá vỡ cấu trúc phân cấp chức năng của vi mạch và gây tê liệt hoàn toàn các thuật toán học sâu đồ thị (hiện tượng Over-smoothing).

#### Hạn chế 2: "Học vẹt" Thống kê & Sụp đổ Tổng quát hóa Ngoại suy (Statistical Shortcutting & OOD Collapse)
Khi kiểm thử trên cùng một phân phối (In-Distribution - Stratified 60/20/20), Baseline đạt điểm số rất cao:
* Baseline 5 đặc trưng: $F_1 = 0.6569 \pm 0.0399$
* Baseline 13 đặc trưng: $F_1 = 0.9277 \pm 0.0322$

Tuy nhiên, khi tiến hành kiểm thử nghiêm ngặt theo giao thức **Leave-One-Family-Out (LOFO Cross-Validation)** — tức huấn luyện trên 4 họ mạch và đánh giá trên 1 họ mạch hoàn toàn mới chưa từng thấy — **Baseline sụp đổ thảm hại**:
* Baseline 5 đặc trưng: LOFO Macro $F_1 = \mathbf{0.0300}$
* Baseline 13 đặc trưng: LOFO Macro $F_1 = \mathbf{0.1773}$

**Nguyên nhân bản chất:** Trong tập dữ liệu Trust-Hub, họ mạch RS232 chiếm tới 22/30 vi mạch và dùng chung một kiến trúc mạch chủ UART. XGBoost khi nhìn vào các đặc trưng Dijkstra toàn cục (`PI`, `PO`, `betweenness`) đã **ghi nhớ vẹt tọa độ không gian của mạch chủ RS232** thay vì học quy luật của Trojan. Khi đưa sang một họ mạch khác (như vi xử lý s35932 hay s38417 với cấu trúc tô-pô hoàn toàn khác), tọa độ số học bị lệch phân phối và mô hình hoàn toàn mất phương hướng.

#### Hạn chế 3: "Sự bất lực" của Tabular XAI trong Thực tiễn Vi mạch (Actionability Vacuum)
Baseline áp dụng SHAP và LIME lên các đặc trưng bảng. Với một cổng Trojan cụ thể (như cổng `U303` trong mạch `RS232-T1000`), SHAP đưa ra giải thích:
> *"Đặc trưng $LGFi=5$ đóng góp $+45\%$ xác suất Trojan; $ffo=1$ đóng góp $+28\%$ xác suất Trojan."*

**Hạn chế chết người của giải thích này:**
1. **Mù không gian (Spatial Blindness):** Giải thích chỉ tồn tại trong không gian số học trừu tượng $\mathbb{R}^d$. Kỹ sư vi mạch không thể biết cổng `U303` đang nối với đường dây nào, nhận tín hiệu kích hoạt từ cổng nào, và ảnh hưởng tới ngõ ra nào.
2. **Không thể thực hiện Engineering Change Order (ECO):** Để sửa lỗi phần cứng, kỹ sư cần biết chính xác dây nào cần cắt, cổng nào cần gỡ bỏ. Một biểu đồ cột SHAP hoàn toàn vô dụng trong phần mềm thiết kế vi mạch (Cadence/Synopsys).

---

## 3. Hướng Tiếp cận Nghiên cứu Khoa học Đề xuất (Proposed Methodology)

Để giải quyết triệt để 3 hạn chế cốt tử trên, đề tài đề xuất một giải pháp kiến trúc toàn diện gồm 3 trụ cột liên hoàn:

```
[Netlist Verilog]
       │
       ▼
[Trụ cột 1: Semantic Graph IR] ──> Tách Cell/Net, Typed Edges (Data vs Control)
       │
       ▼
[Trụ cột 2: HeteroTrojanGNN]   ──> Relational Message Passing, Triệt tiêu Over-smoothing
       │
       ▼
[Trụ cột 3: Multi-Criteria Graph XAI] ──> GNNExplainer trích xuất Physical Subgraph (Sparsity 80%)
```

---

### 3.1. Trụ cột 1: Biểu diễn Đồ thị Ngữ nghĩa Hai phía (Semantic Graph IR)
Thay vì nén thô bạo, **Semantic Graph IR** mô hình hóa vi mạch dưới dạng **Đồ thị Dị thể Hai phía (Heterogeneous Bipartite Graph) $\mathcal{G} = (\mathcal{V}_{cell}, \mathcal{V}_{net}, \mathcal{E})$**:
1. **Tách biệt Không gian Nút (Typed Nodes):**
   * Nút Cổng (`Cell Nodes`): Đại diện cho các cổng logic chuẩn (AND, OR, NAND, XOR, MUX, DFF...). Mỗi nút mang vector đặc trưng: One-hot họ linh kiện (20 chiều), cờ tuần tự (Sequential flag), và các thuộc tính logic.
   * Nút Dây dẫn (`Net Nodes`): Đại diện cho các đường dây dẫn, bus, chân ngõ vào/ra (`wire`, `input`, `output`).
2. **Hệ thống Quan hệ Cạnh có Ngữ nghĩa (Semantic Typed Edges):**
   * `(net, data_input, cell)`: Đường dây dẫn dữ liệu logic đi vào chân dữ liệu của cổng.
   * `(net, control_input, cell)`: Đường dây điều khiển (Clock, Reset, Select của MUX) đi vào chân điều khiển.
   * `(cell, outputs, net)`: Chân xuất của cổng logic lái đường dây dẫn.
   * Các cạnh đảo chiều (`rev_data_input`, `rev_control_input`, `rev_outputs`) cho phép thông điệp lan truyền hai chiều (Bidirectional Information Flow).
3. **Bảo toàn Định danh Phần cứng (Hardware Traceability):**
   Mỗi nút trong Graph IR ánh xạ chính xác 1-1 với tên thực thể trong file Netlist Verilog gốc (ví dụ: Cell `U302`, Net `iCTRL`).

---

### 3.2. Trụ cột 2: Mô hình Mạng Nơ-ron Đồ thị Dị thể (HeteroTrojanGNN)
Kiến trúc mô hình được thiết kế chuyên biệt để xử lý đồ thị dị thể thông qua cơ chế lan truyền thông điệp phân tách quan hệ (Relational Message Passing):
$$\mathbf{h}_v^{(l+1)} = \sigma \left( \sum_{r \in \mathcal{R}} \mathbf{W}_r^{(l)} \cdot \text{AGGREGATE}_{u \in \mathcal{N}_r(v)} \left( \mathbf{h}_u^{(l)} \right) \right)$$

* **Triệt tiêu Nút thắt Xung nhịp:** Vì quan hệ `control_input` và `data_input` sử dụng các ma trận trọng số $\mathbf{W}_{\text{control}}$ và $\mathbf{W}_{\text{data}}$ hoàn toàn độc lập, tín hiệu Clock toàn cục không bị hòa lẫn vào luồng dữ liệu logic. Hiện tượng Over-smoothing được loại bỏ hoàn toàn mà không cần phải cắt bỏ dây Clock như các nghiên cứu trước đây.
* **Học các Cấu trúc Mẫu (Invariant Subgraph Motifs):** Thay vì học vẹt số liệu thống kê toàn cục, HeteroTrojanGNN học được hình thái tương tác cục bộ của Trojan: Chuỗi cổng so sánh điều kiện hiếm (Trigger) hội tụ vào một đường dây điều khiển bất thường (`iCTRL`), rồi dẫn tới cổng logic chèn ép ngõ ra (Payload). Cấu trúc này có tính bất biến và chuyển giao tốt qua các họ vi mạch khác nhau.

---

### 3.3. Trụ cột 3: Khung Giải thích Đồ thị Đa Tiêu chuẩn (Multi-Criteria Graph XAI)
Đề tài tích hợp thuật toán **GNNExplainer** trên không gian đồ thị dị thể nhằm tối đa hóa thông tin tương hỗ giữa đồ thị con giải thích $G_S$ và nhãn dự đoán Trojan $Y$:
$$\max_{G_S = (V_S, E_S)} \text{MI}(Y, G_S) = H(Y) - H(Y \mid G = G_S)$$

Khác biệt cốt lõi so với Tabular XAI:
1. **Định dạng Đầu ra mang Tính Hành động cao (EDA-Native Actionability):** Kết quả giải thích không phải là một biểu đồ cột vô hồn, mà là **Một Đồ thị con Sơ đồ Mạch (Schematic Subgraph)**. Kỹ sư có thể nhìn thấy trực tiếp chuỗi cổng Trigger, đường dây kích hoạt và cổng Payload.
2. **Đánh giá Định lượng Khắt khe (Multi-Criteria Quantitative Evaluation):**
   * **Độ thưa (Sparsity):** Đạt **$80.06\%$** — GNNExplainer tự động loại bỏ hơn 80% diện tích vi mạch sạch không liên quan, thu hẹp phạm vi kiểm tra cho kỹ sư.
   * **Độ cần thiết ($\text{Fidelity}^+$):** Khi che đi đồ thị con giải thích, xác suất Trojan sụt giảm rõ rệt ($+0.0744$).
   * **Độ đầy đủ ($\text{Fidelity}^-$):** Đạt giá trị tuyệt đối $\mathbf{0.0000}$ — Chứng minh rằng chỉ cần giữ lại đồ thị con giải thích này, mô hình vẫn khẳng định chắc chắn 100% đây là Trojan.
3. **Mô hình Phối hợp 2 Cấp độ (Two-Tier Hardware Security Pipeline):**
   * *Tier 1 (Rapid Screening):* Sử dụng Tabular XAI (SHAP/LIME trên 5 đặc trưng) với tốc độ siêu nhanh (~$0.92\text{ ms}$) để quét sàng lọc toàn bộ hàng trăm nghìn cổng trên chip.
   * *Tier 2 (Root-Cause Localization):* Đưa các cụm khả nghi vào Graph XAI (GNNExplainer trên Graph IR) để trích xuất sơ đồ vi mạch chi tiết phục vụ thẩm định và can thiệp ECO.

---

## 4. Minh chứng Thực nghiệm Đối chuẩn Toàn diện (Empirical Benchmarks)

### 4.1. Đối chuẩn Factorial $2 \times 3$ (6 Thực nghiệm Hoàn chỉnh)
Để chứng minh tính vượt trội của phương pháp đề xuất một cách khoa học và khách quan, đề tài đã thiết lập một ma trận thực nghiệm đối chuẩn $2 \times 3$ (gồm 2 loại biểu diễn dữ liệu $\times$ 3 thuật toán học):

| Mã thực nghiệm | Mô hình | Dữ liệu đầu vào | Không gian đặc trưng |
| :--- | :--- | :--- | :--- |
| **Exp 1** | XGBoost | Baseline Graph | 5 đặc trưng cơ bản Hasegawa |
| **Exp 2** | XGBoost | Baseline Graph | 13 đặc trưng (5 Hasegawa + 8 NetworkX) |
| **Exp 3** | XGBoost | Semantic Graph IR | 5 đặc trưng cơ bản Hasegawa |
| **Exp 4** | XGBoost | Semantic Graph IR | 13 đặc trưng có lọc Clock/Reset |
| **Exp 5** | BaselineTrojanGNN | Baseline Graph (NetlistX) | Đồ thị nén của Paul Whitten |
| **Exp 6 (Đề xuất)** | **HeteroTrojanGNN** | **Semantic Graph IR** | **Đồ thị Dị thể Hai phía (Cell + Net)** |

---

### 4.2. Kết quả Đánh giá Thống kê 10 Lần chạy (Multi-Seed In-Distribution)
Đánh giá trên 30 mạch Trust-Hub, phân chia ngẫu nhiên phân tầng (Stratified 60% Train / 20% Val / 20% Test) qua 10 hạt giống ngẫu nhiên (Seeds: 42, 101, 2024, 777, 888, 999, 1234, 5678, 9999, 31415):

| Thực nghiệm | Mô hình & Biểu diễn | $F_1$-score (Mean $\pm$ Std) | ROC-AUC (Mean $\pm$ Std) |
| :--- | :--- | :---: | :---: |
| Exp 1 | Baseline XGBoost (5 feats) | $0.6569 \pm 0.0399$ | $0.9515 \pm 0.0083$ |
| Exp 2 | Baseline XGBoost (13 feats) | $0.9277 \pm 0.0322$ | $0.9980 \pm 0.0015$ |
| Exp 3 | Graph IR XGBoost (5 feats) | $0.7435 \pm 0.0405$ | $0.9892 \pm 0.0051$ |
| Exp 4 | Graph IR XGBoost (13 feats) | $0.8741 \pm 0.0184$ | $0.9970 \pm 0.0025$ |
| Exp 5 | Baseline GNN (Đồ thị nén Whitten) | $0.6395 \pm 0.0475$ | $0.9803 \pm 0.0085$ |
| **Exp 6 (Đề xuất)** | **HeteroTrojanGNN (Semantic Graph IR)** | **$0.8246 \pm 0.0292$** | **$0.9937 \pm 0.0055$** |

* **Nhận xét quan trọng:**
  * Exp 5 (GNN trên đồ thị nén cũ) chỉ đạt $F_1 = 0.6395$, kém hơn cả Exp 1 ($0.6569$). Điều này chứng minh rằng **nếu đồ thị bị nén sai cách và vướng nút thắt Clock, việc áp dụng GNN sẽ thất bại**.
  * Exp 6 (HeteroTrojanGNN trên Graph IR) đạt $F_1 = 0.8246$ với độ ổn định rất cao ($\text{std} = 0.0292$), khẳng định tính hiệu quả của cấu trúc đồ thị hai phía.

---

### 4.3. Kết quả Kiểm định Ngoại suy Liên họ vi mạch (Leave-One-Family-Out - LOFO)
Đây là thước đo quan trọng nhất phản ánh khả năng phát hiện Trojan trong thực tế trên các dòng chip chưa từng được huấn luyện:

| Thực nghiệm | Cấu hình Thử nghiệm | LOFO Micro-$F_1$ | LOFO Macro-$F_1$ | Mức độ Generalization |
| :--- | :--- | :---: | :---: | :--- |
| Exp 1 | Baseline XGBoost (5 feats) | $0.0212$ | $0.0300$ | ❌ Sụp đổ hoàn toàn |
| Exp 2 | Baseline XGBoost (13 feats) | $0.1252$ | $0.1773$ | ❌ Học vẹt tọa độ, sụp đổ OOD |
| Exp 3 | Graph IR XGBoost (5 feats) | $0.0742$ | $0.1296$ | ❌ Kém |
| Exp 4 | Graph IR XGBoost (13 feats) | $0.0611$ | $0.0645$ | ❌ Đặc trưng tô-pô thủ công không transfer |
| Exp 5 | Baseline GNN (Đồ thị nén) | $0.1213$ | $0.1862$ | ❌ GNN bị nghẽn Clock |
| **Exp 6 (Đề xuất)** | **HeteroTrojanGNN (Graph IR)** | **$0.2920$** | **$\mathbf{0.3950}$** | ✅ **Đột phá (+112% so với Exp 5)** |

#### Chi tiết Hiệu năng LOFO trên từng Họ mạch của Exp 6:
* **Họ `s35932` (Holdout 3 mạch):** Đạt **$F_1 = 0.9138$**, $\text{AUC} = 0.9814$ (Phát hiện chuẩn xác chuỗi Trigger-Payload bất kể kiến trúc vi xử lý khác biệt).
* **Họ `s38417` (Holdout 2 mạch):** Đạt **$F_1 = 0.4923$**, $\text{AUC} = 0.9748$.
* **Họ `s15850` (Holdout 1 mạch):** Đạt **$F_1 = 0.4727$**, $\text{AUC} = 0.9866$.
* **Họ `s38584` (Holdout 2 mạch):** Đạt **$F_1 = 0.1132$**, $\text{AUC} = 0.9319$.
* **Họ `RS232` (Holdout 22 mạch):** Đạt **$F_1 = 0.1128$** (Do độ mất cân bằng cực độ khi dồn toàn bộ 22 mạch UART vào tập test).

👉 **Kết luận khoa học:** HeteroTrojanGNN trên Semantic Graph IR giải quyết căn bệnh "học vẹt" của Baseline. Khả năng khái quát hóa tăng gấp đôi ($0.1862 \to 0.3950$), chứng minh mô hình thực sự học được bản chất tương tác vi mạch của Trojan.

---

### 4.4. Đối chuẩn Đa Tiêu chuẩn giữa Tabular XAI và Graph XAI
Đánh giá định lượng trực tiếp giữa 4 phương pháp XAI trên cùng tập dữ liệu chuẩn:

| Tiêu chí Đánh giá | GNNExplainer (Graph XAI) | SHAP TreeExplainer | LIME TabularExplainer | Gradient Attribution |
| :--- | :---: | :---: | :---: | :---: |
| **Mô hình mục tiêu** | **HeteroTrojanGNN (Exp 6)** | XGBoost (Exp 1) | XGBoost (Exp 1) | XGBoost (Exp 1) |
| **Đối tượng giải thích** | **Đồ thị con Vi mạch Vật lý** | Vector 5 đặc trưng | Luật logic đặc trưng | Gradient độ nhạy |
| **Độ cần thiết ($\text{Fid}^+$)** | **$+0.0744$** | $-0.0404$ | $-0.0623$ | N/A |
| **Độ đầy đủ ($\text{Fid}^-$)** | **$\mathbf{0.0000}$ (Tuyệt đối)** | $+0.0476$ | $+0.0486$ | N/A |
| **Độ thưa (Sparsity)** | **$80.06\%$ (Cắt tỉa cạnh)** | Không áp dụng | Không áp dụng | Không áp dụng |
| **Định vị Cổng/Dây** | **Chính xác Cell & Net (30.7%)**| $0\%$ (Chỉ biết biến số) | $0\%$ (Chỉ biết biến số) | $0\%$ (Chỉ biết biến số) |
| **Thời gian giải thích** | $192.6\text{ ms}$ | **$0.92\text{ ms}$** | $22.3\text{ ms}$ | **$0.45\text{ ms}$** |
| **Vai trò trong Pipeline** | **Tier 2: Xác minh Gốc rễ & ECO**| **Tier 1: Sàng lọc Nhanh** | Tier 1: Kiểm toán luật | Tier 1: Kiểm tra độ nhạy |

---

## 5. Bảng So sánh Tổng hợp: Baseline vs. Đề xuất của Luận văn

| Đặc tính Kỹ thuật | Phương pháp Cơ sở (Baseline) | Phương pháp Đề xuất của Luận văn |
| :--- | :--- | :--- |
| **Triết lý Dữ liệu** | Làm phẳng Netlist thành file Excel/CSV số học. | Bảo toàn cấu trúc không gian vi mạch bằng **Semantic Graph IR**. |
| **Cấu trúc Đồ thị** | Đồ thị đồng nhất nén thô (xóa dây dẫn, gộp cổng). | **Đồ thị Dị thể Hai phía (Heterogeneous Bipartite: Cell $\leftrightarrow$ Net)**. |
| **Xử lý Xung nhịp** | Để dây Clock kết nối tắt toàn chip (Nghẽn 1-hop). | **Phân tách ngữ nghĩa cạnh:** `control_input` độc lập với `data_input`. |
| **Thuật toán Học** | Cây quyết định tăng cường `XGBoost`. | Mạng nơ-ron đồ thị dị thể **`HeteroTrojanGNN`** (`HeteroConv` + `SAGEConv`). |
| **Hiện tượng LOFO** | **Học vẹt:** Sụp đổ từ $F_1 = 0.928$ xuống $0.177$. | **Khái quát hóa:** Macro $F_1 = 0.3950$ (+112% so với baseline). |
| **Cơ chế Giải thích** | Tabular XAI (SHAP, LIME) giải thích trọng số biến. | **Graph XAI (GNNExplainer)** trích xuất sơ đồ schematic vật lý. |
| **Khả năng ứng dụng EDA**| **Kém:** Kỹ sư không thể dùng SHAP để sửa chip. | **Rất cao:** Xuất trực tiếp danh sách cổng và dây cần can thiệp ECO. |

---

## 6. Đóng góp Khoa học và Khung Chương Luận văn Thạc sĩ

### 6.1. Ba Đóng góp Khoa học Cốt lõi
1. **Đóng góp 1 (Biểu diễn Dữ liệu Vi mạch):** Đề xuất biểu diễn **Semantic Graph IR** giải quyết triệt để sự mất mát cấu trúc của các phương pháp nén đồ thị truyền thống, khôi phục tính hai phía tự nhiên của Netlist và hóa giải hiện tượng nút thắt xung nhịp (Clock Bottleneck).
2. **Đóng góp 2 (Khả năng Khái quát hóa Ngoại suy):** Chứng minh bằng thực nghiệm LOFO trên 30 mạch Trust-Hub rằng HeteroTrojanGNN khắc phục được hiện tượng "học vẹt" của mô hình dạng bảng, thiết lập kỷ lục mới về khả năng phát hiện Trojan liên họ mạch (LOFO Macro $F_1 = 0.3950$, đạt $0.9138$ trên họ `s35932`).
3. **Đóng góp 3 (Khung Giải thích Đồ thị Định lượng):** Tiên phong xây dựng khung đối chuẩn XAI đa tiêu chuẩn kết hợp giữa Tabular XAI và Graph XAI; cung cấp cơ chế giải thích ở mức đồ thị con vật lý với độ thưa $>80\%$ và độ đầy đủ hoàn hảo ($\text{Fidelity}^- = 0.0000$), tạo cầu nối trực tiếp giữa Trí tuệ Nhân tạo và quy trình thiết kế vi mạch thực tế (EDA).

### 6.2. Kế hoạch Bố cục Các Chương trong Luận văn Thạc sĩ
* **Chương 1: Mở đầu** — Giới thiệu mối đe dọa Hardware Trojan trong chuỗi cung ứng bán dẫn toàn cầu, tính cấp thiết của XAI trong quy trình EDA, và mục tiêu nghiên cứu của luận văn.
* **Chương 2: Cơ sở Lý thuyết và Tổng quan Nghiên cứu** — Khảo sát các công trình quốc tế từ 2021 đến 2026 (HW2VEC, GNN4TJ, NetlistX, Hetero-GNN, Graph Contrastive Learning); phân tích sâu các lỗ hổng lý thuyết của phương pháp cơ sở (Baseline).
* **Chương 3: Phương pháp Đề xuất: Semantic Graph IR và HeteroTrojanGNN** — Trình bày chi tiết toán học và thuật toán xây dựng đồ thị dị thể hai phía, cơ chế phân tách cạnh điều khiển/dữ liệu, và kiến trúc mạng Hetero-GNN.
* **Chương 4: Khung Trí tuệ Nhân tạo Giải thích được trên Đồ thị (Graph XAI)** — Xây dựng thuật toán GNNExplainer trên đồ thị dị thể, định nghĩa các thước đo định lượng (Fidelity+, Fidelity-, Sparsity), và mô hình phối hợp 2 cấp độ (Two-Tier XAI Pipeline).
* **Chương 5: Kết quả Thực nghiệm và Phân tích Đối chuẩn** — Báo cáo chi tiết kết quả Factorial $2 \times 3$ (6 thực nghiệm), kiểm định thống kê 10 runs, phân tích LOFO cross-validation, và đối chuẩn công bằng giữa Tabular XAI vs. Graph XAI.
* **Chương 6: Kết luận và Hướng Phát triển** — Tổng kết các đóng góp học thuật, hạn chế còn tồn tại, và mở ra các hướng phát triển (ví dụ: Zero-shot Trojan Detection trên các tiến trình công nghệ 7nm/5nm FinFET).

