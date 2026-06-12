#!/usr/bin/env python3
"""生成三场景对比的蒙特卡洛模拟图表"""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

# ── 路径配置 ──
BASE = Path('/home/cpy/文档/金融数据库建立/永久投资组合研究/蒙特卡洛模拟')
OUT   = BASE / 'charts'
OUT.mkdir(parents=True, exist_ok=True)

SCENARIOS = ['保守', '中位', '乐观']
COLORS    = {'保守': '#4A90D9', '中位': '#E8833A', '乐观': '#50B86C'}
SCENE_LABELS = {'保守': '保守 (5%年化)', '中位': '中位 (6.5%年化)', '乐观': '乐观 (8%年化)'}

# ── 字体设置 ──
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False

# ── 读取 CSV 数据 ──
dfs = {}
for s in SCENARIOS:
    dfs[s] = pd.read_csv(BASE / f'results_{s}.csv')

ages = dfs['保守']['age'].values

# ── 读取路径数据（直方图用）──
paths = {}
for s in SCENARIOS:
    p = np.load(BASE / f'paths_{s}.npy')
    # 提取每年年末（第11, 23, 35, ...个月）
    yearly_indices = np.arange(11, p.shape[1], 12)
    # 取所有年末值
    paths[s] = p[:, yearly_indices]  # shape (1000, 34)

# ==============================================================
# 图表 1: 年龄-资产曲线图
# ==============================================================
fig1, ax1 = plt.subplots(figsize=(12, 7), facecolor='#1a1a2e')
ax1.set_facecolor('#16213e')

for s in SCENARIOS:
    df = dfs[s]
    c = COLORS[s]
    label = SCENE_LABELS[s]

    # 中位数曲线
    ax1.plot(df['age'], df['p50'] / 10000, color=c, linewidth=2.0, label=label, zorder=3)
    # P25-P75 阴影
    ax1.fill_between(df['age'], df['p25'] / 10000, df['p75'] / 10000,
                     color=c, alpha=0.15, linewidth=0)
    # P5-P95 浅阴影
    ax1.fill_between(df['age'], df['p5'] / 10000, df['p95'] / 10000,
                     color=c, alpha=0.07, linewidth=0)

# 水平参考线：1000万
ax1.axhline(y=1000, color='#FFD700', linestyle='--', linewidth=1.2, alpha=0.7, label='1000万目标')

ax1.set_xlabel('年龄', fontsize=13, color='#cccccc')
ax1.set_ylabel('资产 (万元)', fontsize=13, color='#cccccc')
ax1.set_title('蒙特卡洛模拟：三场景年龄-资产曲线对比', fontsize=15, color='#ffffff', fontweight='bold', pad=15)
ax1.legend(fontsize=11, facecolor='#1a1a2e', edgecolor='#444444', labelcolor='#cccccc')
ax1.set_xlim(26, 60)
ax1.grid(True, alpha=0.2, linestyle=':')
ax1.tick_params(colors='#aaaaaa')

# Y轴格式化
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:.0f}'))

fig1.tight_layout()
fig1.savefig(OUT / '01_年龄_资产曲线.png', dpi=200, bbox_inches='tight', facecolor=fig1.get_facecolor())
plt.close(fig1)
print(f"  ✔ 01_年龄_资产曲线.png")

# ==============================================================
# 图表 2: 60岁资产分布直方图
# ==============================================================
fig2, ax2 = plt.subplots(figsize=(12, 6.5), facecolor='#1a1a2e')
ax2.set_facecolor('#16213e')

# 取第34年年末（60岁）
final_idx = -1  # 最后一个年末

bins = 80
# 为了三场景可比，统一横轴范围
all_vals = []
for s in SCENARIOS:
    all_vals.append(paths[s][:, final_idx] / 10000)
all_flat = np.concatenate(all_vals)
x_min, x_max = np.percentile(all_flat, 0.5), np.percentile(all_flat, 99.5)
bin_edges = np.linspace(x_min, x_max, bins + 1)

