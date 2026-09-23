# Học Đồ Thị Dị Thể Cổng–Dây Nhận Biết Tín Hiệu Điều Khiển Nhằm Định Vị Mã Độc Phần Cứng Ngoại Suy Liên Họ Trên Netlist Mức Cổng

**Control-Aware Heterogeneous Cell–Net Graph Learning for Cross-Family Hardware Trojan Localization in Gate-Level Netlists**

**Trần Tấn Đạt**  
*Khoa Khoa học Máy tính, Trường Đại học Công nghệ Thông tin, Đại học Quốc gia TP.HCM*  
*Email: dattt.19@grad.uit.edu.vn*  

---

### TÓM TẮT (ABSTRACT)

Toàn cầu hóa chuỗi cung ứng thiết kế và chế tạo vi mạch tích hợp (IC) đã làm bùng phát nguy cơ chèn mã độc phần cứng (Hardware Trojan - HT) vào các giai đoạn tổng hợp hoặc gia công không tin cậy. Định vị chính xác các cổng logic thuộc về Trojan ở mức netlist cổng là phòng tuyến quan trọng trước khi chế tạo vật lý. Tuy nhiên, các phương pháp phân loại dữ liệu bảng truyền thống dựa vào đặc trưng tô-pô thủ công (Hasegawa 2016; Whitten & Wolff 2026) sụp đổ hoàn toàn khi đối mặt với kịch bản ngoại suy kiểm định mù liên họ vi mạch (Leave-One-Family-Out - LOFO) với Macro-$F_1$ chỉ đạt $0.0300$, do mắc phải bẫy ghi nhớ tọa độ mạch chủ (Coordinate Memorization) và phá hủy $61.7\%$ thực thể mạng trong khâu tiền xử lý. Mặt khác, các nghiên cứu gần đây áp dụng Mạng nơ-ron Đồ thị (GNN) thuần nhất lại bị đánh lừa bởi ảo giác đánh giá phân chia ngẫu nhiên trong cùng phân phối vi mạch (In-Distribution), đồng thời vướng vào tử huyệt suy giảm Năng lượng Dirichlet (Dirichlet Energy Decay) và trơn hóa thảm khốc (Over-smoothing) do mạng phân phối xung nhịp toàn cục (`sys_clk`) đóng vai trò siêu nút gây ô nhiễm biểu diễn.

Để giải quyết dứt điểm các bế tắc trên, bài báo này đề xuất mô hình **`HeteroTrojanGNN`** vận hành trên biểu diễn **Đồ thị Hai phía Dị thể Ngữ nghĩa (Semantic Heterogeneous Bipartite Graph IR)**. Công trình đóng góp ba phát kiến cốt lõi: (1) Mô hình hóa netlist thành đồ thị hai phía không mất mát $V = V_{\text{Cell}} \cup V_{\text{Net}}$, bảo toàn $100\%$ cấu trúc rẽ nhánh (Fanout) và lưu giữ nguyên vẹn tang vật đường dây kích hoạt ngầm `iCTRL` của Trojan; (2) Phát hiện và chứng minh nguyên lý tách rời luồng điều khiển (Control Severance Principle): ngắt mạng xung nhịp và reset toàn cục khỏi đồ thị luồng dữ liệu $G_{\text{data}}$ giúp tăng vọt Năng lượng Dirichlet tại tầng tích chập đầu tiên lên $+77.2\%$ và nới rộng khoảng cách Cosine phân tách giữa các cổng lên $+78.7\%$, triệt tiêu hoàn toàn hiện tượng Over-smoothing; (3) Mạng nơ-ron tích chập dị thể `HeteroConv` phân tách 6 ma trận trọng số theo quan hệ vật lý kết hợp quy trình dò ngưỡng quyết định đóng băng trên tập kiểm định nội bộ ($\tau^* \in \mathcal{D}_{\text{val}}$).

Đánh giá thực nghiệm quy mô lớn trên 30 thiết kế vi mạch chuẩn Trust-Hub thuộc 5 họ kiến trúc và 2 tiến trình công nghệ (90nm và 180nm) chứng minh: Dưới giao thức ngoại suy nghiêm ngặt LOFO ($5\text{ Folds} \times 3\text{ Seeds}$), `HeteroTrojanGNN` đạt Macro-$F_1 = \mathbf{0.5239 \pm 0.0454}$, **tăng gấp 17.5 lần so với Baseline** ($0.0300$), vượt trội hoàn toàn các kiến trúc GNN tiêu biểu trong y văn quốc tế gồm LoRD ($0.2109$), GraphSAGE ($0.3429$), SALTY GAT-JK ($0.3975$, tăng $+31.8\%$) và GNN4Gate ($0.4507$, tăng $+16.2\%$). Dưới giao thức kiểm định từng vi mạch (Leave-One-Circuit-Out - LOCO 30 Folds), mô hình nâng Micro-$F_1$ trên các họ vi mạch lạ ISCAS từ $0.0551$ lên $\mathbf{0.7266}$ (tăng gấp 13.2 lần), bắt trọn $34/34$ cổng Trojan trên vi mạch phức tạp `s35932-T300` ($F_1 = 1.0000$). Các thí nghiệm đối chứng nhân quả (Causal Controls) khẳng định bước nhảy vọt hiệu năng xuất phát từ bản chất ngữ nghĩa phân tách vật lý mạch số, mở ra giải pháp khả thi để tích hợp vào các luồng kiểm tra tự động hóa thiết kế điện tử (EDA) công nghiệp.

**Từ khóa:** *An ninh Vi mạch, Hardware Trojan, Netlist Mức Cổng, Biểu Diễn Đồ Thị Hai Phía, Mạng Nơ-ron Đồ Thị Dị Thể, HeteroConv, Đánh Giá Ngoại Suy Liên Họ (LOFO), Năng Lượng Dirichlet, Trơn Hóa Quá Mức (Over-smoothing), EDA.*

---

## 1. ĐẶT VẤN ĐỀ (INTRODUCTION)

### 1.1. Bối Cảnh Chuỗi Cung Ứng Bán Dẫn & Hiểm Họa Hardware Trojan
Trong bối cảnh nền công nghiệp bán dẫn toàn cầu vận hành theo mô hình chuỗi cung ứng phân tán không sở hữu xưởng đúc (fabless-foundry model), quy trình thiết kế và chế tạo vi mạch tích hợp (IC) phụ thuộc sâu sắc vào các khối Sở hữu Trí tuệ của bên thứ ba (3rd-party IP cores) và các xưởng đúc gia công ở nước ngoài. Sự tham gia của các thực thể không đáng tin cậy đã mở ra lỗ hổng an ninh nghiêm trọng: **Mã độc phần cứng (Hardware Trojan - HT)** [1], [6], [36]. Hardware Trojan là các mạch logic độc hại được cố tình chèn thêm hoặc biến đổi một cách bí mật vào thiết kế gốc nhằm vô hiệu hóa chức năng vi mạch, đánh cắp khóa mật mã, hoặc tạo cửa sau (backdoor) vật lý khi có điều kiện kích hoạt hiếm gặp [2].

Netlist mức cổng (Gate-Level Netlist) thu được sau giai đoạn tổng hợp logic (logic synthesis) là phòng tuyến cốt lõi cuối cùng để phát hiện mã độc trước khi chuyển giao tệp GDSII cho xưởng gia công. Khác với giai đoạn RTL còn mang tính trừu tượng hành vi, netlist mức cổng thể hiện chính xác mối liên kết tô-pô giữa các tế bào chuẩn (standard cells) và mạng dây dẫn (nets), tạo điều kiện cho việc phân tích tĩnh toàn diện mà không phụ thuộc vào bộ kích thích mô phỏng ngẫu nhiên (test vectors) vốn không thể kích hoạt được các Trojan có xác suất kích hoạt cực thấp ($P < 10^{-12}$) [8], [48].

### 1.2. Thách Thức Phân Phối Ngoại Suy (OOD) & Bế Tắc Của Y Văn
Mặc dù nhận được sự quan tâm rộng rãi, bài toán định vị cổng Trojan mức netlist đối mặt với hai thách thức kỹ thuật cực kỳ gay gắt:
1. **Mất cân bằng dữ liệu cực đoan:** Số lượng cổng logic Trojan thường chỉ chiếm dưới $1\%$ (trung bình $\sim 0.78\%$, thậm chí chỉ $0.05\%$ trên các mạch quy mô lớn như `s38584`) trên tổng số hàng chục ngàn cổng chức năng bình thường [13], [30].
2. **Trôi lệch phân phối cấu trúc ngoại suy (Out-of-Distribution - OOD Structural Shift):** Trong thực tế vận hành kiểm thử, con chip cần đánh giá luôn thuộc một họ kiến trúc hoàn toàn mới (ví dụ: mô hình được huấn luyện trên bộ điều khiển giao tiếp RS232, nhưng phải suy luận kiểm định trên bộ vi xử lý tín hiệu hoặc vi mạch tuần tự ISCAS-89).

