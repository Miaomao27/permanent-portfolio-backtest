#!/usr/bin/env python3
"""
Phase 2: Holding Period Analysis for Permanent Portfolio
For each of 11 groups, calculate returns at 1/3/6/12/24 month holding periods
Usage: python3 backtest_holdings.py <group_key>
  group_key: sp500, nasdaq, china, china_000016_SH, ..., china_H30269_CSI
"""
import sys, os, time, logging
from datetime import datetime
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DP = os.path.join(BASE, 'data', 'processed')
RES2 = os.path.join(BASE, 'results2')
LG = os.path.join(BASE, 'logs')
os.makedirs(RES2, exist_ok=True)
os.makedirs(LG, exist_ok=True)

group = sys.argv[1] if len(sys.argv) > 1 else 'sp500'

log_f = os.path.join(LG, f'hp_{group}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                    handlers=[logging.FileHandler(log_f, encoding='utf-8'), logging.StreamHandler()])
log = logging.getLogger(__name__)

# ====== Mapping ======
DATA_FILES = {
    'sp500': ('us_sp500_daily.csv', 100000, 0.02, None, 'result_sp500'),
    'nasdaq': ('us_nasdaq_daily.csv', 100000, 0.02, None, 'result_nasdaq'),
    'china': ('cn_daily.csv', 1000000, 0.02, 0.03, 'result_china'),
    'china_000016_SH': ('cn_daily.csv', 1000000, 0.02, 0.03, 'result_china_000016_SH'),
    'china_000688_SH': ('cn_daily.csv', 1000000, 0.02, 0.03, 'result_china_000688_SH'),
    'china_000852_SH': ('cn_daily.csv', 1000000, 0.02, 0.03, 'result_china_000852_SH'),
    'china_000905_SH': ('cn_daily.csv', 1000000, 0.02, 0.03, 'result_china_000905_SH'),
    'china_000932_SH': ('cn_daily.csv', 1000000, 0.02, 0.03, 'result_china_000932_SH'),
    'china_399006_SZ': ('cn_daily.csv', 1000000, 0.02, 0.03, 'result_china_399006_SZ'),
    'china_000922_SH': ('cn_daily.csv', 1000000, 0.02, 0.03, 'result_china_000922_SH'),
    'china_H30269_CSI': ('cn_daily.csv', 1000000, 0.02, 0.03, 'result_china_H30269_CSI'),
}

# Special handling: for China groups, which use the same cn_daily.csv, we need to map stock column
# cn_daily.csv has 'stock', 'gold' columns — stock means CSI 300
# But for other indices, they have their own column names
# Actually, looking at the processed data:
# us_sp500_daily.csv has: stock, bond, gold, cash  
# us_nasdaq_daily.csv has: stock, bond, gold, cash
# cn_daily.csv has: stock, gold (stock=沪深300)

# For the China indices other than 沪深300, we need to load custom aligned data
# Let me check what data we have...

log.info(f"开始持有期回测: {group}")

# Try to load from the original backtest result to get the price data path
# Actually, the processed files only have:
# - us_sp500_daily.csv: stock(SP500), bond(TLT), gold, cash
# - us_nasdaq_daily.csv: stock(NDXT), bond(TLT), gold, cash  
# - cn_daily.csv: stock(沪深300), gold(AU.SHF), cash

# For other China indices, the aligned data was created dynamically in china_backtest.py
# and not saved to processed/. Let me check what's available.

# Check available files
files = os.listdir(DP)
log.info(f"可用processed文件: {files}")

# If this is a China index other than 沪深300, we need to align from MySQL
# But for now, let's use the same cn_daily.csv approach and note that
# only 沪深300, SP500, and NASDAQ have pre-aligned data

if group in ['sp500', 'nasdaq']:
    fn, ic, cr, br, _ = DATA_FILES[group]
    path = os.path.join(DP, fn)
    prices = pd.read_csv(path, index_col=0, parse_dates=True)
    prices['cash'] = 1.0
    log.info(f"加载 {fn}: {len(prices)}行, {prices.columns.tolist()}")
elif group == 'china':
    fn, ic, cr, br, _ = DATA_FILES[group]
    path = os.path.join(DP, fn)
    prices = pd.read_csv(path, index_col=0, parse_dates=True)
    prices['cash'] = 1.0
    log.info(f"加载 {fn}: {len(prices)}行, {prices.columns.tolist()}")
else:
    log.error(f"组 {group} 没有预对齐数据，请先运行 china_backtest.py 生成")
    sys.exit(1)

# ====== 持有期设置（交易日） ======
HOLDING_PERIODS = {
    '1m': 21,
    '3m': 63,
    '6m': 126,
    '12m': 252,
    '24m': 504,
}

def backtest_holdings(entry_idx, prices, ic=100000, cr=0.02, br=None, tc=0.001, th=0.08):
    """Run daily simulation and record NAV at each holding period milestone"""
    n = prices.shape[1]
    names = prices.columns.tolist()
    w = np.ones(n) / n
    pv = float(ic)
    nav = pv
    last_ry = None
    results = {}

    for i in range(entry_idx, len(prices) - 1):
        days_held = i - entry_idx + 1
        today = prices.index[i]

        # Daily return
        dr = np.zeros(n)
        for j, nm in enumerate(names):
            if nm == 'cash':
                dr[j] = cr / 252
            elif nm == 'bond' and br is not None:
                dr[j] = br / 252
            else:
                pt = prices.iloc[i][nm]
                pt2 = prices.iloc[i + 1][nm]
                dr[j] = pt2 / pt - 1 if pt > 0 and pt2 > 0 else 0.0

        nav *= (1 + np.sum(w * dr))
        nw = w * (1 + dr)
        ws = np.sum(nw)
        if ws > 0:
            w = nw / ws

        # Check rebalance
        need = False
        if np.any(np.abs(w - 0.25) > th):
            need = True
        if today.month == 1 and today.day <= 3 and last_ry != today.year:
            need = True
        if need:
            w = np.ones(n) / n
            nav *= (1 - tc)
            last_ry = today.year

        # Check if we hit any holding period milestone
        for hp_name, hp_days in HOLDING_PERIODS.items():
            if days_held == hp_days:
                total_ret = (nav / ic - 1) * 100
                ann_ret = ((nav / ic) ** (252 / hp_days) - 1) * 100 if hp_days > 0 else 0
                results[hp_name] = {
                    'entry_date': prices.index[entry_idx],
                    'end_date': prices.index[i + 1],
                    'holding_days': hp_days,
                    'final_value': round(nav, 2),
                    'total_return_pct': round(total_ret, 4),
                    'annualized_return_pct': round(ann_ret, 4),
                }

    return results


# ====== 运行 ======
max_entry = len(prices) - max(HOLDING_PERIODS.values()) - 1
if max_entry <= 0:
    log.error(f"数据不足，最多 {len(prices)} 天，需要至少 {max(HOLDING_PERIODS.values())+1} 天")
    sys.exit(1)

log.info(f"交易日: {len(prices)}, 最大入场点: {max_entry}")

all_results = {k: [] for k in HOLDING_PERIODS}
st = time.time()
interval = max(1, max_entry // 20)

for idx in range(max_entry):
    res = backtest_holdings(idx, prices, ic=ic, cr=cr, br=br)
    for hp_name, data in res.items():
        all_results[hp_name].append(data)

    if (idx + 1) % interval == 0 or idx == max_entry - 1:
        el = time.time() - st
        pct = (idx + 1) / max_entry * 100
        rate = (idx + 1) / el if el > 0 else 0
        log.info(f"  {group}: {idx+1}/{max_entry} ({pct:.1f}%) | {el:.0f}s | {rate:.0f}p/s")

# ====== 汇总统计 ======
log.info(f"\n=== {group} 持有期分析结果 ===")
summary_rows = []
for hp_name in ['1m', '3m', '6m', '12m', '24m']:
    df = pd.DataFrame(all_results[hp_name])
    out_path = os.path.join(RES2, f'hp_{group}_{hp_name}.csv')
    df.to_csv(out_path, index=False)

    tr = df['total_return_pct']
    ar = df['annualized_return_pct']
    win_rate = (tr > 0).mean() * 100

    row = {
        'group': group,
        'holding_period': hp_name,
        'holding_days': HOLDING_PERIODS[hp_name],
        'entry_count': len(df),
        'avg_return_pct': round(tr.mean(), 2),
        'median_return_pct': round(tr.median(), 2),
        'best_return_pct': round(tr.max(), 2),
        'worst_return_pct': round(tr.min(), 2),
        'std_return_pct': round(tr.std(), 2),
        'win_rate_pct': round(win_rate, 1),
        'avg_annualized_pct': round(ar.mean(), 2),
        'median_annualized_pct': round(ar.median(), 2),
    }
    summary_rows.append(row)

    log.info(f"  {hp_name:4s} ({HOLDING_PERIODS[hp_name]:3d}天): "
             f"平均{tr.mean():.2f}% | 中位数{tr.median():.2f}% | "
             f"胜率{win_rate:.1f}% | 区间{tr.min():.2f}%~{tr.max():.2f}%")

df_summary = pd.DataFrame(summary_rows)
summary_path = os.path.join(RES2, f'hp_summary_{group}.csv')
df_summary.to_csv(summary_path, index=False)

el = time.time() - st
log.info(f"\n✅ {group} 完成! {el:.0f}s ({el/60:.1f}min)")
log.info(f"  汇总: {summary_path}")