for s in SCENARIOS:
    c = COLORS[s]
    label = SCENE_LABELS[s]
    vals = paths[s][:, final_idx] / 10000
    ax2.hist(vals, bins=bin_edges, alpha=0.40, color=c, label=label,
             density=True, edgecolor='none')

# 标记中位数线
for s in SCENARIOS:
    med = float(dfs[s][dfs[s]['age']==60]['p50'].iloc[0]) / 10000
    c = COLORS[s]
    ax2.axvline(x=med, color=c, linestyle='--', linewidth=1.8, alpha=0.8)
    ax2.text(med, ax2.get_ylim()[1]*0.92, f'{s}: {med:.0f}万',
             color=c, fontsize=9, ha='center',
             bbox=dict(boxstyle='round,pad=0.2', facecolor='#1a1a2e', edgecolor=c, alpha=0.8))

# 1000万参考线
ax2.axvline(x=1000, color='#FFD700', linestyle='-', linewidth=1.5, alpha=0.6, label='1000万')

ax2.set_xlabel('60岁时资产 (万元)', fontsize=13, color='#cccccc')
ax2.set_ylabel('概率密度', fontsize=13, color='#cccccc')
ax2.set_title('蒙特卡洛模拟：60岁资产分布对比（三场景）', fontsize=15, color='#ffffff', fontweight='bold', pad=15)
ax2.legend(fontsize=11, facecolor='#1a1a2e', edgecolor='#444444', labelcolor='#cccccc')
ax2.grid(True, alpha=0.2, linestyle=':')
ax2.tick_params(colors='#aaaaaa')

# Y轴科学计数法抑制
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:.3f}' if x < 1 else f'{x:.4f}'))

fig2.tight_layout()
fig2.savefig(OUT / '02_60岁资产分布直方图.png', dpi=200, bbox_inches='tight', facecolor=fig2.get_facecolor())
plt.close(fig2)
print(f"  ✔ 02_60岁资产分布直方图.png")

# ==============================================================
# 图表 3: 1000万达成概率年龄演进图
# ==============================================================
fig3, ax3 = plt.subplots(figsize=(12, 6.5), facecolor='#1a1a2e')
ax3.set_facecolor('#16213e')

for s in SCENARIOS:
    df = dfs[s]
    c = COLORS[s]
    label = SCENE_LABELS[s]
    # 跳过 age=26 (years=0) 的数据
    mask = df['years'] > 0
    ax3.plot(df.loc[mask, 'age'], df.loc[mask, 'hit_10m_pct'],
             color=c, linewidth=2.2, marker='o', markersize=3, label=label)

# 30%、50%、80%参考线
for pct, ls in [(30, ':'), (50, '--'), (80, '-.')]:
    ax3.axhline(y=pct, color='#888888', linestyle=ls, linewidth=0.8, alpha=0.4)
    ax3.text(26.5, pct+0.5, f'{pct}%', color='#888888', fontsize=8, alpha=0.5)

ax3.set_xlabel('年龄', fontsize=13, color='#cccccc')
ax3.set_ylabel('1000万达成概率 (%)', fontsize=13, color='#cccccc')
ax3.set_title('蒙特卡洛模拟：1000万达成概率随年龄演进', fontsize=15, color='#ffffff', fontweight='bold', pad=15)
ax3.legend(fontsize=11, facecolor='#1a1a2e', edgecolor='#444444', labelcolor='#cccccc')
ax3.set_xlim(26, 60)
ax3.set_ylim(0, 100)
ax3.grid(True, alpha=0.2, linestyle=':')
ax3.tick_params(colors='#aaaaaa')
ax3.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))

fig3.tight_layout()
fig3.savefig(OUT / '03_千万达成概率年龄演进.png', dpi=200, bbox_inches='tight', facecolor=fig3.get_facecolor())
plt.close(fig3)
print(f"  ✔ 03_千万达成概率年龄演进.png")

print(f"\n✅ 所有图表已生成至: {OUT}")