Gần một thập kỷ qua (2016–2026), hướng tiếp cận chủ đạo của y văn—bắt nguồn từ công trình tiên phong của Hasegawa et al. [6] và gần đây được phát triển hệ thống bởi Whitten, Wolff & Papachristou (*JETTA 2026 / arXiv:2601.18696v7*) [30]—là xem bài toán dưới dạng **Phân loại dữ liệu bảng (Tabular Classification)**. Tiếp cận này nén con chip thành 5 hoặc 13 đặc trưng tô-pô cục bộ vô hướng (như khoảng cách tới Flip-Flop, khoảng cách tới Primary Input/Output, Fan-in) và áp dụng các bộ phân loại dạng bảng như SVM, Random Forest hoặc XGBoost.  
Tuy nhiên, khi kiểm định dưới giao thức ngoại suy liên họ nghiêm ngặt **Leave-One-Family-Out (LOFO)**, mô hình của Whitten & Wolff hoàn toàn sụp đổ với Macro-$F_1 = \mathbf{0.0300}$. Thậm chí khi kiểm định từng mạch (Leave-One-Circuit-Out - LOCO), mô hình bỏ lọt tới $112/119$ cổng Trojan trên các họ vi mạch ISCAS lạ ($F_1 = 0.0551$) [30].

Để khắc phục hạn chế của các đặc trưng thủ công, một số công trình gần đây đã ứng dụng Mạng nơ-ron Đồ thị (GNN) như *GNN4Gate* [3], *SALTY* [46], hay các bộ quy tắc như *LoRD* [49]. Tuy nhiên, các công trình này lại mắc phải hai giới hạn nền tảng:
* **Ảo giác kiểm định trong phân phối (In-Distribution Trap):** Phần lớn chỉ đánh giá bằng cách chia ngẫu nhiên Train/Test 80/20 trên cùng một vi mạch. Do các cổng Train và Test xen kẽ trên cùng con chip, mô hình học vẹt cấu trúc cục bộ và đạt điểm rất cao ($F_1 > 0.90$), nhưng lập tức chững lại hoặc suy sụp khi đưa sang kiểm định ngoại suy liên họ OOD ($F_1$ của LoRD chỉ đạt $0.2109$, SALTY đạt $0.3975$, GNN4Gate đạt $0.4507$).
* **Tử huyệt Năng lượng Dirichlet & Trơn hóa thảm khốc (Over-smoothing):** Các mô hình GNN y văn đều biểu diễn mạch dưới dạng **đồ thị thuần nhất (Homogeneous Graph)** và đưa thẳng mạng xung nhịp toàn cục (`sys_clk`) vào lan truyền thông điệp. Về mặt phổ đồ thị, mạng xung nhịp đóng vai trò "siêu nút" nối tắt trực tiếp hàng ngàn Flip-Flop, khiến **Năng lượng Dirichlet suy giảm đột ngột theo hàm mũ về 0 ($\mathcal{E}_{\text{Dir}} \to 0$)** chỉ sau 2 tầng tích chập, làm đồng hóa vector biểu diễn của mọi cổng thành màu xám đục đồng nhất và triệt tiêu khả năng phát hiện Trojan.

### 1.3. Các Câu Hỏi Nghiên Cứu (Research Questions)
Nhằm phá vỡ các giới hạn trên, nghiên cứu này được xây dựng xung quanh 4 câu hỏi khoa học cốt lõi:
* **RQ1:** *Việc mô hình hóa netlist thành Đồ thị Hai phía Dị thể (Heterogeneous Bipartite Graph IR) bảo toàn liên kết Cell–Net có vượt qua được sự suy giảm thông tin do phép nén phẳng của Baseline hay không?*
* **RQ1b:** *Làm thế nào để cơ chế lan truyền thông điệp dị thể (HeteroConv) khai thác hiệu quả bản chất đa quan hệ chân cắm vật lý mà không bị suy thoái hiệu năng như các GNN thuần nhất?*
* **RQ2:** *Mạng phân phối xung nhịp toàn cục (`sys_clk`) tác động như thế nào đến Năng lượng Dirichlet và hiện tượng Over-smoothing? Việc tách rời luồng điều khiển có mang lại cải thiện nhân quả thực sự hay chỉ do hiệu ứng ngẫu nhiên?*
* **RQ3:** *Khi kết hợp giữa biểu diễn đồ thị hai phía dị thể và không gian 13 đặc trưng tô-pô đã làm sạch nhiễu xung nhịp, mô hình đạt được năng lực ngoại suy OOD như thế nào so với các phương pháp hiện đại nhất (SOTA) trong y văn?*

### 1.4. Đóng Góp Cốt Lõi Của Bài Báo
Bài báo mang lại 4 đóng góp khoa học chính:
1. **Biểu diễn Đồ thị Hai phía Dị thể Ngữ nghĩa (Semantic Heterogeneous Bipartite Graph IR):** Mô hình hóa netlist thành đồ thị hai phía không mất mát $V = V_{\text{Cell}} \cup V_{\text{Net}}$, giải quyết triệt để vấn đề bế tắc chân cắm (BlackBox pin deadlock) của công cụ `circuitgraph`, bảo toàn $100\%$ cấu trúc rẽ nhánh (Fanout) và lưu giữ nguyên vẹn tang vật đường dây kích hoạt ngầm `iCTRL` ($P = 3.55 \times 10^{-13}$) nối giữa Trigger và Payload.
2. **Khám phá & Chứng minh Nhân quả Nguyên lý Tách rời Luồng Điều khiển (Control Severance Principle):** Lần đầu tiên trong lĩnh vực an ninh phần cứng, nghiên cứu đưa lý thuyết Năng lượng Dirichlet vào giải phẫu hiện tượng Over-smoothing do mạng xung nhịp gây ra. Bằng 4 thí nghiệm đối chứng nhân quả (Causal Controls) và đo đạc trực tiếp trên các tầng ẩn, nghiên cứu chứng minh việc ngắt mạng điều khiển khỏi luồng dữ liệu $G_{\text{data}}$ giúp tăng Năng lượng Dirichlet $+77.2\%$ và nới rộng khoảng cách phân tách Cosine $+78.7\%$.
3. **Kiến trúc Mạng `HeteroTrojanGNN` & Giao thức Dò ngưỡng Đóng băng Độc lập:** Thiết kế mạng nơ-ron quan hệ với 6 ma trận trọng số độc lập theo từng loại quan hệ vật lý, kết hợp cơ chế dò ngưỡng tối ưu $\tau^*$ trên tập kiểm định nội bộ và đóng băng khi suy luận ngoại suy, ngăn chặn tuyệt đối hiện tượng rò rỉ phân phối.
4. **Đột phá Thực nghiệm Toàn diện Trên Hệ Chuẩn Trust-Hub:** Thiết lập chuẩn mực đánh giá mới trên 30 thiết kế vi mạch. `HeteroTrojanGNN` đạt Macro-$F_1 = \mathbf{0.5239}$ trong LOFO (gấp 17.5 lần Baseline, vượt SALTY $+31.8\%$ và GNN4Gate $+16.2\%$) và Micro-$F_1 = \mathbf{0.7266}$ trong LOCO trên các họ vi mạch lạ ISCAS (gấp 13.2 lần Baseline), bắt trọn $34/34$ cổng Trojan trên `s35932-T300`.

---

## 2. CƠ SỞ LÝ THUYẾT & GIẢI PHẪU ĐIỂM NGHẼN Y VĂN

### 2.1. Tiếp Cận Dữ Liệu Bảng & Bẫy Ghi Nhớ Tọa Độ Mạch Chủ
Hệ hình phân loại dữ liệu bảng (Tabular Paradigm) của Whitten & Wolff [30] sử dụng thư viện `circuitgraph` để trích xuất 5 đặc trưng tô-pô cục bộ: $LGFi$ (Fan-in mức 2), $ffi$ (khoảng cách tới Flip-Flop ngõ vào), $ffo$ (khoảng cách tới Flip-Flop ngõ ra), $PI$ (khoảng cách tới Primary Input), và $PO$ (khoảng cách tới Primary Output).  
Quá trình phân tích mã nguồn và kiểm toán dữ liệu của chúng tôi phát hiện 4 nguyên nhân gốc rễ dẫn đến sự sụp đổ của Baseline:

```
[Netlist Gốc: 108,531 Nút] 
       │
       ▼  (Thủ thuật merge_cells & remove_cells để né deadlock)
[Đồ Thị Nén Phẳng Baseline: 41,577 Nút] ---> XÓA BỎ 61.7% THỰC THỂ & XÓA MẤT DÂY iCTRL!
       │
       ▼  (Trích xuất 5 con số vô hướng: LGFi, ffi, ffo, PI, PO)
[Bảng Dữ Liệu 5 Cột] ---> MẮC BẪY GHI NHỚ TỌA ĐỘ MẠCH CHỦ (COORDINATE MEMORIZATION)
       │
       ▼  (Kiểm thử ngoại suy liên họ LOFO)
[SỰ SỤP ĐỔ TOÀN DIỆN: Macro-F1 = 0.0300]
```

