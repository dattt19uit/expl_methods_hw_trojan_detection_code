# BỘ KHUNG BÀI BÁO (PAPER SKELETON) & CẨM NANG HƯỚNG DẪN VIẾT TỪNG BƯỚC

**Đề tài:** *Control-Aware Heterogeneous Graph Learning for Cross-Family Gate-Level Hardware Trojan Localization*  
**Mục tiêu:** Xây dựng bản thảo bài báo khoa học (Draft Paper) chuẩn hội thảo/tạp chí quốc tế (IEEE HOST / DAC / DATE / TIFS) theo phương pháp **Results-First (Từ trong ra ngoài)**.

---

## I. THỨ TỰ VIẾT TỪNG MỤC & LÝ GIẢI "VÌ SAO?"

Tuyệt đối **không viết từ trên xuống dưới** (từ Abstract đến Conclusion). Người làm nghiên cứu chuyên nghiệp viết theo thứ tự sau:

| Thứ Tự Viết | Mục Cần Viết | Tên Trong Paper | Lý Giải "Vì Sao Viết Ở Thứ Tự Này?" |
| :---: | :--- | :--- | :--- |
| **BƯỚC 1** | **Bảng số liệu & Thiết lập thí nghiệm** | `Section 4.1` | **Khởi động dễ nhất:** Số liệu Trust-Hub 30 chip, 5 họ vi mạch, giao thức LOFO và ID đã có sẵn 100%. Viết phần này không cần suy nghĩ trừu tượng, tạo ngay đà tâm lý hưng phấn. |
| **BƯỚC 2** | **Thực nghiệm nhân quả từng bước** | `Section 4.2 ➔ 4.6` | **Trái tim của paper:** Đây là nơi chứa đựng toàn bộ bằng chứng khách quan (Evidence). Viết phần này xong bạn sẽ biết chính xác mô hình của mình chứng minh được điều gì và chưa chứng minh được điều gì. |
| **BƯỚC 3** | **Phương pháp đề xuất** | `Section 3` | **Tránh overclaim và viết lan man:** Sau khi đã viết xong Results, bạn chỉ mô tả trong Method đúng những gì mà mô hình cuối cùng (Config F + Control-OFF + DE) thực sự sử dụng. Không biến Method thành nhật ký thử-sai. |
| **BƯỚC 4** | **Thảo luận & Giải mã phần cứng** | `Section 5` | **Nâng tầm học thuật:** Đưa ra lý giải vì sao kết quả lại như vậy (liên hệ giữa Clock tree trong EDA và hiện tượng Oversmoothing trong GNN, giải mã hình học Dirichlet Energy). |
| **BƯỚC 5** | **Giới thiệu & Động lực nghiên cứu** | `Section 1` | **Không còn phỏng đoán:** Introduction lúc này là "bản tóm tắt cô đọng của bằng chứng", dẫn dắt từ thất bại của Baseline (5F/13F) tới nhu cầu cần HeteroGNN + Control-OFF. |
| **BƯỚC 6** | **Nghiên cứu liên quan (Related Work)** | `Section 2` | **Tra cứu có mục tiêu chính xác:** Lúc này bạn chỉ search tài liệu để lấp đúng 4 ô trống còn thiếu (`[CITATION]`), không bị rơi vào cái bẫy đọc tài liệu tràn lan. |
| **BƯỚC 7** | **Kết luận (Conclusion)** | `Section 6` | Đúc kết lại 3 đóng góp thực sự vững chắc đã được chứng minh. |
| **BƯỚC 8** | **Tóm tắt (Abstract) & Tiêu đề (Title)** | `Abstract` & `Title` | **Viết cuối cùng:** Khi mọi con số (F1, Recall, FP) và claim đã chốt hạ, Abstract viết trong 30 phút là hoàn hảo. |

---

## II. CHI TIẾT BỘ KHUNG (SKELETON) & CÁCH VIẾT TỪNG MỤC

---

### BƯỚC 1 & 2: SECTION 4 — EXPERIMENTAL EVALUATION (VIẾT ĐẦU TIÊN)

#### 4.1. Experimental Setup & Protocol
* **Mục tiêu:** Mô tả rõ ràng môi trường thực nghiệm để người khác có thể tái lập (Reproducibility).
* **Nội dung cần viết:**
  * **Bộ dữ liệu:** 30 netlist từ Trust-Hub, chia thành 5 họ kiến trúc (`RS232`, `s15850`, `s35932`, `s38417`, `s38584`). Tổng 47,464 cells, 370 Trojan cells (tỉ lệ mất cân bằng cực đoan $\approx 0.78\%$).
  * **Hai kịch bản đánh giá:**
    1. *In-Distribution (ID):* Phân chia ngẫu nhiên 60/20/20 (cùng họ chip trong cả train và test).
    2. *Leave-One-Family-Out (LOFO):* Huấn luyện trên 4 họ, kiểm thử mù hoàn toàn trên họ thứ 5 (kiểm tra khả năng tổng quát hóa thực tế).
  * **Thước đo:** Macro-$F_1$, Micro-$F_1$, Recall (Trojan Coverage), và Tỷ lệ báo động giả (False Positives / 1,000 gates).

