#!/usr/bin/env python3
"""
蒙特卡洛模拟核心：永久组合变体 × 34年 DCA
用法：python3 mc_core.py <保守|中位|乐观> [--outdir DIR] [--n_sim N]

场景说明（直接设定合理长期年化预期，而非σ倍数调整）：
  保守: 各资产年化约偏低（5%组合级）
  中位: 合理预期（6.5%组合级）← 用户讨论时的合理期望
  乐观: 偏乐观（8%组合级）

输出：
  results_<场景>.csv  — 每个年龄的资产分位数
  paths_<场景>.npy    — 采样路径
"""
import os, sys, time, json, argparse
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
N_SIM = 100000
N_YEARS = 34
N_MONTHS = N_YEARS * 12
START_AGE = 26
BATCH_SIZE = 20000

# 5资产 + 现金（单独处理）
WEIGHTS = np.array([0.30, 0.30, 0.20, 0.12, 0.05], dtype=np.float64)
CASH_WEIGHT = 0.03

# ── 三场景的资产年化收益率（合理长期预期）──
SCENARIO_PARAMS = {
    '保守': {
        '年化_红利低波': 0.05,   # 5%
        '年化_美股标普': 0.06,   # 6%
        '年化_资源能源': 0.04,   # 4%
        '年化_沪金':    0.04,   # 4%
        '年化_债券TLT': 0.03,   # 3%
        '年化_现金':    0.02,   # 2%
        '描述': '5%组合级 — 利率低迷+美股估值回归+增长放缓',
    },
    '中位': {
        '年化_红利低波': 0.07,   # 7%
        '年化_美股标普': 0.08,   # 8%
        '年化_资源能源': 0.06,   # 6%
        '年化_沪金':    0.05,   # 5%
        '年化_债券TLT': 0.03,   # 3%
        '年化_现金':    0.02,   # 2%
        '描述': '6.5%组合级 — 合理长期预期',
    },
    '乐观': {
        '年化_红利低波': 0.09,   # 9%
        '年化_美股标普': 0.10,   # 10%
        '年化_资源能源': 0.08,   # 8%
        '年化_沪金':    0.06,   # 6%
        '年化_债券TLT': 0.03,   # 3%
        '年化_现金':    0.02,   # 2%
        '描述': '8%组合级 — 经济持续增长+资产溢价维持',
    },
}

ASSET_NAMES = ['红利低波', '美股标普', '资源能源', '沪金', '债券TLT']


def dca_amount(month_idx):
    yr = month_idx // 12
    if yr == 0:   return 2000.0
    elif yr == 1: return 2500.0
    elif yr == 2: return 3000.0
    elif yr == 3: return 3500.0
    else:         return 4000.0


def load_cov_structure():
    """从历史数据加载原始协方差矩阵（用于相对结构），然后缩放到合理波动率"""
    with open('/tmp/mc_params.json', 'r') as f:
        p = json.load(f)
    # 相关性矩阵——更稳定，不受绝对尺度影响
    corr = np.array(p['corr'])
    # 历史标准差
    hist_stds = np.sqrt(np.diag(np.array(p['cov'])))
    return corr, hist_stds


def build_scenario_params(scenario_name):
    """根据场景名称构建月收益均值和月协方差矩阵"""
    sp = SCENARIO_PARAMS[scenario_name]
    corr, hist_stds = load_cov_structure()

    # 月收益均值
    monthly_means = []
    for name in ASSET_NAMES:
        annual_r = sp[f'年化_{name}']
        monthly = (1 + annual_r) ** (1/12) - 1
        monthly_means.append(monthly)
    monthly_means = np.array(monthly_means)

    # 风险缩放：用历史的相对波动率比例，但缩放到合理水平
    # 使用历史波动率比值（假设相对风险关系不变）
    # 但用中位场景的年化波动率作为基准
    target_annual_vol = 0.12  # 组合年化波动约12%
    asset_vol_scales = hist_stds / hist_stds.mean()
    monthly_stds = (target_annual_vol / np.sqrt(12)) * asset_vol_scales

    # 用相关性+标准差构建协方差
    cov = np.outer(monthly_stds, monthly_stds) * corr

    return monthly_means, cov, monthly_stds


def run_simulation(means, cov, n_sim):
    """分批运行蒙特卡洛模拟"""
    cash_monthly = (1 + SCENARIO_PARAMS['中位']['年化_现金']) ** (1/12) - 1

    chunk_size = BATCH_SIZE
    n_chunks = (n_sim + chunk_size - 1) // chunk_size

    nav_history = np.zeros((n_sim, N_MONTHS), dtype=np.float64)
    total_in_history = np.zeros((n_sim, N_MONTHS), dtype=np.float64)

    start = 0
    for ch in range(n_chunks):
        end = min(start + chunk_size, n_sim)
        batch_n = end - start
        print(f"    批次 {ch+1}/{n_chunks}: {batch_n} 条路径")

        rng = np.random.default_rng(SEED + ch * 9999)
        rets_batch = rng.multivariate_normal(means, cov, (batch_n, N_MONTHS))

        nav = np.zeros(batch_n, dtype=np.float64)
        total_in = np.zeros(batch_n, dtype=np.float64)

        for m in range(N_MONTHS):
            amt = dca_amount(m)
            nav += amt
            total_in += amt
            ret_5 = rets_batch[:, m, :]
            port_ret = np.dot(WEIGHTS, ret_5.T) + CASH_WEIGHT * cash_monthly
            nav *= (1 + port_ret)
            nav_history[start:end, m] = nav
            total_in_history[start:end, m] = total_in

        start = end

    return nav_history, total_in_history


