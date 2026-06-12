#!/usr/bin/env python3
"""
蒙特卡洛模拟：新配比 — 标普25%+红利低波25%+黄金25%+债券15%(2%)+现金10%(1%)
用法：python3 mc_new.py <保守|中位|乐观> [--n_sim N] [--outdir DIR]
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

# ── 新配比 ──
# 3个风险资产（从原协方差矩阵取子集）
ASSETS = ['红利低波', '美股标普', '沪金']
WEIGHTS = np.array([0.25, 0.25, 0.25], dtype=np.float64)  # 75%
# 固定收益
BOND_WEIGHT = 0.15   # 债券15%
BOND_ANNUAL = 0.02   # 年化2%
CASH_WEIGHT = 0.10   # 现金10%
CASH_ANNUAL = 0.01   # 年化1%
FIXED_WEIGHT = BOND_WEIGHT + CASH_WEIGHT  # 25%

# ── 三场景的资产年化收益率 ──
SCENARIO_PARAMS = {
    '保守': {
        '年化_红利低波': 0.05,
        '年化_美股标普': 0.05,
        '年化_沪金': 0.04,
        '描述': '目标组合年化~4%',
    },
    '中位': {
        '年化_红利低波': 0.07,
        '年化_美股标普': 0.08,
        '年化_沪金': 0.05,
        '描述': '目标组合年化~5.5%',
    },
    '乐观': {
        '年化_红利低波': 0.09,
        '年化_美股标普': 0.10,
        '年化_沪金': 0.06,
        '描述': '目标组合年化~7%',
    },
}

def dca_amount(month_idx):
    yr = month_idx // 12
    if yr == 0:   return 2000.0
    elif yr == 1: return 2500.0
    elif yr == 2: return 3000.0
    elif yr == 3: return 3500.0
    else:         return 4000.0

def load_3asset_params():
    """从原始参数中提取3资产（红利低波, 标普, 黄金）的子协方差矩阵"""
    with open('/tmp/mc_params.json', 'r') as f:
        p = json.load(f)
    assets = p['assets']
    orig_idx = [assets.index(a) for a in ASSETS]
    # 提取3x3子协方差矩阵
    orig_cov = np.array(p['cov'])
    sub_cov = orig_cov[np.ix_(orig_idx, orig_idx)]
    # 相关性
    orig_corr = np.array(p['corr'])
    sub_corr = orig_corr[np.ix_(orig_idx, orig_idx)]
    # 历史月标准差
    hist_stds = np.sqrt(np.diag(sub_cov))
    return sub_cov, sub_corr, hist_stds

def build_scenario_params(scenario_name):
    """构建场景参数（3资产+固定收益）"""
    sp = SCENARIO_PARAMS[scenario_name]
    sub_cov, sub_corr, hist_stds = load_3asset_params()

    # 月收益均值
    monthly_means = []
    for name in ASSETS:
        annual_r = sp[f'年化_{name}']
        monthly_means.append((1 + annual_r) ** (1/12) - 1)
    monthly_means = np.array(monthly_means)

    # 波动率：用历史的相对比例，缩放到组合级~12%年化
    target_annual_vol = 0.12
    asset_vol_scales = hist_stds / hist_stds.mean()
    monthly_stds = (target_annual_vol / np.sqrt(12)) * asset_vol_scales
    cov = np.outer(monthly_stds, monthly_stds) * sub_corr

    return monthly_means, cov, monthly_stds

def run_simulation(means, cov, n_sim):
    """分批运行模拟"""
    bond_monthly = (1 + BOND_ANNUAL) ** (1/12) - 1
    cash_monthly = (1 + CASH_ANNUAL) ** (1/12) - 1

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
            ret_3 = rets_batch[:, m, :]
            # 组合月收益 = 3风险资产加权 + 债券 + 现金
            port_ret = np.dot(WEIGHTS, ret_3.T) + BOND_WEIGHT * bond_monthly + CASH_WEIGHT * cash_monthly
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
    print(f"  新配比: 红利低波25% + 标普25% + 黄金25% + 债券15%(2%) + 现金10%(1%)")
    print(f"  场景: {args.scenario} — {sp['描述']}")
    print(f"  模拟: {args.n_sim:,} 次, {N_YEARS}年")
    print(f"{'='*60}")

    means, cov, stds = build_scenario_params(args.scenario)

    bond_m = (1+BOND_ANNUAL)**(1/12)-1
    cash_m = (1+CASH_ANNUAL)**(1/12)-1
    weighted_mean = np.dot(WEIGHTS, means) + BOND_WEIGHT*bond_m + CASH_WEIGHT*cash_m
    weighted_std = np.sqrt(np.dot(WEIGHTS, np.dot(cov, WEIGHTS)))

    print(f"\n  各资产年化预期:")
    for i, name in enumerate(ASSETS):
        ann_r = (1+means[i])**12 - 1
        print(f"    {name} {WEIGHTS[i]*100:.0f}%: {ann_r*100:.1f}%/年 (月σ={stds[i]*100:.2f}%)")
    print(f"    债券 15%: 固定2%/年")
    print(f"    现金 10%: 固定1%/年")

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