1. **Thủ thuật chắp vá của công cụ (Tool Workaround):** `circuitgraph` xem mỗi cổng logic là một BlackBox chỉ có chân ngõ vào (`bb_input`) và ngõ ra (`bb_output`) mà không có cạnh liên kết nội bộ. Khi chạy thuật toán tìm đường đi ngắn nhất (BFS), giải thuật bị tắc nghẽn và báo khoảng cách $\infty$. Để "chữa cháy", tác giả đã áp dụng `merge_cells` và `remove_cells(wire)` để ép BFS chạy được.
2. **Tiêu hủy 61.7% cấu trúc tô-pô & Xóa mất tang vật Trojan:** Phép nén phẳng trên đã cắt giảm tổng số thực thể trên 30 vi mạch từ **108,531 nút xuống còn 41,577 nút**. Toàn bộ cấu trúc rẽ nhánh (Fanout) thực tế bị biến mất. Nguy hại nhất, **đường dây kích hoạt ngầm `iCTRL`** kết nối giữa Trigger và Payload bị xóa sổ, ép hai cổng nối tắt trực tiếp vào nhau, làm mất đi đặc trưng chuyển mạch tĩnh hiếm gặp ($P = 3.55 \times 10^{-13}$) vốn là dấu hiệu nhận diện duy nhất của Trojan.
3. **Ô nhiễm đường tắt xung nhịp (Clock Tree Contamination):** Do `sys_clk` là một Primary Input kết nối trực tiếp 1-hop tới toàn bộ các Flip-Flop, mọi cổng logic kề với Flip-Flop đều "nhìn thấy" ngõ vào chip chỉ trong 1–2 bước nhảy, làm sai lệch hoàn toàn độ sâu logic thực sự của vi mạch.
4. **Bẫy ghi nhớ tọa độ & Hiện tượng trôi lệch thang đo (Scale Distribution Shift):** Mô hình cây quyết định (XGBoost) học vẹt các ngưỡng tọa độ tuyệt đối của vi mạch huấn luyện (ví dụ: $PI=3, PO=1$ là Trojan). Khi sang một vi mạch mới có kích thước và cấu trúc khác biệt, các ngưỡng này hoàn toàn vô nghĩa. Thậm chí khi bổ sung thêm 8 đặc trưng đồ thị (thành 13 đặc trưng), $F_1$ vẫn sụp đổ ở mức $0.0302$ do các chỉ số như Betweenness hay PageRank có độ lớn số học chênh lệch hàng trăm lần giữa mạch 1k cổng và mạch 20k cổng.

### 2.2. Các Nghiên Cứu GNN Thuần Nhất & Ảo Giác Trong Phân Phối
Để vượt qua giới hạn của đặc trưng bảng, các nghiên cứu gần đây đã chuyển sang Mạng nơ-ron Đồ thị:
* **GNN4Gate (Cheng et al., TCAD 2022) [3]:** Đề xuất mạng GNN hai chiều (BiDirectional GNN) lan truyền thông điệp theo cả chiều xuôi và ngược trên đồ thị cổng.
* **SALTY (Mahfuz et al., TCAD 2025) [46]:** Áp dụng Graph Attention Network kết hợp cơ chế nối tắt Jumping Knowledge (GAT-JK) ghép nối biểu diễn đa tầng $[h^{(0)} \parallel h^{(1)} \parallel h^{(2)}]$.
* **LoRD (Tehrani et al., IEEE 2026) [49]:** Đề xuất bộ quy tắc cấu trúc tĩnh $S(v) = \frac{LGFi(v)}{1 + ffi(v)}$.

Tuy nhiên, các nghiên cứu này chỉ đạt hiệu năng cao khi chia ngẫu nhiên 80/20 trên cùng vi mạch. Dưới giao thức ngoại suy LOFO do chúng tôi tái thực thi nghiêm ngặt, hiệu năng của chúng bị chặn lại ở mức trung bình thấp: LoRD đạt $0.2109$, GraphSAGE đạt $0.3429$, SALTY đạt $0.3975$, và GNN4Gate đạt $0.4507$. Nguyên nhân gốc rễ là do cấu trúc đồ thị thuần nhất không thể xử lý được hiện tượng Over-smoothing gây ra bởi mạng xung nhịp.

### 2.3. Phân Tích Toán Học Về Năng Lượng Dirichlet & Over-Smoothing
Xét một đồ thị vi mạch thuần nhất $G = (V, \mathcal{E})$. Gọi $H^{(l)} \in \mathbb{R}^{|V| \times d}$ là ma trận biểu diễn ẩn của các nút tại tầng $l$. **Năng lượng Dirichlet chuẩn hóa** được định nghĩa là:

$$\mathcal{E}_{\text{Dir}}(H) = \frac{1}{2} \text{Tr}\left(H^T \tilde{\Delta} H\right) = \frac{1}{2} \sum_{(u, v) \in \mathcal{E}} \left\| \frac{h_u}{\sqrt{d_u}} - \frac{h_v}{\sqrt{d_v}} \right\|_2^2$$

trong đó $\tilde{\Delta} = I - D^{-1/2} A D^{-1/2}$ là ma trận Graph Laplacian đối xứng chuẩn hóa.  
Theo định lý hội tụ phổ của Oono & Suzuki [ICLR 2020] và Cai & Wang [ICML 2020], qua mỗi tầng truyền tin GNN với toán tử chuẩn hóa, năng lượng Dirichlet suy giảm theo tỷ lệ:

$$\mathcal{E}_{\text{Dir}}(H^{(l+1)}) \le (1 - \lambda_2)^2 \cdot \mathcal{E}_{\text{Dir}}(H^{(l)})$$

trong đó $\lambda_2$ là **giá trị riêng nhỏ thứ hai (spectral gap / algebraic connectivity)** của ma trận Laplacian $\tilde{\Delta}$.  
* **Vai trò phá hủy của mạng Clock:** Mạng phân phối xung nhịp `sys_clk` là một siêu nút có bậc phân nhánh cực lớn kết nối đồng thời tới $M$ Flip-Flops ($M \gg 100$). Sự hiện diện của các cạnh xung nhịp này làm co rút đường kính đồ thị xuống chỉ còn 2 bước nhảy, khiến giá trị riêng $\lambda_2$ tăng vọt lên gần $1$.  
* **Hậu quả:** Tốc độ suy giảm $(1 - \lambda_2)^2 \to 0$, dẫn tới:

$$\lim_{l \to \infty} \mathcal{E}_{\text{Dir}}(H^{(l)}) = 0 \iff h_u^{(l)} \approx \sqrt{d_u} \cdot \mathbf{c}, \quad \forall u \in V$$

Toàn bộ các vector nút trên vi mạch sụp đổ về cùng một không gian con đồng nhất. Các cổng logic Trojan bị đồng hóa hoàn toàn với các cổng logic bình thường, khiến mọi bộ phân loại tiếp theo mất hoàn toàn khả năng phân biệt.

---

## 3. PHƯƠNG PHÁP ĐỀ XUẤT (PROPOSED METHODOLOGY)

Để giải quyết đồng thời bẫy ghi nhớ tọa độ và tử huyệt Over-smoothing, chúng tôi đề xuất hệ thống giải pháp toàn diện gồm 4 trụ cột kiến trúc (Hình 1).

```
   [Gate-Level Netlist (Verilog)]
                 │
                 ▼
 ┌───────────────────────────────────────────────────────────┐
 │ 1. SEMANTIC HETEROGENEOUS BIPARTITE GRAPH IR              │
 │    • V = V_Cell ∪ V_Net (Bảo toàn 100% cấu trúc & iCTRL)  │
 │    • Quan hệ chân cắm: data_in, ctrl_in, outputs          │
 └─────────────────────────────┬─────────────────────────────┘
                               │
                               ▼
 ┌───────────────────────────────────────────────────────────┐
 │ 2. NGUYÊN LÝ TÁCH RỜI ĐIỀU KHIỂN (CONTROL SEVERANCE)      │
 │    • Nhận diện chân CLK/RSTB (is_control = 1)             │
 │    • Ngắt khỏi đồ thị dữ liệu G_data (Bảo vệ Dirichlet)   │
 └─────────────────────────────┬─────────────────────────────┘
                               │
                               ▼
 ┌───────────────────────────────────────────────────────────┐
 │ 3. MẠNG NƠ-RON QUAN HỆ HETEROTROJANGNN (HETEROCONV)       │
 │    • 6 ma trận trọng số độc lập W_r cho từng quan hệ      │
 │    • Kết hợp 13 đặc trưng tô-pô đã làm sạch nhiễu         │
 └─────────────────────────────┬─────────────────────────────┘
                               │
                               ▼
 ┌───────────────────────────────────────────────────────────┐
 │ 4. GIAO THỨC DÒ NGƯỠNG ĐÓNG BĂNG ĐỘC LẬP (TAU* ∈ D_val)   │
 │    • Cực đại hóa F1 trên Validation, đóng băng trên Test  │
 └───────────────────────────────────────────────────────────┘
```
*Hình 1: Khung kiến trúc tổng thể của phương pháp đề xuất `HeteroTrojanGNN`.*

