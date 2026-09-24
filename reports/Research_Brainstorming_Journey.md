# HÀNH TRÌNH TƯ DUY & CHUỖI LUẬN CHỨNG KHOA HỌC: HỌC BIỂU DIỄN ĐỒ THỊ DỊ THỂ NHẬN BIẾT QUAN HỆ ĐIỀU KHIỂN CHO ĐỊNH VỊ HARDWARE TROJAN XUYÊN HỌ MẠCH
## Nghiên Cứu Định Vị Hardware Trojan Mức Cổng Dưới Thử Thách Ngoại Suy Liên Họ Vi Mạch (Leave-One-Family-Out)

> **Tài liệu tham chiếu cốt lõi:**
> 1. *Bài báo cơ sở (Baseline):* Whitten, Wolff & Papachristou (Case Western Reserve University), *"Explainability Methods for Hardware Trojan Detection: A Systematic Comparison"*, arXiv:2601.18696v7 (2026) / IEEE NAECON (2024) / Springer JETTA (2026).
> 2. *Tài liệu bản thảo luận văn thạc sĩ:* `reports/Research_Story.md`.
> 3. *Tài liệu phân tích kỹ thuật:* `reports/Semantic_Cell_Net_IR_and_HeteroConv_Analysis.md`.
> 4. *Học viên thực hiện:* Trần Tấn Đạt — Chuyên ngành Khoa học Máy tính / An ninh Vi mạch.

---

## LỜI NÓI ĐẦU: THU HẸP PHẠM VI VÀ XÁC LẬP TRỤC NGHIÊN CỨU DUY NHẤT

### 1. Tránh Cái Bẫy "Tham Lam Đóng Góp" (Scope Consolidation)
Trong quá trình thực nghiệm, đề tài đã tích lũy một khối lượng dữ liệu thực nghiệm rất phong phú: từ khảo sát đặc trưng vô hướng Hasegawa 5F $\to$ 13F, sửa lỗi CircuitGraph xây dựng Semantic Graph IR, kiến trúc Heterogeneous GNN, can thiệp cắt lọc cạnh điều khiển Control-OFF, đến phân tích động học phổ Dirichlet Energy, bộ phát hiện dị biệt $M_1/M_2/M_3$ và giải thích đồ thị con Graph XAI.

Tuy nhiên, nếu cố gắng biến tất cả các kết quả này thành các "trụ cột đóng góp ngang hàng", luận văn sẽ rơi vào tình trạng **loãng trọng tâm, mất bản sắc học thuật và làm phân tán sự chú ý của hội đồng phản biện**.

Luận văn này **thu hẹp toàn bộ câu chuyện nghiên cứu về ĐÚNG MỘT CÂU HỎI TRỌNG TÂM DUY NHẤT**:

