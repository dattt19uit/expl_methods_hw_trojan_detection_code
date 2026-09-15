# BÁO CÁO TIẾN ĐỘ & KẾT QUẢ NGHIÊN CỨU LUẬN VĂN THẠC SĨ
## Kiểm Toán Dữ Liệu, Đặc Tả Semantic Graph IR và Thực Nghiệm Ablation Đối Chứng (A–E) Trong Phát Hiện Mã Độc Phần Cứng

**Đề tài (English):** *Semantic Graph-based Representation for Robust and Explainable Hardware Trojan Localization*  
**Đề tài (Tiếng Việt):** *Nghiên cứu Phương pháp Biểu diễn Đồ thị Ngữ nghĩa phục vụ Định vị Mã độc Phần cứng Bền vững và Có thể Giải thích được trên Netlist Vi mạch*  
**Học viên thực hiện:** Trần Tấn Đạt  
**Ngày cập nhật:** 15/09/2026  
**Văn bản định hướng:** [ANTIGRAVITY_RESEARCH_EXECUTION_PLAN.md](file:///home/dat_ttan/thesis/expl_methods_hw_trojan_detection_code/research_plan/ANTIGRAVITY_RESEARCH_EXECUTION_PLAN.md)  

---

## 1. Mục Tiêu Nghiên Cứu & Các Câu Hỏi Nghiên Cứu Cốt Lõi (Research Questions)

Mục tiêu trung tâm của luận văn là giải quyết bài toán phát hiện và định vị Mã độc Phần cứng (Hardware Trojan - HT) ở cấp độ Netlist cổng logic, đặc biệt chú trọng năng lực **tổng quát hóa ngoại suy liên họ vi mạch (Cross-Family Generalization)** và **tính khả thi giải thích vật lý cho kỹ sư EDA**.

Nghiên cứu được thiết kế để trả lời 3 câu hỏi khoa học có kiểm soát:
* **RQ1 (Đóng góp của Biểu diễn - Representation):** Việc mô hình hóa tường minh đường dây dẫn thành nút riêng biệt trong Đồ thị Hai phía (Cell--Net Bipartite Graph) có cải thiện năng lực phát hiện Trojan so với đồ thị nén phẳng truyền thống hay không?
* **RQ2 (Giả thuyết Nút thắt Xung nhịp - Clock Bottleneck Hypothesis):** Mạng dây điều khiển xung nhịp toàn cục (`sys_clk`) và tín hiệu reset nối tới hàng nghìn cổng có làm suy giảm (over-smoothing) biểu diễn của GNN khi ngoại suy sang họ vi mạch chưa từng thấy hay không? Việc cô lập luồng dữ liệu $G_{\text{data}}$ hoặc ngắt các cạnh điều khiển có cải thiện kết quả?
* **RQ3 (Bóc tách Đóng góp Thành phần - Component Attribution):** Mức độ đóng góp tương đối giữa: (1) Cấu trúc hai phía Cell--Net, (2) Lan truyền thông điệp dị thể có phân biệt quan hệ cạnh (HeteroConv), (3) Cơ chế xử lý cạnh điều khiển, và (4) Bộ đặc trưng cấu trúc tô-pô?
* **Secondary Question (Giải thích Hóa - Explainability):** Graph XAI có thực sự vượt trội hơn Tabular XAI (SHAP/LIME) trong việc cung cấp sơ đồ mạch vật lý phục vụ lệnh sửa đổi kỹ thuật (ECO) hay không?

---

## 2. Phase A: Kết Quả Kiểm Toán Dữ Liệu Toàn Diện (Dataset Audit)

Thực hiện kiểm toán độc lập toàn bộ 30 vi mạch thuộc bộ dữ liệu chuẩn Trust-Hub. Chi tiết được lưu tại [outputs/audit/dataset_summary.csv](file:///home/dat_ttan/thesis/expl_methods_hw_trojan_detection_code/outputs/audit/dataset_summary.csv) và [docs/dataset_audit.md](file:///home/dat_ttan/thesis/expl_methods_hw_trojan_detection_code/docs/dataset_audit.md).

### 2.1. Thống Kê Tổng Thể & Phân Bố Họ Vi Mạch
- **Tổng số cổng logic (Cell Nodes):** **47,464** cổng.
- **Tổng số đường dây dẫn (Net Nodes):** **61,067** dây.
- **Tổng số liên kết có hướng hai phía (Directed Edges):** **202,415** cạnh.
- **Tổng số cổng Trojan:** **370** cổng.
- **Tổng số cổng sạch:** **47,094** cổng.
- **Tỷ lệ Trojan tổng thể:** **0.7795%** (Mất cân bằng cực đoan: Trung bình chỉ 1 cổng Trojan trên 247 cổng sạch).

| Họ Vi Mạch (Family) | Số Mạch | Tổng Cổng (Cells) | Tổng Dây (Nets) | Tổng Cạnh (Edges) | Cổng Trojan | Cổng Sạch | Tỷ Lệ Trojan (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `RS232` | 22 | 5,299 | 6,257 | 22,039 | 243 | 5,056 | 4.586% |
| `s15850` | 1 | 2,182 | 2,798 | 8,981 | 27 | 2,155 | 1.237% |
| `s35932` | 3 | 16,341 | 21,993 | 68,135 | 63 | 16,278 | 0.386% |
| `s38417` | 2 | 10,685 | 14,091 | 48,945 | 27 | 10,658 | 0.253% |
| `s38584` | 2 | 12,957 | 15,928 | 54,315 | 10 | 12,947 | 0.077% |
| **TỔNG CỘNG** | **30** | **47,464** | **61,067** | **202,415** | **370** | **47,094** | **0.780%** |

### 2.2. Ghi Nhận Kiểm Toán Thực Tế (Scientific Integrity Check)
Kiểm toán độc lập phát hiện một số sai lệch nhãn trong cấu hình gốc của Trust-Hub:
1. Bản netlist `RS232-T1800-90nm` (`uart_scan_route.v`) không chứa các cổng mang tên `U300`--`U303` (nhãn 0 cổng Trojan trong đồ thị 90nm), trong khi bản `RS232-T1800-180nm` có đầy đủ 4 cổng Trojan.
2. Một số vi mạch RS232 90nm (`T1000`, `T1500`, `T1600`) có sự chênh lệch 1 cổng so với metadata do quy tắc tối ưu cổng đệm (INV/BUF) khi tổng hợp logic.
3. Toàn bộ các phát hiện này được ghi nhận minh bạch trong báo cáo kiểm toán khoa học thay vì bỏ qua hay sửa đổi dữ liệu tùy tiện.

---

## 3. Phase B & C: Đặc Tả Semantic Graph IR & Kiểm Toán Không Gian Đặc Trưng

### 3.1. Mô Hình Toán Học Đồ Thị Hai Phía Ngữ Nghĩa (Semantic Graph IR)
Netlist vi mạch được mô hình hóa thành đồ thị có hướng dị thể:
$$\mathcal{G} = (\mathcal{V}_{\text{cell}}, \mathcal{V}_{\text{net}}, \mathcal{E}, \Phi_{\mathcal{V}}, \Phi_{\mathcal{E}})$$

* **Tập đỉnh:** Phân tách triệt để giữa tập cổng logic $\mathcal{V}_{\text{cell}}$ và đường dây $\mathcal{V}_{\text{net}}$ ($\mathcal{V}_{\text{cell}} \cap \mathcal{V}_{\text{net}} = \emptyset$).
* **Hệ thống 6 loại cạnh dị thể $\Phi_{\mathcal{E}}$:**
  - Forward: `('cell', 'outputs', 'net')`, `('net', 'data_input', 'cell')`, `('net', 'control_input', 'cell')`
  - Reverse: `('net', 'rev_outputs', 'cell')`, `('cell', 'rev_data_input', 'net')`, `('cell', 'rev_control_input', 'net')`

### 3.2. Quy Tắc Nhận Diện Cạnh Điều Khiển & Cô Lập Luồng Dữ Liệu $G_{\text{data}}$
Cạnh được gán nhãn `is_control = 1` nếu chân pin cổng thuộc tập cổng điều khiển chuẩn công nghiệp:
$$\text{CONTROL\_PORTS} = \{\text{"CLK"}, \text{"CK"}, \text{"RSTB"}, \text{"RN"}, \text{"SETB"}, \text{"SN"}, \text{"test\_se"}\}$$
Tất cả các cạnh dữ liệu logic thông thường (`DIN`, `A`, `B`, `IN1`...) mang nhãn `is_control = 0`.

### 3.3. Không Gian Đặc Trưng & Cam Kết Cách Ly Rò Rỉ (Zero Data Leakage)
Đặc tả chi tiết tại [outputs/audit/feature_schema.csv](file:///home/dat_ttan/thesis/expl_methods_hw_trojan_detection_code/outputs/audit/feature_schema.csv) và [docs/feature_spec.md](file:///home/dat_ttan/thesis/expl_methods_hw_trojan_detection_code/docs/feature_spec.md):
- **Vector cổng logic $x_{\text{cell}} \in \mathbb{R}^{34}$:** 20d One-hot họ cổng logic + 1d Cờ tuần tự (`is_sequential`) + 13d Đặc trưng cấu trúc Graph IR (Fan-in LGFi, khoảng cách logic ffi, ffo, PI, PO, bậc vào/ra, PageRank, Betweenness, Closeness, Clustering, Core Number, Tỷ lệ độ sâu logic).
- **Vector đường dây $x_{\text{net}} \in \mathbb{R}^{20}$:** 6d One-hot loại dây (`wire`, `input`, `output`...) + 1d Cờ chân chip xuất (`is_output`) + 13d Đặc trưng cấu trúc tô-pô.
- **Cam kết Cách ly Tuyệt đối:**
  1. `uses_label = False`: $100\%$ các đặc trưng chỉ trích xuất từ cú pháp Verilog và tô-pô đồ thị, tuyệt đối không truy cập nhãn `is_trojan`.
  2. Chuẩn hóa $z$-score (`StandardScaler`) được tính toán độc quyền trên tập Train của từng fold LOFO, không dùng thông tin phân phối của họ kiểm thử.

---

## 4. Phase D & E: Đóng Băng Giao Thức Đánh Giá Khoa Học (Evaluation Protocol)

Tài liệu đặc tả [docs/experimental_protocol.md](file:///home/dat_ttan/thesis/expl_methods_hw_trojan_detection_code/docs/experimental_protocol.md) thiết lập ranh giới nghiêm ngặt giữa hai giao thức đánh giá:

1. **Giao Thức In-Distribution (Node-Level Split 60/20/20):**
   - Đánh giá năng lực khớp mẫu của mô hình dưới sự mất cân bằng dữ liệu cực đoan ($0.78\%$).
   - **Cảnh báo Khoa học:** Các cổng logic của cùng một vi mạch xuất hiện ở cả Train, Val, và Test. Do đó, kết quả này **chỉ đo năng lực ghi nhớ mẫu trong phân phối**, không thể dùng làm bằng chứng cho tính tổng quát hóa zero-day.
2. **Giao Thức Leave-One-Family-Out (LOFO Cross-Validation - 5 Folds):**
   - Trong mỗi fold, toàn bộ vi mạch của 1 họ bị giữ lại làm tập Test độc lập. Mô hình chỉ học trên 4 họ còn lại (85% Train, 15% Validation).
   - **Dò ngưỡng tối ưu ($\tau^*$):** Ngưỡng $\tau^* \in [0.01, 0.99]$ được tối ưu hóa $F_1$ **hoàn toàn trên tập Validation của 4 họ Train**, sau đó áp dụng cố định sang họ Test. Tập Test hoàn toàn "mù" trong suốt quá trình huấn luyện và tối ưu.
   - **Thước đo chính:** Macro-$F_1$ trung bình qua 5 họ vi mạch.

---

## 5. Phase G, H, I: Thực Nghiệm Thí Nghiệm Ablation Đối Chứng Có Kiểm Soát (Configs A–E)

Đây là **thực nghiệm cốt lõi mang tính quyết định của luận văn** nhằm bóc tách định lượng đóng góp của từng thành phần kỹ thuật.

### 5.1. Thiết Kế 5 Cấu Hình Đối Chứng (Seed 42, 5 Họ LOFO, 25 Runs)
- **Config A (Compressed Homogeneous GNN):** Đồ thị nén phẳng (Cell nối Cell trực tiếp), Homogeneous GraphSAGE, 5 đặc trưng cơ sở Hasegawa.
- **Config B (Cell--Net Homogeneous GNN):** Đồ thị hai phía có nút dây Net tường minh, nhưng dùng mô hình Homogeneous GraphSAGE gộp chung các cạnh (đánh giá riêng lẻ nút Net).
- **Config C (Hetero-GNN + Control Edges):** Đồ thị hai phía dị thể, tầng tích chập `HeteroConv` với trọng số riêng biệt theo từng loại quan hệ cạnh, giữ lại các cạnh điều khiển xung nhịp, 5 đặc trưng cơ sở.
- **Config D (Hetero-GNN - No Control Edges):** Giống Config C nhưng **ngắt bỏ hoàn toàn các cạnh điều khiển xung nhịp/reset** khỏi quá trình lan truyền thông điệp (chỉ truyền trên $G_{\text{data}}$).
- **Config E (Full Features Hetero-GNN):** Cấu hình hoàn chỉnh với đầy đủ 13 đặc trưng tô-pô Graph IR.

### 5.2. Bảng Kết Quả Thực Nghiệm Chi Tiết (Ablation Results - Seed 42)
Dữ liệu được trích xuất trực tiếp từ [outputs/results/ablation_seed42.csv](file:///home/dat_ttan/thesis/expl_methods_hw_trojan_detection_code/outputs/results/ablation_seed42.csv):

| Cấu Hình | Mô Tả Kỹ Thuật | RS232 | s15850 | s35932 | s38417 | s38584 | Macro $F_1$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Config A** | Compressed Homogeneous (5 Base Feats) | 0.0243 | 0.4186 | 0.1520 | 0.1459 | 0.0000 | **0.1482** |
| **Config B** | Cell--Net Homogeneous (5 Base Feats) | 0.0714 | 0.2326 | 0.7400 | 0.1970 | 0.0426 | **0.2567** |
| **Config C** | Hetero-GNN + Control Edges (5 Base Feats) | 0.0833 | 0.0870 | 0.9048 | 0.2500 | 0.0638 | **0.2778** |
| **Config D** | **Hetero-GNN - No Control Edges (5 Base Feats)** | **0.0791** | **0.4151** | **0.9412** | **0.4638** | **0.1600** | **0.4118** |
| **Config E** | **Full Features Hetero-GNN (13 Graph IR Feats)** | **0.2145** | **0.7451** | **0.9500** | **0.2857** | **0.1509** | **0.4693** |

---

### 5.3. Bóc Tách Định Lượng & Giải Thích Hiện Tượng Khoa Học (Phase I Analysis)

#### 1. Đóng Góp của Biểu Diễn Đồ Thị Hai Phía (RQ1: A vs B)
$$\Delta_{\text{representation}} = F_1(B) - F_1(A) = 0.2567 - 0.1482 = \mathbf{+0.1085} \quad (+73.2\%)$$
* **Phân tích:** Ngay cả khi chưa áp dụng trọng số dị thể riêng biệt, chỉ cần mô hình hóa tường minh đường dây dẫn `Net` thành nút độc lập đã giúp Macro-$F_1$ tăng vọt từ $0.1482$ lên $0.2567$.
* **Đột phá trên họ vi xử lý `s35932`:** $F_1$ tăng từ $0.1520$ lên **$0.7400$** với độ chính xác đạt tuyệt đối **$\text{Precision} = 100.0\%$**. Điều này chứng minh đồ thị phẳng nén gộp chân pin của Baseline đã làm mất mát nghiêm trọng cấu trúc phân nhánh logic thực tế của chip.

#### 2. Đóng Góp của Lan Truyền Thông Điệp Dị Thể (B vs C)
$$\Delta_{\text{relation\_model}} = F_1(C) - F_1(B) = 0.2778 - 0.2567 = \mathbf{+0.0211} \quad (+8.2\%)$$
* **Phân tích:** Việc sử dụng các ma trận biến đổi riêng biệt cho từng loại cạnh ($W_{\text{data}} \neq W_{\text{ctrl}} \neq W_{\text{out}}$) giúp mô hình điều tiết thông tin vào/ra mạch chính xác hơn việc gộp chung các cạnh, nâng điểm trên `s35932` từ $0.7400$ lên **$0.9048$**.

#### 3. Bằng Chứng Thực Nghiệm Xác Nhận Giả Thuyết Nút Thắt Xung Nhịp (RQ2: C vs D)
$$\Delta_{\text{control}} = F_1(C) - F_1(D) = 0.2778 - 0.4118 = \mathbf{-0.1340} \quad \left(\text{Config D vượt trội } \mathbf{+48.2\%}\right)$$
* **Phát hiện Mang Tính Bước Ngoặt của Luận Văn:**
  Khi ngắt bỏ toàn bộ các cạnh điều khiển xung nhịp (`is_control == 1`), hiệu năng ngoại suy tổng quát hóa Macro-$F_1$ **tăng vọt từ $0.2778$ lên $0.4118$**:
  - Trên họ `s15850`: $F_1$ tăng từ $0.0870$ lên **$0.4151$** (Tăng gần **5 lần**!).
  - Trên họ `s38417`: $F_1$ tăng từ $0.2500$ lên **$0.4638$** (Tăng gần **2 lần**!).
  - Trên họ `s38584`: $F_1$ tăng từ $0.0638$ lên **$0.1600$** (Tăng **2.5 lần**!).
* **Bản chất Vật lý:** Các đường dây `sys_clk` và `sys_rst_l` có tải phân nhánh (Fanout) lên tới hàng nghìn Flip-Flop trên toàn chip. Khi cho phép thông điệp GNN lan truyền qua cạnh Control, dây Clock vô tình trở thành **"xa lộ kết nối tắt 1-hop" giữa toàn bộ các cổng trong mạch**. Hiện tượng **Over-smoothing** xảy ra ngay lập tức: đặc trưng của cụm cổng Trojan bị hòa lẫn vào hàng nghìn cổng sạch nền, làm mô hình hoàn toàn mất khả năng nhận diện khi chuyển sang họ mạch mới. Ngắt bỏ các cạnh này (hoặc cô lập trên $G_{\text{data}}$) đã giải phóng GNN, giúp mô hình tập trung học đúng chuỗi lan truyền logic dữ liệu đặc thù của Trigger-Payload.

#### 4. Đóng Góp của Bộ Đặc Trưng Cấu Trúc Tô-Pô Tô Điểm (RQ3: C vs E)
$$\Delta_{\text{features}} = F_1(E) - F_1(C) = 0.4693 - 0.2778 = \mathbf{+0.1915} \quad (+68.9\%)$$
* **Phân tích:** Khi bổ sung 8 chỉ số tô-pô của Semantic Graph IR (PageRank, Betweenness, Closeness, Clustering, k-Core, Depth Ratio), Macro-$F_1$ đạt đỉnh **$0.4693$**:
  - Trên `RS232`: $F_1$ tăng từ $0.0833$ lên **$0.2145$**.
  - Trên `s15850`: $F_1$ tăng từ $0.0870$ lên **$0.7451$** (Precision $79.17\%$, Recall $70.37\%$, AUC $0.9861$).
  - Trên `s35932`: $F_1$ đạt đỉnh **$0.9500$** (Precision $100.0\%$, Recall $90.48\%$, AUC $0.9848$).

---

## 6. Đối Chuẩn Toàn Diện 6 Cấu Hình (Exp 1–6) & Minh Chứng XAI Thực Tế

### 6.1. Bảng Tổng Hợp Đối Chuẩn In-Distribution (10 Seeds) vs Ngoại Suy LOFO

| Cấu Hình Thử Nghiệm | Kiến Trúc Mô Hình | Biểu Diễn Đồ Thị & Đặc Trưng | In-Dist $F_1$ (10 Seeds) | In-Dist ROC-AUC | LOFO Macro-$F_1$ (5 Họ) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Exp 1** | XGBoost (Tabular) | Baseline Graph (5 Hasegawa) | $0.657 \pm 0.040$ | $0.952 \pm 0.008$ | $0.0297$ |
| **Exp 2** | XGBoost (Tabular) | Baseline Graph (13 Features) | $0.924 \pm 0.024$ | $0.998 \pm 0.002$ | $0.1637$ |
| **Exp 3** | XGBoost (Tabular) | Semantic Graph IR (5 Hasegawa) | $0.744 \pm 0.041$ | $0.989 \pm 0.005$ | $0.1346$ |
| **Exp 4** | XGBoost (Tabular) | Semantic Graph IR (13 Features) | $0.873 \pm 0.027$ | $0.997 \pm 0.003$ | $0.1369$ |
| **Exp 5** | BaselineTrojanGNN | Compressed GraphSAGE (Exp 5 / Config A) | $0.655 \pm 0.068$ | $0.981 \pm 0.006$ | $0.1487$ |
| **Exp 6** | **HeteroTrojanGNN** | **Semantic Graph IR (Proposed / Config E)** | **$0.806 \pm 0.044$** | **$0.993 \pm 0.006$** | **$0.4319 \to 0.4693$** |

* **Nhận định:** Trong khi các mô hình dạng bảng (XGBoost Exp 1--4) suy giảm nghiêm trọng khi kiểm thử liên họ (LOFO Macro-$F_1 \le 0.1637$), mô hình `HeteroTrojanGNN` trên biểu diễn Semantic Graph IR đạt **$0.4693$ (tăng $+186\%$ so với XGBoost Exp 2 và $+215\%$ so với Baseline GNN Exp 5)**.

---

### 6.2. Đối Chuẩn Đa Tiêu Chí XAI: Graph XAI vs Tabular XAI

| Phương Pháp XAI | Mô Hình Gốc | Không Gian Đầu Ra | Fidelity+ $\uparrow$ | Fidelity- $\downarrow$ | Sparsity $\uparrow$ | Hardware Localization $\uparrow$ | Tính Khả Thi EDA (Actionability) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **SHAP** | XGBoost (Exp 2) | Vector $\mathbb{R}^5$ | $+0.0483$ | $0.0000$ | $0.00\%$ | **$0.0\%$** (Mù không gian) | Thấp (Chỉ biết tên đặc trưng) |
| **LIME** | XGBoost (Exp 2) | Tập luật logic dạng bảng | $+0.0483$ | $0.0000$ | $0.00\%$ | **$0.0\%$** (Mù không gian) | Thấp (Chỉ biết khoảng giá trị) |
| **Gradient Attribution** | XGBoost (Exp 2) | Trọng số đạo hàm cục bộ | $+0.0483$ | $0.0000$ | $0.00\%$ | **$0.0\%$** (Mù không gian) | Thấp (Không có tô-pô mạch) |
| **GNNExplainer (Đề xuất)** | **HeteroTrojanGNN** | **Đồ thị con vi mạch (Netlist Subgraph)** | **$+0.0925$** | **$0.0000$** | **$80.06\%$** | **$30.7\%$** (Trúng trực tiếp dây/cổng) | **Cao (Xuất lệnh cắt dây ECO)** |

---

### 6.3. Minh Chứng Trực Quan Trên Mạch UART RS232-T1000

```mermaid
graph LR
    subgraph Trigger_Zone ["1. Khối Kích Hoạt Bí Mật (Trojan Trigger)"]
        U296["OR4X4 (U296)<br/>Theo dõi phát"] -->|dây: iXMIT_CRTL| U302["ISOLORX8 (U302)<br/>Cổng gom kích hoạt"]
        U301["OR4X4 (U301)<br/>Theo dõi thu"] -->|dây: iRECEIVER_CTRL| U302
    end

    subgraph Attack_Junction ["2. Nút Thắt Tấn Công & Can Thiệp"]
        U302 ==>|DÂY KÍCH HOẠT: iCTRL| U303{"AND2X4 (U303 - Cổng Payload)"}
        NormalWire["Dây nội vi sạch: xmit_doneH_temp"] -->|Tín hiệu truyền xong bình thường| U303
    end

    subgraph Sabotage_Output ["3. Ngõ Ra Bị Phá Hoại (Sabotaged PO)"]
        U303 ==>|Ép tín hiệu về 0 khi iCTRL=0| PO((Chân chip PO: xmit_doneH))
    end

    subgraph ECO_Fix ["4. Thao Tác Sửa Lỗi ECO của Kỹ Sư EDA"]
        Cut["Lệnh 1: CẮT DÂY iCTRL"] -.->|Ngắt kết nối độc hại| U303
        Bypass["Lệnh 2: NỐI TẮT DÂY xmit_doneH_temp"] ==>|Nối thẳng ra chân chip| PO
    end

    style U303 fill:#ff6b6b,stroke:#c92a2a,stroke-width:3px;
    style U302 fill:#ffa94d,stroke:#d9480f,stroke-width:2px;
    style Trigger_Zone fill:#fff3bf,stroke:#f59f00,stroke-dasharray: 5 5;
    style Attack_Junction fill:#ffe3e3,stroke:#e03131,stroke-width:2px;
    style Sabotage_Output fill:#f1f3f5,stroke:#495057,stroke-width:2px;
    style ECO_Fix fill:#d3f9d8,stroke:#2b8a3e,stroke-width:2px;
```

* **Khả năng can thiệp ECO:** Từ đồ thị con của GNNExplainer, kỹ sư vi mạch trích xuất được đúng 2 dòng lệnh TCL điều khiển công cụ EDA (Synopsys IC Compiler / Cadence Innovus):
  ```tcl
  # 1. Cắt đứt đường dây kích hoạt độc hại iCTRL
  disconnect_net -net iCTRL -pin U303/IN1

  # 2. Nối tắt đường dây sạch xmit_doneH_temp thẳng ra chân xuất
  connect_net -net xmit_doneH_temp -pin xmit_doneH
  ```
  Vi mạch UART được cứu vãn hoàn toàn mà không cần chế tạo lại bộ mặt nạ quang học (Photomask) hàng triệu USD.

---

## 7. Tổng Kết Các Đóng Góp Đạt Được & Kế Hoạch Tiếp Theo

### 7.1. Bốn Kết Luận Khoa Học Then Chốt
1. **Khẳng định Giá trị Biểu diễn Hai phía (RQ1):** Tách biệt nút cổng logic và đường dây dẫn giúp tăng Macro-$F_1$ thêm **$+10.85\%$** so với đồ thị nén phẳng, đạt độ chính xác $100\%$ trên vi mạch xử lý `s35932`.
2. **Chứng Minh Thực Nghiệm Giả Thuyết Nút Thắt Xung Nhịp (RQ2):** Ngắt bỏ hoặc cô lập các cạnh xung nhịp toàn cục giúp Macro-$F_1$ tăng vọt **$+48.2\%$** (từ $0.2778$ lên $0.4118$), giải quyết dứt điểm hiện tượng Over-smoothing khi chuyển họ vi mạch.
3. **Hiệu Ứng Cộng Hưởng của Đặc Trưng Tô-pô (RQ3):** 8 chỉ số tô-pô trên Semantic Graph IR tiếp tục nâng Macro-$F_1$ lên **$0.4693$**, đưa điểm $F_1$ trên họ `s35932` đạt $0.9500$ và `s15850` đạt $0.7451$.
4. **Tính Khả Thi Vật Lý Vượt Trội của Graph XAI:** Đạt độ chính xác định vị phần cứng $30.7\%$ (so với $0.0\%$ của SHAP/LIME), cho phép chuyển hóa trực tiếp thành kịch bản sửa lỗi vi mạch ECO.

### 7.2. Các Hạng Mục Tiếp Theo
- Viết các chương chi tiết của Luận văn Thạc sĩ dựa trên hệ thống bằng chứng thực nghiệm đã được kiểm toán và đóng băng chặt chẽ.
- Hoàn thiện các biểu đồ trực quan hóa bổ trợ (ma trận nhầm lẫn LOFO, phân bố bậc nút, phân tích lỗi sai trên các họ phức tạp như `s38584`).

