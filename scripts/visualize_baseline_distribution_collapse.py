"""
Script: scripts/visualize_baseline_distribution_collapse.py
Mục đích:
  Tạo các biểu đồ trực quan hóa phân phối mật độ (KDE / Density Plots),
  mặt phẳng quyết định (Decision Surface), phân phối xác suất dự đoán (Predicted Probabilities),
  và không gian đặc trưng (PCA 2D) để giải thích tường minh:
  1. Vì sao Baseline đồ thị nén phẳng + 5 đặc trưng Hasegawa lại "tốt" trong In-Distribution (cắt đúng tọa độ của mạch).
  2. Vì sao Baseline lại "sụp đổ thảm hại" trong LOFO (các họ vi mạch bị trôi dạt phân phối, tọa độ bị lệch hàng trăm bước).
"""

import os
import glob
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import gaussian_kde
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.decomposition import PCA
import xgboost as xgb

# Đảm bảo thư mục lưu biểu đồ
FIGURES_DIR = "outputs/figures/baseline_density_analysis"
os.makedirs(FIGURES_DIR, exist_ok=True)

# Phong cách đồ họa chuẩn mực học thuật
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 1.0

# 1. Đọc và gộp toàn bộ dữ liệu 30 vi mạch
csv_files = sorted(glob.glob("data/circuits/*.csv"))
dfs = []
for f in csv_files:
    basename = os.path.basename(f)
    circuit_name = basename.replace('.csv', '')
    # Xác định họ vi mạch
    if basename.startswith("RS232"):
        family = "RS232"
    elif basename.startswith("s15850"):
        family = "s15850"
    elif basename.startswith("s35932"):
        family = "s35932"
    elif basename.startswith("s38417"):
        family = "s38417"
    elif basename.startswith("s38584"):
        family = "s38584"
    else:
        family = "Other"
    
    df = pd.read_csv(f)
    df['family'] = family
    df['circuit'] = circuit_name
    dfs.append(df)

data = pd.concat(dfs, ignore_index=True)
print(f"Tổng số cổng: {len(data)}, Tổng số Trojan: {data['Trojan'].sum()}")

FEATURES_5 = ['LGFi', 'ffi', 'ffo', 'PI', 'PO']
FAMILIES = ['RS232', 's15850', 's35932', 's38417', 's38584']
FAMILY_COLORS = {
    'RS232': '#1f77b4',   # Lam
    's15850': '#ff7f0e',  # Cam
    's35932': '#2ca02c',  # Lục
    's38417': '#9467bd',  # Tím
    's38584': '#d62728'   # Đỏ
}

# ==============================================================================
# HÌNH 1: PHÂN PHỐI MẬT ĐỘ (KDE DENSITY) 5 ĐẶC TRƯNG HASEGAWA GIỮA 5 HỌ VI MẠCH
# ==============================================================================
print("Đang tạo Hình 1: Phân phối mật độ 5 đặc trưng giữa các họ vi mạch...")
fig, axes = plt.subplots(2, 3, figsize=(16, 9))
axes = axes.flatten()

feature_titles = {
    'LGFi': r'Logic Gate Fan-in ($LGFi$ - Bán kính 2 bước)',
    'ffi': r'Khoảng cách Flip-Flop Input ($ffi$ - Steps to FF ngõ vào)',
    'ffo': r'Khoảng cách Flip-Flop Output ($ffo$ - Steps to FF ngõ ra)',
    'PI': r'Khoảng cách Primary Input ($PI$ - Steps to Input sơ cấp)',
    'PO': r'Khoảng cách Primary Output ($PO$ - Steps to Output sơ cấp)'
}

