# CẨM NANG HƯỚNG DẪN VIẾT BÀI BÁO KHOA HỌC: EVIDENCE-FIRST WRITING GUIDE

**Đề tài:** *Control-Aware Heterogeneous Graph Learning for Cross-Family Gate-Level Hardware Trojan Localization*  
**Mục tiêu tài liệu:** Hướng dẫn quy trình viết bài báo từ thực nghiệm (Evidence) đến lập luận (Reasoning) và cốt truyện (Narrative), bảo đảm tính khoa học chặt chẽ, không overclaim, và chuẩn bị sẵn sàng để nộp các hội thảo/tạp chí hàng đầu (IEEE HOST / DAC / DATE / TIFS).

---

## MỤC LỤC
1. [Nguyên Tắc Cốt Lõi: Tách Rời Thứ Tự Viết Và Thứ Tự Đọc](#1-nguyên-tắc-cốt-lõi-tách-rời-thứ-tự-viết-và-thứ-tự-đọc)
2. [Bước 0: Bảng Claim–Evidence Map Khởi Đầu](#2-bước-0-bảng-claimevidence-map-khởi-đầu)
3. [Template Chuẩn Cho MỌI Tiểu Mục Thực Nghiệm (Results Subsection)](#3-template-chuẩn-cho-mọi-tiểu-mục-thực-nghiệm-results-subsection)
4. [Lộ Trình Viết Chi Tiết Từng Phần (Từ Bước 1 Đến Bước 14)](#4-lộ-trình-viết-chi-tiết-từng-phần-từ-bước-1-đến-bước-14)
   * [Giai Đoạn I: Viết Thực Nghiệm (Results-First)](#giai-đoạn-i-viết-thực-nghiệm-results-first)
   * [Giai Đoạn II: Thảo Luận & Phương Pháp (Discussion & Methodology)](#giai-đoạn-ii-thảo-luận--phương-pháp-discussion--methodology)
   * [Giai Đoạn III: Đóng Gói Cốt Truyện (Related Work, Introduction, Abstract)](#giai-đoạn-iii-đóng-gói-cốt-truyện-related-work-introduction-abstract)
5. [Hệ Thống 4 Marker Để Tự Kiểm Toán Khi Viết](#5-hệ-thống-4-marker-để-tự-kiểm-toán-khi-viết)
6. [Kế Hoạch Tác Chiến Ngày Đầu Tiên (Checklist)](#6-kế-hoạch-tác-chiến-ngày-đầu-tiên-checklist)

---

## 1. NGUYÊN TẮC CỐT LÕI: TÁCH RỜI THỨ TỰ VIẾT VÀ THỨ TỰ ĐỌC

Một trong những sai lầm phổ biến nhất của người làm nghiên cứu là: **Viết paper theo đúng thứ tự mà người đọc sẽ đọc**.  
Viết như vậy sẽ dẫn đến hiện tượng: Đặt ra một câu chuyện quá hoành tráng ở Abstract và Introduction, nhưng đến phần Results lại không đủ bằng chứng để chứng minh, dẫn đến bài viết bị Reviewer bắt bẻ và bác bỏ.

### So Sánh Hai Thứ Tự:

```text
THỨ TỰ BẠN NÊN VIẾT (Writing Order):
0. Claim–Evidence Map             ← Khóa chặt bằng chứng, chưa viết văn
1. Experimental Setup (4.1)       ← Viết đầu tiên, mô tả dữ liệu & protocol
2. Baseline Results: 5F ➔ 13F     ← Bắt đầu từ baseline số liệu thật
3. Structural Results: Graph IR   ← So sánh Tabular vs Graph IR
4. Graph Construction / Repair   ← Đánh giá tác động của độ hoàn thiện đồ thị
5. Relational GNN Results         ← Kết quả mô hình GNN
6. Control / Relation Ablation    ← Bóc tách Control-ON vs Control-OFF
7. Dirichlet Energy Analysis      ← Phân tích biểu diễn toán học
8. Discussion / Findings          ← Đúc kết 3 tầng hiểu biết
9. Methodology                    ← Chỉ viết những gì model cuối cần
10. Related Work                  ← Tra cứu tài liệu có mục tiêu chính xác
11. Introduction                  ← Viết 6 đoạn nén toàn bộ bằng chứng
12. Contributions                 ← Liệt kê đóng góp thực tế
13. Conclusion                    ← Đúc kết và mở ra câu hỏi mới
14. Abstract & Title              ← Viết cuối cùng trong 30 phút

THỨ TỰ NGƯỜI ĐỌC SẼ ĐỌC (Final Manuscript Order):
1. Title & Abstract
2. Introduction
3. Related Work
4. Methodology
5. Experimental Setup & Results
6. Discussion & Representation Analysis
7. Conclusion
```

---

## 2. BƯỚC 0: BẢNG CLAIM–EVIDENCE MAP KHỞI ĐẦU

Trước khi viết bất kỳ câu chữ nào, bạn phải lập bảng kiểm toán giữa **Những gì bạn muốn nói (Claim)** và **Số liệu thực tế bạn đang có (Evidence)**:

| ID | Luận Điểm Muốn Khẳng Định (Claim) | Bằng Chứng Hiện Có (Evidence) | Bằng Chứng Còn Thiếu / Cần Thận Trọng | Cấp Độ Khẳng Định (Claim Level) |
| :---: | :--- | :--- | :--- | :---: |
| **C1** | 5 đặc trưng Hasegawa hoạt động tốt trên In-Distribution nhưng sụp đổ hoàn toàn dưới LOFO | Bảng số liệu: ID $F_1 = 0.6376$, LOFO $F_1 = 0.0300$, Recall $5.59\%$ | Không có (số liệu đã rõ ràng 100%) | **Observation** (Quan sát thực nghiệm chắc chắn) |
| **C2** | Mở rộng lên 13 đặc trưng không giải quyết được vấn đề LOFO | Bảng so sánh 5F vs 13F: LOFO $F_1$ chỉ lên $0.1637$ | Cần bảo đảm cùng model (XGBoost), cùng split, cùng tuning | **Observation** |
| **C3** | Biểu diễn Graph IR chỉ mang lại cải thiện hạn chế nếu không học trực tiếp | Bảng so sánh Tabular 13F vs Graph IR | Cần kiểm tra so sánh công bằng (apples-to-apples) | **Observation** |
| **C4** | Việc sửa đồ thị đầy đủ linh kiện không tự động tạo ra bước nhảy vọt hiệu năng | Thử nghiệm đồ thị cũ vs đồ thị sửa (repair) | Cần ghi chú rõ điều kiện thực nghiệm | **Observation & Negative Result** |
| **C5** | Mô hình GNN vượt trội hơn hẳn các phương pháp dựa trên đặc trưng phẳng | Bảng kết quả Config A $\to$ Config F ($F_1$ lên $0.5239$) | Bảo đảm cùng tập test và metric đánh giá | **Main Empirical Claim** |
| **C6** | Việc học quan hệ cấu trúc (Relational learning) là nguyên nhân tạo ra sự vượt trội | Config B (thuần nhất, $0.2151$) vs Config C (dị thể, $0.3258$) | Có thể cần cân nhắc yếu tố dung lượng mô hình (model capacity) | **Hypothesis có bằng chứng hỗ trợ** |
| **C7** | Bóc tách liên kết điều khiển (Control-OFF) giúp cải thiện khả năng tổng quát hóa liên họ | So sánh Control-ON ($0.4570$) vs Control-OFF ($0.5239$) | Cần chỉ rõ số liệu trên từng họ chip (RS232 triệt tiêu FP) | **Claim được thực nghiệm hỗ trợ vững chắc** |
| **C8** | Dirichlet Energy (DE) cho thấy độ trơn biểu diễn thay đổi rõ rệt giữa cạnh dữ liệu và cạnh điều khiển | Đo lường DE dọc theo các loại cạnh dưới Control-ON và Control-OFF | Cần kiểm tra chuẩn hóa (Normalization) đồ thị | **Representation Analysis** |
| **C9** | DE là nguyên nhân nhân quả giải thích tại sao GNN tổng quát hóa tốt hơn | Số liệu DE tương quan với hiệu năng phân loại | Chưa đủ bằng chứng nhân quả tuyệt đối | **KHÔNG OVERCLAIM:** Dùng từ *"provides evidence consistent with"* |

> **Quy tắc vàng:** Chỉ những luận điểm ở mức `Observation` và `Claim có bằng chứng vững chắc` mới được đưa vào Abstract và Contribution chính. Những luận điểm ở mức `Hypothesis` phải được viết thận trọng trong Discussion.

---

## 3. TEMPLATE CHUẨN CHO MỌI TIỂU MỤC THỰC NGHIỆM (RESULTS SUBSECTION)

Mỗi tiểu mục thực nghiệm trong Section 4 (từ 4.2 đến 4.7) bắt buộc phải tuân thủ đúng khung 10 thành phần sau để bảo đảm tính logic:

```markdown
### X.X [Tên Thực Nghiệm Khoa Học]

**Research Question:**
Chúng ta đang cố gắng trả lời chính xác câu hỏi gì?

**Hypothesis:**
Chúng ta kỳ vọng điều gì sẽ xảy ra, và tại sao?

**Experimental Comparison:**
- Điều gì thay đổi giữa các cấu hình?
- Điều gì được giữ cố định để bảo đảm so sánh công bằng?

**Results:**
Bảng số liệu hoặc giá trị số đo thực tế là bao nhiêu?

**Observation:**
Những sự thật khách quan nào có thể phát biểu trực tiếp từ số liệu đo được?

**Interpretation:**
Quan sát này gợi ý điều gì về mặt cơ chế hoạt động của mô hình?

**Alternative Explanations:**
Có lời giải thích nào khác cũng có thể tạo ra kết quả này không? (Ví dụ: do số lượng tham số, do threshold, do mất cân bằng dữ liệu?)

**Limitation:**
Thí nghiệm này CHƯA chứng minh được điều gì?

**Takeaway:**
Một câu duy nhất đúc kết kết quả của tiểu mục này.

**Next Question:**
Câu hỏi nào còn bỏ ngỏ sẽ dẫn dắt sang thí nghiệm tiếp theo?
```

---

## 4. LỘ TRÌNH VIẾT CHI TIẾT TỪNG PHẦN (TỪ BƯỚC 1 ĐẾN BƯỚC 14)

### GIAI ĐOẠN I: VIẾT THỰC NGHIỆM (RESULTS-FIRST)

#### Bước 1: Section 4.1 — Experimental Setup (Viết Đầu Tiên)
* **Mục tiêu:** Mô tả môi trường thực nghiệm khách quan, không tranh luận.
* **Các mục con:**
  * `4.1.1 Dataset and Circuit Benchmarks:` 30 netlist Trust-Hub, 5 họ (`RS232`, `s15850`, `s35932`, `s38417`, `s38584`), tổng 47,464 cells, 370 Trojans, mất cân bằng cực đoan $\approx 0.78\%$.
  * `4.1.2 Evaluation Protocols:` Phân biệt rõ kịch bản ngẫu nhiên **In-Distribution (ID)** và kịch bản ngoại suy liên họ **Leave-One-Family-Out (LOFO)**.
  * `4.1.3 Evaluation Metrics:` Macro-$F_1$, Micro-$F_1$, Recall (Trojan Coverage), False Positive Rate / 1000 gates. Giải thích vì sao không dùng Accuracy (do mất cân bằng dữ liệu).
  * `4.1.4 Baseline Configurations:` Liệt kê các mô hình đối chứng (XGBoost 5F, XGBoost 13F, Graph IR, GNN).
  * `4.1.5 Training & Implementation Details:` Learning rate, optimizer, seeds, threshold-selection principle (tối ưu trên validation fold).

---

#### Bước 2: Section 4.2 — Handcrafted Feature Baselines (5F ➔ 13F)
* **Ý nghĩa:** Điểm khởi đầu của toàn bộ câu chuyện nghiên cứu.
* **4.2.1 Five Hasegawa Features:**
  * *Question:* 5 đặc trưng khoảng cách logic ($LGFi, ffi, ffo, PI, PO$) có đủ để phân loại Trojan xuyên họ vi mạch không?
  * *Results:* ID đạt $F_1 = 0.6376$, nhưng LOFO sụp đổ về Macro-$F_1 = 0.0300$, Micro-$F_1 = 0.0330$, Recall chỉ $5.59\%$.
  * *Limitation:* Thí nghiệm này chưa chứng minh được sự thất bại là do thiếu số lượng đặc trưng hay do bản chất thiếu ngữ cảnh quan hệ.
* **4.2.2 Extending to 13 Features (13F):**
  * *Hypothesis:* Có thể do 5 đặc trưng quá thô sơ, việc bổ sung 8 đặc trưng tô-pô toàn cục (Degree, PageRank, Centralities) sẽ giải quyết được?
  * *Results:* ID $F_1$ tăng vọt lên $0.9243$, nhưng LOFO chỉ tăng nhẹ lên Macro-$F_1 = 0.1637$.
  * *Takeaway:* Việc làm giàu đặc trưng vô hướng thủ công đơn thuần không giải quyết được khoảng cách tổng quát hóa liên họ.

---

#### Bước 3: Section 4.3 — Graph-Derived Representations (Graph IR)
* **Question:** Khi giữ nguyên thông tin đặc trưng nhưng trích xuất qua đồ thị mức cổng (Graph IR), khả năng tổng quát hóa có được cải thiện không?
* **Experimental Comparison:** Lập bảng đối đầu công bằng (apples-to-apples):
  * Cột 1: Tabular 5F vs Graph IR 5F
  * Cột 2: Tabular 13F vs Graph IR 13F
* **Takeaway:** Việc nén phẳng đồ thị thành các vector thuộc tính dẫn xuất từ đồ thị vẫn chỉ mang lại cải thiện hạn chế.

---

#### Bước 4: Section 4.4 — Graph Construction & Topology Fidelity
* **Question:** Liệu sự cải thiện hạn chế của Graph IR có phải do việc xây dựng đồ thị ban đầu bị thiếu cạnh hay linh kiện không?
* **Thực nghiệm đối chứng:** Đồ thị nén phẳng CircuitGraph (Config A, mất Net, mất 12 Trojan) vs Đồ thị lưỡng phân Cell–Net tường minh (Config B, giữ 100% linh kiện).
* **Negative Result giá trị cao:** Config B dùng GNN thuần nhất lại bị giảm hiệu năng từ $0.3518$ xuống $0.2151$.
* **Takeaway:** Bảo toàn đầy đủ topo là điều kiện cần, nhưng nếu mô hình không phân biệt được ngữ nghĩa của các loại liên kết thì sẽ gây pha loãng thông điệp.

---

#### Bước 5: Section 4.5 — Relational Graph Learning (HeteroTrojanGNN)
* **Question:** Nếu mô hình học trực tiếp trên các quan hệ cấu trúc dị thể (phân tách ma trận $W_r$ theo 6 loại quan hệ Cell–Net), hiệu năng có được khôi phục?
* **Results:** Config C phục hồi mạnh mẽ từ $0.2151$ lên $0.3258$ ($+51.5\%$).
* **Takeaway:** Học biểu diễn quan hệ dị thể là chìa khóa để khai thác đồ thị vi mạch.

---

#### Bước 6: Section 4.6 — The Role of Control Decoupling (`Control-OFF`)
* **Question:** Liệu tất cả các liên kết trong mạch đều có ích, hay mạng điều khiển xung nhịp toàn cục (Clock/Reset) gây cản trở việc học?
* **Thực nghiệm đối chứng:** So sánh **Control-ON** vs **Control-OFF** trên cả nền 5F và 13F.
* **Results:**
  * 5F: Config D (`Control-OFF`) đạt $0.4032$, vượt xa Config C ($0.3258$).
  * 13F: Config F (`Control-OFF`) đạt đỉnh cao $0.5239$ (so với Config E $0.4570$).
  * Trên chip `RS232`: Triệt tiêu hoàn toàn báo động giả ($FP = 0.00$).
* **Takeaway:** Mạng xung nhịp tạo ra các siêu đường tắt nhân tạo; việc ngắt bỏ nó giúp bảo toàn tín hiệu kích hoạt hiếm của Trojan.

---

#### Bước 7: Section 4.7 — Dirichlet Energy & Representation Analysis
* **Cách mở đầu:** Mở đầu bằng một **câu hỏi chưa được trả lời**:
  > *"Hiệu năng cho ta biết CÁI GÌ đã xảy ra, nhưng chưa cho biết BIỂU DIỄN HÌNH HỌC của các nút đã thay đổi như thế nào khi ngắt cạnh điều khiển?"*
* **Công thức toán học:**
  $$E_D(\mathbf{H}) = \frac{1}{2} \sum_{(i,j) \in \mathcal{E}} w_{ij} \|h_i - h_j\|_2^2, \quad E_r(\mathbf{H}) = \frac{1}{2} \sum_{(i,j) \in \mathcal{E}_r} w_{ij} \|h_i - h_j\|_2^2$$
* **Kết quả quan sát:** Dưới `Control-ON`, DE trên cạnh điều khiển sụp đổ về gần $0$ $\to$ Hiện tượng **Quá mượt (Oversmoothing)**. Dưới `Control-OFF`, DE được bảo toàn và Effective Rank tăng từ $4.2$ lên $11.8$.
* **Mức độ khẳng định:** *"Phân tích DE cung cấp bằng chứng phù hợp với giả thuyết (provides evidence consistent with) rằng Control-OFF bảo toàn độ tương phản phổ của cụm Trojan."*

---

### GIAI ĐOẠN II: THẢO LUẬN & PHƯƠNG PHÁP (DISCUSSION & METHODOLOGY)

#### Bước 8: Section 5 — Discussion & Implications
Viết mỗi luận điểm theo công thức 5 tầng:  
**Observation $\to$ Interpretation $\to$ Alternative explanation $\to$ Evidence $\to$ Scope**
* `5.1 Feature Richness vs. Relational Learning:` Vì sao thêm đặc trưng không bằng học quan hệ.
* `5.2 Host Coordinate Memorization vs. Invariant Motifs:` Giải thích bằng hình học (Mặt cắt 2D, Quần đảo PCA).
* `5.3 The Clock Tree Dilemma in Silicon Design:` Vì sao trong EDA, cây clock chỉ phục vụ timing closure chứ không mang ngữ nghĩa logic; do đó loại bỏ clock trong GNN là hoàn toàn tự nhiên và đúng đắn.
* `5.4 Threats to Validity & Limitations:` Thừa nhận thẳng thắn các giới hạn của tập Trust-Hub và bài toán zero-shot threshold transfer.

#### Bước 9: Section 3 — Methodology (Chỉ Viết Những Gì Model Cuối Cần)
* **Nguyên tắc:** Method là tài liệu kỹ thuật để người khác **tái lập công trình (Reproduce)**, không phải nhật ký kể lể các thử nghiệm thất bại.
* **Cấu trúc:**
  * `3.1 Gate-Level Circuit Formulation:` Định nghĩa đồ thị dị thể Cell–Net.
  * `3.2 Node & Edge Characterization:` Mô tả vector đặc trưng đầu vào.
  * `3.3 Relational Message Passing & Control Decoupling:` Công thức HeteroConv trên tập cạnh dữ liệu $\mathcal{R}_{data}$, bóc tách $\mathcal{R}_{ctrl}$.
  * `3.4 Representation Diagnostics:` Định nghĩa toán học của Dirichlet Energy và Effective Rank.

---

### GIAI ĐOẠN III: ĐÓNG GÓI CỐT TRUYỆN (RELATED WORK, INTRODUCTION, ABSTRACT)

#### Bước 10: Section 2 — Related Work
Tra cứu tài liệu có mục tiêu để lấp đúng 4 ô trống:
1. Học máy mức cổng cho Hardware Trojan (Hasegawa, Whitten).
2. Biểu diễn đồ thị cho mạch số EDA (CircuitGraph, NetlistGNN).
3. Đồ thị dị thể trong an ninh phần cứng.
4. Hiện tượng quá mượt (Oversmoothing) và năng lượng Dirichlet trong GNN.

#### Bước 11: Section 1 — Introduction (Đúng 6 Đoạn Văn)
* **P1 (Problem):** Hardware Trojan và thách thức tổng quát hóa liên họ chip (LOFO).
* **P2 (Existing Works):** Các phương pháp dùng đặc trưng thủ công (5 đặc trưng Hasegawa).
* **P3 (Empirical Gap):** Chỉ ra ảo ảnh in-distribution và sự sụp đổ khi sang chip mới do học vẹt tọa độ.
* **P4 (Relational Hypothesis):** Chuyển dịch sang mô hình hóa đồ thị dị thể Cell–Net.
* **P5 (Core Discovery & DE):** Phát hiện tác động tiêu cực của mạng clock toàn cục và giải pháp Control-OFF, được minh chứng qua năng lượng Dirichlet.
* **P6 (Contributions):** Liệt kê 3-4 đóng góp chính xác (Thực nghiệm LOFO có kiểm soát; Kiến trúc HeteroTrojanGNN + Control-OFF; Phân tích hình học biểu diễn DE).

#### Bước 12: Section 6 — Conclusion
Trả lời 3 câu hỏi ngắn gọn:
1. *Chúng ta đã đặt ra câu hỏi gì?*
2. *Chúng ta đã quan sát và chứng minh được điều gì?*
3. *Vấn đề gì vẫn còn bỏ ngỏ cho các nghiên cứu tương lai?*

#### Bước 13: Abstract & Title (Viết Cuối Cùng)
* **Abstract (~200-250 từ):**
  * 1 câu: Bối cảnh & hiểm họa Hardware Trojan.
  * 1 câu: Hạn chế của các đặc trưng nén phẳng (sụp đổ dưới LOFO).
  * 1-2 câu: Phương pháp đề xuất (HeteroTrojanGNN + Control-OFF).
  * 2 câu: Kết quả định lượng cốt lõi ($F_1$ tăng từ $0.03$ lên $0.52$, Recall $61.2\%$).
  * 1 câu: Đóng góp của phân tích Dirichlet Energy.
* **Title:** Khóa tiêu đề phản ánh đúng nhất đóng góp sống sót qua kiểm toán.

---

## 5. HỆ THỐNG 4 MARKER ĐỂ TỰ KIỂM TOÁN KHI VIẾT

Trong quá trình viết draft, khi gặp bất kỳ câu khẳng định nào, bạn hãy gắn 1 trong 4 nhãn sau để tự bảo vệ bài báo:

```text
[CITATION]   ➔ Tôi biết câu này đúng, nhưng cần trích dẫn tài liệu trước đây.
               (Cứ viết tiếp, gom lại tra cứu một lượt sau).

[EVIDENCE]   ➔ Claim này bắt buộc phải có số liệu thực nghiệm của chính tôi chứng minh.
               (Nếu chưa có số liệu -> Phải chạy thí nghiệm hoặc hạ mức claim).

[REASONING]  ➔ Tôi có số liệu, nhưng đây là suy luận logic của tôi về cơ chế phần cứng.
               (Cần kiểm tra xem có alternative explanation nào khác không).

[SCOPE]      ➔ Kết quả này thú vị nhưng có thể làm loãng mạch truyện chính của bài báo.
               (Cân nhắc đẩy xuống phụ lục).
```

---

## 6. KẾ HOẠCH TÁC CHIẾN NGÀY ĐẦU TIÊN (CHECKLIST)

Để không bị ngợp, mục tiêu ngày đầu tiên của bạn chỉ gói gọn trong **3 việc duy nhất**:

- [ ] **Việc 1:** Mở file [reports/draft_paper/04_experimental_results.md](file:///home/dat_ttan/thesis/expl_methods_hw_trojan_detection_code/reports/draft_paper/04_experimental_results.md).
- [ ] **Việc 2:** Đọc và rà soát **Mục 4.1 (Experimental Setup)**: kiểm tra xem các thông số mạch Trust-Hub đã đúng ý bạn chưa.
- [ ] **Việc 3:** Hoàn thiện bản thảo **Mục 4.2 (Handcrafted Baselines: 5F ➔ 13F)** theo đúng công thức 5 câu đã dựng sẵn.

> **Lời khuyên cuối cùng:** Không cần cố viết tiếng Anh thật bóng bẩy ở Draft 0. Mục tiêu của Draft 0 là **mỗi mũi tên chuyển giao giữa các thí nghiệm đều phải có một lý do khoa học rõ ràng**!
