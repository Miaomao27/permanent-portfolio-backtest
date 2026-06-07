#!/usr/bin/env python3
"""
Phase 3: 图表生成工具
===================
生成四版卡尔玛热力图、帕累托前沿对比图等

用法:
  python gen_charts3.py
"""

import os
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import font_manager

# 中文字体
font_paths = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
]
cn_font = None
for fp in font_paths:
    if os.path.exists(fp):
        cn_font = font_manager.FontProperties(fname=fp)
        break
if cn_font is None:
    # Fallback: search
    for f in font_manager.fontManager.ttflist:
        if "Noto Sans CJK" in f.name and "Regular" in f.name:
            cn_font = font_manager.FontProperties(fname=f.fname)
            break

# Force CJK font globally
if cn_font:
    plt.rcParams["font.family"] = cn_font.get_name()
    # Also rebuild font cache with the font
    font_manager.fontManager.addfont(cn_font.get_file())
    plt.rcParams["font.sans-serif"] = [cn_font.get_name(), "DejaVu Sans"]

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
})

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
CHARTS3_DIR = PROJECT_DIR / "charts3"
RESULTS3_DIR = PROJECT_DIR / "results3"
CHARTS3_DIR.mkdir(parents=True, exist_ok=True)

VERSION_LABELS = {
    "hongli_lowvol": "红利低波",
    "sp500": "标普500",
    "nasdaq": "纳指100",
    "nikkei225": "日经225",
}


