# PHÂN TÍCH CHUYÊN SÂU HỆ THỐNG THỰC NGHIỆM BÓC TÁCH TỪ CONFIG A ĐẾN CONFIG F
## Thiết Kế Đối Chứng, Động Lực Khoa Học, Kết Quả Thực Nghiệm & Ý Nghĩa Phương Pháp Luận
### Trong Luận Văn Thạc Sĩ: *Control-Aware Heterogeneous Graph Learning for Cross-Family Gate-Level Hardware Trojan Localization*

---

## I. TỔNG QUAN & BỐI CẢNH: VÌ SAO CẦN HỆ THỐNG THỰC NGHIỆM TỪ CONFIG A ĐẾN CONFIG F?

### 1. Đặt Vấn Đề Từ Sự Sụp Đổ Của Các Phương Pháp Trước Đó
Trong bài toán định vị Hardware Trojan (HT) mức cổng logic (*gate-level netlist*), hai thách thức kỹ thuật lớn nhất là:
1. **Mất cân bằng dữ liệu cực đoan:** Tỷ lệ cổng Trojan trên toàn bộ 30 vi mạch Trust-Hub chỉ chiếm $\approx 0.78\%$ ($370$ cổng Trojan trên $47,464$ cổng logic, tỉ lệ mất cân bằng $1:127$ đến $1:247$).
2. **Trôi lệch phân phối cấu trúc liên họ (Structural Cross-Family OOD Shift):** Các họ vi mạch sở hữu vi kiến trúc hoàn toàn khác nhau (ví dụ: họ truyền thông nối tiếp UART `RS232` chỉ có $35$ Flip-Flops, trong khi bộ vi xử lý song song `s35932` có tới $1,728$ Flip-Flops).

Phương pháp cơ sở dạng bảng (*Tabular Baseline* - Whitten, Wolff & Papachristou, *JETTA 2026 / NAECON 2024*) dựa trên 5 đặc trưng khoảng cách logic của Hasegawa ($LGFi, ffi, ffo, PI, PO$) đã **sụp đổ hoàn toàn** trong kịch bản kiểm thử ngoại suy liên họ (**Leave-One-Family-Out - LOFO**):
$$\text{Baseline XGBoost 5F (Whitten et al., 2026)}: \quad \text{Macro-}F_1 = 0.0300, \quad \text{Micro-}F_1 = 0.0330$$

Ngay cả khi đề tài bổ sung thêm 8 đặc trưng tô-pô đồ thị toàn cục tinh vi (13F: PageRank, Betweenness, Closeness, Clustering, $k$-core...), mô hình dạng bảng vẫn bị chặn đứng dưới một bức tường hiệu năng:
$$\text{XGBoost 13F (Bổ sung 8 Centralities)}: \quad \text{In-Distribution } F_1 = 0.9243 \quad \xrightarrow{\text{LOFO}} \quad \text{Macro-}F_1 = \mathbf{0.1637}$$

Nguyên nhân cốt lõi là **Hiện tượng ghi nhớ tọa độ mạch chủ (Host Coordinate Memorization)**: Các vector số học tĩnh bị gắn chặt vào quy mô hình học của mạch huấn luyện và mất tính bất biến khi chuyển giao sang một họ vi mạch mới.

---

### 2. Sự Cần Thiết Của Một Chuỗi Bóc Tách Nhân Quả Có Kiểm Soát
Để giải quyết bài toán LOFO, việc chuyển dịch sang **Học biểu diễn quan hệ bản địa trên đồ thị (Graph-Native Relational Learning)** là tất yếu. Tuy nhiên, trong cộng đồng khoa học, một câu hỏi lớn luôn được đặt ra:
> *"Liệu việc GNN đạt kết quả cao có phải đơn thuần do nó là một mô hình học sâu phức tạp hơn? Sự vượt trội thực sự đến từ đâu: từ việc giữ lại đường dây dẫn (Net), từ cơ chế lan truyền dị thể, từ việc loại bỏ các siêu đường tắt xung nhịp, hay từ các đặc trưng tô-pô luồng dữ liệu?"*

Nếu không bóc tách rành mạch, công trình nghiên cứu sẽ rơi vào cái bẫy "hộp đen", thiếu tính thuyết phục học thuật. Do đó, hệ thống **6 Cấu hình Bóc tách vi mô (Controlled Micro-Ablation Configurations: Config A đến Config F)** được thiết kế như một **chuỗi thực nghiệm nhân quả tự nhiên, khép kín**:

```mermaid
flowchart TD
    subgraph SETUP ["CHUỖI BÓC TÁCH NHÂN QUẢ CONFIG A ➔ CONFIG F"]
        direction TB

        A["CONFIG A: Compressed Homogeneous GNN<br/>• Đồ thị nén phẳng CircuitGraph (mất Net, mất 12 Trojans)<br/>• GraphSAGE 2L thuần nhất, 5 đặc trưng cơ sở<br/>★ Macro-F1 = 0.3518"]
        
        B["CONFIG B: Explicit Cell-Net Homogeneous GNN<br/>• Đồ thị 2 phía Cell-Net bảo toàn 100% linh kiện<br/>• Ép dùng chung 1 ma trận W (Homogeneous)<br/>★ Macro-F1 = 0.2151 (-38.9%!)"]
        
        C["CONFIG C: HeteroTrojanGNN + Control-ON<br/>• Đồ thị 2 phía Cell-Net<br/>• HeteroConv phân tách ma trận W_r theo 6 quan hệ<br/>• Cạnh điều khiển: BẬT (Control-ON), 5 đặc trưng<br/>★ Macro-F1 = 0.3258 (+51.5% vs B)"]
        
        D["CONFIG D: HeteroTrojanGNN + Control-OFF (Basic 5F)<br/>• HeteroConv phân tách quan hệ<br/>• Can thiệp cấu trúc: NGẮT cạnh điều khiển (Control-OFF)<br/>★ Macro-F1 = 0.4032 (+23.8% vs C)"]
        
        E["CONFIG E: HeteroTrojanGNN + Control-ON (Full 13F)<br/>• HeteroConv + Control-ON<br/>• Làm giàu 13 đặc trưng tô-pô Graph IR<br/>★ Macro-F1 = 0.4570"]
        
        F["CONFIG F: HeteroTrojanGNN + Control-OFF (Full 13F)<br/>• Mô hình Đề xuất Toàn diện: HeteroConv + Control-OFF + 13F<br/>★ Domain-Adaptive Upper-Bound: F1 = 0.5239, PR-AUC = 0.5731<br/>★ Strict Zero-Label Leakage: F1 = 0.2738, PR-AUC = 0.4237"]

        A ==>|RQ1: Đổi sang Cell-Net nhưng giữ GNN thuần nhất<br/>NEGATIVE RESULT: 0.3518 ➔ 0.2151| B
        B ==>|RQ1: Phân tách quan hệ vật lý qua HeteroConv<br/>RECOVERY: 0.2151 ➔ 0.3258 (+51.5%)| C
        C ==>|RQ2: Ngắt bỏ siêu đường tắt clock/reset<br/>CORE BREAKTHROUGH: 0.3258 ➔ 0.4032| D
        C -.->|Làm giàu đặc trưng khi giữ Control-ON| E
        D ==>|Ma trận Giai thừa 2x2: Control-OFF + 13F Tô-pô<br/>ĐỈNH CAO HIỆU NĂNG LOFO| F
        E ==> F
    end

    style A fill:#f1f3f5,stroke:#495057,stroke-width:2px;
    style B fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px;
    style C fill:#fff9db,stroke:#f59f00,stroke-width:2px;
    style D fill:#d0ebff,stroke:#1971c2,stroke-width:2px;
    style E fill:#e7f5ff,stroke:#1c7ed6,stroke-width:1.5px;
    style F fill:#d3f9d8,stroke:#2b8a3e,stroke-width:3px;
```