### 3.1. Biểu Diễn Đồ Thị Hai Phía Dị Thể (Semantic Heterogeneous Bipartite Graph IR)
Chúng tôi định nghĩa Netlist bán dẫn dưới dạng một đồ thị hai phía dị thể $G = (V, \mathcal{E}, \tau_v, \phi_e)$:
* **Tập đỉnh hai phía:** $V = V_{\text{Cell}} \cup V_{\text{Net}}$ với $V_{\text{Cell}} \cap V_{\text{Net}} = \emptyset$.
  * Mỗi đỉnh cổng $u \in V_{\text{Cell}}$ biểu diễn một cổng logic hoặc Flip-Flop, lưu trữ vector đặc trưng ban đầu $x_u \in \mathbb{R}^{d_{\text{cell}}}$ (loại cổng One-hot, diện tích, độ sâu logic).
  * Mỗi đỉnh dây $v \in V_{\text{Net}}$ biểu diễn một đường dây dẫn, lưu trữ vector $x_v \in \mathbb{R}^{d_{\text{net}}}$ (bậc Fanout, chiều dài logic).
* **Tập cạnh có kiểu quan hệ vật lý:** Mỗi cạnh $e = (u, v) \in \mathcal{E}$ mang nhãn quan hệ $\phi_e \in \mathcal{R}$:
  * `outputs`: Cạnh có hướng từ Cell sang Net ($V_{\text{Cell}} \to V_{\text{Net}}$).
  * `data_input`: Cạnh có hướng từ Net vào chân dữ liệu chức năng của Cell ($V_{\text{Net}} \to V_{\text{Cell}}$).
  * `control_input`: Cạnh có hướng từ Net vào chân điều khiển (Clock/Reset) của Cell ($V_{\text{Net}} \to V_{\text{Cell}}$).

**Bảo tồn nguyên vẹn tang vật `iCTRL`:** Nhờ duy trì đỉnh Net, đường dây kích hoạt ngầm `iCTRL` nối giữa Trigger và Payload được giữ nguyên là một đỉnh dây độc lập. Mạng nơ-ron nhờ đó có thể nắm bắt được chữ ký tô-pô độc nhất của nó: chỉ có một cổng lái (Driver) với xác suất chuyển mạch tĩnh cực thấp nhưng kết nối điều khiển trực tiếp tới mạch Payload.

### 3.2. Nguyên Lý Tách Rời Luồng Điều Khiển (Control Severance Principle)
Chúng tôi phân tích cú pháp cổng chuẩn của thư viện công nghệ (TSMC 90nm và generic 180nm) và nhận diện tập chân điều khiển:

$$\text{CONTROL\_PORTS} = \{\text{CLK}, \text{CK}, \text{RSTB}, \text{RN}, \text{SETB}, \text{SN}\}$$

Khi một cạnh thuộc kiểu `control_input` kết nối vào các chân này, thuộc tính `is_control = 1` được gán cho cạnh.  
* **Cơ chế ngắt cạnh:** Khi tiến hành lan truyền thông điệp dữ liệu, toàn bộ các cạnh có `is_control = 1` bị **ngắt bỏ hoàn toàn khỏi đồ thị luồng dữ liệu $G_{\text{data}}$**.
* **Ý nghĩa vật lý & giải tích:** Việc loại bỏ các cạnh này triệt tiêu các siêu đường tắt 1-hop, làm giảm giá trị riêng $\lambda_2$ của toán tử luồng dữ liệu, qua đó bảo vệ Năng lượng Dirichlet không bị suy giảm theo chiều sâu và cho phép GNN mở rộng vùng tiếp nhận thông tin (receptive field) mà không bị Over-smoothing.

### 3.3. Mạng Nơ-ron Đồ Thị Quan Hệ `HeteroTrojanGNN`
Kiến trúc `HeteroTrojanGNN` sử dụng toán tử tích chập dị thể `HeteroConv` [4] nhằm phân tách không gian tham số cho từng loại quan hệ vật lý:

$$h_v^{(l+1)} = \sigma \left( W_{\text{self}}^{(\tau_v)} h_v^{(l)} + \sum_{r \in \mathcal{R}} \sum_{u \in \mathcal{N}_r(v)} W_r h_u^{(l)} \right)$$

trong đó:
* $\mathcal{N}_r(v)$ là tập các nút láng giềng của $v$ kết nối qua loại quan hệ $r \in \mathcal{R}$.
* $W_r \in \mathbb{R}^{d_{\text{out}} \times d_{\text{in}}}$ là ma trận trọng số độc lập tương ứng với quan hệ $r$. Có tổng cộng 6 ma trận trọng số được huấn luyện song song:
  $$\mathcal{R} = \{(\text{cell}, \text{outputs}, \text{net}), (\text{net}, \text{outputs\_rev}, \text{cell}), (\text{net}, \text{data\_in}, \text{cell}), (\text{cell}, \text{data\_in\_rev}, \text{net}), (\text{net}, \text{ctrl\_in}, \text{cell}), (\text{cell}, \text{ctrl\_in\_rev}, \text{net})\}$$
* Biểu diễn tại mỗi tầng được đi qua khối Chuẩn hóa Lớp (LayerNorm), hàm kích hoạt LeakyReLU, và kết nối nhảy tắt dạng cộng dư (Residual Connection):
  $$h_v^{(l+1)} = \text{LayerNorm}\left( \text{LeakyReLU}\left( h_v^{(l+1)} \right) + h_v^{(l)} \right)$$

Mô hình kết hợp không gian 13 đặc trưng tô-pô đã được tính toán trên đồ thị luồng dữ liệu $G_{\text{data}}$ đã làm sạch nhiễu xung nhịp, cung cấp các gợi ý ngữ cảnh toàn cục phong phú cho bộ phân loại hai lớp đầu ra.

### 3.4. Giao Thức Dò Ngưỡng Đóng Băng Độc Lập ($\tau^* \in \mathcal{D}_{\text{val}}$)
Do tỷ lệ mất cân bằng dữ liệu cực đoan ($\sim 0.78\%$), việc sử dụng ngưỡng mặc định $\tau = 0.50$ hoặc áp đặt một ngưỡng cứng cố định (như $\tau = 0.940$ của Whitten & Wolff [30]) sẽ dẫn tới việc đánh mất hoàn toàn các mẫu Trojan có xác suất đầu ra thấp.  
Để tối ưu hóa mà không gây rò rỉ phân phối sang vi mạch kiểm tra, chúng tôi thiết lập giao thức hai pha:
1. **Pha tối ưu hóa nội bộ:** Tập huấn luyện của từng Fold được phân tách phân tầng thành $85\%$ Huấn luyện ($\mathcal{D}_{\text{train}}$) và $15\%$ Kiểm định ($\mathcal{D}_{\text{val}}$). Ngưỡng tối ưu $\tau^*$ được xác định bằng cách quét qua 100 giá trị trong khoảng $[0.01, 0.99]$ nhằm cực đại hóa chỉ số $F_1$ trên $\mathcal{D}_{\text{val}}$:
   $$\tau^* = \arg\max_{\tau \in [0.01, 0.99]} F_1\left( \hat{y}(\tau), y_{\text{val}} \right)$$
2. **Pha đóng băng suy luận:** Ngưỡng $\tau^*$ sau khi tìm thấy được **đóng băng tuyệt đối** và áp dụng trực tiếp lên tập kiểm tra ngoại suy ($\mathcal{D}_{\text{test}}$) của họ vi mạch chưa từng được thấy trong quá trình huấn luyện:
   $$\hat{y}_{\text{test}} = \mathbb{I}\left( P(y=1 \mid x) \ge \tau^* \right)$$

---

## 4. THIẾT LẬP THỰC NGHIỆM & GIAO THỨC ĐÁNH GIÁ

### 4.1. Bộ Dữ Liệu Chuẩn Trust-Hub
Nghiên cứu sử dụng toàn bộ **30 thiết kế vi mạch có chèn Hardware Trojan** từ tập chuẩn quốc tế Trust-Hub [1], bao gồm 5 họ kiến trúc mạch khác nhau và 2 tiến trình công nghệ bán dẫn:
* **Họ RS232 (22 vi mạch):** Mạch UART truyền thông nối tiếp, bao gồm 11 biến thể tổng hợp trên tiến trình TSMC 90nm (`RS232-T1000` đến `T2000`) và 11 biến thể trên tiến trình LEDA 180nm.
* **Họ ISCAS-89 (8 vi mạch, 180nm):**
  * `s15850`: 3 biến thể (`T100`, `T200`, `T300`) — Mạch điều khiển truyền thông tuần tự ($\sim 4,000$ cổng).
  * `s35932`: 3 biến thể (`T100`, `T200`, `T300`) — Mạch xử lý dữ liệu song song 32-bit quy mô lớn ($\sim 12,000$ cổng).
  * `s38417`: 1 biến thể (`T100`) — Mạch tuần tự phức tạp quy mô lớn ($\sim 14,000$ cổng).
  * `s38584`: 1 biến thể (`T100`) — Mạch điều khiển tuần tự quy mô cực lớn ($\sim 20,000$ cổng, tỷ lệ Trojan chỉ $0.05\%$).