---

#### 4.2. Handcrafted Feature Baselines: From 5F to 13F
* **Áp dụng công thức 5 câu:**
  1. *[Question]:* Liệu 5 đặc trưng khoảng cách logic của Hasegawa có đủ để định vị Trojan khi gặp họ chip mới (LOFO) không?
  2. *[Setup]:* Huấn luyện XGBoost / Random Forest trên 5 đặc trưng ($LGFi, ffi, ffo, PI, PO$).
  3. *[Observation]:* Trên ID đạt $F_1 = 0.6376$. Dưới LOFO, hiệu năng sụp đổ: Macro-$F_1 = 0.0300$, Micro-$F_1 = 0.0330$, Recall chỉ đạt $5.59\%$ (bỏ sót $94.4\%$ Trojan).
  4. *[Next Hypothesis & Setup]:* Liệu việc mở rộng không gian đặc trưng lên 13F (bổ sung 8 đặc trưng tô-pô toàn cục: Degree, PageRank, Betweenness, Closeness...) có giải quyết được không?
  5. *[Observation & Conclusion]:* 13F đẩy ID $F_1$ lên $0.9243$, nhưng LOFO chỉ tăng nhẹ lên Macro-$F_1 = 0.1637$.
  6. *[Limitation]:* Việc làm giàu đặc trưng vô hướng thủ công không giải quyết được vấn đề trôi dạt phân phối; cần một cơ chế học quan hệ cấu trúc bản địa.

---

#### 4.3. Compressed Homogeneous Graph vs. Explicit Cell-Net Graph (Config A ➔ Config B)
* **Áp dụng công thức 5 câu:**
  1. *[Question]:* Nếu chuyển từ bảng số học sang đồ thị mức cổng, mô hình hóa netlist như thế nào là đúng đắn?
  2. *[Setup]:* 
     * **Config A:** Đồ thị nén phẳng (CircuitGraph) — chỉ giữ Cell, ép Net thành cạnh vô hướng.
     * **Config B:** Đồ thị lưỡng phân Cell–Net tường minh (giữ cả Cell và Net), nhưng dùng GNN thuần nhất (Homogeneous GNN ép chung ma trận trọng số $W$).
  3. *[Observation]:* Config A đạt Macro-$F_1 = 0.3518$. Nhưng Config B lại bị sụt giảm mạnh xuống Macro-$F_1 = 0.2151$ (giảm $-38.9\%$).
  4. *[Interpretation]:* **Negative Result mang tính đột phá:** Việc bổ sung nút Net làm tăng số nút đồ thị gấp 3 lần, nhưng nếu dùng GNN thuần nhất thì các nút Net bị đối xử như nút Cell, gây nhầm lẫn ngữ nghĩa và pha loãng thông điệp.
  5. *[Conclusion]:* Có topology đầy đủ là chưa đủ; mô hình bắt buộc phải phân tách ngữ nghĩa các loại liên kết khác nhau.

---

#### 4.4. The Necessity of Relational Message Passing (Config B ➔ Config C)
* **Áp dụng công thức 5 câu:**
  1. *[Question]:* Việc phân tách riêng biệt các loại quan hệ hướng qua HeteroConv có phục hồi hiệu năng không?
  2. *[Setup]:* **Config C (HeteroTrojanGNN):** Gán ma trận trọng số riêng $W_r$ cho từng loại quan hệ trong số 6 quan hệ Cell–Net (`cell-to-net`, `net-to-cell`, `driver`, `load`...).
  3. *[Observation]:* Macro-$F_1$ vọt từ $0.2151$ lên $0.3258$ (tăng $+51.5\%$).
  4. *[Interpretation]:* Khẳng định cơ chế học biểu diễn dị thể (Heterogeneous Relational Learning) là chìa khóa then chốt để khai thác đồ thị Cell–Net.

---