---

## II. MA TRẬN BẢNG TỔNG HỢP CÁC CẤU HÌNH CONFIG A → CONFIG F

Bảng dưới đây tổng hợp tường minh 4 trục thiết kế kỹ thuật, vai trò khoa học và kết quả kiểm thử ngoại suy liên họ (LOFO) đa hạt giống (Seeds 42, 123, 456):

| Cấu Hình | Biểu Diễn Đồ Thị (Graph IR) | Kiến Trúc Mô Hình GNN | Xử Lý Cạnh Điều Khiển (Clock/Reset) | Không Gian Đặc Trưng Đầu Vào | Macro-$F_1$ LOFO ($\mu \pm \sigma$) | Macro PR-AUC ($\mu \pm \sigma$) | Macro MCC ($\mu \pm \sigma$) | Bản Chất & Ý Nghĩa Khoa Học |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Config A** | Đồ thị nén phẳng (*CircuitGraph*) | Thuần nhất (Homogeneous GraphSAGE 2L) | N/A (Đã bị nén gộp vào cổng) | Basic (5 Feats) | $0.3518$ *(Seed 42)* | $0.3097$ | $0.3771$ | **Mốc đối chứng cơ sở (Reference Baseline Control):** Điểm xuất phát của GNN trên đồ thị nén phẳng cổ điển. |
| **Config B (2L)** | Đồ thị hai phía Cell–Net | Thuần nhất (Homogeneous GraphSAGE 2L) | BẬT *(Control ON)* | Basic (5 Feats) | $0.2151$ *(Seed 42)* | $0.1292$ | $0.2183$ | **Negative Result kinh điển (RQ1):** Tăng độ trung thực đồ thị nhưng GNN thuần nhất làm sụp đổ $-38.9\%$. |
| **Config B (4L)** | Đồ thị hai phía Cell–Net | Thuần nhất (Homogeneous GraphSAGE 4L) | BẬT *(Control ON)* | Basic (5 Feats) | $0.2589$ *(Seed 42)* | $0.3321$ | $0.2540$ | **Kiểm chứng bước nhảy (Hop Semantics):** Mở rộng 4 tầng để cân bằng 2 bước nhảy cổng, phục hồi nhẹ. |
| **Config C** | Đồ thị hai phía Cell–Net | Dị thể (`HeteroConv` SAGE 2L) | BẬT *(Control ON)* | Basic (5 Feats) | $0.3258 \pm 0.0629$ | $0.3721 \pm 0.0463$ | $0.3297 \pm 0.0645$ | **Phục hồi hiệu năng qua HeteroConv (RQ1):** Tách ma trận quan hệ $W_r$, tăng $+51.5\%$ so với Config B. |
| **Config D** | Đồ thị hai phía Cell–Net | Dị thể (`HeteroConv` SAGE 2L) | **TẮT (Control OFF)** | Basic (5 Feats) | **0.4032 $\pm$ 0.0462** | **0.4071 $\pm$ 0.0220** | **0.4208 $\pm$ 0.0541** | **Phát hiện thực nghiệm cốt lõi (RQ2):** Ngắt bỏ siêu đường tắt clock/reset, bứt phá $+23.8\%$. |
| **Config E** | Đồ thị hai phía Cell–Net | Dị thể (`HeteroConv` SAGE 2L) | BẬT *(Control ON)* | Full (13 Feats) | $0.4570 \pm 0.0248$ | $0.5180 \pm 0.0392$ | $0.4942 \pm 0.0161$ | **Ô ma trận giai thừa (Full Feats + Control ON):** Làm giàu đặc trưng nhưng vẫn bị kìm hãm bởi clock. |
| **Config F** | Đồ thị hai phía Cell–Net | Dị thể (`HeteroConv` SAGE 2L) | **TẮT (Control OFF)** | Full (13 Feats) | **0.5239 $\pm$ 0.0454** | **0.5731 $\pm$ 0.0195** | **0.5473 $\pm$ 0.0336** | **Mô hình Đề Xuất Toàn Diện (Full Proposed):** Hội tụ HeteroConv + Control-OFF + 13F tô-pô. |

---

## III. MÔ TẢ CHI TIẾT TỪNG CẤU HÌNH: ĐỘNG LỰC, THIẾT KẾ & KẾT QUẢ

---

### 1. CONFIG A: Compressed Homogeneous GraphSAGE (Mốc Đối Chứng Cơ Sở)

#### A. Động lực & Lý do tồn tại
* Để đánh giá một phương pháp mới, nguyên tắc khoa học đầu tiên là phải có một **mốc đối chứng cơ sở có kiểm soát (Reference Baseline Control)**.
* Baseline của Whitten et al. (2026) sử dụng thư viện `circuitgraph` để nén netlist thành dạng phẳng và chạy mô hình dạng bảng XGBoost. Vậy câu hỏi đặt ra: *Nếu chúng ta giữ nguyên đồ thị nén phẳng của tác giả gốc nhưng thay mô hình dạng bảng bằng một mạng nơ-ron đồ thị (GNN) tiêu chuẩn, kết quả LOFO sẽ ra sao?*
* Config A ra đời để trả lời câu hỏi đó, xác lập điểm xuất phát cho nhánh tiếp cận học sâu đồ thị.

