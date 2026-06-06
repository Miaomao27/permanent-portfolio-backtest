#!/usr/bin/env python3
"""生成图表 - 11组全量"""
import os, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = '/home/cpy/文档/金融数据库建立/永久投资组合研究'
RES = os.path.join(BASE, 'results')
CHARTS = os.path.join(BASE, 'charts')
os.makedirs(CHARTS, exist_ok=True)

zh_fonts = [f for f in font_manager.findSystemFonts() if any(n in f.lower() for n in ['notosanscjk','notoserifcjk','droid','wenquan','wqy'])]
if zh_fonts:
    preferred = [f for f in zh_fonts if 'notosanscjk' in f.lower() and 'regular' in f.lower()]
    if not preferred:
        preferred = [f for f in zh_fonts if 'droid' in f.lower()]
    if not preferred:
        preferred = zh_fonts
    prop = font_manager.FontProperties(fname=preferred[0])
    plt.rcParams['font.family'] = prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

label_map = {
    'sp500': '标普500', 'nasdaq': '纳指100', 'china': '沪深300',
    'china_000016_SH': '上证50', 'china_000688_SH': '科创50',
    'china_000852_SH': '中证1000', 'china_000905_SH': '中证500',
    'china_000932_SH': '中证2000', 'china_399006_SZ': '创业板指',
    'china_000922_SH': '中证红利', 'china_H30269_CSI': '红利低波',
}

files = [
    ('sp500','result_sp500.csv'), ('nasdaq','result_nasdaq.csv'), ('china','result_china.csv'),
    ('china_000016_SH','result_china_000016_SH.csv'), ('china_000688_SH','result_china_000688_SH.csv'),
    ('china_000852_SH','result_china_000852_SH.csv'), ('china_000905_SH','result_china_000905_SH.csv'),
    ('china_000932_SH','result_china_000932_SH.csv'), ('china_399006_SZ','result_china_399006_SZ.csv'),
    ('china_000922_SH','result_china_000922_SH.csv'), ('china_H30269_CSI','result_china_H30269_CSI.csv'),
]

all_data = {}
for key, fn in files:
    path = os.path.join(RES, fn)
    if os.path.exists(path):
        df = pd.read_csv(path)
        df['total_return_pct'] = pd.to_numeric(df['total_return_pct'], errors='coerce')
        all_data[key] = df

colors = ['#2196F3','#4CAF50','#FF5722','#FF9800','#9C27B0','#00BCD4','#795548','#607D8B','#E91E63','#3F51B5','#009688']
labels_plot = [label_map[k] for k in all_data]

# 图1: 收益分布
plt.figure(figsize=(14, 8))
for i, (key, df) in enumerate(all_data.items()):
    data = df['total_return_pct'].dropna().values
    plt.hist(data, bins=80, alpha=0.5, color=colors[i], label=label_map[key], density=True)
plt.xlabel('累计收益率(%)', fontsize=12)
plt.ylabel('密度', fontsize=12)
plt.title('永久投资组合不同入场点收益分布对比(11组)', fontsize=14)
plt.legend(fontsize=7, loc='upper right')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, 'distribution_compare.png'), dpi=150)
plt.close()
print("✓ distribution_compare.png")

# 图2: 累计收益柱状图
plt.figure(figsize=(14, 7))
means = [all_data[k]['total_return_pct'].dropna().mean() for k in all_data]
stds = [all_data[k]['total_return_pct'].dropna().std()/np.sqrt(len(all_data[k])) for k in all_data]
bars = plt.bar(range(len(means)), means, yerr=stds, color=colors[:len(means)], capsize=5, alpha=0.85)
for bar, v in zip(bars, means):
    plt.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(stds)*0.1, f'{v:.1f}%', ha='center', va='bottom', fontsize=8)
plt.xticks(range(len(labels_plot)), labels_plot, rotation=30, ha='right')
plt.ylabel('平均累计收益率(%)', fontsize=12)
plt.title('各组永久组合平均累计收益对比(11组)', fontsize=14)
plt.grid(alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, 'return_bar_compare.png'), dpi=150)
plt.close()
print("✓ return_bar_compare.png")

# 图3: 夏普比率
plt.figure(figsize=(14, 7))
sharpe_vals = [all_data[k]['sharpe_ratio'].dropna().mean() for k in all_data]
bars = plt.bar(range(len(sharpe_vals)), sharpe_vals, color=colors[:len(sharpe_vals)], alpha=0.85)
for bar, v in zip(bars, sharpe_vals):
    plt.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.02, f'{v:.4f}', ha='center', va='bottom', fontsize=8)
plt.axhline(y=0, color='red', linestyle='--', alpha=0.5)
plt.xticks(range(len(labels_plot)), labels_plot, rotation=30, ha='right')
plt.ylabel('平均夏普比率', fontsize=12)
plt.title('风险调整收益对比(11组)', fontsize=14)
plt.grid(alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, 'sharpe_compare.png'), dpi=150)
plt.close()
print("✓ sharpe_compare.png")

# 图4: 风险-收益散点
plt.figure(figsize=(12, 8))
ann_ret = [all_data[k]['annual_return_pct'].dropna().mean() for k in all_data]
mdd = [all_data[k]['max_drawdown_pct'].dropna().mean() for k in all_data]
sharpe = [all_data[k]['sharpe_ratio'].dropna().mean() for k in all_data]
sc = plt.scatter(mdd, ann_ret, c=sharpe, s=200, cmap='RdYlGn', alpha=0.8, edgecolors='black')
for i, key in enumerate(all_data):
    plt.annotate(label_map[key], (mdd[i], ann_ret[i]), textcoords="offset points", xytext=(5,5), fontsize=8)
plt.colorbar(sc, label='夏普比率')
plt.xlabel('平均最大回撤(%)', fontsize=12)
plt.ylabel('平均年化收益率(%)', fontsize=12)
plt.title('风险-收益散点图(11组, 颜色=夏普)', fontsize=14)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, 'risk_return_scatter.png'), dpi=150)
plt.close()
print("✓ risk_return_scatter.png")

print(f"\n全部图表已保存到 {CHARTS}")
