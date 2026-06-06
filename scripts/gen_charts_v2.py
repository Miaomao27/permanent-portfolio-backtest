#!/usr/bin/env python3
"""
用 matplotlib 重新生成 4 张持有期分析图表（中文 + 美观）
"""
import os, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib.patches as mpatches

# ── 路径 ──
BASE = '/home/cpy/文档/金融数据库建立/永久投资组合研究'
RES2 = os.path.join(BASE, 'results2')
CHARTS2 = os.path.join(BASE, 'charts2')
os.makedirs(CHARTS2, exist_ok=True)

# ── 字体 ──
FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if os.path.exists(FONT_PATH):
    font_manager.fontManager.addfont(FONT_PATH)
    prop = font_manager.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = prop.get_name()
    print(f"✓ 使用字体: {FONT_PATH} -> {prop.get_name()}")
else:
    # fallback
    zh_fonts = [f for f in font_manager.findSystemFonts()
                if any(n in f.lower() for n in ['notosanscjk','notoserifcjk','droid','wenquan','wqy'])]
    if zh_fonts:
        prop = font_manager.FontProperties(fname=zh_fonts[0])
        plt.rcParams['font.family'] = prop.get_name()
        print(f"⚠ fallback 字体: {zh_fonts[0]}")
    else:
        print("⚠ 未找到中文字体，使用默认字体")
plt.rcParams['axes.unicode_minus'] = False

# ── 数据 ──
groups = ['sp500','nasdaq','china','china_000016_SH','china_000688_SH','china_000852_SH',
          'china_000905_SH','china_000932_SH','china_399006_SZ','china_000922_SH','china_H30269_CSI']
labels = ['标普500','纳指100','沪深300','上证50','科创50','中证1000',
          '中证500','中证2000','创业板指','中证红利','红利低波']
hp_labels = ['1月','3月','6月','12月','24月']
hp_keys   = ['1m','3m','6m','12m','24m']
hp_days   = [21, 63, 126, 252, 504]

all_data = {}
for g in groups:
    path = os.path.join(RES2, f'hp_summary_{g}.csv')
    if os.path.exists(path):
        all_data[g] = pd.read_csv(path)
        print(f"  ✓ {g}")
    else:
        print(f"  ✗ {g} 不存在")

N = len(groups)

# 专业配色方案 (Tableau 20 风格)
colors = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b',
          '#e377c2','#7f7f7f','#bcbd22','#17becf','#aec7e8']
group_colors = dict(zip(groups, colors))

# ───────────────────────────────────────────────────────────────
# 图1: win_rate_heatmap_v2.png  —  胜率热力图
# ───────────────────────────────────────────────────────────────
print("\n▶ 图1: 胜率热力图")
win_rates = np.zeros((N, 5))
for i, g in enumerate(groups):
    df = all_data[g]
    for j, hp in enumerate(hp_keys):
        win_rates[i, j] = df[df['holding']==hp]['win_rate'].values[0] / 100.0

fig, ax = plt.subplots(figsize=(13, 9))
im = ax.imshow(win_rates, cmap='RdYlGn', aspect='auto', vmin=0.4, vmax=1.0)

# 色条
cbar = fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
cbar.set_label('胜率', fontsize=12)
cbar.ax.tick_params(labelsize=10)

# 轴标签
ax.set_xticks(range(5))
ax.set_xticklabels(hp_labels, fontsize=12)
ax.set_yticks(range(N))
ax.set_yticklabels(labels, fontsize=10)
ax.set_title('不同持有期胜率热力图', fontsize=16, fontweight='bold', pad=15)

# 网格线
ax.set_xticks(np.arange(-0.5, 5, 1), minor=True)
ax.set_yticks(np.arange(-0.5, N, 1), minor=True)
ax.grid(which='minor', color='gray', linestyle='-', linewidth=0.8, alpha=0.3)

# 标注数值
for i in range(N):
    for j in range(5):
        val = win_rates[i, j]
        txt = f'{val*100:.0f}%'
        color = 'white' if val < 0.55 else 'black'
        ax.text(j, i, txt, ha='center', va='center', fontsize=9,
                fontweight='bold', color=color)

plt.tight_layout()
fig.savefig(os.path.join(CHARTS2, 'win_rate_heatmap_v2.png'), dpi=200, bbox_inches='tight')
plt.close()
print("  ✓ win_rate_heatmap_v2.png")