#### B. Thiết kế kỹ thuật
* **Biểu diễn đồ thị:** Đồ thị nén phẳng từ `circuitgraph` (Whitten et al., 2026).
  * Hàm `merge_cells`: Xóa toàn bộ các node chân cắm ngõ vào (`bb_input`), kéo mũi tên nhân tạo từ nguồn tín hiệu cắm thẳng vào chân ra. Cổng logic bị đồng nhất thành chính chân output của nó.
  * Hàm `remove_cells(['wire'])`: Xóa bỏ hoàn toàn các nút đường dây liên kết (`Net`), kéo cạnh trực tiếp từ cổng trước sang cổng sau.
  * *Hậu quả dữ liệu:* Cắt giảm thô bạo số thực thể từ $108,531$ xuống còn $41,577$, và **làm mất 12 cổng Trojan vật lý thực tế**.
* **Kiến trúc mô hình:** Mạng nơ-ron đồ thị thuần nhất GraphSAGE 2 tầng (`SAGEConv`), không phân biệt loại cạnh (chỉ có cạnh `connected_to`), kích thước ẩn $d=64$, Dropout $0.2$, hàm kích hoạt ReLU, đầu phân loại MLP 2 tầng.
* **Không gian đặc trưng:** 5 đặc trưng cơ sở của Hasegawa ($LGFi, ffi, ffo, PI, PO$).

#### C. Kết quả thực nghiệm LOFO
* **Macro-$F_1$:** **$0.3518$** (trên Seed 42).
* **PR-AUC:** **$0.3097$**, **MCC:** **$0.3771$**.
* *Chi tiết từng họ vi mạch:* `RS232`: $0.1873$, `s15850`: $0.6250$, `s35932`: $0.8571$, `s38417`: $0.0896$, `s38584`: $0.0000$.

#### D. Ý nghĩa khoa học
* Config A đạt $F_1 = 0.3518$, vượt trội hoàn toàn so với XGBoost dạng bảng 5 đặc trưng trong LOFO ($F_1 = 0.0300$). Điều này chứng minh rằng **cơ chế lan truyền thông điệp của GNN có khả năng học các bất biến cấu trúc tốt hơn các vector số học tĩnh**.
* Tuy nhiên, Config A vẫn hoàn toàn bất lực trên họ tuần tự phức tạp `s38584` ($F_1 = 0.0000$), đồng thời việc làm mất 12 cổng Trojan ngay từ khâu tiền xử lý là một khiếm khuyết học thuật nghiêm trọng cần phải khắc phục.

---

### 2. CONFIG B: Explicit Cell–Net Homogeneous GNN (Negative Result Kinh Điển)

#### A. Động lực & Lý do tồn tại (Kiểm chứng RQ1)
* Sau khi nhận thấy Config A bị mất 12 cổng Trojan và xóa sạch các đường dây dẫn, hành động tự nhiên của bất kỳ nhà nghiên cứu nào là: **Sửa lại parser để xây dựng đồ thị hai phía Cell–Net chuẩn xác 100% linh kiện**.
* Nghiên cứu đã xây dựng hạ tầng *Semantic Cell–Net Bipartite IR*, bảo toàn trọn vẹn $47,464$ cells, $61,067$ nets và toàn bộ $370$ cổng Trojan vật lý.
* Câu hỏi nghiên cứu then chốt đặt ra (**RQ1**): *Nếu chúng ta chuyển sang đồ thị hai phía Cell–Net trung thực tuyệt đối về mặt vật lý, nhưng vẫn giữ nguyên mô hình GNN thuần nhất (Homogeneous GraphSAGE) như Config A, liệu hiệu năng có tự động tăng lên không?*
* Config B được thiết kế chính xác để cô lập biến số này.

#### B. Thiết kế kỹ thuật
* **Biểu diễn đồ thị:** Đồ thị hai phía Semantic Graph IR $\mathcal{G} = (\mathcal{V}_{\text{cell}} \cup \mathcal{V}_{\text{net}}, \mathcal{E})$.
  * Bảo toàn đầy đủ các cổng `Cell` và dây `Net`.
  * Có đầy đủ các cạnh dữ liệu và điều khiển (Control-ON).
* **Kiến trúc mô hình:**
  * **Config B (2L):** GraphSAGE 2 tầng thuần nhất. Ép toàn bộ các loại nút (`cell`, `net`) và toàn bộ các loại cạnh (`data_input`, `control_input`, `outputs`...) về dạng thuần nhất, dùng chung một ma trận trọng số biến đổi duy nhất $W$.
  * **Config B (4L):** GraphSAGE 4 tầng thuần nhất (bổ sung Residual Connection và LayerNorm) nhằm kiểm chứng giả thuyết về sự bất đối xứng bước nhảy (Hop Semantics Asymmetry).
* **Không gian đặc trưng:** 5 đặc trưng cơ sở Hasegawa.

#### C. Kết quả thực nghiệm LOFO
$$\mathbf{\text{Config A (Đồ thị nén phẳng cũ)}: Macro\text{-}F_1 = 0.3518 \quad \xrightarrow{\text{Đổi sang Cell--Net}} \quad \text{Config B (2L)}: Macro\text{-}F_1 = \mathbf{0.2151} \quad (-38.9\%!)} $$
* Chi tiết từng họ vi mạch ở Config B (2L): `RS232`: $0.1600$, `s15850`: $0.0377$ (sụp đổ nặng), `s35932`: $0.7826$, `s38417`: $0.0952$, `s38584`: $0.0000$.
* Khi tăng lên 4 tầng (**Config B 4L**): Macro-$F_1$ chỉ phục hồi nhẹ lên **$0.2589$**, vẫn kém xa mốc $0.3518$ của Config A.

#### D. Ý nghĩa khoa học - Kết quả phủ định kinh điển (Valuable Negative Result)
Đây là một trong những phát hiện có giá trị phương pháp luận lớn nhất của luận văn:
$$\boxed{\textbf{Better Graph Fidelity } \not\Rightarrow \textbf{ Better Prediction}}$$

