#!/usr/bin/env python3
"""
永久投资组合回测 — 延续脚本
只跑纳指组和中国组 + 生成汇总统计
"""

import os, sys, json, time, logging
from datetime import datetime, date
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PROC_DIR = os.path.join(BASE_DIR, 'data', 'processed')
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

os.makedirs(LOGS_DIR, exist_ok=True)

END_DATE = date(2026, 6, 6)

log_file = os.path.join(LOGS_DIR, f'backtest_cont_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def backtest_single_entry(entry_idx, prices, initial_capital=100000,
                           cash_rate=0.02, bond_rate=None, trade_cost=0.001,
                           rebalance_threshold=0.08):
    n_assets = prices.shape[1]
    asset_names = prices.columns.tolist()
    has_bond = 'bond' in asset_names

    weights = np.ones(n_assets) / n_assets
    portfolio_value = float(initial_capital)

    nav_history = []
    rebalance_dates = []
    last_rebalance_year = None
    total_days = len(prices)

    for i in range(entry_idx, total_days - 1):
        today = prices.index[i]

        daily_rets = np.zeros(n_assets)
        for j, name in enumerate(asset_names):
            if name == 'cash':
                daily_rets[j] = cash_rate / 252
            elif name == 'bond' and bond_rate is not None:
                daily_rets[j] = bond_rate / 252
            else:
                p_today = prices.iloc[i][name]
                p_tomorrow = prices.iloc[i+1][name]
                if p_today > 0 and p_tomorrow > 0:
                    daily_rets[j] = p_tomorrow / p_today - 1
                else:
                    daily_rets[j] = 0.0

        portfolio_return = np.sum(weights * daily_rets)
        portfolio_value *= (1 + portfolio_return)

        new_weights = weights * (1 + daily_rets)
        weight_sum = np.sum(new_weights)
        if weight_sum > 0:
            weights = new_weights / weight_sum

        nav_history.append((today, portfolio_value))

        need_rebalance = False
        if np.any(np.abs(weights - 0.25) > rebalance_threshold):
            need_rebalance = True
        if today.month == 1 and today.day <= 3:
            if last_rebalance_year != today.year:
                need_rebalance = True

        if need_rebalance:
            weights = np.ones(n_assets) / n_assets
            portfolio_value *= (1 - trade_cost)
            rebalance_dates.append(today)
            last_rebalance_year = today.year

    final_value = portfolio_value
    holding_years = (nav_history[-1][0] - nav_history[0][0]).days / 365.0
    total_return = (final_value / initial_capital - 1) * 100
    annual_return = ((final_value / initial_capital) ** (1 / holding_years) - 1) * 100 if holding_years > 0 else 0

    nav_values = [v for _, v in nav_history]
    peak = nav_values[0]
    max_drawdown = 0
    for v in nav_values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_drawdown:
            max_drawdown = dd

    daily_returns = []
    for i in range(len(nav_history) - 1):
        r = nav_history[i+1][1] / nav_history[i][1] - 1
        daily_returns.append(r)

    if len(daily_returns) > 1:
        annual_vol = np.std(daily_returns) * np.sqrt(252) * 100
        sharpe = float(np.mean(np.array(daily_returns) - (0.025/252)) / np.std(daily_returns) * np.sqrt(252)) if np.std(daily_returns) > 0 else 0
    else:
        annual_vol = 0
        sharpe = 0

    stock_col = 'stock' if 'stock' in asset_names else asset_names[0]
    stock_start = prices.iloc[entry_idx][stock_col]
    stock_end = prices.iloc[-1][stock_col]
    benchmark_return = (stock_end / stock_start - 1) * 100 if stock_start > 0 else 0

    return {
        'entry_date': prices.index[entry_idx],
        'final_value': round(final_value, 2),
        'total_return_pct': round(total_return, 4),
        'annual_return_pct': round(annual_return, 4),
        'max_drawdown_pct': round(max_drawdown, 4),
        'sharpe_ratio': round(sharpe, 4),
        'annual_volatility_pct': round(annual_vol, 4),
        'benchmark_return_pct': round(benchmark_return, 4),
        'outperform_benchmark': 'Yes' if total_return > benchmark_return else 'No',
        'holding_years': round(holding_years, 2),
        'rebalance_count': len(rebalance_dates),
        'entry_index': entry_idx,
    }

