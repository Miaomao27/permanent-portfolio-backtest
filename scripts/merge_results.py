#!/usr/bin/env python3
"""
Phase 3: 批次结果合并 + 汇总工具
=============================
合并四个版本的 grid_results.csv → 生成汇总表

用法:
  python merge_results.py
"""

import os
import sys
from pathlib import Path

import pandas as pd
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
RESULTS3_DIR = PROJECT_DIR / "results3"


def merge_all():
    """合并所有版本结果并生成汇总"""
    versions = ["hongli_lowvol", "sp500", "nasdaq", "nikkei225"]
    version_labels = {
        "hongli_lowvol": "红利低波",
        "sp500": "标普500",
        "nasdaq": "纳指100",
        "nikkei225": "日经225",
    }

    all_pareto = []
    summaries = []

    for ver in versions:
        grid_path = RESULTS3_DIR / ver / "grid_results.csv"
        rec_path = RESULTS3_DIR / ver / "top_recommendations.csv"

        if not grid_path.exists():
            print(f"[SKIP] {ver}: grid_results.csv 不存在")
            continue

        df = pd.read_csv(grid_path)
        print(f"[{ver}] {len(df)} 组权重")

        # 帕累托前沿
        df_sorted = df.sort_values("worst_maxdd")
        pareto = []
        max_cagr = -np.inf
        for _, row in df_sorted.iterrows():
            if row["mean_cagr"] > max_cagr:
                pareto.append(row.to_dict())
                max_cagr = row["mean_cagr"]
                pareto[-1]["version_label"] = version_labels.get(ver, ver)
        print(f"  帕累托前沿: {len(pareto)} 点")
        all_pareto.extend(pareto)

        # 推荐
        if rec_path.exists():
            rec_df = pd.read_csv(rec_path)
            for _, row in rec_df.iterrows():
                summaries.append({
                    "version": ver,
                    "version_label": version_labels.get(ver, ver),
                    "tier": row.get("tier", ""),
                    "w_stock": row["w_stock"],
                    "w_bond": row["w_bond"],
                    "w_gold": row["w_gold"],
                    "w_cash": row["w_cash"],
                    "mean_cagr": row["mean_cagr"],
                    "worst_maxdd": row["worst_maxdd"],
                    "mean_calmar": row.get("mean_calmar", np.nan),
                    "mean_sharpe": row.get("mean_sharpe", np.nan),
                    "worst_return": row.get("worst_return", np.nan),
                    "sort_criterion": row.get("sort_criterion", ""),
                })

    # 保存汇总
    # 帕累托前沿
    if all_pareto:
        pd.DataFrame(all_pareto).to_csv(RESULTS3_DIR / "pareto_frontiers.csv", index=False)
        print(f"\n帕累托前沿汇总: {RESULTS3_DIR / 'pareto_frontiers.csv'} ({len(all_pareto)} 点)")

    # 三档推荐汇总
    if summaries:
        pd.DataFrame(summaries).to_csv(RESULTS3_DIR / "optimal_summary.csv", index=False)
        print(f"三档推荐汇总: {RESULTS3_DIR / 'optimal_summary.csv'} ({len(summaries)} 行)")

        # 打印汇总表
        print("\n" + "=" * 80)
        print("四版本三档推荐配置汇总")
        print("=" * 80)
        print(f"{'版本':<10} {'档位':<8} {'股票':>6} {'债券':>6} {'黄金':>6} {'现金':>6} {'CAGR':>8} {'回撤':>8} {'Calmar':>8}")
        print("-" * 80)
        for s in summaries:
            print(f"{s['version_label']:<10} {s['tier']:<8} "
                  f"{s['w_stock']:>6.0%} {s['w_bond']:>6.0%} {s['w_gold']:>6.0%} {s['w_cash']:>6.0%} "
                  f"{s['mean_cagr']:>7.2%} {s['worst_maxdd']:>7.2%} {s['mean_calmar']:>7.2f}")

    print("\n完成 ✓")


if __name__ == "__main__":
    merge_all()