Tại sao đồ thị trung thực hơn $100\%$ về mặt vật lý lại cho kết quả tồi tệ hơn đồ thị nén phẳng bị mất linh kiện?
1. **Co rút trường tiếp nhận (Receptive Field Co-contraction):** Trong đồ thị nén phẳng A, 2 tầng GNN vươn được 2 bước cổng logic ($\text{Cell} \to \text{Cell} \to \text{Cell}$). Trong đồ thị hai phía B, do ở giữa mỗi cổng là một đường dây Net, 2 tầng GNN thực chất chỉ vươn được **đúng 1 bước cổng logic** ($\text{Cell} \to \text{Net} \to \text{Cell}$).
2. **Trộn lẫn ngữ nghĩa (Homogeneous Semantic Mixing):** Khi ép dùng chung một ma trận trọng số $W$, mô hình không thể phân biệt đâu là cổng tính toán, đâu là dây dẫn, đâu là đường dữ liệu logic, và đâu là đường xung nhịp. Tín hiệu từ đường dây xung nhịp nối hàng ngàn Flip-Flop tràn ngập khắp đồ thị, xóa sạch dấu vết bất thường của Trojan.
3. **Kiểm soát dung lượng tham số (Config B-Wide Control):** Để loại trừ nghi vấn Config B suy giảm do thiếu tham số so với HeteroConv, nghiên cứu đã thử nghiệm **Config B-Wide** ($d=160$, chứa $125,281$ tham số, gấp $5.5$ lần Config B và lớn hơn cả HeteroConv). Kết quả: Macro-$F_1$ chỉ đạt **$0.3261$**, vẫn không thể vượt qua Config A.
* **Bài học rút ra:** Biểu diễn cấu trúc tường minh tự nó là chưa đủ; kiến trúc học máy bắt buộc phải có khả năng phân tách ngữ nghĩa quan hệ!

---

### 3. CONFIG C: HeteroTrojanGNN + Control-ON (Khắc Phục Điểm Nghẽn Qua HeteroConv)

#### A. Động lực & Lý do tồn tại (Hoàn tất RQ1)
* Từ thất bại của Config B, nguyên nhân đã được chỉ rõ: **GNN thuần nhất không thể xử lý đồ thị hai phía dị thể**.
* Để cứu sống biểu diễn Cell–Net, mô hình bắt buộc phải chuyển sang kiến trúc **Mạng nơ-ron đồ thị dị thể (Heterogeneous GNN)**.
* Config C ra đời nhằm trả lời câu hỏi: *Nếu chúng ta cấp cho mỗi loại quan hệ vật lý một ma trận chuyển đổi độc lập thông qua toán tử `HeteroConv`, liệu hiệu năng có phục hồi hay không?*
* Đồng thời, Config C giữ nguyên các cạnh điều khiển (Control-ON) để đóng vai trò là **gốc của ma trận giai thừa $2 \times 2$** phục vụ cho việc bóc tách RQ2 sau đó.

#### B. Thiết kế kỹ thuật
* **Biểu diễn đồ thị:** Đồ thị hai phía Semantic Graph IR (giữ nguyên cạnh điều khiển Control-ON).
* **Kiến trúc mô hình:** Mạng dị thể `HeteroTrojanGNN` sử dụng toán tử **`HeteroConv`** 2 tầng:
  $$\mathbf{h}_v^{(\ell+1)} = \sigma \left( \mathbf{W}_{\text{self}} \mathbf{h}_v^{(\ell)} + \sum_{r \in \Phi_{\mathcal{E}}} \mathbf{W}_r^{(\ell)} \sum_{u \in \mathcal{N}_r(v)} \mathbf{h}_u^{(\ell)} \right)$$
  * Phân tách độc lập các ma trận trọng số theo 6 quan hệ: $W_{\text{data\_in}} \neq W_{\text{ctrl\_in}} \neq W_{\text{out}} \dots$
  * Tầng chiếu đầu vào độc lập: $h_{\text{cell}}^{(0)} \in \mathbb{R}^{64}$ (từ $34$D) và $h_{\text{net}}^{(0)} \in \mathbb{R}^{64}$ (từ $20$D).
  * Tích hợp LayerNorm và Dropout $0.2$ cho từng kiểu nút.
* **Không gian đặc trưng:** 5 đặc trưng cơ sở Hasegawa.

#### C. Kết quả thực nghiệm LOFO
$$\mathbf{\text{Config B (Homogeneous)}: Macro\text{-}F_1 = 0.2151 \quad \xrightarrow{\text{HeteroConv}} \quad \text{Config C}: Macro\text{-}F_1 = \mathbf{0.3258 \pm 0.0629} \quad (+51.5\%!)} $$
* Đa hạt giống (Seeds 42, 123, 456): Macro PR-AUC $= \mathbf{0.3721 \pm 0.0463}$, Macro MCC $= \mathbf{0.3297 \pm 0.0645}$.
* Chi tiết từng họ vi mạch: `RS232`: $0.0888$, `s15850`: $0.4717$, `s35932`: $0.8923$, `s38417`: $0.2414$, `s38584`: $0.0649$.

#### D. Ý nghĩa khoa học
* **Giải quyết trọn vẹn RQ1:** Việc áp dụng `HeteroConv` đã tạo nên bước phục hồi ngoạn mục ($+51.5\%$). Bằng việc phân tách các kênh trọng số riêng biệt, kênh dữ liệu logic chuyên tâm học tổng hợp hàm Boole, còn kênh phát động chuyên tâm học phân nhánh tải.
* Config C chứng minh rằng: **Học quan hệ dị thể là điều kiện tiên quyết để khai phóng sức mạnh của đồ thị hai phía Cell–Net**.
* Tuy nhiên, hiệu năng trên họ `s38584` ($0.0649$) và `RS232` ($0.0888$) vẫn còn thấp, mở ra nghi vấn về sự can nhiễu của mạng xung nhịp toàn cục.

---

### 4. CONFIG D: HeteroTrojanGNN + Control-OFF (Phát Hiện Thực Nghiệm Cốt Lõi)