def run_backtest_group(prices, group_name, initial_capital, cash_rate=0.02,
                       bond_rate=None, trade_cost=0.001):
    logger.info(f"\n{'='*60}")
    logger.info(f"开始回测: {group_name}")
    logger.info(f"  交易日数: {len(prices)}")
    max_entry = len(prices) - 252
    if max_entry <= 0:
        max_entry = len(prices) - 1
    logger.info(f"  入场点总数: {max_entry}")
    logger.info(f"{'='*60}")

    results = []
    start_time = time.time()
    progress_interval = max(1, max_entry // 20)

    for idx in range(max_entry):
        result = backtest_single_entry(
            entry_idx=idx, prices=prices,
            initial_capital=initial_capital,
            cash_rate=cash_rate, bond_rate=bond_rate,
            trade_cost=trade_cost
        )
        results.append(result)

        if (idx + 1) % progress_interval == 0 or idx == max_entry - 1:
            elapsed = time.time() - start_time
            pct = (idx + 1) / max_entry * 100
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            remaining = (max_entry - idx - 1) / rate if rate > 0 else 0
            logger.info(f"  {group_name}: {idx+1}/{max_entry} ({pct:.1f}%) | "
                       f"耗时 {elapsed:.0f}s | 速率 {rate:.0f} 点/秒 | 预计剩余 {remaining:.0f}s")

    elapsed_total = time.time() - start_time
    logger.info(f"{group_name} 完成! 总耗时: {elapsed_total:.0f}s ({elapsed_total/60:.1f}min)")
    logger.info(f"  {len(results)} 个入场点")

    return pd.DataFrame(results)

def generate_summary(all_results, group_names):
    """生成汇总统计"""
    logger.info("\n" + "="*60)
    logger.info("生成汇总统计")
    logger.info("="*60)

    summary_rows = []
    for name in group_names:
        df = all_results[name]
        row = {
            'group': name,
            'entry_count': len(df),
            'avg_total_return': df['total_return_pct'].mean(),
            'median_total_return': df['total_return_pct'].median(),
            'best_total_return': df['total_return_pct'].max(),
            'worst_total_return': df['total_return_pct'].min(),
            'std_total_return': df['total_return_pct'].std(),
            'avg_annual_return': df['annual_return_pct'].mean(),
            'median_annual_return': df['annual_return_pct'].median(),
            'best_annual_return': df['annual_return_pct'].max(),
            'worst_annual_return': df['annual_return_pct'].min(),
            'avg_max_drawdown': df['max_drawdown_pct'].mean(),
            'median_max_drawdown': df['max_drawdown_pct'].median(),
            'avg_sharpe': df['sharpe_ratio'].mean(),
            'median_sharpe': df['sharpe_ratio'].median(),
            'avg_annual_vol': df['annual_volatility_pct'].mean(),
            'outperform_pct': (df['outperform_benchmark'] == 'Yes').mean() * 100,
            'avg_benchmark_return': df['benchmark_return_pct'].mean(),
            'avg_holding_years': df['holding_years'].mean(),
            'best_entry_date': str(df.loc[df['total_return_pct'].idxmax(), 'entry_date']),
            'worst_entry_date': str(df.loc[df['total_return_pct'].idxmin(), 'entry_date']),
        }
        summary_rows.append(row)

    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(os.path.join(RESULTS_DIR, 'summary_statistics.csv'), index=False)

    print("\n" + "="*70)
    print("📊 汇总统计")
    print("="*70)
    for _, row in df_summary.iterrows():
        print(f"\n{'='*50}")
        print(f"  {row['group'].upper()}")
        print(f"{'='*50}")
        print(f"  入场点:         {int(row['entry_count'])}")
        print(f"  平均累计收益:    {row['avg_total_return']:.2f}%")
        print(f"  中位数累计收益:  {row['median_total_return']:.2f}%")
        print(f"  最好收益:        {row['best_total_return']:.2f}% ({row['best_entry_date']})")
        print(f"  最差收益:        {row['worst_total_return']:.2f}% ({row['worst_entry_date']})")
        print(f"  标准差:          {row['std_total_return']:.2f}%")
        print(f"  平均年化收益:    {row['avg_annual_return']:.2f}%")
        print(f"  平均最大回撤:    {row['avg_max_drawdown']:.2f}%")
        print(f"  平均夏普比率:    {row['avg_sharpe']:.4f}")
        print(f"  跑赢基准比例:    {row['outperform_pct']:.1f}%")
        print(f"  平均持有年限:    {row['avg_holding_years']:.1f}年")

    return df_summary

def main():
    logger.info("=" * 60)
    logger.info("永久投资组合回测 - 延续脚本")
    logger.info(f"结束日期: {END_DATE}")
    logger.info("=" * 60)

    # 加载已对齐的processed数据
    logger.info("加载已对齐数据...")
    us_nasdaq = pd.read_csv(os.path.join(DATA_PROC_DIR, 'us_nasdaq_daily.csv'), index_col=0, parse_dates=True)
    cn = pd.read_csv(os.path.join(DATA_PROC_DIR, 'cn_daily.csv'), index_col=0, parse_dates=True)

    # 添加现金列
    us_nasdaq['cash'] = 1.0
    cn['cash'] = 1.0

    logger.info(f"  纳指组: {len(us_nasdaq)} 行, {us_nasdaq.index[0]} ~ {us_nasdaq.index[-1]}")
    logger.info(f"  中国组: {len(cn)} 行, {cn.index[0]} ~ {cn.index[-1]}")

    # 运行纳指组
    df_nasdaq = run_backtest_group(us_nasdaq, 'NASDAQ', 100000, cash_rate=0.02)
    df_nasdaq.to_csv(os.path.join(RESULTS_DIR, 'result_nasdaq.csv'), index=False)

    # 运行中国组
    df_cn = run_backtest_group(cn, 'CHINA', 1000000, cash_rate=0.02, bond_rate=0.03)
    df_cn.to_csv(os.path.join(RESULTS_DIR, 'result_china.csv'), index=False)

    # 加载已有的标普组结果
    df_sp500 = pd.read_csv(os.path.join(RESULTS_DIR, 'result_sp500.csv'))

    # 生成汇总统计
    all_results = {
        'sp500': df_sp500,
        'nasdaq': df_nasdaq,
        'china': df_cn,
    }
    df_summary = generate_summary(all_results, ['sp500', 'nasdaq', 'china'])

    logger.info(f"\n✅ 全部完成! 日志: {log_file}")

if __name__ == '__main__':
    main()