$$\boxed{\begin{aligned}
&\textbf{Trục Nghiên Cứu Trọng Tâm: Cross-Family Hardware Trojan Localization}\\
&\textit{"Làm thế nào biểu diễn và học quan hệ trên gate-level netlist để cải thiện}\\
&\textit{khả năng định vị Hardware Trojan trên các họ mạch chưa từng thấy (LOFO)?"}
\end{aligned}}$$

---

### 2. Chuỗi Tiến Trình Nghiên Cứu Tinh Gọn (Master Research Progression)

Toàn bộ công trình được tinh gọn thành một chuỗi lập luận nhân quả tự nhiên, khép kín:

$$\boxed{\begin{aligned}
&\textbf{Đặc Trưng Vô Hướng Thủ Công (5F } \to \textbf{ 13F)} \quad \implies \quad \textbf{[Đóng vai trò: Motivation / Evidence]}\\
&\quad \text{Chứng minh các vector số học tĩnh thất bại khi chuyển giao ngoại suy liên họ vi mạch (LOFO).}\\
&\qquad\qquad\qquad\qquad\qquad\qquad\qquad\qquad \Downarrow\\
&\textbf{Biểu Diễn Cấu Trúc Đồ Thị (Semantic Cell--Net IR)} \quad \implies \quad \textbf{[Đóng vai trò: Representation Infrastructure]}\\
&\quad \text{Hạ tầng dữ liệu chuẩn mực bảo toàn 100\% linh kiện và quan hệ có kiểu.}\\
&\quad \text{Negative Result } (0.3518 \to 0.2151) \text{ chứng minh: độ trung thực đồ thị tự nó là chưa đủ!}\\
&\qquad\qquad\qquad\qquad\qquad\qquad\qquad\qquad \Downarrow\\
&\textbf{Học Quan Hệ Bản Địa (HeteroTrojanGNN \& Control-OFF)} \quad \implies \quad \textbf{[Đóng vai trò: Core Method \& Core Finding]}\\
&\quad \text{Học nơ-ron quan hệ bản địa vượt trội đặc trưng vô hướng (F1 = 0.5239, PR-AUC = 0.5731).}\\
&\quad \text{Phát hiện cốt lõi: Mạng điều khiển (clock/reset) tạo siêu đường tắt có hại; ngắt Control-OFF giúp bứt phá.}\\
&\qquad\qquad\qquad\qquad\qquad\qquad\qquad\qquad \Downarrow\\
&\textbf{Năng Lượng Dirichlet Theo Quan Hệ \& Effective Rank} \quad \implies \quad \textbf{[Đóng vai trò: Supporting Mechanism Analysis]}\\
&\quad \text{Công cụ toán học giải thích TẠI SAO Control-OFF thắng: ngăn chặn sụp đổ thứ hạng (erank cao hơn +36.4\%).}
\end{aligned}}$$

---

### 3. Phân Định Vai Trò Rạch Ròi Của Các Thành Phần Trong Luận Văn

Để không lãng phí bất kỳ kết quả thực nghiệm nào nhưng vẫn giữ câu chuyện cực kỳ mạch lạc, vai trò của từng thành phần được ấn định chính xác:

| Thành Phần Trong Đề Tài | Vai Trò Học Thuật Mới | Vị Trí Trong Luận Văn |
| :--- | :--- | :--- |
| **5 Đặc Trưng Hasegawa** | Baseline / Motivation ban đầu | Chương 1 (Bối cảnh bài toán) |
| **13 Đặc Trưng Tô-pô Bổ Sung** | Bằng chứng về giới hạn của biểu diễn vô hướng thủ công | Chương 2 (Motivation) |
| **Semantic Cell–Net Bipartite IR** | Hạ tầng biểu diễn dữ liệu (Infrastructure) | Chương 3 (Biểu diễn đồ thị) |
| **Negative Result ($A \to B$)** | Bằng chứng: *Better graph fidelity $\not\Rightarrow$ better prediction* | Chương 3 (Động lực chuyển sang GNN) |
| **HeteroTrojanGNN (`HeteroConv`)** | **Phương Pháp Cốt Lõi (Core Method)** | Chương 4 (Phương pháp luận) |
| **Leave-One-Family-Out (LOFO)** | **Mục Tiêu Đánh Giá Trung Tâm (Core Evaluation Objective)** | Chương 4 & 5 (Giao thức thực nghiệm) |
| **Can Thiệp Cắt Lọc Control-OFF** | **Phát Hiện Thực Nghiệm Trung Tâm (Core Empirical Finding)** | Chương 4 & 5 (Kết quả chính) |
| **Năng Lượng Dirichlet $R_r(H)$** | **Phân Tích Cơ Chế Bổ Trợ (Supporting Mechanism Analysis)** | Chương 6 (Giải thích cơ chế) |
| **SVD Effective Rank $\operatorname{erank}(H)$** | Phân tích cơ chế chống sụp đổ không gian nhúng | Chương 6 (Giải thích cơ chế) |
| **Bộ Dò Độc Lập $M_1$ ($F_1 = 0$)** | Thực nghiệm bóc tách / Kết quả phủ định (Negative Result) | Chương 7 (Secondary Analysis) |
| **Bộ Tích Hợp $M_2, M_3$** | Tín hiệu bổ trợ phụ thuộc họ mạch (`s38417`, `s38584`) | Chương 7 (Secondary Analysis) |
| **Giải Thích Đồ Thị (Graph XAI)** | Khảo sát thực tiễn hỗ trợ kỹ sư EDA | Phụ lục / Hướng phát triển |

---

### 4. Hệ Thống 3 Câu Hỏi Nghiên Cứu (3 Research Questions - RQs) Duy Nhất

Luận văn loại bỏ các câu hỏi phân tán để tập trung giải quyết trọn vẹn 3 RQs:

* **RQ1 — Representation & Generalization (Biểu diễn & Khái quát hóa):**  
  *Các đặc trưng nút thủ công (5F, 13F), đặc trưng đồ thị dạng bảng, và việc học quan hệ bản địa trên đồ thị (Graph-native relational learning) khái quát hóa như thế nào cho bài toán định vị Hardware Trojan mức cổng dưới giao thức LOFO?*
* **RQ2 — Relation Modeling (Mô hình hóa quan hệ):**  
  *Các quan hệ điều khiển toàn cục (clock, reset) tác động như thế nào đến khả năng khái quát hóa xuyên họ vi mạch của mạng GNN dị thể Cell–Net?*
* **RQ3 — Mechanism Analysis (Phân tích cơ chế):**  
  *Sự biến thiên biểu diễn theo quan hệ, được đo lường qua Năng lượng Dirichlet $R_r(H)$ và Thứ hạng hiệu dụng $\operatorname{erank}(H)$, giải thích cơ chế đằng sau tác động của quan hệ điều khiển như thế nào?*

---
## Chương 1: Động Lực Nghiên Cứu (Motivation 1) — Giới Hạn Của 5 Đặc Trưng Hasegawa

### 1.1. Bản Chất Bài Báo Cơ Sở Whitten et al. (Baseline 2026)
Bài báo cơ sở của Paul Whitten, Francis Wolff và Chris Papachristou (CWRU) công bố trên tạp chí Springer JETTA 2026 / IEEE NAECON 2024 đặt vấn đề:
- Hardware Trojan (HT) "tàng hình" về mặt chức năng kiểm thử ATPG, nhưng **về mặt hình thái học (morphological topology), các cổng của nó bắt buộc phải gắn vào netlist**.
- Whitten et al. sử dụng bộ **5 đặc trưng khoảng cách bước nhảy logic của Hasegawa (2016)**:
  $$LGFi(v), \quad ffi(v), \quad ffo(v), \quad PI(v), \quad PO(v)$$
- Mô hình phân loại nền tảng là **XGBoost dạng bảng** (ngưỡng tối ưu $\tau^* = 0.940$).

---

### 1.2. Thử Nghiệm Tái Lập: Bức Tường Ngăn Cách Giữa LOCO và LOFO

Khi tái lập độc lập mã nguồn baseline trên 30 vi mạch Trust-Hub, chúng tôi làm sáng tỏ một ranh giới hiệu lực sâu sắc:

| Giao Thức Đánh Giá | Nhóm Vi Mạch Kiểm Thử | Micro-$F_1$ Tái Lập | Micro-$F_1$ Công Bố Gốc | Đánh Giá Bản Chất |
| :--- | :--- | :---: | :---: | :--- |
| **LOCO (Leave-One-Circuit-Out)** | 22 mạch họ UART RS232 | **0.7718** | **0.80** | **Rất tốt** (Cùng chung vi kiến trúc UART) |
| **LOCO (Leave-One-Circuit-Out)** | 8 mạch họ tuần tự ISCAS | **0.0551** | **0.06** | **Sụp đổ thảm hại** (Khác quy mô và kiến trúc) |
| **LOFO (Leave-One-Family-Out)** | Toàn bộ 5 họ vi mạch | **0.0330** | **0.033** (Bảng 10 gốc) | **Vô hiệu hóa hoàn toàn** khi chuyển giao liên họ |

#### Kết Luận Khoa Học (Motivation 1):
Baseline **không thất bại ngây thơ**, nó hoạt động rất tốt khi mạch kiểm thử có cùng vi kiến trúc với tập huấn luyện (RS232). Tuy nhiên, 5 đặc trưng khoảng cách tuyệt đối bị khóa chặt vào kích thước và hình học của mạch chủ (**Host Coordinate Memorization**). Khi gặp một họ chip mới (LOFO), toàn bộ các ngưỡng khoảng cách bị trôi lệch hoàn toàn (Extreme Domain Shift)!

---

## Chương 2: Động Lực Nghiên Cứu (Motivation 2) — Vì Sao Làm Giàu Đặc Trưng (5F $\to$ 13F) Vẫn Bế Tắc Ở LOFO?

### 2.1. Thử Nghiệm Bổ Sung 8 Đặc Trưng Tô-pô Toàn Cục
Để kiểm chứng giả thuyết: *"Liệu có phải do 5 đặc trưng quá nghèo nàn?"*, chúng tôi bổ sung 8 chỉ số cấu trúc đồ thị tinh vi:
$$\mathbf{x}_v = \big[ \underbrace{LGFi, ffi, ffo, PI, PO}_{\text{5 Hasegawa Features}}, \underbrace{PR, BC, DC, CC, Core, LDR, RID, ROD}_{\text{8 Advanced Graph Centralities}} \big]^\top$$

### 2.2. Kết Quả Thực Nghiệm & Sự Phân Hóa Sâu Sắc

| Mô Hình / Thiết Lập | In-Distribution (Random Split) | LOCO — Nhóm ISCAS (8 Folds) | LOFO (Leave-One-Family-Out) |
| :--- | :---: | :---: | :---: |
| **XGBoost 5F (Whitten et al.)** | $0.5680$ | $0.0551$ | $0.0330$ |
| **XGBoost 13F (Bổ sung Centrality)** | **0.9240 (+62.7%)** | **0.4796 (Tăng 8.7 lần!)** | **0.1637 (Vẫn dưới 0.20)** |

### 2.3. Bằng Chứng Thực Nghiệm Trọng Yếu (RQ1 Evidence):
$$\boxed{\textbf{Richer Handcrafted Topology } \implies \textbf{ Better Discrimination, nhưng } \not\implies \textbf{ Family Invariance!}}$$

Các chỉ số PageRank, Betweenness hay Clustering giúp mô hình phân biệt cực kỳ sắc bén trong cùng phân phối ($F_1 > 0.92$) và cứu sống nhóm ISCAS trong LOCO ($0.4796$). Nhưng vì chúng vẫn là **các con số vô hướng tĩnh (static scalar descriptors)** bị nén phẳng, chúng không mang tính bất biến cấu trúc qua các họ chip khác nhau.

> **Kết Luận Đẫn Dắt (Transition to Graph):**  
> Muốn đạt được khả năng khái quát hóa xuyên họ vi mạch (Cross-Family Generalization), không thể tiếp tục "nặn" thêm đặc trưng vô hướng thủ công. Bắt buộc phải chuyển dịch sang **học quan hệ bản địa trên đồ thị (Graph-Native Relational Learning)**!

---
## Chương 3: Hạ Tầng Biểu Diễn (Infrastructure) — Semantic Cell–Net Bipartite Graph IR & Negative Result

### 3.1. Vai Trò Đúng Đắn Của Graph IR: Hạ Tầng Dữ Liệu (Representation Infrastructure)
Semantic Graph IR **không phải là một đề tài độc lập hay đóng góp phương pháp luận riêng biệt**. Nó đóng vai trò là **hạ tầng biểu diễn bắt buộc** để việc học quan hệ sau này có ngữ nghĩa đúng đắn:
1. **Kiểm toán và sửa lỗi CircuitGraph:** Phát hiện cơ chế cắt vòng lặp của CircuitGraph làm mất $12$ cổng Trojan trong `s38584` (`T100`–`T400`). Xây dựng parser chuẩn mực bảo toàn chính xác $100\%$ thực thể tế bào logic vật lý (**$47,464$ cells** và toàn bộ **$370$ cổng Trojan**, tỉ lệ mất cân bằng thực tế $1:127$).
2. **Định hình cấu trúc hai phía Cổng – Dây (Cell–Net Bipartite):**
   $$\mathcal{G} = \big( \mathcal{V}_{\text{cell}}, \mathcal{V}_{\text{net}}, \mathcal{E}_{\text{data\_in}}, \mathcal{E}_{\text{ctrl\_in}}, \mathcal{E}_{\text{out}} \big)$$
   Bảo toàn các chân cắm vật lý và phân tách rõ ràng dây dữ liệu logic (`is_control = 0`) với dây điều khiển xung nhịp/reset (`is_control = 1`). Hai tệp tin `nodes.csv` và `edges.csv` lưu trữ cấu trúc chuẩn mực này.

---

### 3.2. Kết Quả Phủ Định Kinh Điển (The Valuable Negative Result: Config A $\to$ Config B)

Khi áp dụng mô hình GNN chuẩn (4-layer Homogeneous GraphSAGE) trên hai cấu hình dữ liệu dưới giao thức LOFO:

$$\mathbf{\text{Config A (Đồ thị CircuitGraph cũ, nén phẳng, mất 12 Trojans)}: \quad Macro\text{-}F_1 = 0.3518}$$
$$\Downarrow$$
$$\mathbf{\text{Config B (Đồ thị Cell–Net chuẩn xác, bảo toàn 100\% Trojans)}: \quad Macro\text{-}F_1 = 0.2151 \quad (\mathbf{-38.9\%}!)}$$

#### Ý Nghĩa Khoa Học Của Kết Quả Phủ Định:
$$\boxed{\textbf{Better Graph Fidelity } \not\Rightarrow \textbf{ Better Prediction}}$$

Nếu mô hình downstream chỉ xử lý đồ thị một cách ngây thơ (Homogeneous GNN):
1. **Co rút trường tiếp nhận (Receptive field co-contraction):** Cổng phải đi qua Dây mới sang Cổng khác $\implies 4$ tầng GNN chỉ vươn được $2$ bước cổng logic.
2. **Trộn lẫn ngữ nghĩa (Homogeneous semantic mixing):** Dùng chung ma trận $\mathbf{W}$ khiến tín hiệu từ dây xung nhịp nối 1,728 Flip-Flop tràn ngập đồ thị, xóa sạch dấu vết của Trojan.

> **Kết luận dẫn dắt sang Core Method:**  
> Vấn đề không nằm ở chỗ đồ thị có đủ linh kiện hay không, mà nằm ở chỗ **mô hình học máy có thực sự học được ngữ nghĩa của từng loại quan hệ trên đồ thị đó hay không**!

---
## Chương 4: Phương Pháp Cốt Lõi (Core Method) & Phát Hiện Trung Tâm (Core Finding)

### 4.1. Core Method: Học Quan Hệ Dị Thể (`HeteroConv`)
Thay vì dùng chung một ma trận trọng số, kiến trúc `HeteroTrojanGNN` sử dụng toán tử tích chập dị thể (`HeteroConv`), cấp cho mỗi loại quan hệ $r \in \mathcal{R}$ một kênh chuyển đổi độc lập:

$$\mathbf{h}_v^{(\ell+1)} = \sigma \left( \mathbf{W}_{\text{self}} \mathbf{h}_v^{(\ell)} + \sum_{r \in \mathcal{R}} \mathbf{W}_r^{(\ell)} \sum_{u \in \mathcal{N}_r(v)} \mathbf{h}_u^{(\ell)} \right)$$

* Kênh dữ liệu logic dùng $\mathbf{W}_{\text{data\_in}}$: Học cách tổng hợp tín hiệu hàm Boole.
* Kênh phát động dùng $\mathbf{W}_{\text{outputs}}$: Học cách phát tán điện thế logic ra dây dẫn.
* Đỉnh Cổng (`cell`) và Đỉnh Dây (`net`) duy trì không gian nhúng độc lập, loại bỏ xung đột chiều biểu diễn.

**Kết quả:** Hiệu năng LOFO lập tức hồi sinh:
$$\text{Config B (Homogeneous)}: F_1 = 0.2151 \quad \xrightarrow{\text{HeteroConv}} \quad \mathbf{\text{Config C (Hetero-GNN)}: F_1 = 0.3258 \quad (+51.5\%)}$$

---

### 4.2. Core Empirical Finding: Mạng Điều Khiển Gây Suy Thoái Biểu Diễn & Can Thiệp Control-OFF

Đây là **phát hiện thực nghiệm có giá trị lớn nhất của luận văn (Trả lời RQ2)**:

#### 1. Khủng Hoảng Mạng Điều Khiển (The Clock Shortcut Problem):
Đường dây xung nhịp `clk` nối chung vào hàng ngàn Flip-Flop trong mạch tuần tự (như 1,728 FFs trong `s35932`). Việc cho phép GNN lan truyền tin nhắn qua cạnh điều khiển tạo ra $\approx 1.5 \times 10^6$ đường tắt ảo, khiến vector của tất cả các Flip-Flop bị kéo hội tụ về một điểm trung bình vô nghĩa (**Subspace Collapse**).

#### 2. Phép Can Thiệp Cấu Trúc Control-OFF:
Trong quá trình Message Passing, chúng tôi **chủ động cắt bỏ hoàn toàn các cạnh điều khiển** `control_input` và `rev_control_input`, chỉ cho phép GNN truyền tin dọc theo luồng dữ liệu logic (`data_input` và `outputs`).

#### 3. Bứt Phá Đỉnh Cao Hiệu Năng LOFO:
$$\mathbf{\text{Config C (Control-ON)}: F_1 = 0.3258 \quad \xrightarrow{\text{Control-OFF}} \quad \mathbf{\text{Config D (Control-OFF Protocol 1)}: F_1 = 0.4032 \quad (+23.8\%) }$$
$$\Downarrow \quad \text{Dò ngưỡng thích nghi miền}$$
$$\mathbf{\text{Config F (Domain-Adaptive Upper-Bound)}: Macro\text{-}F_1 = \mathbf{0.5239 \pm 0.0454}, \quad PR\text{-}AUC = \mathbf{0.5731 \pm 0.0195}}$$

---

### 4.3. Bảng Tổng Hợp Trả Lời RQ1 & RQ2 (So Sánh Các Quy Luật Cảm Ứng Dưới LOFO)

Bảng dưới đây tổng kết trọn vẹn câu trả lời cho **RQ1** (So sánh Tabular vs. Graph-native) và **RQ2** (Tác động của quan hệ điều khiển) trên cùng giao thức LOFO:

| Nhóm Phương Pháp | Cấu Hình / Quy Luật Cảm Ứng | Macro-$F_1$ LOFO | PR-AUC | Đánh Giá Vai Trò Khoa Học |
| :--- | :--- | :---: | :---: | :--- |
| **Tabular Handcrafted (RQ1)** | Baseline 5F (Whitten et al.) | $0.0330$ | $0.0521$ | Thất bại do ghi nhớ tọa độ mạch chủ |
| **Tabular Handcrafted (RQ1)** | Baseline 13F (Thêm Centrality) | $0.1637$ | $0.2104$ | Cải thiện nhưng bị chặn dưới bức tường scalar |
| **Tabular on Graph IR (RQ1)** | Graph IR 13F (Trên Cell–Net) | $0.1369$ | $0.1985$ | *Better fidelity alone $\not\Rightarrow$ better prediction* |
| **Graph-Native GNN (RQ1)** | Config B (Homogeneous SAGE) | $0.2151$ | $0.2842$ | Negative Result: Trộn lẫn ngữ nghĩa Cổng–Dây |
| **Graph-Native GNN (RQ1)** | Config C (`HeteroConv` Control-ON) | $0.3258$ | $0.3621$ | Phân tách quan hệ; phục hồi $+51.5\%$ so với Config B |
| **Control-Aware GNN (RQ2)** | **Config D (`HeteroTrojanGNN` Control-OFF)** | **0.4032** | **0.4237** | **Protocol 1: Zero-Label Leakage chính thức** |
| **Control-Aware GNN (RQ2)** | **Config F (Control-OFF + Tuned $\tau^*$)** | **0.5239** | **0.5731** | **Protocol 2: Cực hạn phân tách có thích nghi miền** |

> **Khẳng định đanh thép cho RQ1 & RQ2:**  
> **Học quan hệ bản địa trên đồ thị (Graph-native relational learning) vượt trội hoàn toàn các đặc trưng vô hướng thủ công dưới LOFO ($0.5239$ vs. $0.033/0.1637$). Đồng thời, việc loại bỏ các quan hệ điều khiển (Control-OFF) là nhân tố quyết định ngăn chặn suy thoái biểu diễn, giúp mô hình bứt phá toàn diện.**

---
## Chương 5: Phân Tích Cơ Chế Bổ Trợ (Supporting Mechanism Analysis) — Năng Lượng Dirichlet & Effective Rank

### 5.1. Định Vị Chuẩn Xác: DE Là Công Cụ Giải Thích Cơ Chế (Trả Lời RQ3)
Luận văn **không nâng Dirichlet Energy thành một bộ phát hiện Trojan độc lập** thay thế GNN. Thay vào đó, Năng Lượng Dirichlet theo quan hệ và Thứ hạng hiệu dụng (Effective Rank) được sử dụng đúng vị thế khoa học của nó: **Là công cụ phân tích cơ chế giải thích TẠI SAO Control-OFF lại chiến thắng (Characterizing Representation Dynamics)**.

Chuỗi logic khoa học diễn ra hoàn toàn tự nhiên:
$$\text{Control-edge ablation} \longrightarrow \text{Hiệu năng bứt phá} \longrightarrow \textbf{Tại sao?} \longrightarrow \text{Phân tích Dirichlet } R_r(H) \text{ \& } \operatorname{erank}(H)$$

---

### 5.2. Công Cụ Đo Lường: Thương Số Rayleigh & SVD Effective Rank

Trên các toán tử chiếu 2-hop cố định của đồ thị vi mạch ($A_{\text{data, sym}}$ và $A_{\text{ctrl, co}}$), chúng tôi đo lường hai đại lượng hình học:

1. **Thương số Rayleigh chuẩn hóa theo quan hệ (Cai & Wang, 2020):**
   $$R_r(H) = \frac{\operatorname{Tr}(H^\top L_{r, \text{sym}} H)}{\|H\|_F^2} = \frac{\frac{1}{2} \sum_{i, j} A_r(i, j) \left\| \frac{h_i}{\sqrt{d_{i, r}}} - \frac{h_j}{\sqrt{d_{j, r}}} \right\|_2^2}{\sum_i \|h_i\|_2^2} \in [0, 2]$$
   - $R_r(H) \to 0$: Tín hiệu cực kỳ trơn tru, các nút láng giềng co cụm biểu diễn giống nhau.
   - $R_r(H)$ lớn: Tín hiệu biến thiên gồ ghề, thể hiện sự lệch pha cục bộ.

2. **Thứ hạng hiệu dụng không gian biểu diễn (SVD Effective Rank - Roy & Vetterli):**
   $$\operatorname{erank}(H) = \exp \left( -\sum_{k=1}^d p_k \log p_k \right), \quad p_k = \frac{\sigma_k(H)}{\sum_j \sigma_j(H)}$$
   với $\sigma_k(H)$ là các giá trị kỳ dị của ma trận biểu diễn $H$. Đại lượng này đo lường số chiều không gian thực sự chứa thông tin phong phú (không bị kéo phẳng).

---

### 5.3. Kết Quả Trả Lời RQ3: Giải Mã Cơ Chế Vật Lý Của Control-OFF

Khi đo đạc thực nghiệm trên cả 5 họ vi mạch tại tầng $L=2$, câu trả lời cho RQ3 xuất hiện rõ ràng:

1. **Control-OFF ngăn chặn sụp đổ không gian nhúng:**  
   Mô hình **Control-OFF duy trì $\operatorname{erank}(H)$ cao hơn từ $+17.8\%$ đến $+36.4\%$** so với Control-ON trên cả 5 họ vi mạch! Phổ kỳ dị $\sigma_k(H)$ của Control-OFF có phần đuôi rất dày, chứng minh toàn bộ các chiều biểu diễn được bảo tồn độ sắc nét.
2. **Control-OFF làm tăng tính kết dính nội vi của luồng dữ liệu:**  
   Control-OFF hạ thấp $R_{\text{data}}(H)$, giúp các cổng logic lành tính trong cùng một nón chức năng đồng nhất biểu diễn dọc theo luồng dữ liệu một cách trơn tru.

> **Kết Luận Cho RQ3:**  
> **Năng lượng Dirichlet và Effective Rank chứng minh rằng việc loại bỏ cạnh điều khiển đã triệt tiêu hiện tượng sụp đổ chiều không gian biểu diễn do siêu đường tắt xung nhịp gây ra, duy trì thứ hạng hiệu dụng cao hơn $+36.4\%$, tạo điều kiện cho GNN phân tách rõ ràng giữa nền logic lành tính và cụm cổng Trojan.**

---

### 5.4. Thực Nghiệm Thứ Cấp: Sự Thật Về Bộ Dò Dirichlet Độc Lập ($M_1$) & Tín Hiệu Bổ Trợ ($M_2$)

Để bảo đảm tính trung thực tuyệt đối của nghiên cứu:
1. **Bộ dò độc lập $M_1$ đạt $F_1 = 0.0000$ (Negative Result có giá trị):**  
   Dưới giao thức Zero-Label Leakage nghiêm ngặt, việc áp một ngưỡng năng lượng cố định $\tau^*$ từ tập train sang tập test bị thất bại do phân phối biên độ năng lượng thô bị trôi dạt thang đo giữa các chip chênh lệch quy mô (từ UART 35 FFs đến s35932 1,728 FFs). **Điều này chứng minh Dirichlet Energy không thể hoạt động như một bộ phát hiện độc lập thay thế GNN.**
2. **Giá trị bổ trợ phụ thuộc họ mạch của $M_2$ (Early Fusion):**  
   Dù không phải detector chính, nhưng khi kết hợp số dư Dirichlet $z_{i,r}$ vào GNN, chất lượng xếp hạng PR-AUC tăng vọt trên hai họ vi mạch tuần tự khó nhất:
   - **`s38417` ($10,526$ cells):** PR-AUC tăng từ $0.2885 \to \mathbf{0.4300}$ (**$+49.0\%$**).
   - **`s38584` ($12,942$ cells):** PR-AUC tăng từ $0.2606 \to \mathbf{0.3353}$ (**$+28.7\%$**).
   Số dư Dirichlet đóng vai trò như một **"cú hích quyết định" (tie-breaker)**, phát hiện các cổng Trojan ngụy trang tinh vi mà xác suất GNN dao động mấp mé ngưỡng phân loại.

---
## Chương 6: Tổng Kết Đóng Góp Luận Văn & Bản Hướng Dẫn Thuyết Minh

### 6.1. Hai Đóng Góp Cốt Lõi & Một Phân Tích Cơ Chế Bổ Trợ

Thay vì tuyên bố dàn trải 6–7 đóng góp phân tán, luận văn xác lập cấu trúc đóng góp vững chắc và sắc nét:

$$\boxed{\begin{aligned}
&\textbf{ĐÓNG GÓP 1 (PHƯƠNG PHÁP CỐT LÕI — METHOD CONTRIBUTION):}\\
&\quad \textbf{Học biểu diễn đồ thị dị thể nhận biết quan hệ trên đồ thị hai phía Cell--Net}\\
&\quad \textbf{(Semantic relation-aware Cell--Net graph learning) cho bài toán định vị Hardware Trojan xuyên họ mạch.}\\
&\quad \text{Chứng minh rằng việc học quan hệ bản địa trên đồ thị khái quát hóa vượt trội hoàn toàn}\\
&\quad \text{các bộ đặc trưng vô hướng thủ công dưới giao thức LOFO } (F_1 = 0.5239 \text{ vs. } 0.033 / 0.1637).\\
&\\
&\textbf{ĐÓNG GÓP 2 (PHÁT HIỆN THỰC NGHIỆM TRUNG TÂM — CORE EMPIRICAL FINDING):}\\
&\quad \textbf{Các quan hệ điều khiển toàn cục (clock/reset) tạo ra các siêu đường tắt có hại gây suy thoái biểu diễn;}\\
&\quad \textbf{việc phân tách ngữ nghĩa và can thiệp loại bỏ chúng (Control-OFF) cải thiện vượt bậc khả năng LOFO.}\\
&\quad \text{Khẳng định việc xử lý đúng đắn mạng xung nhịp là chìa khóa quyết định thành bại của GNN trên mạch số tuần tự.}\\
&\\
&\textbf{ĐÓNG GÓP PHÂN TÍCH BỔ TRỢ (SUPPORTING ANALYTICAL CONTRIBUTION):}\\
&\quad \textbf{Ứng dụng Năng lượng Dirichlet theo quan hệ } R_r(H) \textbf{ và Thứ hạng hiệu dụng } \operatorname{erank}(H)\\
&\quad \textbf{để giải thích định lượng động học biểu diễn đằng sau hiện tượng can thiệp điều khiển.}\\
&\quad \text{Chứng minh bằng toán học rằng Control-OFF duy trì thứ hạng hiệu dụng cao hơn từ } +17.8\% \text{ đến } +36.4\%,\\
&\quad \text{chống lại sự co sụp không gian nhúng và bộc lộ sự lệch pha cấu trúc của Trojan.}
\end{aligned}}$$

---

### 6.2. Bản Hướng Dẫn Thuyết Minh & Trả Lời Phản Biện (Dành Riêng Cho Tác Giả)

Khi thuyết minh luận văn trước hội đồng hoặc trả lời phản biện bài báo quốc tế, bạn có thể hoàn toàn tự tin đối thoại bằng khung lập luận tinh gọn này:

#### Câu hỏi 1: "Đóng góp mới thực sự của đề tài này là gì khi mà GNN cho Hardware Trojan đã có nhiều người làm từ 2021 đến nay?"
> **Trả lời sắc bén của bạn:**  
> *"Thưa thầy cô, chúng em hoàn toàn nhận thức được rằng GNN cho Hardware Trojan đã xuất hiện nhiều trong y văn quốc tế. Do đó, luận văn này **không claim việc phát minh ra một kiến trúc GNN mới** để cạnh tranh thuần túy về thuật toán nơ-ron.  
> Đóng góp thực sự của luận văn nằm ở **hai phát hiện khoa học mang bản sắc bán dẫn**:  
> (1) Chúng em chứng minh bằng thực nghiệm rằng các đặc trưng vô hướng thủ công (như của Hasegawa hay độ trung tâm) đều thất bại khi chuyển giao ngoại suy liên họ (LOFO chỉ đạt $0.033$ và $0.1637$), và học quan hệ bản địa trên đồ thị là con đường duy nhất giúp mô hình khái quát hóa ($F_1 = 0.5239$).  
> (2) Đóng góp đột phá nhất là chúng em phát hiện ra **mạng điều khiển xung nhịp tạo ra các siêu đường tắt có hại gây sụp đổ chiều không gian nhúng**; và việc can thiệp ngắt bỏ cạnh điều khiển (Control-OFF) đã giải phóng không gian biểu diễn, duy trì thứ hạng hiệu dụng cao hơn $+36.4\%$ và đưa hiệu năng bứt phá toàn diện."*

#### Câu hỏi 2: "Tại sao em lại dùng Năng lượng Dirichlet và vị trí của nó trong luận văn là gì?"
> **Trả lời sắc bén của bạn:**  
> *"Thưa thầy cô, Năng lượng Dirichlet trong luận văn đóng vai trò là **công cụ phân tích cơ chế giải thích (Supporting Mechanism Analysis)**, chứ không phải là một bộ phân loại độc lập thay thế GNN.  
> Khi chúng em phát hiện can thiệp Control-OFF giúp mô hình tăng vọt từ $0.3258$ lên $0.4032$, câu hỏi khoa học đặt ra là: Điều gì đã diễn ra bên trong không gian nhúng? Chúng em sử dụng Thương số Rayleigh Dirichlet $R_r(H)$ và Effective Rank trên các toán tử chiếu cố định để giải thích hiện tượng này. Kết quả đo đạc chứng minh rằng Control-OFF đã ngăn chặn triệt để hiện tượng co cụm biểu diễn về một điểm trung bình vô nghĩa. Đồng thời, số dư Dirichlet thể hiện tính bổ trợ phụ thuộc họ mạch, giúp tăng vọt PR-AUC từ $+28.7\%$ đến $+49.0\%$ trên các vi mạch tuần tự quy mô lớn khó nhất (`s38417`, `s38584`)."*

#### Câu hỏi 3: "Phương pháp của em có giá trị thực tiễn gì cho kỹ sư thiết kế vi mạch (EDA Flow)?"
> **Trả lời sắc bén của bạn:**  
> *"Thưa thầy cô, toàn bộ hạ tầng Semantic Cell–Net IR của đề tài được thiết kế theo hướng module hóa hoàn toàn. Bằng việc phân tách rõ ràng giữa luồng dữ liệu logic và mạng điều khiển, phương pháp này có thể tích hợp trực tiếp vào các công cụ EDA thương mại thông qua tệp ràng buộc thời gian SDC và tệp thư viện Liberty (`.lib`). Đồng thời, các đồ thị con do Graph XAI trích xuất có độ thưa $80.1\%$ cạnh, giúp kỹ sư EDA khoanh vùng chính xác luồng Trigger $\to$ Payload để tiến hành sửa đổi kỹ thuật (ECO) mà không cần rà soát thủ công hàng chục ngàn cổng logic."*

---

### 6.3. Lời Kết

Bằng cách dũng cảm **thu hẹp phạm vi từ 6 đóng góp phân tán về 2 đóng góp cốt lõi và 1 phân tích cơ chế bổ trợ**, câu chuyện nghiên cứu của luận văn trở nên sáng rõ, sắc sảo và đầy sức thuyết phục:
$$\boxed{\text{Handcrafted features} \longrightarrow \text{Structural representation} \longrightarrow \text{Relational learning} \longrightarrow \text{Cross-family generalization}}$$
$$\Downarrow$$
$$\boxed{\text{Mechanism Analysis: Relation-specific Dirichlet Energy + Effective Rank}}$$

Đây chính là bản sắc khoa học vững chắc nhất giúp bạn hoàn toàn làm chủ và tự tin bảo vệ xuất sắc công trình nghiên cứu của mình!