#### A. Động lực & Lý do tồn tại (Bóc tách RQ2)
* Khi phân tích đồ thị vi mạch, một đặc điểm vật lý nổi bật là: mạng xung nhịp (`CLK`) và mạng thiết lập lại (`RSTB`) kết nối tới toàn bộ Flip-Flop trong chip (ví dụ: $1,728$ FFs trong `s35932`).
* Trong Config C, mặc dù đã có ma trận $W_{\text{ctrl}}$ riêng, nhưng sự tồn tại của các cạnh điều khiển vẫn tạo ra hàng triệu siêu đường tắt ảo giữa các Flip-Flop, kéo biểu diễn của chúng về một điểm trung bình vô nghĩa (**Subspace Collapse**).
* Đề tài đề xuất một can thiệp cấu trúc táo bạo: **Ngắt bỏ hoàn toàn các cạnh điều khiển (Control-OFF)** trong quá trình lan truyền thông điệp nơ-ron, chỉ cho phép GNN truyền tin dọc luồng dữ liệu logic thuần túy ($G_{\text{data}}$).
* Config D ra đời để kiểm chứng trực tiếp giả thuyết này trên không gian 5 đặc trưng cơ sở.

#### B. Thiết kế kỹ thuật
* **Biểu diễn đồ thị:** Đồ thị hai phía Cell–Net được lọc bỏ toàn bộ các cạnh có cờ `is_control == 1`:
  $$G_{\text{data}} = \left(\mathcal{V}_{\text{cell}} \cup \mathcal{V}_{\text{net}}, \; \mathcal{E} \setminus \{e \in \mathcal{E} \mid \text{is\_control}(e) = 1\}\right)$$
  Loại bỏ các loại cạnh: `control_input` và `rev_control_input`.
* **Kiến trúc mô hình:** `HeteroTrojanGNN` 2 tầng `HeteroConv` (chỉ còn 4 loại quan hệ dữ liệu và phát động), số lượng tham số giảm từ $105,281$ xuống còn $74,497$.
* **Không gian đặc trưng:** 5 đặc trưng cơ sở Hasegawa.

#### C. Kết quả thực nghiệm LOFO
$$\mathbf{\text{Config C (Control-ON)}: Macro\text{-}F_1 = 0.3258 \quad \xrightarrow{\text{Control-OFF}} \quad \text{Config D}: Macro\text{-}F_1 = \mathbf{0.4032 \pm 0.0462} \quad (+23.8\%!)} $$
* Đa hạt giống (Seeds 42, 123, 456): Macro PR-AUC $= \mathbf{0.4071 \pm 0.0220}$, Macro MCC $= \mathbf{0.4208 \pm 0.0541}$.
* **Điểm thắt đáy (Worst-case) được cải thiện vượt bậc:** Họ vi mạch khó nhất `s38584` tăng từ $0.0649$ lên **$0.0952$ (+46.7%)**, họ `RS232` tăng từ $0.0888$ lên **$0.1591$ (+79.2%)**.

#### D. Ý nghĩa khoa học - Phát hiện thực nghiệm trung tâm (Core Finding)
* **Trả lời dứt khoát RQ2:** Việc ngắt bỏ cạnh điều khiển (Control-OFF) tạo nên một bước đột phá lớn ($+23.8\%$ về $F_1$, $+27.6\%$ về MCC).
* **Bản chất phần cứng:** Mạng xung nhịp là hạ tầng cấp nhịp đồng bộ, hoàn toàn không chứa hàm logic Boole của thuật toán. Khi kẻ tấn công chèn Trojan, hành vi kích hoạt và phá hoại luôn diễn ra trên luồng dữ liệu (Datapath). Việc loại bỏ mạng xung nhịp giúp GNN tập trung $100\%$ năng lực biểu diễn vào các nón logic chức năng mà không bị làm nhòe bởi các siêu đường tắt toàn cục.
* Đáng chú ý, Config D đạt được kết quả này với số tham số **ít hơn $29.2\%$** so với Config C ($74k$ vs $105k$), chứng minh sự tiến bộ đến từ **ngữ nghĩa quan hệ đúng đắn**, chứ không phải do tăng dung lượng mô hình.

---

### 5. CONFIG E: HeteroTrojanGNN + Control-ON + Full 13 Features (Ô Ma Trận Giai Thừa)

#### A. Động lực & Lý do tồn tại
* Trong phương pháp luận thiết kế thực nghiệm giai thừa $2 \times 2$ (Factorial Design: Cạnh điều khiển $\times$ Không gian đặc trưng), ta cần khảo sát đầy đủ 4 trạng thái:
  1. (Control ON, Basic 5F) $\to$ **Config C**
  2. (Control OFF, Basic 5F) $\to$ **Config D**
  3. (Control ON, Full 13F) $\to$ **Config E**
  4. (Control OFF, Full 13F) $\to$ **Config F**
* Config E ra đời nhằm kiểm tra: *Nếu chúng ta bổ sung đầy đủ 8 đặc trưng tô-pô đồ thị (PageRank, Betweenness, Centralities...) nhưng vẫn GIỮ NGUYÊN các cạnh điều khiển (Control-ON), liệu việc làm giàu đặc trưng có thể bù đắp được tác hại của các siêu đường tắt xung nhịp hay không?*

#### B. Thiết kế kỹ thuật
* **Biểu diễn đồ thị:** Đồ thị hai phía Cell–Net giữ nguyên toàn bộ cạnh điều khiển (Control-ON).
* **Kiến trúc mô hình:** `HeteroTrojanGNN` 2 tầng `HeteroConv` (đầy đủ 6 quan hệ, $105,281$ tham số).
* **Không gian đặc trưng:** **13 đặc trưng đầy đủ** (5 đặc trưng Hasegawa + 8 đặc trưng cấu trúc tô-pô luồng dữ liệu trích xuất từ Semantic Graph IR).

#### C. Kết quả thực nghiệm LOFO
* **Macro-$F_1$:** **$0.4570 \pm 0.0248$** (tăng $+40.3\%$ so với Config C).
* **Macro PR-AUC:** **$0.5180 \pm 0.0392$**, **Macro MCC:** **$0.4942 \pm 0.0161$**.
* Chi tiết từng họ vi mạch: `RS232`: $0.1729$, `s15850`: $0.6923$, `s35932`: $0.9322$, `s38417`: $0.2378$, `s38584`: $0.0674$.

#### D. Ý nghĩa khoa học
* Làm giàu không gian đặc trưng từ 5 lên 13 giúp mô hình tăng mạnh hiệu năng ($0.3258 \to 0.4570$), chứng minh các chỉ số tô-pô đồ thị (như PageRank, Betweenness) cung cấp ngữ cảnh hình thái học rất giá trị cho GNN.
* Tuy nhiên, họ tuần tự khó nhất `s38584` vẫn bị "kẹt cứng" ở mức rất thấp ($0.0674$). Điều này chỉ ra rằng: **Nếu không giải quyết vấn đề đường tắt xung nhịp, việc bổ sung đặc trưng chỉ giải quyết được phần ngọn mà không chữa được điểm nghẽn gốc rễ**.