# ───────────────────────────────────────────────────────────────
# 图2: return_24m_v2.png  —  持有24月收益柱状图（按收益排序）
# ───────────────────────────────────────────────────────────────
print("\n▶ 图2: 持有24月收益柱状图")
rets_24m_avg = np.array([all_data[g][all_data[g]['holding']=='24m']['avg_ret'].values[0] for g in groups])
rets_24m_med = np.array([all_data[g][all_data[g]['holding']=='24m']['med_ret'].values[0] for g in groups])

# 按平均收益从高到低排序
sort_idx = np.argsort(rets_24m_avg)[::-1]
sorted_groups = [groups[i] for i in sort_idx]
sorted_labels = [labels[i] for i in sort_idx]
sorted_avg = rets_24m_avg[sort_idx]
sorted_med = rets_24m_med[sort_idx]
sorted_colors = [group_colors[groups[i]] for i in sort_idx]

# 找到红利低波和标普500的位置用于高亮
hl_idx = None
sp_idx = None
for idx, g in enumerate(sorted_groups):
    if g == 'china_H30269_CSI':
        hl_idx = idx
    if g == 'sp500':
        sp_idx = idx

fig, ax = plt.subplots(figsize=(14, 7.5))
x = np.arange(len(sorted_groups))
width = 0.6

bars = ax.bar(x, sorted_avg, width, color=sorted_colors, alpha=0.85, edgecolor='white', linewidth=0.5,
              zorder=3)

# 叠加中位数点
ax.scatter(x, sorted_med, color='black', s=60, zorder=5, marker='D',
           label='中位数收益', edgecolors='white', linewidth=0.5)

# 标注数值（平均收益）
for bar, avg, med in zip(bars, sorted_avg, sorted_med):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
            f'{avg:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

# 高亮红利低波和标普500的柱
for idx, (g, bar) in enumerate(zip(sorted_groups, bars)):
    if g == 'china_H30269_CSI':
        bar.set_edgecolor('#d62728')
        bar.set_linewidth(3)
    elif g == 'sp500':
        bar.set_edgecolor('#1f77b4')
        bar.set_linewidth(3)

ax.set_xticks(x)
ax.set_xticklabels(sorted_labels, rotation=25, ha='right', fontsize=10)
ax.set_ylabel('持有24月累计收益率(%)', fontsize=13)
ax.set_title('各组合持有24月收益对比（按平均收益排序）', fontsize=15, fontweight='bold', pad=12)
ax.legend(fontsize=10, loc='upper left')
ax.grid(axis='y', alpha=0.3, zorder=0)
ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5, linewidth=0.8)

# 红蓝标注说明
red_patch = mpatches.Patch(edgecolor='#d62728', linewidth=3, facecolor='none', label='红利低波（突出）')
blue_patch = mpatches.Patch(edgecolor='#1f77b4', linewidth=3, facecolor='none', label='标普500（突出）')
ax.legend(handles=[red_patch, blue_patch], fontsize=9, loc='upper right')

plt.tight_layout()
fig.savefig(os.path.join(CHARTS2, 'return_24m_v2.png'), dpi=200, bbox_inches='tight')
plt.close()
print("  ✓ return_24m_v2.png")

# ───────────────────────────────────────────────────────────────
# 图3: return_vs_holding_v2.png  —  持有期vs平均收益曲线
# ───────────────────────────────────────────────────────────────
print("\n▶ 图3: 持有期vs平均收益曲线")
fig, ax = plt.subplots(figsize=(14, 8))

for i, g in enumerate(groups):
    df = all_data[g]
    rets = [df[df['holding']==hp]['avg_ret'].values[0] for hp in hp_keys]
    lw = 3.5 if g in ['sp500', 'china_H30269_CSI'] else 1.8
    alpha = 1.0 if g in ['sp500', 'china_H30269_CSI'] else 0.6
    ls = '-' if g in ['sp500', 'china_H30269_CSI'] else '--'
    ax.plot(hp_days, rets, 'o-', color=group_colors[g], label=labels[i],
            linewidth=lw, markersize=7 if g in ['sp500', 'china_H30269_CSI'] else 5,
            alpha=alpha, zorder=3 if g in ['sp500', 'china_H30269_CSI'] else 1)

ax.axhline(y=0, color='gray', linestyle='--', alpha=0.4, linewidth=0.8)
ax.set_xlabel('持有天数', fontsize=13)
ax.set_ylabel('平均累计收益率(%)', fontsize=13)
ax.set_title('持有期 vs 平均累计收益率', fontsize=16, fontweight='bold', pad=12)
ax.set_xticks(hp_days)
ax.set_xticklabels([f'{d}天\n({l})' for d, l in zip(hp_days, hp_labels)], fontsize=10)
ax.legend(fontsize=8, ncol=2, loc='upper left')
ax.grid(alpha=0.3, linestyle=':', linewidth=0.5)