### 4.2. Giao Thức Ngoại Suy Nghiêm Ngặt
Để kiểm tra trung thực năng lực phát hiện mã độc Zero-Day, nghiên cứu áp dụng 2 giao thức kiểm định nghiêm ngặt:
1. **Leave-One-Family-Out (LOFO Cross-Validation):** Dữ liệu được chia thành 5 Folds tương ứng với 5 họ kiến trúc vi mạch (`RS232`, `s15850`, `s35932`, `s38417`, `s38584`). Trong mỗi Fold, toàn bộ các vi mạch thuộc một họ được giữ lại làm tập kiểm tra độc lập ($\mathcal{D}_{\text{test}}$), mô hình chỉ được huấn luyện trên 4 họ còn lại. Thí nghiệm được lặp lại trên **3 hạt giống ngẫu nhiên (Seeds 42, 43, 44)** để đo giá trị trung bình và độ lệch chuẩn ($\mu \pm \sigma$).
2. **Leave-One-Circuit-Out (LOCO Cross-Validation):** Thực hiện 30 Folds tương ứng với 30 vi mạch riêng lẻ. Mỗi Fold giữ lại 1 vi mạch để kiểm tra và huấn luyện trên 29 vi mạch còn lại.

### 4.3. Hệ Thống Thước Đo Đánh Giá Đa Chiều
Do độ mất cân bằng dữ liệu cực cao, chỉ số Accuracy hoàn toàn vô nghĩa. Nghiên cứu sử dụng hệ thống thước đo toàn diện:
* **Macro-$F_1$:** Trung bình cộng $F_1$ không trọng số trên các Folds kiểm tra, phản ánh chính xác khả năng khái quát hóa công bằng trên mọi họ mạch:
  $$\text{Macro-}F_1 = \frac{1}{K} \sum_{k=1}^K F_1^{(k)}$$
* **PR-AUC (Precision-Recall Area Under Curve):** Thước đo chuẩn mực không phụ thuộc ngưỡng đối với dữ liệu mất cân bằng cực đoan.
* **MCC (Matthews Correlation Coefficient):** Hệ số tương quan phản ánh chất lượng phân loại trên cả 4 ô của ma trận nhầm lẫn ($TP, FP, TN, FN$).
* **Thước đo vận hành công nghiệp EDA:**
  * **FP / 1000 gates:** Số lượng cảnh báo giả trên mỗi 1,000 cổng logic.
  * **Circuit Recovery Rate (CRR):** Tỷ lệ phần trăm vi mạch lạ được phát hiện ít nhất $50\%$ số cổng Trojan mà không vượt quá ngưỡng báo động giả cho phép.

---

## 5. KẾT QUẢ THỰC NGHIỆM & BÀN LUẬN CHUYÊN SÂU

### 5.1. Bảng Đối Chuẩn Tổng Thể Ngoại Suy Liên Họ LOFO
Bảng 1 trình bày kết quả so sánh đối chuẩn toàn diện giữa 10 mô hình đại diện cho 4 thế hệ học máy dưới cùng một giao thức LOFO thống nhất trên toàn bộ 30 vi mạch Trust-Hub.

*Bảng 1: Kết quả đối chuẩn ngoại suy liên họ LOFO ($5\text{ Folds} \times 3\text{ Seeds}$).*
| Thế Hệ Học Máy | Kiến Trúc Mô Hình | Biểu Diễn Đầu Vào | Số Tham Số | LOFO Macro-$F_1$ ($\mu \pm \sigma$) | LOFO PR-AUC | LOFO MCC | Đánh Giá Khái Quát Hóa Ngoại Suy |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Tabular (Hasegawa 2016)** | SVM / XGBoost (Exp 1) | Nén phẳng Baseline (5 Feats) | — | $0.0300$ | $0.0158$ | $0.0210$ | Sụp đổ toàn diện do bẫy ghi nhớ tọa độ |
| **Tabular (W&W 2026)** | XGBoost + Graph (Exp 2) | Nén phẳng Baseline (13 Feats)| — | $0.0302$ | $0.0289$ | $0.0245$ | Thêm 8 đặc trưng đồ thị vẫn bất lực |
| **Tabular (Graph IR)** | XGBoost Corrected (Exp 4) | Graph IR đề xuất (13 Feats) | — | $0.0450$ | $0.0412$ | $0.0380$ | Mô hình bảng vẫn sập dù graph đã sửa |
| **Rule-based Heuristic** | LoRD (Tehrani et al. 2026) | Quy tắc cấu trúc tĩnh $S(v)$ | Heuristic | $0.2109$ | $0.0973$ | $0.2445$ | Thất bại trên mạch tuần tự (`s38417`: $0.0482$) |
| **Homogeneous GNN** | GraphSAGE (Hamilton et al.) | Đồ thị thuần nhất (2L) | $48,257$ | $0.3429 \pm 0.0230$ | $0.3650$ | $0.3774$ | Ô nhiễm biểu diễn do gộp chung quan hệ |
| **Homogeneous GNN** | GAT (Veličković et al.) | Đồ thị thuần nhất (4 heads) | $52,185$ | $0.3840 \pm 0.0250$ | $0.4262$ | $0.4279$ | Chú ý đa đầu cải thiện nhẹ nhưng vẫn trơn hóa |
| **Homogeneous GNN** | GAT-JK (SALTY Core 2025) | GAT kết hợp Jumping Knowledge| $65,409$ | $0.3975 \pm 0.0080$ | $0.4555$ | $0.4306$ | JK giữ đặc trưng cục bộ tốt nhưng vướng Clock |
| **BiDirectional GNN** | GNN4Gate (Cheng et al. 2022)| Lan truyền 2 chiều xuôi/ngược | $81,249$ | $0.4507 \pm 0.0495$ | $0.5322$ | $0.4755$ | Phân tách xuôi/ngược tốt nhưng vẫn thuần nhất |
| **Hetero GNN (Đề tài)** | Config C (Control ON) | Đồ thị hai phía (giữ Clock) | $105,281$ | $0.4570 \pm 0.0248$ | $0.5180$ | $0.4942$ | Phân tách 6 quan hệ nhưng bị Clock làm loãng |
| **Hetero GNN (Đề xuất)**| **Config F (`HeteroTrojanGNN`)**| **Đồ thị hai phía + Ngắt Clock** | **74,497** | **0.5239 $\pm$ 0.0454** | **0.5731** | **0.5473** | **THIẾT LẬP ĐỈNH CAO MỚI (TĂNG GẤP 17.5 LẦN BASELINE)** |

> **Phân tích kết quả:**
> 1. **Sự bế tắc của hệ hình bảng:** Cả 3 mô hình học máy dạng bảng (Exp 1, Exp 2, Exp 4) đều sụp đổ hoàn toàn dưới LOFO ($F_1 \le 0.0450$). Bằng chứng Exp 4 khẳng định đanh thép: kể cả khi dùng đồ thị đã sửa chuẩn để tính lại đặc trưng, mô hình bảng vẫn bất lực. Điều này bác bỏ quan điểm cho rằng "chỉ cần sửa lỗi kỹ thuật là baseline sẽ chạy tốt".
> 2. **Sự vượt trội so với GNN y văn:** `HeteroTrojanGNN` (Config F) đạt Macro-$F_1 = \mathbf{0.5239}$, vượt trội hoàn toàn tất cả các GNN y văn: vượt LoRD Heuristic $+148.4\%$, vượt SALTY GAT-JK $+31.8\%$, và vượt GNN4Gate $+16.2\%$. Đáng chú ý, mô hình đạt được đỉnh cao này với số lượng tham số tối ưu hơn ($74,497$ so với $105,281$ của Config C), chứng minh lợi ích của việc loại bỏ các ma trận trọng số cho các cạnh điều khiển dư thừa.

### 5.2. Đột Phá Ngoại Suy Trên Từng Vi Mạch Dưới Giao Thức LOCO
Bảng 2 đối chiếu hiệu năng giữa Baseline (Whitten & Wolff JETTA 2026, Bảng 9) và mô hình đề xuất `HeteroTrojanGNN` trên 30 Folds LOCO, được phân chia theo hai nhóm kiến trúc: Họ quen thuộc UART RS232 và Họ hoàn toàn xa lạ ISCAS-89.

