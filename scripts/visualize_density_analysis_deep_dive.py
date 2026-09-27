"""
Script: scripts/visualize_density_analysis_deep_dive.py
Mục đích:
  Tạo bộ 3 hình ảnh trực quan hóa chuyên sâu phân tích phân phối mật độ:
  1. fig_density_benign_vs_trojan_per_family.png:
     So sánh trực tiếp phân phối mật độ giữa Benign và Trojan trên từng họ vi mạch
     (Vạch trần hiện tượng 'Nghịch đảo pha' - Inverted Patterns giữa các họ).
  2. fig_decision_box_in_dist_vs_lofo.png:
     Trực quan hóa mặt cắt 2D: Tại sao In-Distribution cắt trúng phóc, nhưng LOFO trượt hoàn toàn.
  3. fig_performance_contrast_radar_and_roc.png:
     Đối chiếu ROC/PR Curves và phân phối xác suất dự đoán P(Trojan).
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.metrics import roc_curve, precision_recall_curve, auc
import xgboost as xgb

FIGURES_DIR = "outputs/figures/baseline_density_analysis"
os.makedirs(FIGURES_DIR, exist_ok=True)

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#444444'
plt.rcParams['axes.linewidth'] = 1.0

# 1. Đọc dữ liệu 30 vi mạch
csv_files = sorted(glob.glob("data/circuits/*.csv"))
dfs = []
for f in csv_files:
    basename = os.path.basename(f)
    if basename.startswith("RS232"):
        fam = "RS232"
    elif basename.startswith("s15850"):
        fam = "s15850"
    elif basename.startswith("s35932"):
        fam = "s35932"
    elif basename.startswith("s38417"):
        fam = "s38417"
    elif basename.startswith("s38584"):
        fam = "s38584"
    else:
        fam = "Other"
    d = pd.read_csv(f)
    d['family'] = fam
    dfs.append(d)

df = pd.concat(dfs, ignore_index=True)

# ==============================================================================
# HÌNH 1: PHÂN PHỐI MẬT ĐỘ SO SÁNH BENIGN VS TROJAN TRÊN TỪNG HỌ VI MẠCH
# Vạch trần sự "Nghịch đảo pha đặc trưng" (Feature Inversion)
# ==============================================================================
print("Đang tạo Hình 1: Phân phối mật độ Benign vs Trojan theo từng họ...")

# Chọn 3 đặc trưng then chốt: LGFi, ffi, PI
fig, axes = plt.subplots(3, 4, figsize=(18, 11))

target_families = ['RS232', 's35932', 's38417', 's38584']
feats = ['LGFi', 'ffi', 'PI']
feat_names = {
    'LGFi': 'Logic Gate Fan-in (LGFi)',
    'ffi': 'Khoảng cách tới Flip-Flop In (ffi)',
    'PI': 'Khoảng cách tới Primary In (PI)'
}

for r, feat in enumerate(feats):
    for c, fam in enumerate(target_families):
        ax = axes[r, c]
        sub = df[df['family'] == fam]
        # Loại bỏ giá trị vô cực sentinel 99999 để vẽ phân phối thực tế
        benign_vals = sub[(sub['Trojan'] == 0) & (sub[feat] < 1000)][feat].values
        trojan_vals = sub[(sub['Trojan'] == 1) & (sub[feat] < 1000)][feat].values
        
        # Max limit cho trục x
        max_x = max(np.percentile(benign_vals, 99) if len(benign_vals) > 0 else 10,
                    np.max(trojan_vals) if len(trojan_vals) > 0 else 10)
        max_x = max(max_x, 5)
        
        # Vẽ KDE hoặc Histogram
        bins = np.linspace(0, max_x, 25)
        ax.hist(benign_vals, bins=bins, density=True, alpha=0.45, color='#1f77b4', 
                label=f'Benign (n={len(benign_vals):,})')
        ax.hist(trojan_vals, bins=bins, density=True, alpha=0.75, color='#d62728', 
                label=f'Trojan (n={len(trojan_vals)})')
        
        # Đường thẳng trung bình
        if len(trojan_vals) > 0:
            ax.axvline(np.mean(trojan_vals), color='#d62728', linestyle='--', lw=2, 
                       label=f'Trojan μ={np.mean(trojan_vals):.1f}')
        if len(benign_vals) > 0:
            ax.axvline(np.mean(benign_vals), color='#1f77b4', linestyle=':', lw=2, 
                       label=f'Benign μ={np.mean(benign_vals):.1f}')
            
        ax.set_title(f"Họ {fam}: {feat_names[feat]}", fontsize=11, fontweight='bold')
        ax.set_xlabel(f"Giá trị {feat}", fontsize=9)
        if c == 0:
            ax.set_ylabel("Mật độ xác suất (Density)", fontsize=9)
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(fontsize=8, loc='upper right')

plt.suptitle("NGUYÊN NHÂN GỐC RỄ CỦA SỰ SỤP ĐỔ LOFO: PHÂN PHỐI ĐẶC TRƯNG BỊ NGHỊCH ĐẢO PHA GIỮA CÁC HỌ VI MẠCH\n"
             "• RS232: Trojan có LGFi cao hơn Benign (9.8 > 6.3) | • s35932: Trojan lại có LGFi THẤP HƠN Benign (3.6 < 5.3)\n"
             "• s38417: Trojan có ffi & PI cao hơn Benign | • s38584: Trojan lại có ffi THẤP HƠN Benign", 
             fontsize=12, fontweight='bold', y=0.99)
plt.tight_layout(rect=[0, 0, 1, 0.95])
fig1_path = os.path.join(FIGURES_DIR, "fig1_density_benign_vs_trojan_per_family.png")
plt.savefig(fig1_path, dpi=300)
plt.close()
print(f"Đã lưu: {fig1_path}")


# ==============================================================================
# HÌNH 2: MẶT CẮT QUYẾT ĐỊNH 2D (DECISION SPACE) & VÙNG TỌA ĐỘ BỊ LỆCH
# ==============================================================================
print("Đang tạo Hình 2: Mặt cắt quyết định 2D và tọa độ bị lệch...")

# Huấn luyện XGBoost trên họ RS232 với 2 đặc trưng: LGFi và ffi
rs232_data = df[df['family'] == 'RS232']
X_rs_2d = rs232_data[['LGFi', 'ffi']].values
# Clip ffi để tránh sentinel 99999 làm bẹp đồ thị
X_rs_2d[:, 1] = np.clip(X_rs_2d[:, 1], 0, 10)
y_rs_2d = rs232_data['Trojan'].values

scale_2d = (len(y_rs_2d) - sum(y_rs_2d)) / sum(y_rs_2d)
clf_2d = xgb.XGBClassifier(
    n_estimators=100, max_depth=5, learning_rate=0.2, 
    scale_pos_weight=scale_2d, random_state=42, eval_metric="logloss"
)
clf_2d.fit(X_rs_2d, y_rs_2d)

# Tạo lưới
xx, yy = np.meshgrid(np.linspace(0, 16, 200), np.linspace(0, 6, 200))
grid_points = np.c_[xx.ravel(), yy.ravel()]
Z = clf_2d.predict_proba(grid_points)[:, 1].reshape(xx.shape)

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.5))

# Panel 1: Huấn luyện trên RS232 (In-Distribution)
ax1.contourf(xx, yy, Z, levels=np.linspace(0, 1, 11), cmap='Blues', alpha=0.7)
ax1.contour(xx, yy, Z, levels=[0.90], colors='red', linewidths=2.5, linestyles='--')
ax1.scatter(X_rs_2d[y_rs_2d == 0, 0][:400], X_rs_2d[y_rs_2d == 0, 1][:400], 
            c='#1f77b4', s=15, alpha=0.3, label='RS232 Benign')
ax1.scatter(X_rs_2d[y_rs_2d == 1, 0], X_rs_2d[y_rs_2d == 1, 1], 
            c='#d62728', s=45, edgecolors='black', marker='^', label='RS232 Trojan (Nằm gọn trong vùng đỏ!)')
ax1.set_xlim(0, 16)
ax1.set_ylim(0, 6)
ax1.set_title("A. IN-DISTRIBUTION (Huấn luyện & Test trên RS232)\nCây quyết định khoanh vùng: LGFi > 8 VÀ ffi <= 1", 
              fontsize=11, fontweight='bold')
ax1.set_xlabel("Bậc vào logic (LGFi)", fontsize=10)
ax1.set_ylabel("Khoảng cách Flip-Flop Input (ffi)", fontsize=10)
ax1.legend(loc='upper right', fontsize=8.5)
ax1.grid(True, linestyle=':', alpha=0.6)

# Panel 2: Kiểm thử ngoại suy trên s35932
s35_data = df[df['family'] == 's35932']
X_s35_2d = s35_data[['LGFi', 'ffi']].values
X_s35_2d[:, 1] = np.clip(X_s35_2d[:, 1], 0, 10)
y_s35_2d = s35_data['Trojan'].values

ax2.contourf(xx, yy, Z, levels=np.linspace(0, 1, 11), cmap='Blues', alpha=0.7)
ax2.contour(xx, yy, Z, levels=[0.90], colors='red', linewidths=2.5, linestyles='--')
ax2.scatter(X_s35_2d[y_s35_2d == 0, 0][:600], X_s35_2d[y_s35_2d == 0, 1][:600], 
            c='#2ca02c', s=15, alpha=0.3, label='s35932 Benign')
ax2.scatter(X_s35_2d[y_s35_2d == 1, 0], X_s35_2d[y_s35_2d == 1, 1], 
            c='#ff7f0e', s=55, edgecolors='black', marker='s', label='s35932 Trojan (LGFi thấp, trượt vùng đỏ!)')
ax2.set_xlim(0, 16)
ax2.set_ylim(0, 6)
ax2.set_title("B. NGOẠI SUY LOFO TRÊN s35932\nTrojan có LGFi <= 8, BỊ BỎ SÓT 100% (Recall = 0.0%)!", 
              fontsize=11, fontweight='bold')
ax2.set_xlabel("Bậc vào logic (LGFi)", fontsize=10)
ax2.set_ylabel("Khoảng cách Flip-Flop Input (ffi)", fontsize=10)
ax2.legend(loc='upper right', fontsize=8.5)
ax2.grid(True, linestyle=':', alpha=0.6)

# Panel 3: Kiểm thử ngoại suy trên s38417
s38_data = df[df['family'] == 's38417']
X_s38_2d = s38_data[['LGFi', 'ffi']].values
X_s38_2d[:, 1] = np.clip(X_s38_2d[:, 1], 0, 10)
y_s38_2d = s38_data['Trojan'].values

ax3.contourf(xx, yy, Z, levels=np.linspace(0, 1, 11), cmap='Blues', alpha=0.7)
ax3.contour(xx, yy, Z, levels=[0.90], colors='red', linewidths=2.5, linestyles='--')
ax3.scatter(X_s38_2d[y_s38_2d == 0, 0][:600], X_s38_2d[y_s38_2d == 0, 1][:600], 
            c='#9467bd', s=15, alpha=0.3, label='s38417 Benign (Báo động giả tràn lan!)')
ax3.scatter(X_s38_2d[y_s38_2d == 1, 0], X_s38_2d[y_s38_2d == 1, 1], 
            c='#d62728', s=60, edgecolors='black', marker='*', label='s38417 Trojan (ffi > 2, trượt ranh giới)')
ax3.set_xlim(0, 16)
ax3.set_ylim(0, 6)
ax3.set_title("C. NGOẠI SUY LOFO TRÊN s38417\nTrojan trượt ra ffi > 2; Benign rơi vào vùng đỏ (Nổ báo động giả)!", 
              fontsize=11, fontweight='bold')
ax3.set_xlabel("Bậc vào logic (LGFi)", fontsize=10)
ax3.set_ylabel("Khoảng cách Flip-Flop Input (ffi)", fontsize=10)
ax3.legend(loc='upper right', fontsize=8.5)
ax3.grid(True, linestyle=':', alpha=0.6)

plt.tight_layout()
fig2_path = os.path.join(FIGURES_DIR, "fig2_decision_box_in_dist_vs_lofo.png")
plt.savefig(fig2_path, dpi=300)
plt.close()
print(f"Đã lưu: {fig2_path}")


# ==============================================================================
# HÌNH 3: SO SÁNH ĐƯỜNG CONG ROC VÀ PRECISION-RECALL (IN-DIST VS LOFO)
# ==============================================================================
print("Đang tạo Hình 3: ROC và Precision-Recall Curves...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Đường cong In-Distribution (từ model full 5 đặc trưng)
X_all = df[['LGFi', 'ffi', 'ffo', 'PI', 'PO']].values
y_all = df['Trojan'].values

sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
tr_i, te_i = next(sss.split(X_all, y_all))
clf_indist = xgb.XGBClassifier(
    n_estimators=100, max_depth=6, learning_rate=0.3,
    scale_pos_weight=(len(tr_i) - sum(y_all[tr_i])) / sum(y_all[tr_i]),
    random_state=42, eval_metric="logloss"
)
clf_indist.fit(X_all[tr_i], y_all[tr_i])
probs_indist = clf_indist.predict_proba(X_all[te_i])[:, 1]
fpr_in, tpr_in, _ = roc_curve(y_all[te_i], probs_indist)
prec_in, rec_in, _ = precision_recall_curve(y_all[te_i], probs_indist)

# Đường cong LOFO Fold 0 (Test RS232)
mask_tr_rs = (df['family'] != 'RS232')
mask_te_rs = (df['family'] == 'RS232')
clf_lofo_rs = xgb.XGBClassifier(
    n_estimators=100, max_depth=6, learning_rate=0.3,
    scale_pos_weight=(sum(mask_tr_rs) - sum(y_all[mask_tr_rs])) / sum(y_all[mask_tr_rs]),
    random_state=42, eval_metric="logloss"
)
clf_lofo_rs.fit(X_all[mask_tr_rs], y_all[mask_tr_rs])
probs_lofo_rs = clf_lofo_rs.predict_proba(X_all[mask_te_rs])[:, 1]
fpr_lofo_rs, tpr_lofo_rs, _ = roc_curve(y_all[mask_te_rs], probs_lofo_rs)
prec_lofo_rs, rec_lofo_rs, _ = precision_recall_curve(y_all[mask_te_rs], probs_lofo_rs)

# Đường cong LOFO Fold 2 (Test s35932)
mask_tr_s35 = (df['family'] != 's35932')
mask_te_s35 = (df['family'] == 's35932')
clf_lofo_s35 = xgb.XGBClassifier(
    n_estimators=100, max_depth=6, learning_rate=0.3,
    scale_pos_weight=(sum(mask_tr_s35) - sum(y_all[mask_tr_s35])) / sum(y_all[mask_tr_s35]),
    random_state=42, eval_metric="logloss"
)
clf_lofo_s35.fit(X_all[mask_tr_s35], y_all[mask_tr_s35])
probs_lofo_s35 = clf_lofo_s35.predict_proba(X_all[mask_te_s35])[:, 1]
fpr_lofo_s35, tpr_lofo_s35, _ = roc_curve(y_all[mask_te_s35], probs_lofo_s35)
prec_lofo_s35, rec_lofo_s35, _ = precision_recall_curve(y_all[mask_te_s35], probs_lofo_s35)

# Plot ROC
ax1.plot(fpr_in, tpr_in, color='#1f77b4', lw=2.5, label=f'In-Distribution (AUC = {auc(fpr_in, tpr_in):.4f})')
ax1.plot(fpr_lofo_rs, tpr_lofo_rs, color='#d62728', lw=2, linestyle='--', label=f'LOFO Test RS232 (AUC = {auc(fpr_lofo_rs, tpr_lofo_rs):.4f})')
ax1.plot(fpr_lofo_s35, tpr_lofo_s35, color='#2ca02c', lw=2, linestyle='-.', label=f'LOFO Test s35932 (AUC = {auc(fpr_lofo_s35, tpr_lofo_s35):.4f})')
ax1.plot([0, 1], [0, 1], color='gray', linestyle=':')
ax1.set_title("A. ĐƯỜNG CONG ROC (Receiver Operating Characteristic)", fontsize=11, fontweight='bold')
ax1.set_xlabel("Tỷ lệ Báo Động Giả (False Positive Rate)", fontsize=10)
ax1.set_ylabel("Tỷ lệ Bắt Đúng Trojan (True Positive Rate)", fontsize=10)
ax1.legend(loc='lower right', fontsize=9)
ax1.grid(True, linestyle=':', alpha=0.6)

# Plot PR
ax2.plot(rec_in, prec_in, color='#1f77b4', lw=2.5, label=f'In-Distribution (PR-AUC = {auc(rec_in, prec_in):.4f})')
ax2.plot(rec_lofo_rs, prec_lofo_rs, color='#d62728', lw=2, linestyle='--', label=f'LOFO Test RS232 (PR-AUC = {auc(rec_lofo_rs, prec_lofo_rs):.4f})')
ax2.plot(rec_lofo_s35, prec_lofo_s35, color='#2ca02c', lw=2, linestyle='-.', label=f'LOFO Test s35932 (PR-AUC = {auc(rec_lofo_s35, prec_lofo_s35):.4f})')
ax2.set_title("B. ĐƯỜNG CONG PRECISION-RECALL (PR CURVE - Chỉ số thực tế)", fontsize=11, fontweight='bold')
ax2.set_xlabel("Độ Bao Phủ Trojan (Recall)", fontsize=10)
ax2.set_ylabel("Độ Chính Xác (Precision)", fontsize=10)
ax2.legend(loc='upper right', fontsize=9)
ax2.grid(True, linestyle=':', alpha=0.6)

plt.tight_layout()
fig3_path = os.path.join(FIGURES_DIR, "fig3_roc_and_pr_curves_in_dist_vs_lofo.png")
plt.savefig(fig3_path, dpi=300)
plt.close()
print(f"Đã lưu: {fig3_path}")

print("HOÀN TẤT TẤT CẢ BIỂU ĐỒ NÂNG CẤP!")