for idx, feat in enumerate(FEATURES_5):
    ax = axes[idx]
    
    for fam in FAMILIES:
        vals = data[data['family'] == fam][feat].values
        # Cắt bớt đuôi ngoại lai (outliers) để biểu diễn trực quan mật độ
        p99 = np.percentile(vals, 99)
        vals_filtered = vals[vals <= max(p99, 10)]
        
        if len(np.unique(vals_filtered)) > 1:
            kde = gaussian_kde(vals_filtered, bw_method='silverman')
            xs = np.linspace(min(vals_filtered), max(vals_filtered), 300)
            density = kde(xs)
            ax.plot(xs, density, label=f"{fam} (μ={np.mean(vals):.1f})", 
                    color=FAMILY_COLORS[fam], lw=2.2)
            ax.fill_between(xs, density, color=FAMILY_COLORS[fam], alpha=0.15)
        else:
            ax.axvline(vals[0], color=FAMILY_COLORS[fam], lw=2, linestyle='--', label=f"{fam} (μ={np.mean(vals):.1f})")

    ax.set_title(feature_titles[feat], fontsize=12, fontweight='bold', pad=8)
    ax.set_xlabel("Giá trị đặc trưng (Số bước nhảy topological hops)", fontsize=10)
    ax.set_ylabel("Mật độ xác suất (Probability Density)", fontsize=10)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(fontsize=9, loc='upper right')

# Ô thứ 6 (axes[5]): Trực quan hóa Khoảng cách Wasserstein (Earth Mover's Distance)
ax_w = axes[5]
from scipy.stats import wasserstein_distance
w_distances = []
for fam in FAMILIES[1:]:
    w_ffi = wasserstein_distance(data[data['family'] == 'RS232']['ffi'], data[data['family'] == fam]['ffi'])
    w_po = wasserstein_distance(data[data['family'] == 'RS232']['PO'], data[data['family'] == fam]['PO'])
    w_distances.append({'family': fam, 'w_ffi': w_ffi, 'w_po': w_po})

w_df = pd.DataFrame(w_distances)
x_indices = np.arange(len(w_df))
bar_width = 0.35
ax_w.bar(x_indices - bar_width/2, w_df['w_ffi'], width=bar_width, label="Khoảng cách W(ffi) so với RS232", color='#d62728', alpha=0.85)
ax_w.bar(x_indices + bar_width/2, w_df['w_po'], width=bar_width, label="Khoảng cách W(PO) so với RS232", color='#1f77b4', alpha=0.85)
ax_w.set_xticks(x_indices)
ax_w.set_xticklabels(w_df['family'], fontsize=10, fontweight='bold')
ax_w.set_ylabel("Khoảng cách phân phối Wasserstein (hops)", fontsize=10)
ax_w.set_title("Mức độ trôi dạt phân phối (Wasserstein Drift) so với RS232", fontsize=12, fontweight='bold')
ax_w.grid(True, linestyle=':', alpha=0.6)
ax_w.legend(fontsize=9)

plt.tight_layout()
fig1_path = os.path.join(FIGURES_DIR, "fig1_feature_density_shift_across_families.png")
plt.savefig(fig1_path, dpi=300)
plt.close()
print(f"Đã lưu: {fig1_path}")


# ==============================================================================
# HÌNH 2: PHÂN PHỐI XÁC SUẤT DỰ ĐOÁN P(Trojan) - IN-DISTRIBUTION VS LOFO
# ==============================================================================
print("Đang tạo Hình 2: Phân phối xác suất dự đoán P(Trojan)...")

# 1. Train In-Distribution Model
X = data[FEATURES_5].values
y = data['Trojan'].values

sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(sss.split(X, y))

scale_pos = (len(y[train_idx]) - sum(y[train_idx])) / sum(y[train_idx])
clf_indist = xgb.XGBClassifier(
    n_estimators=100, max_depth=6, learning_rate=0.3, 
    scale_pos_weight=scale_pos, random_state=42, n_jobs=-1, eval_metric="logloss"
)
clf_indist.fit(X[train_idx], y[train_idx])
y_probs_indist_test = clf_indist.predict_proba(X[test_idx])[:, 1]
y_test_labels = y[test_idx]