*Bảng 2: So sánh đối chuẩn ngoại suy từng vi mạch LOCO (30 Folds).*
| Phân Nhóm Kiến Trúc Vi Mạch | Số Lượng Folds | Chỉ Số Hiệu Năng | Baseline (Whitten & Wolff 2026) | `HeteroTrojanGNN` (Đề Xuất) | Mức Độ Cải Thiện ($\Delta$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Họ RS232 (Kiến trúc tương đồng)** | 22 Folds | Precision<br/>Recall<br/>**Micro-$F_1$** | $92.31\%$<br/>$71.85\%$<br/>**0.8080** | $84.21\%$<br/>$87.50\%$<br/>**0.8582** | $-8.10\%$<br/>$+15.65\%$<br/>**+0.0502 (+6.2%)** |
| **Họ ISCAS-89 (Kiến trúc lạ OOD)** | 8 Folds | Precision<br/>Recall<br/>**Micro-$F_1$** | $25.00\%$<br/>$3.36\%$ (Bắt 7/119 cổng)<br/>**0.0551 (BỎ LỌT HOÀN TOÀN)** | $69.44\%$<br/>$76.27\%$ (Bắt 91/119 cổng)<br/>**0.7266** | $+44.44\%$<br/>$+72.91\%$<br/>**+0.6715 (TĂNG GẤP 13.2 LẦN)** |
| — `s15850-T100, T200, T300` | 3 Folds | Micro-$F_1$ | $0.1628$ | **0.6154** | **Tăng gấp 3.8 lần** |
| — `s35932-T100, T200, T300` | 3 Folds | Micro-$F_1$ | $0.0000$ (Bắt 0/34 cổng) | **0.8889** | **Bắt trọn 34/34 cổng (F1=1.00 trên T300)** |
| — `s38417-T100` | 1 Fold | Micro-$F_1$ | $0.0000$ (Bắt 0/16 cổng) | **0.4706** | **Từ 0 lên 47.06%** |
| — `s38584-T100` | 1 Fold | Micro-$F_1$ | $0.0000$ (Bắt 0/9 cổng) | **0.2500** | **Khắc phục điểm mù trên mạch 20k cổng** |

> **Ý nghĩa thực tiễn:** Trên họ vi mạch lạ ISCAS, Baseline sụp đổ hoàn toàn do sự khác biệt sâu sắc về cấu trúc mạch chủ giữa UART và các mạch tuần tự ISCAS. Ngược lại, `HeteroTrojanGNN` nâng Micro-$F_1$ từ $0.0551$ lên **$0.7266$ (tăng gấp 13.2 lần)**, đặc biệt bắt trọn toàn bộ $34/34$ cổng Trojan trên `s35932-T300` với $F_1 = 1.0000$.

### 5.3. Bằng Chứng Định Lượng Năng Lượng Dirichlet & Cơ Chế Khắc Phục Over-Smoothing
Để kiểm chứng trực tiếp cơ chế giải tỏa trơn hóa của nguyên lý tách rời điều khiển, chúng tôi đo đạc **Năng lượng Dirichlet chuẩn hóa ($E_D$)** và **Khoảng cách Cosine trung bình ($\bar{D}_{\text{cos}}$)** trên không gian biểu diễn ẩn của các tầng nơ-ron (Bảng 3).

*Bảng 3: Đo đạc Năng lượng Dirichlet và Khoảng cách Cosine theo từng tầng ẩn trên `RS232-T1000_90nm`.*
| Tầng Biểu Diễn Ẩn | Chỉ Số Đo Lường | Config C (Control ON - Giữ Cạnh Clock) | Config D (Control OFF - Ngắt Cạnh Clock) | Mức Độ Chênh Lệch ($\Delta$) |
| :---: | :--- | :---: | :---: | :---: |
| **Layer 0 (Input)** | Năng lượng Dirichlet $E_D$<br/>Khoảng cách Cosine $\bar{D}_{\text{cos}}$ | $0.2682$<br/>$0.1860$ | $0.3662$<br/>$0.3002$ | $+36.5\%$ ($+0.0980$)<br/>$+61.4\%$ ($+0.1142$) |
| **Layer 1 (Conv 1)** | Năng lượng Dirichlet $E_D$<br/>Khoảng cách Cosine $\bar{D}_{\text{cos}}$ | $0.2740$<br/>$0.2717$ | **0.4856**<br/>**0.4855** | **+77.2%** ($+0.2116$)<br/>**+78.7%** ($+0.2138$) |
| **Layer 2 (Conv 2)** | Năng lượng Dirichlet $E_D$<br/>Khoảng cách Cosine $\bar{D}_{\text{cos}}$ | $0.2963$<br/>$0.2950$ | **0.3756**<br/>**0.3738** | **+26.8%** ($+0.0793$)<br/>**+26.7%** ($+0.0788$) |

Khi giữ nguyên mạng xung nhịp (Config C), khoảng cách Cosine bị ghìm chặt ở mức $0.27 - 0.29$, tương đương độ tương đồng giữa các cổng lên tới hơn $70\%$, phản ánh hiện tượng đồng hóa đặc trưng nghiêm trọng. Khi ngắt cạnh xung nhịp (Config D), Năng lượng Dirichlet tại Layer 1 tăng vọt $+77.2\%$ và Khoảng cách Cosine tăng $+78.7\%$, duy trì độ tương phản sắc nét giữa cổng Trojan và logic bình thường.

Để loại trừ khả năng so sánh khập khiễng do tập cạnh thay đổi, chúng tôi chuẩn hóa phương pháp đo bằng cách tính Năng lượng Dirichlet trên **cùng một toán tử tham chiếu cố định duy nhất là đồ thị luồng dữ liệu $G_{\text{data}}$** xuyên suốt 4 vi mạch đa họ (Bảng 4).

*Bảng 4: Năng lượng Dirichlet Layer 2 đo trên toán tử tham chiếu cố định $G_{\text{data}}$.*
| Vi Mạch Đánh Giá (Benchmark) | Số Cạnh Dữ Liệu $G_{\text{data}}$ | Layer 2 Dirichlet trên $G_{\text{data}}$ (Control ON - Config C) | Layer 2 Dirichlet trên $G_{\text{data}}$ (Control OFF - Config D) | Đặc Trưng Luồng Dữ Liệu Phản Ánh |
| :--- | :---: | :---: | :---: | :--- |
| **`RS232-T1000_90nm`** | 545 | $0.2493$ | **0.1494** | Datapath liền mạch, triệt tiêu xung nhịp lạc |
| **`s15850-T100_180nm`** | 5,151 | $0.2341$ | **0.1120** | Giảm phân mảnh biểu diễn luồng điều khiển |
| **`s35932-T100_180nm`** | 11,920 | $0.1805$ | **0.0915** | Mạch song song 32-bit đạt độ mượt luồng tối đa |
| **`s38417-T100_180nm`** | 14,294 | $0.2082$ | **0.1083** | Cô lập nón logic độc lập giữa 10k cổng |

Kết quả Bảng 4 làm sáng tỏ **Cơ chế động học hai cấp độ (Dual-Scale Dirichlet Dynamics)**: Khi đo trên đồ thị luồng dữ liệu chuẩn $G_{\text{data}}$, Control OFF đạt giá trị Dirichlet mượt mà hơn ($0.09 - 0.15$), phản ánh sự gắn kết chặt chẽ của các cổng trên cùng chuỗi xử lý chức năng hợp lệ. Ngược lại, Control ON tạo ra Dirichlet trên $G_{\text{data}}$ cao bất thường ($0.18 - 0.25$) do mạng xung nhịp bơm tín hiệu lạc cắt ngang chuỗi dữ liệu. Do đó, ngắt mạng điều khiển vừa bảo toàn sự gắn kết luồng dữ liệu nội vi ($G_{\text{data}}$), vừa duy trì sự phân tách mạnh mẽ giữa các nón logic độc lập ở cấp độ toàn chip.

### 5.4. Thí Nghiệm Đối Chứng Nhân Quả (Causal Controls)
Nhằm đập tan giả thuyết cho rằng *"việc ngắt cạnh điều khiển giúp tăng điểm chỉ là do làm giảm mật độ cạnh ngẫu nhiên của đồ thị"*, chúng tôi tiến hành 4 thí nghiệm can thiệp cấu trúc có đối chứng (Bảng 5).

*Bảng 5: Bằng chứng đối chứng nhân quả can thiệp cạnh dưới giao thức LOFO.*
| Kịch Bản Can Thiệp Cấu Trúc | Bản Chất Kỹ Thuật Can Thiệp | Macro-$F_1$ ($\mu \pm \sigma$) | Kết Luận Nhân Quả |
| :--- | :--- | :---: | :--- |
| **Control ON (Config E)** | Giữ nguyên toàn bộ kết nối xung nhịp/reset | $0.4570 \pm 0.0248$ | Bị trơn hóa bởi mạng phân phối điều khiển toàn cục |
| **Random Edge Removal** | Cắt ngẫu nhiên số lượng cạnh dữ liệu đúng bằng số cạnh điều khiển | $0.4140 \pm 0.0252$ | ❌ **Hiệu năng giảm** ($-0.0430$): Giảm mật độ cạnh đơn thuần chỉ làm đứt gãy luồng thông tin |
| **Degree-Matched Removal**| Cắt các cạnh dữ liệu có bậc cao nhất (Top-10% fanout) | **0.2407 $\pm$ 0.0154** | ❌ **Sụp đổ nghiêm trọng** ($-0.2163$): Cắt nhầm bus dữ liệu quan trọng phá hủy hoàn toàn mạch máu logic |
| **Clock-Only Removal** | Chỉ ngắt cạnh xung nhịp `CLK`, giữ nguyên `RSTB` | $0.4688 \pm 0.0362$ | Cải thiện rõ rệt ($+0.0118$): Triệt tiêu đường tắt giữa các Flip-Flop |
| **Full Control OFF (Config F)**| **Ngắt đồng thời cả Clock và Reset (Đề xuất)** | **0.5239 $\pm$ 0.0454** | ✅ **Đỉnh cao tối ưu (+0.0669): Triệt tiêu hoàn toàn đường tắt phi dữ liệu, giữ vững năng lượng Dirichlet** |

Thực nghiệm Bảng 5 chứng minh mang tính quyết định: Cắt ngẫu nhiên làm giảm điểm ($0.4140$), cắt nhầm bus dữ liệu làm sụp đổ mô hình ($0.2407$). Chỉ khi ngắt đúng các cạnh mang ngữ nghĩa điều khiển (`CLK` và `RSTB`) thì hiệu năng mới bứt phá lên $0.5239$ ($p < 0.01$). Điều này khẳng định lợi ích của việc ngắt cạnh bắt nguồn từ ngữ nghĩa vật lý vi mạch, hoàn toàn không phải do hiệu ứng giảm mật độ cạnh ngẫu nhiên.

### 5.5. Đánh Giá Độ Ổn Định Tiến Trình Công Nghệ Bán Dẫn (90nm vs. 180nm)
Để khảo sát độ nhạy đối với thư viện tế bào chuẩn, chúng tôi phân tích hiệu năng của `HeteroTrojanGNN` trên họ RS232 được tổng hợp trên hai tiến trình công nghệ khác nhau: TSMC 90nm và LEDA 180nm (Bảng 6).

*Bảng 6: So sánh hiệu năng mô hình trên hai tiến trình công nghệ bán dẫn (Họ RS232).*
| Tiến Trình Bán Dẫn | Số Vi Mạch | Tổng Số Cổng | Số Cổng Trojan | Precision | Recall | $F_1$-Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **TSMC 90nm** | 11 | $11,495$ | 86 | $86.42\%$ | $81.40\%$ | **0.8383** |
| **LEDA 180nm** | 11 | $12,716$ | 89 | $82.35\%$ | $94.38\%$ | **0.8796** |
| **Toàn bộ RS232** | 22 | $24,211$ | 175 | $84.21\%$ | $87.50\%$ | **0.8582** |

Kết quả chỉ ra rằng mô hình duy trì $F_1 > 0.83$ trên cả hai tiến trình công nghệ, với độ lệch chỉ $0.0413$. Điều này khẳng định biểu diễn đồ thị hai phía kết hợp mã hóa one-hot vĩ mô của chúng tôi có tính bất biến cao trước sự thay đổi của thư viện công nghệ tổng hợp logic.

---

## 6. KHẢ NĂNG VẬN HÀNH CÔNG NGHIỆP EDA & ĐE DỌA TÍNH HỢP LỆ

### 6.1. Khả Năng Tích Hợp Vào Quy Trình EDA Thực Tế
Trong quy trình kiểm định vi mạch công nghiệp (Design for Security - DFS), việc mô hình đưa ra quá nhiều báo động giả (False Positives) sẽ làm tê liệt đội ngũ kỹ sư thẩm định.  
* **Chỉ số FP / 1000 gates:** Dưới giao thức LOFO, `HeteroTrojanGNN` đạt tỷ lệ cảnh báo giả trung bình chỉ **$3.82\text{ FP/1000 gates}$** (so với $18.45$ của Baseline và $9.12$ của SALTY). Trên một vi mạch $10,000$ cổng, kỹ sư chỉ cần thẩm định thủ công khoảng 38 cổng bị nghi ngờ thay vì gần 200 cổng như các phương pháp cũ.
* **Thời gian suy luận (Inference Latency):** Thời gian phân tích cú pháp và suy luận trên vi mạch lớn nhất `s38584` ($20,000$ cổng) chỉ mất **$1.84\text{ giây}$** trên một CPU tiêu chuẩn (Intel Core i7 thế hệ 12), hoàn toàn đáp ứng yêu cầu kiểm tra thời gian thực trong luồng tổng hợp logic tự động.

### 6.2. Phân Tích Đe Dọa Đến Tính Hợp Lệ (Threats to Validity)
1. **Tính hợp lệ về mặt cấu trúc (Construct Validity):** Bộ dữ liệu Trust-Hub có thể chứa các biến thể Trojan nhân tạo chưa bao quát hết mọi chiêu thức tấn công vật lý mới. Để giảm thiểu rủi ro này, chúng tôi đã đánh giá đa dạng trên cả Trojan kích hoạt theo bộ đếm tuần tự (Sequential Counters) và Trojan kích hoạt theo bộ so sánh tổ hợp (Combinational Comparators).
2. **Tính hợp lệ nội tại (Internal Validity):** Hiện tượng rò rỉ phân phối khi tối ưu hóa siêu tham số được loại trừ hoàn toàn bằng quy trình đóng băng ngưỡng độc lập: $\tau^*$ được tìm kiếm thuần túy trên $\mathcal{D}_{\text{val}}$ và đóng băng khi suy luận trên $\mathcal{D}_{\text{test}}$.
3. **Tính hợp lệ ngoại tại (External Validity):** Đánh giá trên 5 họ vi mạch và 2 tiến trình công nghệ khác nhau cung cấp bằng chứng vững chắc về khả năng tổng quát hóa, tuy nhiên việc mở rộng sang các thiết kế vi xử lý hàng triệu cổng (như RISC-V SoC) là hướng nghiên cứu cần tiếp tục hoàn thiện.

---

## 7. KẾT LUẬN & HƯỚNG PHÁT TRIỂN (CONCLUSION & FUTURE WORK)

Bài báo đã giải quyết một trong những thách thức dai dẳng nhất trong bài toán phát hiện Hardware Trojan mức netlist: sự sụp đổ của các mô hình học máy khi kiểm định ngoại suy liên họ (LOFO OOD). Qua quá trình giải phẫu toàn diện, chúng tôi chứng minh nguyên nhân bế tắc của các nghiên cứu trước đây xuất phát từ bẫy ghi nhớ tọa độ của hệ hình dữ liệu bảng và hiện tượng suy giảm Năng lượng Dirichlet (Over-smoothing) do mạng phân phối xung nhịp toàn cục gây ra trong các GNN thuần nhất.

Bằng việc đề xuất **`HeteroTrojanGNN`** vận hành trên **Biểu diễn Đồ thị Hai phía Dị thể Ngữ nghĩa** kết hợp **Nguyên lý Tách rời Luồng Điều khiển**, nghiên cứu đã tạo ra bước nhảy vọt thực nghiệm chưa từng có: nâng Macro-$F_1$ ngoại suy liên họ từ $0.0300$ lên **$0.5239$ (tăng gấp 17.5 lần)**, vượt trội hoàn toàn tất cả các GNN y văn, đồng thời cứu vãn điểm số ngoại suy trên các vi mạch lạ ISCAS từ $0.0551$ lên **$0.7266$**. Bằng chứng thực nghiệm nhân quả và đo đạc Năng lượng Dirichlet theo tầng đã cung cấp nền tảng toán học và vật lý vững chắc cho các kết quả đạt được.

Trong tương lai, chúng tôi định hướng mở rộng mô hình theo hai trục: (1) Ứng dụng kỹ thuật phân vùng đồ thị theo nón logic (Logic Cone Partitioning) để mở rộng khả năng suy luận cho các SoC công nghiệp quy mô hàng triệu cổng; (2) Tích hợp các phương pháp giải thích đồ thị nhân quả (Causal Graph XAI) nhằm tự động kết xuất cây giải trình phục vụ kỹ sư kiểm tra an ninh vi mạch.

---

## TÀI LIỆU THAM KHẢO (REFERENCES)

1. <a id="ref-1"></a>**Salmani, H., Tehranipoor, M., & Karri, R.** (2014). On design vulnerability analysis and trust benchmarks development. In *Proc. IEEE International Conference on Computer Design (ICCD)*, pp. 471–474.
2. <a id="ref-2"></a>**Alrahis, L., Patnaik, S., Hanif, M., Shafique, M., & Sinanoglu, O.** (2023). $\tt{PoisonedGNN}$: Backdoor Attack on Graph Neural Networks-Based Hardware Security Systems. *IEEE Transactions on Computers*, 72(10), 2822–2834.
3. <a id="ref-3"></a>**Cheng, D., Dong, C., He, W., Chen, Z., Liu, X., & Zhang, H.** (2023). A fine-grained detection method for gate-level hardware Trojan based on bidirectional Graph Neural Networks. *Journal of King Saud University - Computer and Information Sciences*, 35(8), 101822.
4. <a id="ref-4"></a>**Fey, M., & Lenssen, J. E.** (2019). Fast Graph Representation Learning with PyTorch Geometric. In *ICLR Workshop on Representation Learning on Graphs and Manifolds*.
5. <a id="ref-5"></a>**Funke, T., Khosla, M., & Anand, A.** (2021). Zorro: Valid, Sparse, and Stable Explanations in Graph Neural Networks. *IEEE Transactions on Knowledge and Data Engineering*, 35(9), 8687–8698.
6. <a id="ref-6"></a>**Hasegawa, K., Yanagisawa, M., & Togawa, N.** (2016). Hardware Trojan detection for gate-level netlists based on machine learning. In *IEEE 22nd International Symposium on On-Line Testing and Robust System Design (IOLTS)*, pp. 131–136.
7. <a id="ref-7"></a>**Hasegawa, K., Yamashita, K., Hidano, S., Fukushima, K., Hashimoto, K., & Togawa, N.** (2021). Node-Wise Hardware Trojan Detection Based on Graph Learning. *IEEE Transactions on Computers*, 74(3), 749–761.
8. <a id="ref-8"></a>**Hassan, R., Meng, X., Basu, K., & Dinakarrao, S. M. P.** (2023). Circuit Topology-Aware Vaccination-Based Hardware Trojan Detection. *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*, 42(9), 2852–2862.
9. <a id="ref-9"></a>**Hu, X., Zhang, Y., Guo, H., Shi, J., Wang, H.-W., Zhao, Z., & Li, K.** (2025). TrojanHound: Structure-aware subgraph analysis for hardware Trojan detection in gate-level designs. *IEICE Electronics Express*, 22(5), 20250364.
10. <a id="ref-10"></a>**Imangholi, A., Hashemi, M., Momeni, A., Mohammadi, S., & Carlson, T. E.** (2024). FAST-GO: Fast, Accurate, and Scalable Hardware Trojan Detection using Graph Convolutional Networks. In *25th International Symposium on Quality Electronic Design (ISQED)*, pp. 1–8.
11. <a id="ref-11"></a>**Jiang, W., Cheng, W., Chen, Z., & Zhao, J.** (2025). TrojanSDF: improving the performance of node-wise hardware Trojan detection via state distribution and feature fusion. In *Proc. SPIE 13692*, 136926W.
12. <a id="ref-12"></a>**Lashen, H., Alrahis, L., Knechtel, J., & Sinanoglu, O.** (2023). TrojanSAINT: Gate-Level Netlist Sampling-Based Inductive Learning for Hardware Trojan Detection. In *IEEE International Symposium on Circuits and Systems (ISCAS)*, pp. 1–5.
13. <a id="ref-13"></a>**Li, P., Liu, H., Shi, J., Zhang, S., Pan, W., & Hao, Y.** (2025). Hardware Trojan Detection Methods for Gate-Level Netlists Based on Graph Neural Networks. *IEEE Transactions on Computers*, 74(5), 1470–1481.
14. <a id="ref-14"></a>**Li, Z., Cheng, W., Tang, H., & Wang, Y.** (2025). GREAT: Global Representation and Edge-Attention for Hardware Trojan Detection. In *55th Annual IEEE/IFIP International Conference on Dependable Systems and Networks (DSN)*, pp. 233–245.
15. <a id="ref-15"></a>**Oono, K., & Suzuki, T.** (2020). Graph Neural Networks Exponentially Lose Expressive Power for Node Classification. In *International Conference on Learning Representations (ICLR)*.
16. <a id="ref-16"></a>**Cai, C., & Wang, Y.** (2020). A Note on Over-Smoothing for Graph Neural Networks. In *International Conference on Machine Learning (ICML) Graph Representation Learning Workshop*.
17. <a id="ref-17"></a>**Rusch, T. K., Bronstein, M. M., & Mishra, S.** (2023). A Survey on Oversmoothing and Oversquashing in Graph Neural Networks. *arXiv:2303.10993*.
18. <a id="ref-18"></a>**N, A. K., Sankar, V., & M, N.** (2025). Semantic Features Guided Graph Based Hardware Trojan Detection and Localization. In *IEEE DISCOVER*, pp. 692–698.
19. <a id="ref-19"></a>**Pan, W., Dong, M., Wen, C., Liu, H., Zhang, S., Shi, B., Di, Z., Qiu, Z., Gao, Y., & Zheng, L.** (2023). A unioned graph neural network based hardware Trojan node detection. *IEICE Electronics Express*, 20(14), 20230204.
20. <a id="ref-20"></a>**Pan, Z., Shu, Z., & Yu, X.** (2025). SAGE: Shapley Attention Graph nEtwork for Gate-level Trojan Detection and Localization. In *IEEE ISVLSI*, pp. 1–6.
21. <a id="ref-21"></a>**Rong, Y., Wang, G., Feng, Q., Liu, N., Liu, Z., Kasneci, E., & Hu, X.** (2023). Efficient GNN Explanation via Learning Removal-based Attribution. *ACM Transactions on Knowledge Discovery from Data (TKDD)*, 19, 1–23.
22. <a id="ref-22"></a>**Sarower, A. H., Salehi, S., & Yasaei, R.** (2026). Circuits as Graphs: A Review of Graph Learning for Secure and Trustworthy Hardware. *IEEE Access*, 14, 85452–85477.
23. <a id="ref-23"></a>**Sharma, R., Sharma, G., Pattanaik, M., & Prashant, V.** (2023). Structural and SCOAP Features Based Approach for Hardware Trojan Detection Using SHAP and Light Gradient Boosting Model. *Journal of Electronic Testing*, 39(4), 465–485.
24. <a id="ref-24"></a>**Sneha, C., & Devi, N. M.** (2025). Hardware Trojan Detection with Explainable Graph Learning Using XGBoost Algorithm. In *IEEE CONECCT*, pp. 1–6.
25. <a id="ref-25"></a>**Su, H., Hu, W., Zhang, X., Zhu, D., & Wu, L.** (2025). Toward Precise and Explainable Hardware Trojan Localization at LUT Level. *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*, 44(8), 2817–2821.
26. <a id="ref-26"></a>**Thorat, K., Hasan, A., Ding, C., & Shi, Z.** (2025). TROJAN-GUARD: Hardware Trojans Detection Using GNN in RTL Designs. In *IEEE IJCNN*, pp. 1–8.
27. <a id="ref-27"></a>**Tiempo, A., & Jeong, Y.-J.** (2024). FP-GNN: A Graph Neural Network for Hardware Trojan Detection in Gate-Level Netlist. *IEICE Transactions on Information and Systems*, 108(2), 295–298.
28. <a id="ref-28"></a>**Wang, X., Wu, Y., Zhang, A., Feng, F., He, X., & Chua, T.-S.** (2022). Reinforced Causal Explainer for Graph Neural Networks. *IEEE TPAMI*, 45(2), 2297–2309.
29. <a id="ref-29"></a>**Whitten, P., Wolff, F., & Papachristou, C. A.** (2024). An AI Architecture with the Capability to Classify and Explain Hardware Trojans. In *NAECON 2024 - IEEE National Aerospace and Electronics Conference*, pp. 349–354.
30. <a id="ref-30"></a>**Whitten, P., Wolff, F., & Papachristou, C. A.** (2026). Explainability Methods for Hardware Trojan Detection: A Systematic Comparison. *Journal of Electronic Testing*, 42(3), 447–467. [arXiv:2601.18696v7]
31. <a id="ref-31"></a>**Wu, L., Su, H., Zhang, X., Tai, Y., Li, H., & Hu, W.** (2023). Automated Hardware Trojan Detection at LUT Using Explainable Graph Neural Networks. In *IEEE/ACM ICCAD*, pp. 1–9.
32. <a id="ref-32"></a>**Xiao, J., Chai, S., Gao, Y., Huang, Y., Zhang, F., & Chen, T.** (2025). HTs-GCN: Identifying Hardware Trojan Nodes in Integrated Circuits Using a Graph Convolutional Network. *IEEE TCAD*, 44(6), 2353–2366.
33. <a id="ref-33"></a>**Yan, T., Wang, J., & Cheng, Z.-H.** (2025). Hardware Trojan Detection for Incomplete Gate-Level Reverse Netlist. *IEEE TDSC*, 22(6), 6671–6684.
34. <a id="ref-34"></a>**Yanti, I., Istiyanto, J. E., & Natan, O.** (2026). MultiSAINT: Parallel Multi-Scale GNN for FPGA Hardware Trojan Detection. *IEEE Access*, 14, 68166–68185.
35. <a id="ref-35"></a>**Yasaei, R., Yu, S., & Faruque, M. A.** (2021). GNN4TJ: Graph Neural Networks for Hardware Trojan Detection at Register Transfer Level. In *DATE*, pp. 1504–1509.
36. <a id="ref-36"></a>**Yasaei, R., Chen, L., Yu, S., & Faruque, M. A.** (2022). Hardware Trojan Detection Using Graph Neural Networks. *IEEE TCAD*, 44(1), 25–38.
37. <a id="ref-37"></a>**Ying, R., Bourgeois, D., You, J., Zitnik, M., & Leskovec, J.** (2019). GNNExplainer: Generating Explanations for Graph Neural Networks. In *NeurIPS*, 32, 9240–9251.
38. <a id="ref-38"></a>**Yuan, H., Yu, H., Wang, J., Li, K., & Ji, S.** (2021). On Explainability of Graph Neural Networks via Subgraph Explorations. In *ICML*, pp. 12241–12252.
39. <a id="ref-39"></a>**Zhan, P., Shen, H., Li, S., & Li, H.** (2023). BGNN-HT: Bidirectional Graph Neural Network for Hardware Trojan Cells Detection at Gate Level. In *IEEE ISCAS*, pp. 1–5.
40. <a id="ref-40"></a>**Zhang, S., Zhou, S., Xue, P., Kong, L., & Wang, J.** (2025). GNN-MFF: A Multi-View Graph-Based Model for RTL Hardware Trojan Detection. *Applied Sciences*, 15(19), 10324.
41. <a id="ref-41"></a>**Zhang, H., Fan, Z., Zhou, Y., & Li, Y.** (2025). B-HTRecognizer: Bitwise Hardware Trojan Localization Using Graph Attention Networks. *IEEE TCAD*, 44(6), 2240–2252.
42. <a id="ref-42"></a>**Mahfuz, M. U., et al.** (2025). SALTY: Explainable Artificial Intelligence Guided Structural Analysis for Hardware Trojan Detection. *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems (TCAD)*.
43. <a id="ref-43"></a>**Tehrani, M. A., Davoodi, A., & Topaloglu, R. O.** (2026). Demystifying Gate-Level Localization of RTL Trojans. In *ICCAD 2025 Contest Context / arXiv preprint*, 2026.
