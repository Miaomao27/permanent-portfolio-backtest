#!/usr/bin/env python3
"""
Phase 2: Holding Period Analysis — 11 groups
Reads from MySQL/data files, runs daily simulation for each entry point,
records portfolio value at 1/3/6/12/24 month milestones.

Usage: python3 backtest_holdings2.py <group_key>
  group_key: sp500, nasdaq, china, china_000016_SH, china_000688_SH,
             china_000852_SH, china_000905_SH, china_000932_SH,
             china_399006_SZ, china_000922_SH, china_H30269_CSI
"""
import sys, os, time, logging
from datetime import datetime, date
import numpy as np
import pandas as pd
import pymysql

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DP = os.path.join(BASE, 'data', 'processed')
RES2 = os.path.join(BASE, 'results2')
LG = os.path.join(BASE, 'logs')
os.makedirs(RES2, exist_ok=True)
os.makedirs(LG, exist_ok=True)

group = sys.argv[1] if len(sys.argv) > 1 else 'sp500'

log_f = os.path.join(LG, f'hp2_{group}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                    handlers=[logging.FileHandler(log_f, encoding='utf-8'), logging.StreamHandler()])
log = logging.getLogger(__name__)

DB = {'host': '127.0.0.1', 'user': 'finance_user', 'password': 'Finance2026!',
      'database': 'china_finance_db', 'charset': 'utf8mb4'}
END_DATE = date(2026, 6, 6)

HOLDING_DAYS = {'1m': 21, '3m': 63, '6m': 126, '12m': 252, '24m': 504}

# ====== Group configs ======
GROUP_CONFIG = {
    # (data_source, stock_code, initial_capital, cash_rate, bond_rate)
    # data_source: 'processed' = read from processed CSV, 'mysql' = read from MySQL
    'sp500': ('processed', 'us_sp500_daily.csv', 100000, 0.02, None,
              ['stock', 'bond', 'gold', 'cash']),
    'nasdaq': ('processed', 'us_nasdaq_daily.csv', 100000, 0.02, None,
               ['stock', 'bond', 'gold', 'cash']),
    'china': ('processed', 'cn_daily.csv', 1000000, 0.02, 0.03,
              ['stock', 'gold', 'cash']),
    'china_000016_SH': ('processed', 'cn_000016_SH.csv', 1000000, 0.02, 0.03,
                        ['stock', 'gold', 'cash']),
    'china_000688_SH': ('processed', 'cn_000688_SH.csv', 1000000, 0.02, 0.03,
                        ['stock', 'gold', 'cash']),
    'china_000852_SH': ('processed', 'cn_000852_SH.csv', 1000000, 0.02, 0.03,
                        ['stock', 'gold', 'cash']),
    'china_000905_SH': ('processed', 'cn_000905_SH.csv', 1000000, 0.02, 0.03,
                        ['stock', 'gold', 'cash']),
    'china_000932_SH': ('processed', 'cn_000932_SH.csv', 1000000, 0.02, 0.03,
                        ['stock', 'gold', 'cash']),
    'china_399006_SZ': ('processed', 'cn_399006_SZ.csv', 1000000, 0.02, 0.03,
                        ['stock', 'gold', 'cash']),
    'china_000922_SH': ('processed', 'cn_000922_SH.csv', 1000000, 0.02, 0.03,
                        ['stock', 'gold', 'cash']),
    'china_H30269_CSI': ('processed', 'cn_H30269_CSI.csv', 1000000, 0.02, 0.03,
                         ['stock', 'gold', 'cash']),
}

def load_prices(group_key):
    """Load and align price data for a group"""
    cfg = GROUP_CONFIG.get(group_key)
    if not cfg:
        log.error(f"未知组: {group_key}")
        sys.exit(1)

    src, fn, ic, cr, br, col_names = cfg

    if src == 'processed':
        path = os.path.join(DP, fn)
        prices = pd.read_csv(path, index_col=0, parse_dates=True)
        log.info(f"加载 {fn}: {len(prices)}行, 列={list(prices.columns)}")
    else:
        log.error(f"未知数据源: {src}")
        sys.exit(1)

    # Add cash column if not present
    if 'cash' not in prices.columns:
        prices['cash'] = 1.0

    # Add bond column if not present (China groups use fixed bond rate)
    # This ensures we have 4 assets for correct 25% weights
    if 'bond' not in prices.columns and br is not None:
        prices['bond'] = 1.0

    log.info(f"最终列: {list(prices.columns)}, 资产数: {prices.shape[1]}")
    log.info(f"数据范围: {prices.index[0]} ~ {prices.index[-1]}")
    return prices, ic, cr, br


def run_holdings(group_key):
    prices, ic, cr, br = load_prices(group_key)

    max_entry = len(prices) - max(HOLDING_DAYS.values()) - 1
    if max_entry <= 0:
        log.error(f"数据不足! {len(prices)}天, 需要>{max(HOLDING_DAYS.values())}天")
        return

    log.info(f"交易日: {len(prices)}, 入场点: {max_entry}")
    n = prices.shape[1]
    names = prices.columns.tolist()
    all_res = {k: [] for k in HOLDING_DAYS}
    st = time.time()
    intv = max(1, max_entry // 20)

    for idx in range(max_entry):
        w = np.ones(n) / n
        pv = float(ic)
        last_ry = None
        milestones = {}

        for i in range(idx, len(prices) - 1):
            days_h = i - idx + 1
            today = prices.index[i]

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

            pv *= (1 + np.sum(w * dr))
            nw = w * (1 + dr)
            ws = np.sum(nw)
            if ws > 0:
                w = nw / ws

            need = False
            if np.any(np.abs(w - 0.25) > 0.08):
                need = True
            if today.month == 1 and today.day <= 3 and last_ry != today.year:
                need = True
            if need:
                w = np.ones(n) / n
                pv *= (1 - 0.001)
                last_ry = today.year

            for hp_name, hp_d in HOLDING_DAYS.items():
                if days_h == hp_d:
                    tr = (pv / ic - 1) * 100
                    ar = ((pv / ic) ** (252 / hp_d) - 1) * 100 if hp_d > 0 else 0
                    milestones[hp_name] = {
                        'entry_date': prices.index[idx],
                        'end_date': prices.index[i + 1],
                        'holding_days': hp_d,
                        'total_return_pct': round(tr, 4),
                        'annualized_return_pct': round(ar, 4),
                    }

        for hp_name, data in milestones.items():
            all_res[hp_name].append(data)

        if (idx + 1) % intv == 0 or idx == max_entry - 1:
            el = time.time() - st
            pct = (idx + 1) / max_entry * 100
            rate = (idx + 1) / el if el > 0 else 0
            log.info(f"  {group_key}: {idx+1}/{max_entry} ({pct:.1f}%) | {el:.0f}s | {rate:.0f}p/s")

    # Save & summarize
    summary = []
    for hp_name in ['1m', '3m', '6m', '12m', '24m']:
        df = pd.DataFrame(all_res[hp_name])
        out = os.path.join(RES2, f'hp_{group_key}_{hp_name}.csv')
        df.to_csv(out, index=False)

        tr = df['total_return_pct']
        ar = df['annualized_return_pct']
        wr = (tr > 0).mean() * 100
        summary.append({
            'group': group_key, 'holding': hp_name, 'days': HOLDING_DAYS[hp_name],
            'entries': len(df), 'avg_ret': round(tr.mean(), 2),
            'med_ret': round(tr.median(), 2), 'best': round(tr.max(), 2),
            'worst': round(tr.min(), 2), 'std': round(tr.std(), 2),
            'win_rate': round(wr, 1), 'avg_ann': round(ar.mean(), 2),
        })
        log.info(f"  {hp_name:4s}({HOLDING_DAYS[hp_name]:3d}d): "
                 f"均{tr.mean():.2f}% 中{tr.median():.2f}% 胜{wr:.1f}% "
                 f"[{tr.min():.2f}%, {tr.max():.2f}%]")

    df_s = pd.DataFrame(summary)
    df_s.to_csv(os.path.join(RES2, f'hp_summary_{group_key}.csv'), index=False)

    el = time.time() - st
    log.info(f"\n✅ {group_key} 完成! {el:.0f}s ({el/60:.1f}min)")


if __name__ == '__main__':
    run_holdings(group)