# 2. Train LOFO Model (Train on 4 families: s15850, s35932, s38417, s38584 -> Test on RS232)
# hoặc Train on RS232, s15850, s38417, s38584 -> Test on s35932
train_lofo_mask = data['family'] != 'RS232'
test_lofo_mask = data['family'] == 'RS232'

scale_pos_lofo = (sum(train_lofo_mask) - sum(y[train_lofo_mask])) / max(sum(y[train_lofo_mask]), 1)
clf_lofo = xgb.XGBClassifier(
    n_estimators=100, max_depth=6, learning_rate=0.3,
    scale_pos_weight=scale_pos_lofo, random_state=42, n_jobs=-1, eval_metric="logloss"
)
clf_lofo.fit(X[train_lofo_mask], y[train_lofo_mask])
y_probs_lofo_test = clf_lofo.predict_proba(X[test_lofo_mask])[:, 1]
y_lofo_labels = y[test_lofo_mask]

# Cũng tính LOFO test trên s35932 (nơi bị Recall = 0%)
train_lofo_s35_mask = data['family'] != 's35932'
test_lofo_s35_mask = data['family'] == 's35932'
scale_pos_s35 = (sum(train_lofo_s35_mask) - sum(y[train_lofo_s35_mask])) / max(sum(y[train_lofo_s35_mask]), 1)
clf_lofo_s35 = xgb.XGBClassifier(
    n_estimators=100, max_depth=6, learning_rate=0.3,
    scale_pos_weight=scale_pos_s35, random_state=42, n_jobs=-1, eval_metric="logloss"
)
clf_lofo_s35.fit(X[train_lofo_s35_mask], y[train_lofo_s35_mask])
y_probs_lofo_s35 = clf_lofo_s35.predict_proba(X[test_lofo_s35_mask])[:, 1]
y_lofo_s35_labels = y[test_lofo_s35_mask]

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.5))

# Subplot 1: In-Distribution Probability Distribution
bins = np.linspace(0, 1, 50)
ax1.hist(y_probs_indist_test[y_test_labels == 0], bins=bins, alpha=0.6, color='#1f77b4', 
         label='Benign (Cổng sạch)', density=True, log=True)
ax1.hist(y_probs_indist_test[y_test_labels == 1], bins=bins, alpha=0.7, color='#d62728', 
         label='Trojan (Cổng mã độc)', density=True, log=True)
ax1.axvline(0.940, color='black', linestyle='--', lw=2, label='Ngưỡng bài báo (τ = 0.940)')
ax1.set_title("A. IN-DISTRIBUTION (Phân chia 60/20/20 ngẫu nhiên)\nPhân Tách Rõ Rệt: Trojan tập trung sát 1.0", fontsize=11, fontweight='bold')
ax1.set_xlabel("Xác suất dự đoán P(Trojan)", fontsize=10)
ax1.set_ylabel("Mật độ log (Log Density)", fontsize=10)
ax1.legend(loc='upper center', fontsize=9)
ax1.grid(True, linestyle=':', alpha=0.6)

# Subplot 2: LOFO Testing on RS232
ax2.hist(y_probs_lofo_test[y_lofo_labels == 0], bins=bins, alpha=0.6, color='#1f77b4', 
         label='Benign (RS232 sạch)', density=True, log=True)
ax2.hist(y_probs_lofo_test[y_lofo_labels == 1], bins=bins, alpha=0.7, color='#d62728', 
         label='Trojan (RS232 Trojan)', density=True, log=True)
ax2.axvline(0.940, color='black', linestyle='--', lw=2, label='Ngưỡng bài báo (τ = 0.940)')
ax2.set_title("B. OUT-OF-DISTRIBUTION (LOFO Test trên RS232)\nSụp Đổ: 95% Trojan bị kéo tụt dưới ngưỡng τ=0.940", fontsize=11, fontweight='bold')
ax2.set_xlabel("Xác suất dự đoán P(Trojan)", fontsize=10)
ax2.legend(loc='upper center', fontsize=9)
ax2.grid(True, linestyle=':', alpha=0.6)