def calc_quantiles(nav_history, total_in_history):
    ages = np.arange(START_AGE, START_AGE + N_YEARS + 1)
    yearly_indices = np.arange(11, N_MONTHS, 12)

    if len(yearly_indices) < N_YEARS:
        yearly_indices = np.arange(N_MONTHS - N_YEARS, N_MONTHS)

    rows = []
    for i, age in enumerate(ages):
        if i == 0:
            rows.append({'age': age, 'years': 0, 'p5': 0, 'p25': 0, 'p50': 0,
                         'p75': 0, 'p95': 0, 'total_in': 0, 'gain_p50': 0})
            continue
        mi = yearly_indices[i-1] if i-1 < len(yearly_indices) else N_MONTHS - 1
        navs = nav_history[:, mi]
        ti_vals = total_in_history[:, mi]

        p5 = float(np.percentile(navs, 5))
        p25 = float(np.percentile(navs, 25))
        p50 = float(np.percentile(navs, 50))
        p75 = float(np.percentile(navs, 75))
        p95 = float(np.percentile(navs, 95))
        ti = float(np.median(ti_vals))
        hit_10m = float((navs >= 10_000_000).mean())

        rows.append({
            'age': age, 'years': i,
            'p5': p5, 'p25': p25, 'p50': p50, 'p75': p75, 'p95': p95,
            'total_in': ti, 'gain_p50': p50 - ti,
            'hit_10m_pct': hit_10m * 100,
            'portfolio_ratio': p50 / ti if ti > 0 else 0,
        })
    return pd.DataFrame(rows)


def fmt(v):
    if abs(v) >= 1_0000_0000:  return f'{v/1_0000_0000:.1f}亿'
    elif abs(v) >= 10000:       return f'{v/10000:.0f}万'
    return f'{v:.0f}元'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('scenario', choices=['保守', '中位', '乐观'])
    parser.add_argument('--outdir', default=None)
    parser.add_argument('--n_sim', type=int, default=N_SIM)
    args = parser.parse_args()

    outdir = Path(args.outdir) if args.outdir else Path(__file__).resolve().parent
    outdir.mkdir(parents=True, exist_ok=True)

    sp = SCENARIO_PARAMS[args.scenario]
    print(f"\n{'='*60}")
    print(f"  场景: {args.scenario}")
    print(f"  描述: {sp['描述']}")
    print(f"  模拟: {args.n_sim:,} 次, {N_YEARS}年")
    print(f"{'='*60}")

    means, cov, stds = build_scenario_params(args.scenario)

    # 打印加权组合预期
    cash_monthly = (1 + sp['年化_现金']) ** (1/12) - 1
    weighted_mean = np.dot(WEIGHTS, means) + CASH_WEIGHT * cash_monthly
    weighted_std = np.sqrt(np.dot(WEIGHTS, np.dot(cov, WEIGHTS)))

    print(f"\n  各资产年化预期:")
    for i, name in enumerate(ASSET_NAMES):
        ann_r = (1+means[i])**12 - 1
        print(f"    {name}: {ann_r*100:.1f}%/年 (月σ={stds[i]*100:.2f}%)")

    print(f"\n  组合预期月收益: {weighted_mean*100:.2f}%")
    print(f"  组合预期月σ:    {weighted_std*100:.2f}%")
    print(f"  组合预期年化:   {((1+weighted_mean)**12-1)*100:.1f}%")

    t0 = time.time()
    print(f"\n  正在模拟...")
    nav_hist, total_in_hist = run_simulation(means, cov, args.n_sim)
    print(f"  完成! 耗时 {time.time()-t0:.1f}s")

    df = calc_quantiles(nav_hist, total_in_hist)

    csv_path = outdir / f'results_{args.scenario}.csv'
    df.to_csv(csv_path, index=False, float_format='%.2f')
    print(f"  分位数表 → {csv_path}")

    paths_path = outdir / f'paths_{args.scenario}.npy'
    np.save(str(paths_path), nav_hist[::100, :])
    print(f"  采样路径 → {paths_path}")

    # 输出关键数字
    print(f"\n{'='*60}")
    print(f"  【{args.scenario}场景】34年结果")
    print(f"{'='*60}")
    print(f"  {'年龄':>4s} │ {'投入':>8s} │ {'中位数':>10s} │ {'P25~P75':>18s} │ {'最差5%':>10s} │ {'千万达成':>9s}")
    print(f"  {'────':>4s}─┼─{'──────':>8s}─┼─{'──────────':>10s}─┼─{'──────────────────':>18s}─┼─{'──────────':>10s}─┼─{'────────':>9s}")

    for _, row in df.iterrows():
        if row['years'] == 0: continue
        if row['years'] in [5, 10, 15, 20, 25, 30, 34]:
            print(f"  {int(row['age']):>4d}岁 │ {fmt(row['total_in']):>8s} │ {fmt(row['p50']):>10s} │ {fmt(row['p25']):>8s}~{fmt(row['p75']):>8s} │ {fmt(row['p5']):>9s} │ {row['hit_10m_pct']:>6.1f}%")

    final = df.iloc[-1]
    print(f"\n  ╔═══ 60岁结果 ═══╗")
    print(f"  ║  累计投入:      {fmt(final['total_in']):>10s}")
    print(f"  ║  中位数资产:    {fmt(final['p50']):>10s}  (投入的{final['portfolio_ratio']:.1f}倍)")
    print(f"  ║  中位数收益:    +{fmt(final['gain_p50']):>10s}")
    print(f"  ║  最差5%资产:    {fmt(final['p5']):>10s}")
    print(f"  ║  P25~P75区间:   {fmt(final['p25']):>10s} ~ {fmt(final['p75']):>10s}")
    print(f"  ║  1000万达成率:   {final['hit_10m_pct']:.1f}%")
    print(f"  ╚════════════════════╝")


if __name__ == '__main__':
    main()