#### 4.5. Which Relations Matter? Decoupling the Global Control Infrastructure (Config C/D & E/F)
* **Áp dụng công thức 5 câu:**
  1. *[Question]:* Trong các loại quan hệ của netlist, liệu có loại liên kết nào gây hại cho khả năng tổng quát hóa liên họ không?
  2. *[Setup]:* So sánh cấu hình bật mạng điều khiển (**Control-ON**) và ngắt bỏ mạng điều khiển (**Control-OFF** — bóc tách dây xung nhịp `clock` và `reset` trong quá trình lan truyền tin).
  3. *[Observation]:*
     * Trên nền 5 đặc trưng: Config D (`Control-OFF`) đạt Macro-$F_1 = 0.4032$, vượt trội Config C (`Control-ON`, $0.3258$, tăng $+23.8\%$).
     * Trên nền 13 đặc trưng: Config F (`Control-OFF`) đạt đỉnh cao Macro-$F_1 = 0.5239$ (so với Config E `Control-ON` chỉ đạt $0.4570$).
     * Trên chip UART `RS232`: `Control-OFF` triệt tiêu hoàn toàn báo động giả ($FP = 0.00$).
  4. *[Interpretation]:* Mạng Clock kết nối đồng thời tới hàng ngàn Flip-Flop tạo ra "siêu đường tắt" nhân tạo, làm nhiễu loạn dòng thông tin luồng dữ liệu (Datapath). Việc ngắt bỏ mạng Clock giúp bảo toàn tín hiệu kích hoạt hiếm của Trojan.

---

#### 4.6. Representation Geometry & Smoothness Analysis (Dirichlet Energy & Effective Rank)
* **Mục tiêu:** Dùng toán học biểu diễn giải thích tại sao `Control-OFF` lại thắng `Control-ON`.
* **Nội dung:**
  * **Dirichlet Energy (DE):** Đo độ biến thiên của vector biểu diễn nút dọc theo các cạnh đồ thị.
    * Khi bật Clock (`Control-ON`): DE tụt xuống mức cực thấp $\to$ Chứng minh hiện tượng **Quá mượt (Oversmoothing)** dọc theo mạng xung nhịp. Biểu diễn của cổng Trojan bị hòa lẫn vào $99.5\%$ cổng sạch.
    * Khi ngắt Clock (`Control-OFF`): DE được phục hồi ở mức tối ưu $\to$ Bảo toàn độ tương phản phổ (Spectral Contrast) của cụm Trojan.
  * **Effective Rank:** Đo số chiều không gian biểu diễn thực tế không bị sụp đổ (Representation Collapse).

---

### BƯỚC 3: SECTION 3 — METHODOLOGY (VIẾT THỨ HAI)

Chỉ mô tả kiến trúc đề xuất hoàn chỉnh (Final Model), gồm 4 phần con:
1. **3.1. Bipartite Cell-Net Netlist Formulation:** Định nghĩa đồ thị dị thể $\mathcal{G} = (\mathcal{V}_{cell}, \mathcal{V}_{net}, \mathcal{E}, \mathcal{R})$.
2. **3.2. Node Feature Representation:** 5 đặc trưng nén phẳng và bộ mở rộng 13 đặc trưng tô-pô.
3. **3.3. Relational Message Passing & Control Decoupling (`Control-OFF`):**
   * Công thức lan truyền tin dị thể: $h_i^{(l+1)} = \sigma \left( \sum_{r \in \mathcal{R}_{data}} \sum_{j \in \mathcal{N}_r(i)} W_r^{(l)} h_j^{(l)} \right)$.
   * Nêu rõ $\mathcal{R}_{data}$ chỉ bao gồm các cạnh luồng dữ liệu, loại bỏ $\mathcal{R}_{ctrl}$.
4. **3.4. Representation Smoothness Metrics:** Định nghĩa toán học của Dirichlet Energy $E_D(\mathbf{H}) = \text{Tr}(\mathbf{H}^T \mathbf{\tilde{L}} \mathbf{H})$ và Effective Rank.

---

### BƯỚC 4: SECTION 5 — DISCUSSION & HARDWARE IMPLICATIONS

Trả lời 3 câu hỏi sâu sắc:
1. **Host Coordinate Memorization vs. Topology-Invariant Trigger Motifs:** Giải thích vì sao mô hình dạng bảng học vẹt tọa độ (Hình 3 trong báo cáo mật độ), còn GNN học cấu trúc kíp nổ bất biến (Rare Trigger Subgraph).
2. **Silicon Engineering Context (Góc nhìn EDA):** Trong thiết kế vi mạch, Clock Tree Synthesis (CTS) được tối ưu hóa cho cân bằng trễ thời gian (Skew), không mang thông tin logic. Do đó, loại bỏ Clock trong GNN hoàn toàn phù hợp với thực tế phần cứng.
3. **Threats to Validity & Limitations:** Thừa nhận thẳng thắn: Benchmark Trust-Hub dù là chuẩn nhưng quy mô còn hạn chế; kịch bản zero-label threshold transfer trong môi trường công nghiệp còn cần thêm cơ chế thích ứng miền.