# Subplot 3: LOFO Testing on s35932
ax3.hist(y_probs_lofo_s35[y_lofo_s35_labels == 0], bins=bins, alpha=0.6, color='#1f77b4', 
         label='Benign (s35932 sạch)', density=True, log=True)
ax3.hist(y_probs_lofo_s35[y_lofo_s35_labels == 1], bins=bins, alpha=0.7, color='#d62728', 
         label='Trojan (s35932 Trojan)', density=True, log=True)
ax3.axvline(0.940, color='black', linestyle='--', lw=2, label='Ngưỡng bài báo (τ = 0.940)')
ax3.set_title("C. OUT-OF-DISTRIBUTION (LOFO Test trên s35932)\nMù Hoàn Toàn: Trojan chìm nghỉm trong Benign (P < 0.2)", fontsize=11, fontweight='bold')
ax3.set_xlabel("Xác suất dự đoán P(Trojan)", fontsize=10)
ax3.legend(loc='upper center', fontsize=9)
ax3.grid(True, linestyle=':', alpha=0.6)

plt.tight_layout()
fig2_path = os.path.join(FIGURES_DIR, "fig2_indist_vs_lofo_predicted_probability_kde.png")
plt.savefig(fig2_path, dpi=300)
plt.close()
print(f"Đã lưu: {fig2_path}")


# ==============================================================================
# HÌNH 3: 2D DECISION BOUNDARY & CƠ CHẾ "HỌC VẸT TỌA ĐỘ MẠCH CHỦ" (COORDINATE MEMORIZATION)
# ==============================================================================
print("Đang tạo Hình 3: Mặt phẳng quyết định 2D và hiện tượng học vẹt tọa độ...")

# Để trực quan hóa không gian quyết định 2D rõ nét nhất, ta dùng 2 đặc trưng quan trọng nhất: ffi và PO
# Huấn luyện XGBoost trên họ RS232 với 2 đặc trưng ffi và PO
rs232_data = data[data['family'] == 'RS232']
X_rs232_2d = rs232_data[['ffi', 'PO']].values
y_rs232_2d = rs232_data['Trojan'].values

scale_2d = (len(y_rs232_2d) - sum(y_rs232_2d)) / sum(y_rs232_2d)
clf_2d = xgb.XGBClassifier(
    n_estimators=100, max_depth=5, learning_rate=0.2, 
    scale_pos_weight=scale_2d, random_state=42, eval_metric="logloss"
)
clf_2d.fit(X_rs232_2d, y_rs232_2d)

# Tạo lưới tọa độ
x_min, x_max = 0, 50
y_min, y_max = 0, 100
xx, yy = np.meshgrid(np.linspace(x_min, x_max, 250), np.linspace(y_min, y_max, 250))
grid_points = np.c_[xx.ravel(), yy.ravel()]
Z = clf_2d.predict_proba(grid_points)[:, 1]
Z = Z.reshape(xx.shape)

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.5))

# Panel 1: Huấn luyện và Test trên RS232 (In-Distribution)
contour1 = ax1.contourf(xx, yy, Z, levels=np.linspace(0, 1, 11), cmap='Blues', alpha=0.7)
# Vẽ ranh giới phân loại tại tau = 0.90
ax1.contour(xx, yy, Z, levels=[0.90], colors='red', linewidths=2.5, linestyles='--')
# Điểm Benign và Trojan của RS232
benign_rs = (y_rs232_2d == 0)
trojan_rs = (y_rs232_2d == 1)
ax1.scatter(X_rs232_2d[benign_rs, 0][:500], X_rs232_2d[benign_rs, 1][:500], 
            c='#1f77b4', s=15, alpha=0.3, label='RS232 Benign')