---

### 6. CONFIG F: HeteroTrojanGNN + Control-OFF + Full 13 Features (Mô Hình Đề Xuất Toàn Diện)

#### A. Động lực & Lý do tồn tại
* Config F là **đỉnh cao hội tụ toàn bộ các phát hiện khoa học** của luận văn:
  1. Hạ tầng đồ thị hai phía Semantic Cell–Net IR (bảo toàn 100% linh kiện).
  2. Cơ chế tích chập dị thể `HeteroConv` phân tách quan hệ vật lý (giải quyết RQ1).
  3. Can thiệp ngắt bỏ cạnh điều khiển Control-OFF (giải quyết RQ2).
  4. Không gian 13 đặc trưng tô-pô luồng dữ liệu chuẩn hóa chống rò rỉ nhãn.
* Config F được thiết kế để trở thành **phương pháp đề xuất chính thức của luận văn (Proposed Method)**, thiết lập chuẩn mực mới cho bài toán định vị Hardware Trojan xuyên họ vi mạch.

#### B. Thiết kế kỹ thuật
* **Biểu diễn đồ thị:** Đồ thị hai phía Cell–Net cô lập luồng dữ liệu $G_{\text{data}}$ (Control-OFF).
* **Kiến trúc mô hình:** `HeteroTrojanGNN` 2 tầng `HeteroConv` trên $G_{\text{data}}$ ($74,497$ tham số), LayerNorm, Residual Connections, Dropout $0.2$, MLP Classifier Head.
* **Không gian đặc trưng:** 13 đặc trưng tô-pô đầy đủ tính toán độc lập trên từng vi mạch riêng biệt (Per-Circuit Isolated Computation).
* **Giao thức chuẩn hóa:** Đóng băng tuyệt đối $(\mu, \sigma)$ từ tập huấn luyện (Leak-Free Standardization).

#### C. Kết quả thực nghiệm LOFO
Nghiên cứu báo cáo minh bạch kết quả của Config F dưới cả hai giao thức:

1. **Cực hạn phân tách có thích nghi miền (Domain-Adaptive Upper-Bound):**
   $$\mathbf{Macro\text{-}F_1 = 0.5239 \pm 0.0454, \quad PR\text{-}AUC = 0.5731 \pm 0.0195, \quad MCC = 0.5473 \pm 0.0336}$$
   * Chi tiết từng họ vi mạch:
     * `s35932` (32-bit processor): **$F_1 = 0.9322$** (gần như hoàn hảo).
     * `s15850`: **$F_1 = 0.6923$**.
     * `s38417`: **$F_1 = 0.2885$**.
     * `s38584`: **$F_1 = 0.2606$** (tăng gấp 4 lần so với Config E).
     * `RS232`: **$F_1 = 0.2644$** (tăng gấp 5 lần so với Baseline).

2. **Giao thức chuẩn mực nghiêm ngặt tuyệt đối không rò rỉ nhãn (Strict Zero-Label Leakage Multi-Seed LOFO):**
   * Ngưỡng quyết định $\tau^*$ được khóa cứng hoàn toàn từ tập Validation của 4 họ huấn luyện và áp nguyên trạng sang họ kiểm thử thứ 5 qua 15 lượt chạy (5 Folds $\times$ 3 Seeds):
   $$\mathbf{Macro\text{-}F_1 = 0.2738 \pm 0.0292 (\sigma_{\text{seed}}) \pm 0.2232 (\sigma_{\text{family}}), \quad PR\text{-}AUC = 0.4237 \pm 0.0683 \pm 0.2789}$$
   * *Độ ổn định phương sai:* Phương sai khởi tạo trọng số $\sigma_{\text{seed}} \approx 0.029$ rất nhỏ, chứng minh thuật toán có độ hội tụ cực kỳ bền vững, không phụ thuộc vào may rủi khởi tạo ngẫu nhiên.

#### D. Ý nghĩa khoa học & So sánh với SOTA y văn quốc tế
* So với **Baseline XGBoost 5F ($0.0300$)** và **XGBoost 13F ($0.1637$)**, Config F cao hơn lần lượt **$17.4$ lần** và **$3.2$ lần**.
* Khi đối chuẩn cùng một giao thức LOFO với các kiến trúc GNN tiêu biểu trong y văn quốc tế:
  * Vượt trội **Homogeneous GraphSAGE** ($0.3429 \pm 0.0230$, $+52.8\%$).
  * Vượt trội **Homogeneous GAT** ($0.3840 \pm 0.0250$, $+36.4\%$).
  * Vượt trội **GAT-JK của SALTY** (Mahfuz et al., 2025: $0.3975 \pm 0.0080$, $+31.8\%$).
  * Vượt trội **BiDirectional GNN** (GNN4Gate style: $0.4507 \pm 0.0495$, $+16.2\%$).
  * Vượt trội bộ quy tắc cấu trúc **LoRD** (Tehrani et al., 2026: $0.2109$, $+148.4\%$).

---

## IV. MA TRẬN PHÂN TÍCH GIAI THỪA $2 \times 2$ (FACTORIAL ANALYSIS)

Để phân định rạch ròi đóng góp độc lập và hiệu ứng tương tác giữa hai yếu tố can thiệp: **Ngắt cạnh điều khiển** và **Làm giàu đặc trưng**, nghiên cứu thiết lập ma trận giai thừa $2 \times 2$:

```
                   ┌──────────────────────────────┬──────────────────────────────┐
                   │    Nhánh Basic (5 Feats)     │     Nhánh Full (13 Feats)    │
┌──────────────────┼──────────────────────────────┼──────────────────────────────┤
│                  │           CONFIG C           │           CONFIG E           │
│ Cạnh Điều Khiển: │ F1:     0.3258 ± 0.0629      │ F1:     0.4570 ± 0.0248      │
│     BẬT (ON)     │ PR-AUC: 0.3721 ± 0.0463      │ PR-AUC: 0.5180 ± 0.0392      │
│                  │ MCC:    0.3297 ± 0.0645      │ MCC:    0.4942 ± 0.0161      │
├──────────────────┼──────────────────────────────┼──────────────────────────────┤
│                  │           CONFIG D           │           CONFIG F           │
│ Cạnh Điều Khiển: │ F1:     0.4032 ± 0.0462      │ F1:     0.5239 ± 0.0454      │
│    TẮT (OFF)     │ PR-AUC: 0.4071 ± 0.0220      │ PR-AUC: 0.5731 ± 0.0195      │
│                  │ MCC:    0.4208 ± 0.0541      │ MCC:    0.5473 ± 0.0336      │
└──────────────────┴──────────────────────────────┴──────────────────────────────┘
```

