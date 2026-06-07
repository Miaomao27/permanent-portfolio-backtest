#!/usr/bin/env python3
"""
日经225永久组合回测
股票: 日经225指数 (^N225) | 债券: 固定1.5% (日债近似)
黄金: GOLD_USD (国际金价) | 现金: 年化0.5% (日本接近零利率)
本金: 1000万日元 (约10万美元级别，便于对比)
"""
import os, sys, time, logging
from datetime import datetime, date
import numpy as np
import pandas as pd
import pymysql

DB = {'host':'127.0.0.1','user':'finance_user','password':'Finance2026!','database':'china_finance_db','charset':'utf8mb4'}
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, 'data', 'raw')
PROC = os.path.join(BASE, 'data', 'processed')
RES = os.path.join(BASE, 'results')
LG = os.path.join(BASE, 'logs')
os.makedirs(LG, exist_ok=True)

log_f = os.path.join(LG, f'nikkei_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                    handlers=[logging.FileHandler(log_f, encoding='utf-8'), logging.StreamHandler()])
log = logging.getLogger(__name__)

END_DATE = date(2026, 6, 6)

def fetch(q):
    with pymysql.connect(**DB) as c:
        return pd.read_sql(q, c)

log.info("=== 加载数据 ===")

# 1. 日经225
nk = pd.read_csv(os.path.join(RAW, 'nikkei225.csv'), skiprows=2, parse_dates=[0])
nk.columns = ['date', 'close', 'high', 'low', 'open', 'volume']
nk['date'] = pd.to_datetime(nk['date']).dt.date
nk = nk[['date', 'close']].rename(columns={'close': 'stock_price'})
log.info(f"日经225: {len(nk)} 行, {min(nk['date'])} ~ {max(nk['date'])}")

# 2. GOLD_USD
gold = fetch("SELECT 交易日期, 收盘价 FROM commodity_daily WHERE 商品代码='GOLD_USD' ORDER BY 交易日期")
gold.columns = ['date', 'gold_price']
gold['date'] = pd.to_datetime(gold['date']).dt.date
log.info(f"GOLD_USD: {len(gold)} 行, {min(gold['date'])} ~ {max(gold['date'])}")

# 3. 合并对齐
m = pd.merge(nk, gold, on='date', how='inner').sort_values('date')

m = m.ffill(limit=3).dropna()
log.info(f"合并后: {len(m)} 行, {m['date'].iloc[0]} ~ {m['date'].iloc[-1]}")

# 4. 限定时间范围: 日经225数据很全，但GOLD_USD从约2003年开始
# 至少需要2003年以后的数据
m = m[m['date'] >= date(2003, 1, 1)]
log.info(f"限定2003年后: {len(m)} 行, {m['date'].iloc[0]} ~ {m['date'].iloc[-1]}")

# 5. 构建价格矩阵 (2个真实资产 + bond/cash固定)
prices = m[['stock_price', 'gold_price']].copy()
prices.index = pd.to_datetime(m['date'])
log.info(f"最终数据: {len(prices)} 交易日")

# ========== 回测引擎 (直接从backtest_full.py移植) ==========
def backtest_single_entry(entry_idx, px, initial_capital=10000000,
                           cash_rate=0.005, bond_rate=0.015, trade_cost=0.001,
                           rebalance_threshold=0.08, annual_rebalance=True):
    n_assets = 4  # stock, gold, bond, cash
    asset_names = ['stock', 'gold', 'bond', 'cash']

    weights = np.ones(n_assets) / n_assets
    portfolio_value = float(initial_capital)
    nav_history = []
    rebalance_dates = []
    last_rebalance_year = None
    total_days = len(px)

    for i in range(entry_idx, total_days - 1):
        today = px.index[i]
        stock_today = px.iloc[i]['stock_price']
        stock_next = px.iloc[i+1]['stock_price']
        gold_today = px.iloc[i]['gold_price']
        gold_next = px.iloc[i+1]['gold_price']

        # 各资产日收益率
        stock_ret = stock_next / stock_today - 1 if stock_today > 0 and stock_next > 0 else 0
        gold_ret = gold_next / gold_today - 1 if gold_today > 0 and gold_next > 0 else 0
        bond_ret = bond_rate / 252
        cash_ret = cash_rate / 252

        daily_rets = np.array([stock_ret, gold_ret, bond_ret, cash_ret])

        portfolio_value *= (1 + np.sum(weights * daily_rets))

        new_weights = weights * (1 + daily_rets)
        ws = np.sum(new_weights)
        if ws > 0:
            weights = new_weights / ws

        nav_history.append((today, portfolio_value))

        need_rebalance = False
        if np.any(np.abs(weights - 0.25) > rebalance_threshold):
            need_rebalance = True
        if annual_rebalance and today.month == 1 and today.day <= 3:
            if last_rebalance_year != today.year:
                need_rebalance = True

        if need_rebalance:
            weights = np.ones(n_assets) / n_assets
            portfolio_value *= (1 - trade_cost)
            rebalance_dates.append(today)
            last_rebalance_year = today.year

    # 计算指标
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
        excess = np.array(daily_returns) - (0.025 / 252)
        sharpe = float(np.mean(excess) / np.std(daily_returns) * np.sqrt(252)) if np.std(daily_returns) > 0 else 0
    else:
        annual_vol = 0
        sharpe = 0

    # 基准：纯持股
    stock_start = px.iloc[entry_idx]['stock_price']
    stock_end = px.iloc[-1]['stock_price']
    benchmark_return = (stock_end / stock_start - 1) * 100 if stock_start > 0 else 0

    return {
        'entry_date': px.index[entry_idx],
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
    }

def run_backtest(px, group_name, capital, cash_rate=0.005, bond_rate=0.015):
    log.info(f"\n{'='*60}")
    log.info(f"开始回测: {group_name}")
    log.info(f"  交易日数: {len(px)}, 入场点: {len(px) - 252}")
    log.info(f"  股票: 日经225 | 债券: 固定{bond_rate*100:.1f}% | 黄金: GOLD_USD | 现金: {cash_rate*100:.1f}%")
    log.info(f"{'='*60}")

    max_entry = len(px) - 252
    if max_entry <= 0:
        max_entry = len(px) - 1

    results = []
    start_time = time.time()
    prog = max(1, max_entry // 20)

    for idx in range(max_entry):
        r = backtest_single_entry(idx, px, initial_capital=capital, cash_rate=cash_rate, bond_rate=bond_rate)
        results.append(r)
        if (idx + 1) % prog == 0 or idx == max_entry - 1:
            elapsed = time.time() - start_time
            pct = (idx + 1) / max_entry * 100
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            rem = (max_entry - idx - 1) / rate if rate > 0 else 0
            log.info(f"  {idx+1}/{max_entry} ({pct:.1f}%) | 耗时{elapsed:.0f}s | 速率{rate:.0f}点/秒 | 预计剩余{rem:.0f}s")

    log.info(f"完成! 总耗时: {time.time()-start_time:.0f}s, {len(results)}个入场点")
    return pd.DataFrame(results)

# ========== 主流程 ==========
log.info("="*60)
log.info("日经225永久组合回测")
log.info(f"结束日期: {END_DATE}")
log.info("="*60)

# 用1000万日元 (便于阅读的数字，约10万美元)
df = run_backtest(prices, 'NIKKEI225', capital=10000000, cash_rate=0.005, bond_rate=0.015)

out = os.path.join(RES, 'result_nikkei225.csv')
df.to_csv(out, index=False)
log.info(f"结果已保存: {out}")

# 汇总统计
log.info("\n=== 汇总统计 ===")
print("\n" + "="*60)
print("📊 日经225永久组合 - 回测结果")
print("="*60)
print(f"  入场点:          {len(df)}")
print(f"  平均累计收益:    {df['total_return_pct'].mean():.2f}%")
print(f"  中位数累计收益:  {df['total_return_pct'].median():.2f}%")
print(f"  最好收益:        {df['total_return_pct'].max():.2f}% ({df.loc[df['total_return_pct'].idxmax(),'entry_date']})")
print(f"  最差收益:        {df['total_return_pct'].min():.2f}% ({df.loc[df['total_return_pct'].idxmin(),'entry_date']})")
print(f"  标准差:          {df['total_return_pct'].std():.2f}%")
print(f"  平均年化收益:    {df['annual_return_pct'].mean():.2f}%")
print(f"  中位数年化收益:  {df['annual_return_pct'].median():.2f}%")
print(f"  平均最大回撤:    {df['max_drawdown_pct'].mean():.2f}%")
print(f"  平均夏普比率:    {df['sharpe_ratio'].mean():.4f}")
print(f"  跑赢基准比例:    {(df['outperform_benchmark']=='Yes').mean()*100:.1f}%")
print(f"  平均持有年限:    {df['holding_years'].mean():.1f}年")
print(f"  数据范围: {prices.index[0].date()} ~ {prices.index[-1].date()}")
print("="*60)

log.info(f"\n✅ 完成! 日志: {log_f}")