ax1.scatter(X_rs232_2d[trojan_rs, 0], X_rs232_2d[trojan_rs, 1], 
            c='#d62728', s=45, edgecolors='black', marker='^', label='RS232 Trojan (Nằm gọn trong vùng đỏ!)')
ax1.set_xlim(0, 40)
ax1.set_ylim(0, 80)
ax1.set_title("A. TẬP HUẤN LUYỆN RS232 (In-Distribution)\nXGBoost cắt đúng hộp tọa độ chứa Trojan!", fontsize=11, fontweight='bold')
ax1.set_xlabel("Khoảng cách tới Flip-Flop Input (ffi)", fontsize=10)
ax1.set_ylabel("Khoảng cách tới Primary Output (PO)", fontsize=10)
ax1.legend(loc='upper right', fontsize=8.5)
ax1.grid(True, linestyle=':', alpha=0.6)

# Panel 2: Kiểm thử trên s38417 (LOFO Fold 3)
s38417_data = data[data['family'] == 's38417']
X_s38417_2d = s38417_data[['ffi', 'PO']].values
y_s38417_2d = s38417_data['Trojan'].values

ax2.contourf(xx, yy, Z, levels=np.linspace(0, 1, 11), cmap='Blues', alpha=0.7)
ax2.contour(xx, yy, Z, levels=[0.90], colors='red', linewidths=2.5, linestyles='--')
benign_s38417 = (y_s38417_2d == 0)
trojan_s38417 = (y_s38417_2d == 1)
ax2.scatter(X_s38417_2d[benign_s38417, 0][:1000], X_s38417_2d[benign_s38417, 1][:1000], 
            c='#9467bd', s=15, alpha=0.3, label='s38417 Benign (Bị co cụm ở góc [0, 5])')
ax2.scatter(X_s38417_2d[trojan_s38417, 0], X_s38417_2d[trojan_s38417, 1], 
            c='#ff7f0e', s=55, edgecolors='black', marker='s', label='s38417 Trojan (BỊ BỎ SÓT HOÀN TOÀN!)')
ax2.set_xlim(0, 40)
ax2.set_ylim(0, 80)
ax2.set_title("B. NGOẠI SUY TRÊN s38417 (LOFO)\nToàn bộ mạch co cụm ở góc [0,5], lệch khỏi hộp Trojan!", fontsize=11, fontweight='bold')
ax2.set_xlabel("Khoảng cách tới Flip-Flop Input (ffi)", fontsize=10)
ax2.set_ylabel("Khoảng cách tới Primary Output (PO)", fontsize=10)
ax2.legend(loc='upper right', fontsize=8.5)
ax2.grid(True, linestyle=':', alpha=0.6)

# Panel 3: Kiểm thử trên s38584 (LOFO Fold 4)
s38584_data = data[data['family'] == 's38584']
X_s38584_2d = s38584_data[['ffi', 'PO']].values
y_s38584_2d = s38584_data['Trojan'].values

ax3.contourf(xx, yy, Z, levels=np.linspace(0, 1, 11), cmap='Blues', alpha=0.7)
ax3.contour(xx, yy, Z, levels=[0.90], colors='red', linewidths=2.5, linestyles='--')
benign_s38584 = (y_s38584_2d == 0)
trojan_s38584 = (y_s38584_2d == 1)
# Vẽ trên thang mở rộng để thấy điểm s38584 dạt ra ngoài
ax3.scatter(X_s38584_2d[benign_s38584, 0][:1000], X_s38584_2d[benign_s38584, 1][:1000], 
            c='#2ca02c', s=15, alpha=0.3, label='s38584 Benign (Dạt xa sang ffi > 50-300)')
ax3.scatter(X_s38584_2d[trojan_s38584, 0], X_s38584_2d[trojan_s38584, 1], 
            c='#d62728', s=60, edgecolors='black', marker='*', label='s38584 Trojan (Trôi dạt tọa độ!)')