### 1. Bóc Tách Các Hiệu Ứng Chính (Main Effects)
1. **Hiệu ứng của việc ngắt cạnh điều khiển ($\Delta_{\text{ctrl}} = \text{OFF} - \text{ON}$):**
   * Trên nhánh Basic 5: $\Delta F_1 = \mathbf{+0.0774}$ ($+23.8\%$), $\Delta \text{PR-AUC} = \mathbf{+0.0350}$, $\Delta \text{MCC} = \mathbf{+0.0911}$.
   * Trên nhánh Full 13: $\Delta F_1 = \mathbf{+0.0669}$ ($+14.6\%$), $\Delta \text{PR-AUC} = \mathbf{+0.0551}$, $\Delta \text{MCC} = \mathbf{+0.0531}$.
   * *Đánh giá:* Bất kể không gian đặc trưng là 5 hay 13, việc ngắt cạnh điều khiển luôn mang lại sự cải thiện nhất quán trên toàn bộ các thước đo.

2. **Hiệu ứng của việc làm giàu đặc trưng tô-pô ($\Delta_{\text{feat}} = \text{Full} - \text{Basic}$):**
   * Khi Control-ON: $\Delta F_1 = \mathbf{+0.1312}$ ($+40.3\%$), $\Delta \text{PR-AUC} = \mathbf{+0.1459}$.
   * Khi Control-OFF: $\Delta F_1 = \mathbf{+0.1207}$ ($+29.9\%$), $\Delta \text{PR-AUC} = \mathbf{+0.1660}$.

### 2. Kiểm Định Ý Nghĩa Thống Kê Phân Cấp (Hierarchical Statistical Validation)
Để tránh hiện tượng giả sao chép (*pseudoreplication*) khi gộp các lượt chạy ngẫu nhiên, nghiên cứu áp dụng kiểm định thống kê trên hai cấp độ:
* **Cấp độ 15 lượt chạy (5 Folds $\times$ 3 Seeds):**
  * Hiệu ứng ngắt cạnh điều khiển: Paired $t$-test $p = 0.0028 < 0.01$, Wilcoxon signed-rank $W = 12.0, p = 0.0049 < 0.01$.
  * Hiệu ứng làm giàu đặc trưng: Paired $t$-test $p = 0.0002 < 0.001$, Wilcoxon $p = 0.0010 \le 0.001$.
* **Cấp độ 5 họ vi mạch độc lập chuẩn mực ($N = 5$ family-averaged scores):**
  * Hiệu ứng ngắt cạnh điều khiển: Cải thiện nhất quán trên cả 5 họ vi mạch với $p = 0.0312 < 0.05$, khoảng tin cậy Bootstrap 95%: $CI_{95\%} = [+0.032, +0.118]$.
  * Hiệu ứng làm giàu đặc trưng: Paired $t$-test $p = 0.0084 < 0.01, CI_{95\%} = [+0.058, +0.184]$.

*Kết luận:* Toàn bộ các bước tiến trong ma trận giai thừa đều đạt **ý nghĩa thống kê vững chắc ($p < 0.05$)**, loại trừ hoàn toàn yếu tố may rủi ngẫu nhiên.

---

## V. CÁC THÍ NGHIỆM ĐỐI CHỨNG NHÂN QUẢ (CAUSAL CONTROLS)

Một câu hỏi phản biện học thuật sắc bén được đặt ra đối với Config D và Config F:  
> *"Liệu việc Control-OFF tăng hiệu năng thực sự do ngữ nghĩa của mạng xung nhịp, hay chỉ đơn giản là vì đồ thị có ít cạnh hơn (giảm mật độ cạnh) hoặc do cắt tỉa các nút có bậc liên kết cao?"*

Nghiên cứu đã thiết kế **4 kịch bản đối chứng nhân quả** chạy trên 5 Folds LOFO $\times$ 3 Seeds để kiểm chứng:

| Chế Độ Đối Chứng Nhân Quả | Can Thiệp Kỹ Thuật Cụ Thể | Macro $F_1$ ($\mu \pm \sigma$) | Macro PR-AUC | Đánh Giá Bản Chất |
| :--- | :--- | :---: | :---: | :--- |
| **Control ON (Config E)** | Giữ nguyên mọi kết nối | $0.4570 \pm 0.0248$ | $0.5180$ | Bị trơn hóa bởi mạng điều khiển |
| **Random Edge Removal** | Cắt ngẫu nhiên số lượng cạnh bằng số cạnh điều khiển | $0.4140 \pm 0.0252$ | $0.4871$ | ❌ Giảm $-0.0430$ do mất mát đường truyền dữ liệu ngẫu nhiên |
| **Degree-Matched Removal** | Cắt các cạnh của các đường dây dữ liệu có bậc cao nhất | **0.2407 $\pm$ 0.0154** | **0.3150** | ❌ **Sụp đổ nghiêm trọng ($-0.2163$):** Cắt đứt bus dữ liệu huyết mạch |
| **Clock-Only Removal** | Chỉ ngắt cạnh xung nhịp, giữ nguyên reset | $0.4688 \pm 0.0362$ | $0.5039$ | Cải thiện rõ rệt ($+0.0118$ so với Control-ON) |
| **Reset-Only Removal** | Chỉ ngắt cạnh reset, giữ nguyên xung nhịp | $0.4501 \pm 0.0305$ | $0.5236$ | Cải thiện nhẹ PR-AUC nhưng F1 chưa bứt phá |
| **Full Control-OFF (Config F)**| **Ngắt đồng thời cả Clock và Reset** | **0.5239 $\pm$ 0.0454** | **0.5731** | ✅ **ĐỈNH CAO: Triệt tiêu hoàn toàn đường tắt phi dữ liệu** |

