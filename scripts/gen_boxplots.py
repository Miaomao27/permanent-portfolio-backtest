#!/usr/bin/env python3
"""箱线图版持有期图表 - 替代原柱状图"""
import os, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = '/home/cpy/文档/金融数据库建立/永久投资组合研究'
RES2 = os.path.join(BASE, 'results2')
CHARTS2 = os.path.join(BASE, 'charts2')
os.makedirs(CHARTS2, exist_ok=True)

font_path = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
prop = font_manager.FontProperties(fname=font_path)
plt.rcParams['font.family'] = prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

groups = ['sp500','nasdaq','china','china_000016_SH','china_000688_SH','china_000852_SH',
          'china_000905_SH','china_000932_SH','china_399006_SZ','china_000922_SH','china_H30269_CSI']
labels = ['标普500','纳指100','沪深300','上证50','科创50','中证1000',
          '中证500','中证2000','创业板指','中证红利','红利低波']

# 图1: 24月收益箱线图 (11组)
plt.figure(figsize=(14, 8))
data_24m = []
valid_labels = []
valid_groups = []
for g, lb in zip(groups, labels):
    try:
        df = pd.read_csv(os.path.join(RES2, f'hp_{g}_24m.csv'))
        data_24m.append(df['total_return_pct'].values)
        valid_labels.append(lb)
        valid_groups.append(g)
    except:
        pass

# 按中位数排序
medians = [np.median(d) for d in data_24m]
order = np.argsort(medians)[::-1]  # 降序
data_sorted = [data_24m[i] for i in order]
labels_sorted = [valid_labels[i] for i in order]

bp = plt.boxplot(data_sorted, labels=labels_sorted, patch_artist=True, vert=True,
                  showmeans=True, meanprops=dict(marker='D', markerfacecolor='red', markersize=5),
                  medianprops=dict(color='black', linewidth=2),
                  flierprops=dict(marker='o', markerfacecolor='gray', markersize=3, alpha=0.3))

# 配色
colors_box = ['#2196F3','#4CAF50','#FF5722','#FF9800','#9C27B0','#00BCD4',
              '#795548','#607D8B','#E91E63','#3F51B5','#009688']
for patch, c in zip(bp['boxes'], [colors_box[i] for i in order]):
    patch.set_facecolor(c)
    patch.set_alpha(0.7)

plt.axhline(y=0, color='red', linestyle='--', alpha=0.4, linewidth=1)
plt.xticks(rotation=30, ha='right', fontsize=9)
plt.ylabel('持有24月累计收益率(%)', fontsize=12)
plt.title('各组永久组合持有24月收益分布（箱线图）', fontsize=14, fontweight='bold')
plt.grid(alpha=0.2, axis='y')
# 添加说明
plt.figtext(0.5, -0.02, '箱体=25%~75%分位 中横线=中位数 菱形=均值 点=异常值', 
            ha='center', fontsize=9, color='gray')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS2, 'return_24m_boxplot.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✓ return_24m_boxplot.png")

# 图2: 沪深300五个持有期收益箱线图
plt.figure(figsize=(12, 7))
hp_names = ['1m', '3m', '6m', '12m', '24m']
hp_labels_display = ['1月\n(21天)', '3月\n(63天)', '6月\n(126天)', '12月\n(252天)', '24月\n(504天)']
data_hp = []
for hp in hp_names:
    df = pd.read_csv(os.path.join(RES2, f'hp_china_{hp}.csv'))
    data_hp.append(df['total_return_pct'].values)

bp2 = plt.boxplot(data_hp, labels=hp_labels_display, patch_artist=True, vert=True,
                   showmeans=True, meanprops=dict(marker='D', markerfacecolor='red', markersize=6),
                   medianprops=dict(color='black', linewidth=2.5),
                   flierprops=dict(marker='o', markerfacecolor='gray', markersize=3, alpha=0.2))

colors_hp = ['#64B5F6','#42A5F5','#1E88E5','#1565C0','#0D47A1']
for patch, c in zip(bp2['boxes'], colors_hp):
    patch.set_facecolor(c)
    patch.set_alpha(0.8)

plt.axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=1.5)
plt.ylabel('累计收益率(%)', fontsize=12)
plt.title('沪深300永久组合不同持有期收益分布（箱线图）', fontsize=14, fontweight='bold')
plt.grid(alpha=0.2, axis='y')
# 标注统计值
for i, d in enumerate(data_hp):
    q25, q50, q75 = np.percentile(d, [25, 50, 75])
    mean = np.mean(d)
    plt.text(i+1.35, q75, f'Q3={q75:.1f}%', fontsize=7, color='blue', va='bottom')
    plt.text(i+1.35, q50, f'Md={q50:.1f}%', fontsize=7, color='black', va='center')
    plt.text(i+1.35, q25, f'Q1={q25:.1f}%', fontsize=7, color='blue', va='top')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS2, 'return_distribution_boxplot.png'), dpi=150)
plt.close()
print("✓ return_distribution_boxplot.png")

# 图3: 红利低波 vs 沪深300 箱线图对比
plt.figure(figsize=(12, 7))
hp_days = [21, 63, 126, 252, 504]
hp_xlabels = ['21天\n(1月)', '63天\n(3月)', '126天\n(6月)', '252天\n(12月)', '504天\n(24月)']
data_hs300 = []
data_hldb = []
for hp in hp_names:
    d1 = pd.read_csv(os.path.join(RES2, f'hp_china_{hp}.csv'))['total_return_pct'].values
    d2 = pd.read_csv(os.path.join(RES2, f'hp_china_H30269_CSI_{hp}.csv'))['total_return_pct'].values
    data_hs300.append(d1)
    data_hldb.append(d2)

positions_hs = [i*3 + 0.8 for i in range(5)]
positions_hl = [i*3 + 1.6 for i in range(5)]

bp_hs = plt.boxplot(data_hs300, positions=positions_hs, widths=0.5, patch_artist=True,
                     showmeans=True, meanprops=dict(marker='D', markerfacecolor='white', markersize=4),
                     medianprops=dict(color='yellow', linewidth=1.5))
bp_hl = plt.boxplot(data_hldb, positions=positions_hl, widths=0.5, patch_artist=True,
                     showmeans=True, meanprops=dict(marker='D', markerfacecolor='white', markersize=4),
                     medianprops=dict(color='yellow', linewidth=1.5))

for b in bp_hs['boxes']:
    b.set_facecolor('#FF5722')
    b.set_alpha(0.6)
for b in bp_hl['boxes']:
    b.set_facecolor('#4CAF50')
    b.set_alpha(0.6)

plt.xticks([i*3+1.2 for i in range(5)], hp_xlabels, fontsize=9)
plt.legend([bp_hs['boxes'][0], bp_hl['boxes'][0]], ['沪深300永久组合', '红利低波永久组合'], 
           loc='upper left', fontsize=10)
plt.axhline(y=0, color='red', linestyle='--', alpha=0.4)
plt.ylabel('累计收益率(%)', fontsize=12)
plt.title('沪深300 vs 红利低波永久组合——各持有期收益分布对比', fontsize=13, fontweight='bold')
plt.grid(alpha=0.2, axis='y')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS2, 'return_compare_boxplot.png'), dpi=150)
plt.close()
print("✓ return_compare_boxplot.png")

print(f"\n✅ 3张箱线图已保存到 {CHARTS2}")