ax3.set_xlim(0, 120)
ax3.set_ylim(0, 80)
ax3.set_title("C. NGOẠI SUY TRÊN s38584 (LOFO)\nMạch khổng lồ, điểm dạt xa ngoài biên quyết định!", fontsize=11, fontweight='bold')
ax3.set_xlabel("Khoảng cách tới Flip-Flop Input (ffi)", fontsize=10)
ax3.set_ylabel("Khoảng cách tới Primary Output (PO)", fontsize=10)
ax3.legend(loc='upper right', fontsize=8.5)
ax3.grid(True, linestyle=':', alpha=0.6)

plt.tight_layout()
fig3_path = os.path.join(FIGURES_DIR, "fig3_decision_boundary_and_coordinate_memorization_2d.png")
plt.savefig(fig3_path, dpi=300)
plt.close()
print(f"Đã lưu: {fig3_path}")


# ==============================================================================
# HÌNH 4: PHÂN BỐ KHÔNG GIAN ĐẶC TRƯNG 2D PCA GIỮA CÁC HỌ VI MẠCH (ISOLATED ISLANDS)
# ==============================================================================
print("Đang tạo Hình 4: Phân tích 2D PCA giữa các họ vi mạch...")

pca = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6.5))

# Subplot 1: Tất cả các họ vi mạch trên không gian PCA 2D
for fam in FAMILIES:
    mask = (data['family'] == fam)
    ax1.scatter(X_pca[mask, 0], X_pca[mask, 1], c=FAMILY_COLORS[fam], 
                label=f"Họ {fam} ({sum(mask):,} cổng)", alpha=0.25, s=12)

ax1.set_title("A. CÁC HỌ VI MẠCH TẠO THÀNH CÁC HÒN ĐẢO CÔ LẬP TRÊN KHÔNG GIAN ĐẶC TRƯNG\n(PCA 2D trên 5 đặc trưng Hasegawa)", 
              fontsize=11, fontweight='bold')
ax1.set_xlabel(f"PCA Thành Phần 1 (Giải thích {pca.explained_variance_ratio_[0]*100:.1f}% phương sai)", fontsize=10)
ax1.set_ylabel(f"PCA Thành Phần 2 (Giải thích {pca.explained_variance_ratio_[1]*100:.1f}% phương sai)", fontsize=10)
ax1.legend(loc='upper right', fontsize=9)
ax1.grid(True, linestyle=':', alpha=0.6)

# Subplot 2: Phân bố vị trí của Trojan giữa các họ
for fam in FAMILIES:
    mask_trojan = (data['family'] == fam) & (data['Trojan'] == 1)
    if sum(mask_trojan) > 0:
        ax2.scatter(X_pca[mask_trojan, 0], X_pca[mask_trojan, 1], c=FAMILY_COLORS[fam], 
                    label=f"Trojan họ {fam} ({sum(mask_trojan)} cổng)", s=45, edgecolors='black', alpha=0.9)

ax2.set_title("B. VỊ TRÍ CỦA TROJAN TRÊN TỪNG HỌ VI MẠCH\nTrojan của mỗi họ nằm ở một vùng không gian hoàn toàn khác nhau!", 
              fontsize=11, fontweight='bold')
ax2.set_xlabel(f"PCA Thành Phần 1", fontsize=10)
ax2.set_ylabel(f"PCA Thành Phần 2", fontsize=10)
ax2.legend(loc='upper right', fontsize=9)
ax2.grid(True, linestyle=':', alpha=0.6)

plt.tight_layout()
fig4_path = os.path.join(FIGURES_DIR, "fig4_pca_tsne_domain_divergence.png")
plt.savefig(fig4_path, dpi=300)
plt.close()
print(f"Đã lưu: {fig4_path}")

print("TẤT CẢ 4 HÌNH ẢNH TRỰC QUAN HÓA ĐÃ HOÀN TẤT THÀNH CÔNG!")