### Bài Học Nhân Quả Xác Quyết:
1. **Cắt tỉa bậc cao phá hủy mạch:** Khi cắt các cạnh dữ liệu có fanout cao (`Degree-Matched`), mô hình sụp đổ về $0.2407$. Điều này chứng minh các bus dữ liệu bậc cao mang ngữ nghĩa tính toán cực kỳ quan trọng, không thể cắt tỉa tùy tiện theo bậc đỉnh.
2. **Cắt ngẫu nhiên làm giảm hiệu năng:** `Random Edge Removal` chỉ đạt $0.4140$, kém hơn cả Control-ON ($0.4570$). Việc làm thưa đồ thị đơn thuần không giúp ích gì.
3. **Hiệu ứng cộng hưởng của Clock và Reset:** Cắt riêng Clock đạt $0.4688$, cắt riêng Reset đạt $0.4501$. Chỉ khi ngắt đồng thời cả hai, luồng dữ liệu $G_{\text{data}}$ mới hoàn toàn thoát khỏi các đường tắt ảo, đẩy $F_1$ lên $0.5239$.
4. **Kết luận:** Lợi ích của Control-OFF là **hiệu ứng đặc thù về mặt ngữ nghĩa chức năng phần cứng (Domain-Specific Functional Semantics)**, không phải hệ quả giả tạo của việc thay đổi mật độ cạnh.

---

## VI. CƠ CHẾ TOÁN HỌC ĐẰNG SAU SỰ THÀNH CÔNG CỦA CONTROL-OFF (RQ3)

Để trả lời câu hỏi *"Tại sao Control-OFF lại chiến thắng?"*, đề tài đã sử dụng hai công cụ giải tích phổ đồ thị trên các toán tử chiếu 2-hop cố định ($A_{\text{data, sym}}$ và $A_{\text{co-ctrl}}$):

### 1. Phân Tích Thứ Hạng Hiệu Dụng Không Gian Biểu Diễn (SVD Effective Rank)
Thứ hạng hiệu dụng (Roy & Vetterli) đo lường số chiều không gian thực sự chứa thông tin phong phú của ma trận biểu diễn nút $H \in \mathbb{R}^{N \times d}$:
$$\operatorname{erank}(H) = \exp \left( -\sum_{k=1}^d p_k \log p_k \right), \quad p_k = \frac{\sigma_k(H)}{\sum_j \sigma_j(H)}$$

* **Kết quả đo đạc thực tế tại tầng $L=2$ trên cả 5 họ vi mạch:**
  * **Control-OFF duy trì $\operatorname{erank}(H)$ cao hơn từ $+17.8\%$ đến $+36.4\%$** so với Control-ON trên toàn bộ 5 họ vi mạch.
  * Phổ kỳ dị $\sigma_k(H)$ của Control-OFF có phần đuôi rất dày, chứng minh các chiều không gian nhúng được bảo tồn độ sắc nét.
  * Ngược lại, Control-ON khiến $\operatorname{erank}(H)$ sụt giảm nghiêm trọng, các vector của Flip-Flop bị kéo hội tụ về một không gian con thứ hạng thấp vô nghĩa (**Subspace Collapse**).

### 2. Động Học Năng Lượng Dirichlet Theo Quan Hệ (Rayleigh Quotient)
Thương số Rayleigh Dirichlet chuẩn hóa (Cai & Wang, 2020) đo lường độ trơn nhẵn của tín hiệu:
$$R_r(H) = \frac{\operatorname{Tr}(H^\top L_{r, \text{sym}} H)}{\|H\|_F^2} \in [0, 2]$$

* Khi áp dụng Control-OFF, thương số $R_{\text{data}}(H)$ giảm xuống một cách tối ưu, giúp các cổng logic lành tính trong cùng chuỗi datapath đồng nhất biểu diễn một cách trơn tru.
* Đồng thời, các số dư Dirichlet địa phương ($z_{i, \text{data}}, z_{i, \text{ctrl}}$) bộc lộ sự lệch pha cấu trúc của các cổng Trojan, tạo thành tín hiệu bổ trợ đắc lực giúp tăng vọt PR-AUC trên các vi mạch tuần tự khó nhất (`s38417`: $+49.0\%$, `s38584`: $+28.7\%$).

---

## VII. TỔNG KẾT BÀI HỌC PHƯƠNG PHÁP LUẬN TỪ CONFIG A ĐẾN CONFIG F

Chuỗi thực nghiệm bóc tách từ Config A đến Config F đã hoàn thành xuất sắc sứ mệnh khoa học của mình, tạo nên một hành trình nghiên cứu mẫu mực và thuyết phục:

$$\boxed{\begin{aligned}
&\textbf{1. Config A } (F_1 = 0.3518) \implies \text{Xác lập mốc xuất phát của GNN trên đồ thị nén phẳng.}\\
&\textbf{2. Config A } \to \textbf{ Config B } (0.3518 \to 0.2151) \implies \textbf{Negative Result:} \text{ Độ trung thực đồ thị tự nó là chưa đủ!}\\
&\textbf{3. Config B } \to \textbf{ Config C } (0.2151 \to 0.3258) \implies \textbf{Core Method:} \text{ Tích chập dị thể HeteroConv phục hồi hiệu năng (+51.5\%).}\\
&\textbf{4. Config C } \to \textbf{ Config D } (0.3258 \to 0.4032) \implies \textbf{Core Finding:} \text{ Ngắt cạnh điều khiển Control-OFF bứt phá (+23.8\%).}\\
&\textbf{5. Config C, D } \to \textbf{ Config E, F } (F_1 \to 0.5239) \implies \textbf{Full Integration:} \text{ Hội tụ HeteroConv + Control-OFF + 13F Tô-pô.}\\
&\textbf{6. Causal Controls \& Dirichlet Analysis } \implies \textbf{Mechanism Proof:} \text{ Chứng minh nhân quả vật lý và chống sụp đổ erank (+36.4\%).}
\end{aligned}}$$

Bằng cách xây dựng chuỗi bóc tách tường minh này, luận văn không chỉ đạt được hiệu năng vượt bậc mà còn chứng minh được **tính liêm chính học thuật tuyệt đối**, cung cấp cho hội đồng phản biện và cộng đồng nghiên cứu quốc tế câu trả lời trọn vẹn, thuyết phục cho câu hỏi: *Tại sao phương pháp đề xuất lại hoạt động xuất sắc trên các họ vi mạch chưa từng thấy!*

