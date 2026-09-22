#!/usr/bin/env python3
"""
Generate publication-quality architectural comparison diagrams:
Figure A: Baseline Compressed Graph (CircuitGraph - Whitten & Wolff, JETTA 2026)
Figure B: Proposed Semantic Heterogeneous Bipartite Graph IR (HeteroTrojanGNN)
Target Subcircuit: RS232-T1000 90nm
"""

import subprocess
from pathlib import Path

OUT_DIR = Path("docs/images")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# 1. Baseline Compressed Graph DOT
# -------------------------------------------------------------
baseline_dot = """digraph BaselineCompressedGraph {
    graph [
        rankdir=LR,
        splines=spline,
        nodesep=0.6,
        ranksep=0.75,
        bgcolor="#ffffff",
        fontname="DejaVu Sans",
        fontsize=13,
        compound=true,
        pad="0.3"
    ];
    node [fontname="DejaVu Sans", fontsize=10.5];
    edge [fontname="DejaVu Sans", fontsize=9.5];

    // Main Title
    labelloc="t";
    label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">
        <TR><TD><FONT POINT-SIZE="16"><B>(a) ĐỒ THỊ NÉN PHẲNG BASELINE (WHITTEN &amp; WOLFF, JETTA 2026 - CIRCUITGRAPH)</B></FONT></TD></TR>
        <TR><TD><FONT POINT-SIZE="11" COLOR="#495057">Trích đoạn mạch RS232-T1000 90nm: Biến đổi Netlist thành Đồ thị Thuần nhất Cổng-Cổng (Toàn bộ Dây nội vi bị xóa sạch)</FONT></TD></TR>
    </TABLE>>;

    // Primary Input Group
    subgraph cluster_pi {
        label="Ngõ Vào Chính PI";
        fontname="DejaVu Sans Bold";
        fontsize=11;
        color="#15aabf";
        fillcolor="#e3fafc";
        style="filled,rounded";

        b_pi [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="3">
                <TR><TD BGCOLOR="#15aabf"><FONT COLOR="#ffffff"><B>PRIMARY INPUT</B></FONT></TD></TR>
                <TR><TD><FONT COLOR="#0c8599"><B>xmit_dataH[0]</B></FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="9" COLOR="#495057">Chân ngõ vào chip</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffffff",
            color="#15aabf",
            penwidth=2.0
        ];
    }

    // Logic Gate Chain Group
    subgraph cluster_logic {
        label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
            <TR><TD><B>Chuỗi Cổng Logic Bị Nén Phẳng (Homogeneous Logic Chain)</B></TD></TR>
            <TR><TD><FONT COLOR="#c92a2a" POINT-SIZE="9.5"><B>CÁC DÂY n27, n190, n118 ĐÃ BỊ XÓA BỎ HOÀN TOÀN KHỎI ĐỒ THỊ</B></FONT></TD></TR>
        </TABLE>>;
        fontname="DejaVu Sans Bold";
        fontsize=11;
        color="#fa5252";
        fillcolor="#fff5f5";
        style="filled,rounded";

        b_u33 [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#228be6"><FONT COLOR="#ffffff"><B>Node gộp: U33.QN</B></FONT></TD></TR>
                <TR><TD><B>Cổng AOI22X2</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="9" COLOR="#c92a2a">Đại diện bằng pin QN</FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#868e96">Xóa các pin IN1..4</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffffff",
            color="#228be6",
            penwidth=2.0
        ];

        b_u32 [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#228be6"><FONT COLOR="#ffffff"><B>Node gộp: U32.QN</B></FONT></TD></TR>
                <TR><TD><B>Cổng OAI21X2</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="9" COLOR="#c92a2a">Đại diện bằng pin QN</FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#868e96">Xóa các pin IN1..3</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffffff",
            color="#228be6",
            penwidth=2.0
        ];

        b_u122 [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#228be6"><FONT COLOR="#ffffff"><B>Node gộp: U122.Q</B></FONT></TD></TR>
                <TR><TD><B>Cổng MUX21X1</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="9" COLOR="#c92a2a">Đại diện bằng pin Q</FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#868e96">Xóa các pin S, IN1..2</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffffff",
            color="#228be6",
            penwidth=2.0
        ];

        b_reg [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#1971c2"><FONT COLOR="#ffffff"><B>Node gộp: reg_0.Q</B></FONT></TD></TR>
                <TR><TD><B>Flip-Flop DFFARX1</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="9" COLOR="#495057">ShiftRegH_reg_0_</FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="9" COLOR="#c92a2a">Mất chân D &amp; CLK</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffffff",
            color="#1971c2",
            penwidth=2.0
        ];
    }

    // Global Control Network Group
    subgraph cluster_ctrl {
        label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
            <TR><TD><B>Mạng Điều Khiển Toàn Cục</B></TD></TR>
            <TR><TD><FONT COLOR="#d9480f" POINT-SIZE="9.5"><B>Đường tắt 1-hop tới 35 FFs</B></FONT></TD></TR>
        </TABLE>>;
        fontname="DejaVu Sans Bold";
        fontsize=11;
        color="#fab005";
        fillcolor="#fff9db";
        style="filled,rounded";

        b_clk [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#fab005"><FONT COLOR="#ffffff"><B>sys_clk</B></FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="9" COLOR="#d9480f">Primary Input Clock</FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#c92a2a"><B>Bậc ra Out-deg = 76</B></FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffffff",
            color="#fab005",
            penwidth=1.8
        ];

        b_rst [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#fab005"><FONT COLOR="#ffffff"><B>sys_rst_l</B></FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="9" COLOR="#d9480f">Primary Input Reset</FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#495057">Nối trực tiếp chân reset</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffffff",
            color="#fab005",
            penwidth=1.8
        ];
    }

    // Trojan Subcircuit Group
    subgraph cluster_trojan {
        label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
            <TR><TD><B>Khối Hardware Trojan Bị Nén Phẳng</B></TD></TR>
            <TR><TD><FONT COLOR="#c92a2a" POINT-SIZE="9.5"><B>DÂY KÍCH HOẠT iCTRL BỊ XÓA BỎ HOÀN TOÀN</B></FONT></TD></TR>
        </TABLE>>;
        fontname="DejaVu Sans Bold";
        fontsize=11;
        color="#c92a2a";
        fillcolor="#ffe3e3";
        style="filled,rounded";

        b_trig [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#c92a2a"><FONT COLOR="#ffffff"><B>U302.Q (Trigger)</B></FONT></TD></TR>
                <TR><TD><B>Cổng OR4X1</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="9" COLOR="#c92a2a">Theo dõi trạng thái hiếm</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffffff",
            color="#c92a2a",
            penwidth=2.2
        ];

        b_payl [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#c92a2a"><FONT COLOR="#ffffff"><B>U303.Q (Payload)</B></FONT></TD></TR>
                <TR><TD><B>Cổng AND2X1</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="9" COLOR="#c92a2a">Bẻ gãy dữ liệu xuất</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffffff",
            color="#c92a2a",
            penwidth=2.2
        ];

        b_po [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#15aabf"><FONT COLOR="#ffffff"><B>PRIMARY OUTPUT</B></FONT></TD></TR>
                <TR><TD><FONT COLOR="#0c8599"><B>xmit_doneH</B></FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="9" COLOR="#495057">Chân ngõ ra chip</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffffff",
            color="#15aabf",
            penwidth=2.0
        ];
    }

    // Connections in Dataflow
    b_pi -> b_u33 [
        label="add_edge nhân tạo\\n(Xóa chân IN1..4)",
        color="#fa5252",
        fontcolor="#c92a2a",
        penwidth=2.2
    ];
    b_u33 -> b_u32 [
        label="add_edge trực tiếp\\n(XÓA BỎ DÂY n27)",
        color="#fa5252",
        fontcolor="#c92a2a",
        penwidth=2.2
    ];
    b_u32 -> b_u122 [
        label="add_edge trực tiếp\\n(XÓA BỎ DÂY n190)",
        color="#fa5252",
        fontcolor="#c92a2a",
        penwidth=2.2
    ];
    b_u122 -> b_reg [
        label="add_edge trực tiếp\\n(XÓA BỎ DÂY n118)",
        color="#fa5252",
        fontcolor="#c92a2a",
        penwidth=2.2
    ];

    // Clock and Reset Shortcuts
    b_clk -> b_reg [
        label="ĐƯỜNG TẮT 1-HOP TOÀN CỤC\\n(Bỏ qua logic & Gây Over-smoothing)",
        style="dashed",
        color="#f76707",
        fontcolor="#d9480f",
        penwidth=2.2
    ];
    b_rst -> b_reg [
        label="1-hop reset",
        style="dashed",
        color="#fab005",
        fontcolor="#d9480f",
        penwidth=1.8
    ];

    // Trojan Connections
    b_trig -> b_payl [
        label="NỐI TẮT TRỰC TIẾP\\n(XÓA MẤT DÂY iCTRL)",
        color="#c92a2a",
        fontcolor="#c92a2a",
        penwidth=2.5
    ];
    b_payl -> b_po [
        label="add_edge",
        color="#1971c2",
        penwidth=2.0
    ];

    // Bottom Summary Banner
    subgraph cluster_footer {
        rank=sink;
        color="#ced4da";
        fillcolor="#f8f9fa";
        style="filled,rounded";
        label="";

        footer [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="4" CELLPADDING="3">
                <TR><TD ALIGN="LEFT"><FONT COLOR="#c92a2a"><B>HẬU QUẢ CỐT LÕI CỦA CƠ CHẾ NÉN PHẲNG BASELINE TRÊN RS232-T1000 90nm:</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT"><FONT COLOR="#333333">• <B>Mất 61.7% thực thể:</B> Toàn bộ các dây n27, n190, n118 và iCTRL bị xóa sạch; đồ thị chỉ còn lại các nút chân ra cổng gộp.</FONT></TD></TR>
                <TR><TD ALIGN="LEFT"><FONT COLOR="#333333">• <B>Phá vỡ tính hai phía:</B> Triệt tiêu cấu trúc phân nhánh Fanout thực tế của netlist vi mạch.</FONT></TD></TR>
                <TR><TD ALIGN="LEFT"><FONT COLOR="#333333">• <B>Co cụm cấu trúc bởi xung nhịp:</B> sys_clk tạo 76 đường tắt 1-hop làm sụp đổ đường kính đồ thị và gây Over-smoothing nghiêm trọng khi áp dụng GNN.</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#fff9db",
            color="#fab005",
            penwidth=1.5
        ];
    }
}
"""