# 额外文字说明
ax.annotate('加粗=标普500 & 红利低波', xy=(0.02, 0.98), xycoords='axes fraction',
            fontsize=9, ha='left', va='top',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8))

plt.tight_layout()
fig.savefig(os.path.join(CHARTS2, 'return_vs_holding_v2.png'), dpi=200, bbox_inches='tight')
plt.close()
print("  ✓ return_vs_holding_v2.png")

# ───────────────────────────────────────────────────────────────
# 图4: return_distribution_v2.png  —  沪深300不同持有期收益区间
# ───────────────────────────────────────────────────────────────
print("\n▶ 图4: 沪深300持有期收益区间")
group_key = 'china'  # 沪深300
df = all_data[group_key]

avg_vals = []
med_vals = []
best_vals = []
worst_vals = []
std_vals = []
for hp in hp_keys:
    row = df[df['holding']==hp].iloc[0]
    avg_vals.append(row['avg_ret'])
    med_vals.append(row['med_ret'])
    best_vals.append(row['best'])
    worst_vals.append(row['worst'])
    std_vals.append(row['std'])

fig, ax = plt.subplots(figsize=(12, 7))
x = np.arange(len(hp_keys))
width = 0.55

# 最好-最差区间作为误差条
yerr_low  = np.array(avg_vals) - np.array(worst_vals)
yerr_high = np.array(best_vals) - np.array(avg_vals)
yerr = np.array([yerr_low, yerr_high])

bars = ax.bar(x, avg_vals, width, yerr=yerr, color='#2ca02c', alpha=0.8,
              edgecolor='white', linewidth=0.5, capsize=6, error_kw={'linewidth':1.5, 'ecolor':'#555555'},
              label='平均收益', zorder=3)

# 叠加中位数点
ax.scatter(x, med_vals, color='#d62728', s=100, zorder=5, marker='D',
           label='中位数收益', edgecolors='white', linewidth=0.5)

# 标注均值和标准差
for i, (avg, std) in enumerate(zip(avg_vals, std_vals)):
    ax.text(i, best_vals[i] + 0.8, f'均值={avg:.1f}%', ha='center', va='bottom',
            fontsize=8, fontweight='bold', color='#2ca02c')
    ax.text(i, worst_vals[i] - 1.2, f'σ={std:.1f}%', ha='center', va='top',
            fontsize=8, color='#555555')

# 最好/最差标注
for i in range(len(hp_keys)):
    ax.annotate(f'最高:{best_vals[i]:.1f}%', xy=(i, best_vals[i]),
                xytext=(i+0.3, best_vals[i]+2), fontsize=7, color='#1f77b4',
                arrowprops=dict(arrowstyle='->', color='#1f77b4', lw=0.8))
    ax.annotate(f'最低:{worst_vals[i]:.1f}%', xy=(i, worst_vals[i]),
                xytext=(i+0.3, worst_vals[i]-2), fontsize=7, color='#d62728',
                arrowprops=dict(arrowstyle='->', color='#d62728', lw=0.8))

ax.set_xticks(x)
ax.set_xticklabels(hp_labels, fontsize=12)
ax.set_ylabel('累计收益率(%)', fontsize=13)
ax.set_title('沪深300 — 不同持有期收益区间（最好~最差）', fontsize=15, fontweight='bold', pad=12)
ax.legend(fontsize=11, loc='lower right')
ax.grid(axis='y', alpha=0.3, zorder=0)
ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5, linewidth=0.8)

plt.tight_layout()
fig.savefig(os.path.join(CHARTS2, 'return_distribution_v2.png'), dpi=200, bbox_inches='tight')
plt.close()
print("  ✓ return_distribution_v2.png")

print(f"\n{'='*50}")
print(f"✅ 全部 4 张图表已保存到:")
print(f"   {CHARTS2}/")
for f in ['win_rate_heatmap_v2.png', 'return_24m_v2.png', 'return_vs_holding_v2.png', 'return_distribution_v2.png']:
    fp = os.path.join(CHARTS2, f)
    sz = os.path.getsize(fp)
    print(f"   📊 {f}  ({sz/1024:.0f} KB)")
print(f"{'='*50}")