def gen_calmar_heatmap():
    """生成四版卡尔玛热力图 (2x2布局)"""
    versions = ["hongli_lowvol", "sp500", "nasdaq", "nikkei225"]
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    axes = axes.flatten()

    for idx, ver in enumerate(versions):
        ax = axes[idx]
        grid_path = RESULTS3_DIR / ver / "grid_results.csv"
        if not grid_path.exists():
            ax.text(0.5, 0.5, f"{VERSION_LABELS[ver]}\n数据缺失", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14)
            continue

        df = pd.read_csv(grid_path)
        # 创建透视表: 股票权重 × 债券权重, 值=Calmar
        pivot = df.pivot_table(
            values="mean_calmar",
            index="w_stock",
            columns="w_bond",
            aggfunc="mean",
        )

        im = ax.imshow(pivot.values, aspect="auto", origin="lower", cmap="RdYlGn")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([f"{x:.0%}" for x in pivot.columns], rotation=45, fontsize=8)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels([f"{x:.0%}" for x in pivot.index], fontsize=8)
        ax.set_xlabel("债券权重")
        ax.set_ylabel("股票权重")
        ax.set_title(f"{VERSION_LABELS[ver]} — Calmar热力图", fontproperties=cn_font)
        plt.colorbar(im, ax=ax, shrink=0.8, label="Calmar")

        # 标注最优
        best = df.loc[df["mean_calmar"].idxmax()]
        best_i = list(pivot.index).index(best["w_stock"])
        best_j = list(pivot.columns).index(best["w_bond"])
        ax.plot(best_j, best_i, "k*", markersize=15, markeredgecolor="white", markeredgewidth=1)
        ax.annotate(f"最优\nS={best['w_stock']:.0%}\nB={best['w_bond']:.0%}",
                    (best_j, best_i), xytext=(10, 10), textcoords="offset points",
                    fontsize=7, color="black",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    fig.suptitle("四版本卡尔玛比率热力图\n(横轴=债券权重, 纵轴=股票权重, 颜色=Calmar比率)",
                 fontproperties=cn_font, fontsize=15)
    plt.tight_layout()
    out_path = CHARTS3_DIR / "calmar_heatmap_4panel.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"卡尔玛热力图: {out_path}")


def gen_frontier_comparison():
    """生成四版本帕累托前沿对比图"""
    versions = ["hongli_lowvol", "sp500", "nasdaq", "nikkei225"]
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"]
    markers = ["o", "s", "D", "^"]

    fig, ax = plt.subplots(figsize=(12, 8))

    for ver, color, marker in zip(versions, colors, markers):
        pareto_path = RESULTS3_DIR / ver / "pareto_frontier.csv"
        grid_path = RESULTS3_DIR / ver / "grid_results.csv"

        if not grid_path.exists():
            continue

        df = pd.read_csv(grid_path)

        # 背景散点（所有组合）
        ax.scatter(df["worst_maxdd"] * 100, df["mean_cagr"] * 100,
                   alpha=0.15, s=15, c=color, edgecolors="none")

        # 帕累托前沿
        if pareto_path.exists():
            pareto = pd.read_csv(pareto_path)
            ax.plot(pareto["worst_maxdd"] * 100, pareto["mean_cagr"] * 100,
                    color=color, marker=marker, markersize=6, linewidth=2,
                    label=f"{VERSION_LABELS[ver]} 前沿", alpha=0.9)

        # 标注等权25%
        eq = df[(df["w_stock"] == 0.25) & (df["w_bond"] == 0.25) &
                (df["w_gold"] == 0.25) & (df["w_cash"] == 0.25)]
        if len(eq) > 0:
            eq = eq.iloc[0]
            ax.scatter([eq["worst_maxdd"] * 100], [eq["mean_cagr"] * 100],
                       s=120, c=color, marker="X", edgecolors="black", linewidth=1.5,
                       zorder=10)
            ax.annotate(f"25%等权", (eq["worst_maxdd"] * 100, eq["mean_cagr"] * 100),
                        textcoords="offset points", xytext=(5, 5), fontsize=8, color=color)

    ax.set_xlabel("最差回撤 (%)", fontproperties=cn_font)
    ax.set_ylabel("平均年化收益 (%)", fontproperties=cn_font)
    ax.set_title("四版本帕累托前沿对比\n(× = 25%等权, 线 = 帕累托前沿)",
                 fontproperties=cn_font, fontsize=14)
    ax.legend(loc="lower right", prop=cn_font)
    ax.grid(True, alpha=0.3)
    ax.invert_xaxis()  # 回撤越小越好 → 向左

    plt.tight_layout()
    out_path = CHARTS3_DIR / "frontier_all_versions.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"帕累托前沿对比: {out_path}")


def gen_optimal_bars():
    """生成三档推荐配置柱状图"""
    summary_path = RESULTS3_DIR / "optimal_summary.csv"
    if not summary_path.exists():
        print("[SKIP] optimal_summary.csv 不存在")
        return

    df = pd.read_csv(summary_path)
    versions = df["version"].unique()

    fig, axes = plt.subplots(1, len(versions), figsize=(5 * len(versions), 6), sharey=True)
    if len(versions) == 1:
        axes = [axes]

    for idx, ver in enumerate(versions):
        ax = axes[idx]
        ver_df = df[df["version"] == ver].copy()
        ver_df = ver_df.set_index("tier")

        tiers = ["稳健型", "均衡型", "进取型"]
        available_tiers = [t for t in tiers if t in ver_df.index]

        assets = ["股票", "债券", "黄金", "现金"]
        colors_list = ["#e74c3c", "#3498db", "#f39c12", "#2ecc71"]

        x = np.arange(len(available_tiers))
        width = 0.2

        for i, (asset, color) in enumerate(zip(assets, colors_list)):
            values = []
            for t in available_tiers:
                row = ver_df.loc[t]
                values.append(row[f"w_{['stock','bond','gold','cash'][i]}"] * 100)
            bars = ax.bar(x + i * width, values, width, label=asset, color=color, alpha=0.85)

        ax.set_xticks(x + width * 1.5)
        ax.set_xticklabels(available_tiers, fontproperties=cn_font)
        ax.set_ylabel("权重 (%)", fontproperties=cn_font)
        ax.set_title(f"{VERSION_LABELS.get(ver, ver)}", fontproperties=cn_font, fontsize=13)
        ax.set_ylim(0, 60)
        ax.grid(True, alpha=0.3, axis="y")

    axes[0].legend(loc="upper right", fontsize=9, prop=cn_font)
    fig.suptitle("四版本三档推荐配置", fontproperties=cn_font, fontsize=15)

    plt.tight_layout()
    out_path = CHARTS3_DIR / "optimal_allocation_bars.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"推荐配置柱状图: {out_path}")


def gen_weight_sensitivity():
    """股票权重敏感度分析"""
    versions = ["hongli_lowvol", "sp500", "nasdaq", "nikkei225"]
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    axes = axes.flatten()

    for idx, ver in enumerate(versions):
        ax = axes[idx]
        grid_path = RESULTS3_DIR / ver / "grid_results.csv"
        if not grid_path.exists():
            continue

        df = pd.read_csv(grid_path)

        # 按股票权重分组，取收益和回撤的中位数
        grouped = df.groupby("w_stock").agg(
            median_cagr=("mean_cagr", "median"),
            median_dd=("worst_maxdd", "median"),
        ).reset_index()

        color1 = "#2ecc71"
        color2 = "#e74c3c"

        ax1 = ax
        ax2 = ax.twinx()

        ax1.plot(grouped["w_stock"] * 100, grouped["median_cagr"] * 100,
                 "o-", color=color1, linewidth=2, markersize=6, label="年化收益")
        ax2.plot(grouped["w_stock"] * 100, grouped["median_dd"] * 100,
                 "s--", color=color2, linewidth=2, markersize=6, label="最大回撤")

        ax1.set_xlabel("股票权重 (%)")
        ax1.set_ylabel("年化收益 (%)", color=color1)
        ax2.set_ylabel("最大回撤 (%)", color=color2)
        ax1.tick_params(axis="y", labelcolor=color1)
        ax2.tick_params(axis="y", labelcolor=color2)

        ax.set_title(f"{VERSION_LABELS.get(ver, ver)}", fontproperties=cn_font)
        ax.grid(True, alpha=0.3)

    fig.suptitle("股票权重对收益/回撤的敏感性\n(实线=收益左轴, 虚线=回撤右轴)",
                 fontproperties=cn_font, fontsize=14)
    plt.tight_layout()
    out_path = CHARTS3_DIR / "sensitivity_stock_weight.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"敏感度分析: {out_path}")


def main():
    print("Phase 3 图表生成")
    print("=" * 60)

    try:
        gen_calmar_heatmap()
    except Exception as e:
        print(f"[ERROR] 热力图失败: {e}")

    try:
        gen_frontier_comparison()
    except Exception as e:
        print(f"[ERROR] 前沿图失败: {e}")

    try:
        gen_optimal_bars()
    except Exception as e:
        print(f"[ERROR] 柱状图失败: {e}")

    try:
        gen_weight_sensitivity()
    except Exception as e:
        print(f"[ERROR] 敏感度图失败: {e}")

    print("\n完成 ✓")


if __name__ == "__main__":
    main()