---

### BƯỚC 5: SECTION 1 — INTRODUCTION (VIẾT THỨ TƯ)

Viết đúng **6 đoạn văn chuẩn mực**:
* **Đoạn 1 (Problem):** Tầm quan trọng của định vị Hardware Trojan mức cổng logic trong chuỗi cung ứng bán dẫn toàn cầu không tin cậy. Thách thức cốt lõi: Khả năng tổng quát hóa sang họ chip chưa từng biết (Cross-family generalization).
* **Đoạn 2 (Prior Work & Tabular Baseline):** Các phương pháp trước đây chủ yếu dựa vào đặc trưng dạng bảng (5 đặc trưng Hasegawa, Whitten et al., 2026).
* **Đoạn 3 (The Generalization Barrier):** Bằng thực nghiệm, ta chỉ ra rằng mô hình dạng bảng bị "ảo ảnh in-distribution": đạt $F_1 = 0.63$ trên cùng chip nhưng sụp đổ về $F_1 = 0.03$ dưới kiểm thử LOFO do hiện tượng ghi nhớ tọa độ mạch chủ.
* **Đoạn 4 (Relational Hypothesis):** Để vượt qua điểm nghẽn, cần chuyển từ tọa độ tĩnh sang học quan hệ cấu trúc bản địa qua đồ thị dị thể Cell–Net.
* **Đoạn 5 (Core Discovery & Control-OFF):** Việc có đồ thị là chưa đủ; ta phát hiện mạng xung nhịp toàn cục gây quá mượt biểu diễn. Kỹ thuật `Control-OFF` giúp khôi phục độ phân biệt của cụm Trojan.
* **Đoạn 6 (Contributions):** Liệt kê 3 đóng góp chính xác (Bóc tách thực nghiệm LOFO đầu tiên; Kiến trúc HeteroTrojanGNN + Control-OFF; Phân tích hình học Dirichlet Energy).

---

### BƯỚC 6: SECTION 2 — RELATED WORK (VIẾT THỨ NĂM)

Chia làm 3 cụm đề mục có trích dẫn mục tiêu:
1. **Gate-Level Hardware Trojan Detection:** Từ phương pháp trắc lượng (Side-channel) đến học máy dạng bảng (Hasegawa, Whitten).
2. **Graph Learning for Circuit Netlists:** CircuitGraph, NetlistGNN và sự hạn chế của đồ thị thuần nhất (Homogeneous Graphs).
3. **Oversmoothing & Representation Collapse in GNNs:** Các nghiên cứu nền tảng về Dirichlet Energy (Rusch et al.) và ứng dụng vào phân tích mạng phân cấp.

---

### BƯỚC 7 & 8: CONCLUSION, ABSTRACT & TITLE (VIẾT CUỐI CÙNG)

* **Conclusion:** 2 đoạn ngắn đúc kết thành công và hướng mở (áp dụng cho chip công nghiệp cỡ lớn >1M gates).
* **Abstract:** Đúng 1 đoạn văn (khoảng 200–250 từ): [Bối cảnh] $\to$ [Điểm nghẽn LOFO của Baseline] $\to$ [Giải pháp HeteroTrojanGNN + Control-OFF] $\to$ [Số liệu định lượng vượt trội: F1 tăng từ 0.03 lên 0.52, Recall 61.2%] $\to$ [Ý nghĩa phân tích Dirichlet Energy].

---

## III. QUY TẮC BẢO VỆ BẢN THẢO (THE 4-MARKER AUDIT)

Trong quá trình viết, mỗi khi viết một câu khẳng định, hãy dùng 4 nhãn sau để tự kiểm soát:

```text
[EVIDENCE]    ➔ Claim này đã có số liệu trong bảng thực nghiệm (An toàn 100%).
[REASONING]   ➔ Ta đang diễn giải cơ chế (Cần kiểm tra lại tính logic phần cứng).
[CITATION]    ➔ Cần chèn trích dẫn bài báo gốc (Sẽ tra cứu sau, không dừng viết).
[SCOPE]       ➔ Kết quả thú vị nhưng cân nhắc xem có nên đưa vào hay để phụ lục.
```

---

## IV. BẮT ĐẦU NGAY BÂY GIỜ

File bản thảo đầu tiên cần tạo ngay lập tức là:  
`reports/draft_paper/04_experimental_results.md`

Bắt đầu bằng **Mục 4.1 và Mục 4.2**, đặt các bảng số liệu Config A $\to$ F ngay cạnh màn hình và viết bằng các con số thực nghiệm!
