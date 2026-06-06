#!/usr/bin/env python3
"""生成永久投资组合回测图表"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = '/home/cpy/文档/金融数据库建立/永久投资组合研究'
RES = os.path.join(BASE, 'results')
CHARTS = os.path.join(BASE, 'charts')
os.makedirs(CHARTS, exist_ok=True)

# 中文字体
zh_fonts = [f for f in font_manager.findSystemFonts() if any(n in f.lower() for n in ['noto', 'wqy', 'simsun', 'simhei', 'source', 'droid', 'cjk'])]
if zh_fonts:
    prop = font_manager.FontProperties(fname=zh_fonts[0])
    plt.rcParams['font.family'] = prop.get_name()
else:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

label_map = {
    'sp500': '标普500', 'nasdaq': '纳指100',
    'china': '沪深300', 'china_000016_SH': '上证50',
    'china_000688_SH': '科创50', 'china_000852_SH': '中证1000',
    'china_000905_SH': '中证500', 'china_000932_SH': '中证2000',
    'china_399006_SZ': '创业板指',
}

files = [
    ('sp500', 'result_sp500.csv'), ('nasdaq', 'result_nasdaq.csv'),
    ('china', 'result_china.csv'), ('china_000016_SH', 'result_china_000016_SH.csv'),
    ('china_000688_SH', 'result_china_000688_SH.csv'),
    ('china_000852_SH', 'result_china_000852_SH.csv'),
    ('china_000905_SH', 'result_china_000905_SH.csv'),
    ('china_000932_SH', 'result_china_000932_SH.csv'),
    ('china_399006_SZ', 'result_china_399006_SZ.csv'),
]

all_data = {}
for key, fn in files:
    path = os.path.join(RES, fn)
    if os.path.exists(path):
        df = pd.read_csv(path)
        df['total_return_pct'] = pd.to_numeric(df['total_return_pct'], errors='coerce')
        all_data[key] = df

# 图1: 收益分布对比
plt.figure(figsize=(14, 8))
colors = ['#2196F3','#4CAF50','#FF5722','#FF9800','#9C27B0','#00BCD4','#795548','#607D8B','#E91E63']
for i, (key, df) in enumerate(all_data.items()):
    data = df['total_return_pct'].values
    data = data[~np.isnan(data)]
    plt.hist(data, bins=80, alpha=0.5, color=colors[i % len(colors)], label=label_map[key], density=True)
plt.xlabel('累计收益率 (%)', fontsize=12)
plt.ylabel('密度', fontsize=12)
plt.title('永久投资组合不同入场点收益分布对比', fontsize=14)
plt.legend(fontsize=8, loc='upper right')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, 'distribution_compare.png'), dpi=150)
plt.close()
print("✓ distribution_compare.png")

# 图2: 累计收益排序柱状图
plt.figure(figsize=(14, 7))
means = []
labels_plot = []
std_errs = []
for key, df in list(all_data.items()):
    labels_plot.append(label_map[key])
    data = df['total_return_pct'].dropna().values
    means.append(np.mean(data))
    std_errs.append(np.std(data)/np.sqrt(len(data)))
colors_plot = ['#2196F3','#4CAF50'] + ['#FF5722','#FF9800','#9C27B0','#00BCD4','#795548','#607D8B','#E91E63']
bars = plt.bar(range(len(means)), means, yerr=std_errs, color=colors_plot[:len(means)],
               capsize=5, alpha=0.85)
for i, (bar, v) in enumerate(zip(bars, means)):
    plt.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(std_errs)*0.1,
             f'{v:.1f}%', ha='center', va='bottom', fontsize=9)
plt.xticks(range(len(labels_plot)), labels_plot, rotation=30, ha='right')
plt.ylabel('平均累计收益率 (%)', fontsize=12)
plt.title('各组永久组合平均累计收益对比', fontsize=14)
plt.grid(alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, 'return_bar_compare.png'), dpi=150)
plt.close()
print("✓ return_bar_compare.png")

# 图3: 夏普比率对比
plt.figure(figsize=(14, 7))
sharpe_vals = []
for key, df in list(all_data.items()):
    sharpe_vals.append(df['sharpe_ratio'].dropna().mean())
bars = plt.bar(range(len(sharpe_vals)), sharpe_vals, color=colors_plot[:len(sharpe_vals)], alpha=0.85)
for i, (bar, v) in enumerate(zip(bars, sharpe_vals)):
    plt.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.02,
             f'{v:.4f}', ha='center', va='bottom', fontsize=9)
plt.axhline(y=0, color='red', linestyle='--', alpha=0.5)
plt.xticks(range(len(labels_plot)), labels_plot, rotation=30, ha='right')
plt.ylabel('平均夏普比率', fontsize=12)
plt.title('各组风险调整收益对比', fontsize=14)
plt.grid(alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, 'sharpe_compare.png'), dpi=150)
plt.close()
print("✓ sharpe_compare.png")

# 图4: 年化收益 vs 最大回撤散点图
plt.figure(figsize=(12, 8))
ann_ret = [all_data[k]['annual_return_pct'].dropna().mean() for k in all_data]
mdd = [all_data[k]['max_drawdown_pct'].dropna().mean() for k in all_data]
sharpe = [all_data[k]['sharpe_ratio'].dropna().mean() for k in all_data]
sc = plt.scatter(mdd, ann_ret, c=sharpe, s=200, cmap='RdYlGn', alpha=0.8, edgecolors='black')
for i, key in enumerate(all_data):
    plt.annotate(label_map[key], (mdd[i], ann_ret[i]),
                 textcoords="offset points", xytext=(5,5), fontsize=9)
plt.colorbar(sc, label='夏普比率')
plt.xlabel('平均最大回撤 (%)', fontsize=12)
plt.ylabel('平均年化收益率 (%)', fontsize=12)
plt.title('风险-收益散点图 (圆圈颜色=夏普比率)', fontsize=14)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, 'risk_return_scatter.png'), dpi=150)
plt.close()
print("✓ risk_return_scatter.png")

print(f"\n所有图表已保存到 {CHARTS}")
