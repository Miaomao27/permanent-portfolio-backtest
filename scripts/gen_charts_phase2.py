#!/usr/bin/env python3
"""Phase 2 图表生成 - 持有期分析"""
import os, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = '/home/cpy/文档/金融数据库建立/永久投资组合研究'
RES2 = os.path.join(BASE, 'results2')
CHARTS2 = os.path.join(BASE, 'charts2')
os.makedirs(CHARTS2, exist_ok=True)

zh_fonts = [f for f in font_manager.findSystemFonts() if any(n in f.lower() for n in ['notosanscjk','notoserifcjk','droid','wenquan','wqy'])]
if zh_fonts:
    preferred = [f for f in zh_fonts if 'notosanscjk' in f.lower() and 'regular' in f.lower()]
    if not preferred:
        preferred = [f for f in zh_fonts if 'droid' in f.lower()]
    if not preferred:
        preferred = zh_fonts
    prop = font_manager.FontProperties(fname=preferred[0])
    plt.rcParams['font.family'] = prop.get_name()
    print(f"Using font: {preferred[0]} -> {prop.get_name()}")
plt.rcParams['axes.unicode_minus'] = False

groups = ['sp500','nasdaq','china','china_000016_SH','china_000688_SH','china_000852_SH',
          'china_000905_SH','china_000932_SH','china_399006_SZ','china_000922_SH','china_H30269_CSI']
labels = ['标普500','纳指100','沪深300','上证50','科创50','中证1000',
          '中证500','中证2000','创业板指','中证红利','红利低波']
hp_labels = ['1月','3月','6月','12月','24月']

all_data = {}
for g in groups:
    try:
        all_data[g] = pd.read_csv(os.path.join(RES2, f'hp_summary_{g}.csv'))
    except:
        pass

colors = ['#2196F3','#4CAF50','#FF5722','#FF9800','#9C27B0','#00BCD4','#795548','#607D8B','#E91E63','#3F51B5','#009688']

# 图1: 胜率热力图
plt.figure(figsize=(12, 8))
win_rates = np.zeros((len(groups), 5))
for i, g in enumerate(groups):
    df = all_data[g]
    for j, hp in enumerate(['1m','3m','6m','12m','24m']):
        win_rates[i, j] = df[df['holding']==hp]['win_rate'].values[0] / 100

im = plt.imshow(win_rates, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
plt.colorbar(im, label='胜率', shrink=0.8)
plt.xticks(range(5), hp_labels, fontsize=11)
plt.yticks(range(len(labels)), labels, fontsize=9)
plt.title('不同持有期胜率热力图', fontsize=14, fontweight='bold')
for i in range(len(groups)):
    for j in range(5):
        txt = f'{win_rates[i,j]*100:.0f}%'
        plt.text(j, i, txt, ha='center', va='center', fontsize=8,
                 color='white' if win_rates[i,j] < 0.5 else 'black')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS2, 'win_rate_heatmap.png'), dpi=150)
plt.close()
print("✓ win_rate_heatmap.png")

# 图2: 持有期vs平均收益曲线
plt.figure(figsize=(14, 8))
hp_days = [21, 63, 126, 252, 504]
for i, g in enumerate(groups):
    df = all_data[g]
    rets = [df[df['holding']==hp]['avg_ret'].values[0] for hp in ['1m','3m','6m','12m','24m']]
    plt.plot(hp_days, rets, 'o-', color=colors[i], label=labels[i], linewidth=2, markersize=6)
plt.axhline(y=0, color='red', linestyle='--', alpha=0.3)
plt.xlabel('持有天数', fontsize=12)
plt.ylabel('平均收益率(%)', fontsize=12)
plt.title('持有期 vs 平均收益曲线', fontsize=14, fontweight='bold')
plt.legend(fontsize=8, ncol=2)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS2, 'return_vs_holding.png'), dpi=150)
plt.close()
print("✓ return_vs_holding.png")

# 图3: 24月持有期收益对比柱状图
plt.figure(figsize=(14, 7))
rets_24m = [all_data[g][all_data[g]['holding']=='24m']['avg_ret'].values[0] for g in groups]
wr_24m = [all_data[g][all_data[g]['holding']=='24m']['win_rate'].values[0] for g in groups]
bars = plt.bar(range(len(groups)), rets_24m, color=colors, alpha=0.85)
for bar, v, w in zip(bars, rets_24m, wr_24m):
    plt.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
             f'{v:.1f}%\n胜{w:.0f}%', ha='center', va='bottom', fontsize=8)
plt.xticks(range(len(labels)), labels, rotation=30, ha='right', fontsize=9)
plt.ylabel('持有24月平均收益(%)', fontsize=12)
plt.title('各组合持有24月收益对比', fontsize=14, fontweight='bold')
plt.grid(alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS2, 'return_24m_compare.png'), dpi=150)
plt.close()
print("✓ return_24m_compare.png")

# 图4: 胜率vs持有期散点图
plt.figure(figsize=(12, 8))
for i, g in enumerate(groups):
    df = all_data[g]
    hp_d = [21, 63, 126, 252, 504]
    wrs = [df[df['holding']==hp]['win_rate'].values[0] for hp in ['1m','3m','6m','12m','24m']]
    plt.plot(hp_d, wrs, 'o-', color=colors[i], label=labels[i], linewidth=2, markersize=6)
plt.axhline(y=50, color='red', linestyle='--', alpha=0.3, label='50%分界线')
plt.xlabel('持有天数', fontsize=12)
plt.ylabel('胜率(%)', fontsize=12)
plt.title('持有期 vs 胜率曲线', fontsize=14, fontweight='bold')
plt.legend(fontsize=8, ncol=2)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS2, 'win_rate_vs_holding.png'), dpi=150)
plt.close()
print("✓ win_rate_vs_holding.png")

print(f"\n✅ 全部图表已保存到 {CHARTS2}")