# -------------------------------------------------------------
# 2. Proposed Semantic Heterogeneous Bipartite Graph IR DOT
# -------------------------------------------------------------
hetero_dot = """digraph HeteroBipartiteGraph {
    graph [
        rankdir=LR,
        splines=spline,
        nodesep=0.5,
        ranksep=0.7,
        bgcolor="#ffffff",
        fontname="DejaVu Sans",
        fontsize=13,
        compound=true,
        pad="0.3"
    ];
    node [fontname="DejaVu Sans", fontsize=10.5];
    edge [fontname="DejaVu Sans", fontsize=9.5];

    // Main Title
    labelloc="t";
    label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">
        <TR><TD><FONT POINT-SIZE="16"><B>(b) ĐỒ THỊ HAI PHÍA DỊ THỂ ĐỀ XUẤT (SEMANTIC HETEROGENEOUS BIPARTITE GRAPH IR)</B></FONT></TD></TR>
        <TR><TD><FONT POINT-SIZE="11" COLOR="#2b8a3e">Trích đoạn mạch RS232-T1000 90nm: Bảo toàn 100% Cổng (Cell) và Dây (Net), Giữ nguyên Ngữ nghĩa Chân cắm (Pin Semantics)</FONT></TD></TR>
    </TABLE>>;

    // Functional Dataflow Bipartite Chain
    subgraph cluster_hetero_data {
        label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
            <TR><TD><B>Luồng Dữ Liệu Chức Năng (Bảo Toàn Chuỗi Xen Kẽ Hai Phía: Cell ↔ Net)</B></TD></TR>
            <TR><TD><FONT COLOR="#2b8a3e" POINT-SIZE="9.5"><B>ĐƯỢC GIỮ NGUYÊN TRONG ĐỒ THỊ DỮ LIỆU G_data ĐỂ TRUYỀN TIN MESSAGE PASSING</B></FONT></TD></TR>
        </TABLE>>;
        fontname="DejaVu Sans Bold";
        fontsize=11;
        color="#12b886";
        fillcolor="#e6fcf5";
        style="filled,rounded";

        h_pi [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#15aabf"><FONT COLOR="#ffffff"><B>Net: Primary Input</B></FONT></TD></TR>
                <TR><TD><B>xmit_dataH[0]</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#495057">Chân ngõ vào chip</FONT></TD></TR>
            </TABLE>>,
            shape=ellipse,
            style="filled",
            fillcolor="#ffffff",
            color="#15aabf",
            penwidth=2.0
        ];

        h_u33 [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#1971c2"><FONT COLOR="#ffffff"><B>Cell: U33</B></FONT></TD></TR>
                <TR><TD><B>AOI22X2</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#1971c2">Cell tổ hợp</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#d0ebff",
            color="#1971c2",
            penwidth=2.0
        ];

        h_n27 [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#495057"><FONT COLOR="#ffffff"><B>Net: n27</B></FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#333333">Dây nội vi logic</FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#2b8a3e"><B>Bảo toàn Fanout</B></FONT></TD></TR>
            </TABLE>>,
            shape=ellipse,
            style="filled",
            fillcolor="#f8f9fa",
            color="#495057",
            penwidth=1.8
        ];

        h_u32 [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#1971c2"><FONT COLOR="#ffffff"><B>Cell: U32</B></FONT></TD></TR>
                <TR><TD><B>OAI21X2</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#1971c2">Cell tổ hợp</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#d0ebff",
            color="#1971c2",
            penwidth=2.0
        ];

        h_n190 [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#495057"><FONT COLOR="#ffffff"><B>Net: n190</B></FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#333333">Dây nội vi logic</FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#2b8a3e"><B>Bảo toàn Fanout</B></FONT></TD></TR>
            </TABLE>>,
            shape=ellipse,
            style="filled",
            fillcolor="#f8f9fa",
            color="#495057",
            penwidth=1.8
        ];

        h_u122 [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#1971c2"><FONT COLOR="#ffffff"><B>Cell: U122</B></FONT></TD></TR>
                <TR><TD><B>MUX21X1</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#1971c2">Cổng ghép kênh</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#d0ebff",
            color="#1971c2",
            penwidth=2.0
        ];

        h_n118 [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#495057"><FONT COLOR="#ffffff"><B>Net: n118</B></FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#333333">Dây dữ liệu vào FF</FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#2b8a3e"><B>Nối tới chân D</B></FONT></TD></TR>
            </TABLE>>,
            shape=ellipse,
            style="filled",
            fillcolor="#f8f9fa",
            color="#495057",
            penwidth=1.8
        ];

        h_reg [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#1971c2"><FONT COLOR="#ffffff"><B>Cell: reg_0</B></FONT></TD></TR>
                <TR><TD><B>DFFARX1 (Flip-Flop)</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#495057">ShiftRegH_reg_0_</FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#2b8a3e"><B>Phân định rõ D, CLK, RST</B></FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#d0ebff",
            color="#1971c2",
            penwidth=2.0
        ];
    }

    // Decoupled Global Control Network
    subgraph cluster_hetero_ctrl {
        label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
            <TR><TD><B>Mạng Điều Khiển Toàn Cục Tách Rời (G_ctrl)</B></TD></TR>
            <TR><TD><FONT COLOR="#862e9c" POINT-SIZE="9.5"><B>Gán nhãn is_control=1 và NGẮT BỎ trong G_data</B></FONT></TD></TR>
        </TABLE>>;
        fontname="DejaVu Sans Bold";
        fontsize=11;
        color="#be4bdb";
        fillcolor="#f8f0fc";
        style="filled,rounded";

        h_clk [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#ae3ec9"><FONT COLOR="#ffffff"><B>Net: sys_clk</B></FONT></TD></TR>
                <TR><TD><B>Clock Network</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#862e9c"><B>is_control = 1</B></FONT></TD></TR>
            </TABLE>>,
            shape=ellipse,
            style="filled",
            fillcolor="#ffffff",
            color="#ae3ec9",
            penwidth=2.0
        ];

        h_rst [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#ae3ec9"><FONT COLOR="#ffffff"><B>Net: sys_rst_l</B></FONT></TD></TR>
                <TR><TD><B>Reset Network</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#862e9c"><B>is_control = 1</B></FONT></TD></TR>
            </TABLE>>,
            shape=ellipse,
            style="filled",
            fillcolor="#ffffff",
            color="#ae3ec9",
            penwidth=2.0
        ];
    }

    // Hardware Trojan Subcircuit
    subgraph cluster_hetero_trojan {
        label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
            <TR><TD><B>Khối Hardware Trojan: Bảo Toàn Dây Kích Hoạt iCTRL</B></TD></TR>
            <TR><TD><FONT COLOR="#c92a2a" POINT-SIZE="9.5"><B>CẦU NỐI NGỮ NGHĨA GIỮA TRIGGER VÀ PAYLOAD</B></FONT></TD></TR>
        </TABLE>>;
        fontname="DejaVu Sans Bold";
        fontsize=11;
        color="#e03131";
        fillcolor="#fff5f5";
        style="filled,rounded";

        h_trig [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#c92a2a"><FONT COLOR="#ffffff"><B>Cell: U302 (Trigger)</B></FONT></TD></TR>
                <TR><TD><B>ISOLORX8 (Cổng OR4)</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#c92a2a"><B>Label = 1 (Trojan Cell)</B></FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffe3e3",
            color="#c92a2a",
            penwidth=2.5
        ];

        h_ictrl [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#e03131"><FONT COLOR="#ffffff"><B>Net: iCTRL (Trojan Net)</B></FONT></TD></TR>
                <TR><TD><B>DÂY KÍCH HOẠT HIẾM</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#c92a2a"><B>Cầu nối Trigger ↔ Payload</B></FONT></TD></TR>
            </TABLE>>,
            shape=hexagon,
            style="filled",
            fillcolor="#ffc9c9",
            color="#e03131",
            penwidth=2.5
        ];

        h_payl [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#c92a2a"><FONT COLOR="#ffffff"><B>Cell: U303 (Payload)</B></FONT></TD></TR>
                <TR><TD><B>AND2X4 (Cổng AND2)</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#c92a2a"><B>Label = 1 (Trojan Cell)</B></FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#ffe3e3",
            color="#c92a2a",
            penwidth=2.5
        ];

        h_po [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                <TR><TD BGCOLOR="#15aabf"><FONT COLOR="#ffffff"><B>Net: Primary Output</B></FONT></TD></TR>
                <TR><TD><B>xmit_doneH</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="8.5" COLOR="#c92a2a">Ngõ ra bị bẻ gãy logic</FONT></TD></TR>
            </TABLE>>,
            shape=ellipse,
            style="filled",
            fillcolor="#ffffff",
            color="#15aabf",
            penwidth=2.0
        ];
    }

    // Connections in Heterogeneous Dataflow (Cell <-> Net alternating)
    h_pi -> h_u33 [
        label="data_input\\n(chân IN1)",
        color="#2b8a3e",
        fontcolor="#2b8a3e",
        penwidth=2.2
    ];
    h_u33 -> h_n27 [
        label="outputs\\n(chân QN)",
        color="#1971c2",
        fontcolor="#1864ab",
        penwidth=2.2
    ];
    h_n27 -> h_u32 [
        label="data_input\\n(chân IN3)",
        color="#2b8a3e",
        fontcolor="#2b8a3e",
        penwidth=2.2
    ];
    h_u32 -> h_n190 [
        label="outputs\\n(chân QN)",
        color="#1971c2",
        fontcolor="#1864ab",
        penwidth=2.2
    ];
    h_n190 -> h_u122 [
        label="data_input\\n(chân IN1)",
        color="#2b8a3e",
        fontcolor="#2b8a3e",
        penwidth=2.2
    ];
    h_u122 -> h_n118 [
        label="outputs\\n(chân Q)",
        color="#1971c2",
        fontcolor="#1864ab",
        penwidth=2.2
    ];
    h_n118 -> h_reg [
        label="data_input\\n(chân dữ liệu D)",
        color="#2b8a3e",
        fontcolor="#2b8a3e",
        penwidth=2.5
    ];

    // Decoupled Control Connections (is_control=1 filtered in G_data)
    h_clk -> h_reg [
        label="control_input (chân CLK)\\nis_control=1 [NGẮT KHỎI G_data]\\nBảo vệ Dirichlet Energy",
        style="dashed",
        color="#ae3ec9",
        fontcolor="#862e9c",
        penwidth=2.2
    ];
    h_rst -> h_reg [
        label="control_input (chân RSTB)\\nis_control=1 [NGẮT KHỎI G_data]",
        style="dashed",
        color="#ae3ec9",
        fontcolor="#862e9c",
        penwidth=1.8
    ];

    // Trojan Bipartite Chain
    h_trig -> h_ictrl [
        label="payload_output\\n(chân Q)",
        color="#c92a2a",
        fontcolor="#c92a2a",
        penwidth=2.5
    ];
    h_ictrl -> h_payl [
        label="trigger_input\\n(chân IN1)",
        color="#c92a2a",
        fontcolor="#c92a2a",
        penwidth=2.5
    ];
    h_payl -> h_po [
        label="payload_output\\n(chân Q)",
        color="#c92a2a",
        fontcolor="#c92a2a",
        penwidth=2.5
    ];

    // Bottom Summary Banner
    subgraph cluster_hetero_footer {
        rank=sink;
        color="#ced4da";
        fillcolor="#f8f9fa";
        style="filled,rounded";
        label="";

        hetero_footer [
            label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="4" CELLPADDING="3">
                <TR><TD ALIGN="LEFT"><FONT COLOR="#2b8a3e"><B>ƯU THẾ VƯỢT TRỘI CỦA ĐỒ THỊ HAI PHÍA DỊ THỂ TRÊN RS232-T1000 90nm:</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT"><FONT COLOR="#333333">• <B>Bảo toàn 100% topo Netlist:</B> Phân định rõ 268 Cell (hình chữ nhật xanh) và 312 Net (hình oval xám/đỏ), bảo toàn phân nhánh Fanout.</FONT></TD></TR>
                <TR><TD ALIGN="LEFT"><FONT COLOR="#333333">• <B>Dây kích hoạt iCTRL được giữ nguyên:</B> Đóng vai trò cầu nối truyền tin giữa Trigger và Payload, giúp HeteroTrojanGNN bắt trọn mẫu hình tấn công.</FONT></TD></TR>
                <TR><TD ALIGN="LEFT"><FONT COLOR="#333333">• <B>Tách rời Clock/Reset:</B> Giữ năng lượng Dirichlet không suy giảm theo chiều sâu GNN, tăng LOCO Micro-F1 trên họ ISCAS từ 0.0551 lên 0.7266 (13.2x).</FONT></TD></TR>
            </TABLE>>,
            shape=box,
            style="filled,rounded",
            fillcolor="#e6fcf5",
            color="#12b886",
            penwidth=1.5
        ];
    }
}
"""

def generate_figure(dot_content, base_name):
    dot_path = OUT_DIR / f"{base_name}.dot"
    svg_path = OUT_DIR / f"{base_name}.svg"
    png_path = OUT_DIR / f"{base_name}.png"

    with open(dot_path, "w", encoding="utf-8") as f:
        f.write(dot_content)

    print(f"Generating {svg_path}...")
    subprocess.run(["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)], check=True)

    print(f"Generating {png_path} (High DPI)...")
    subprocess.run(["dot", "-Tpng", "-Gdpi=200", str(dot_path), "-o", str(png_path)], check=True)

    print(f"Done: {base_name}")

if __name__ == "__main__":
    generate_figure(baseline_dot, "baseline_compressed_graph_rs232")
    generate_figure(hetero_dot, "hetero_bipartite_graph_rs232")
    print("All figures successfully generated in docs/images/")
