#!/usr/bin/env python3
"""
Run a single backtest group. Usage: python3 run_single.py <nasdaq|china>
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json, time, logging
from datetime import datetime, date
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PROC_DIR = os.path.join(BASE_DIR, 'data', 'processed')
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

group = sys.argv[1] if len(sys.argv) > 1 else 'nasdaq'

log_file = os.path.join(LOGS_DIR, f'backtest_{group}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                    handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def backtest_single_entry(entry_idx, prices, ic=100000, cash_r=0.02, bond_r=None, tc=0.001, th=0.08):
    n = prices.shape[1]
    names = prices.columns.tolist()
    w = np.ones(n)/n
    pv = float(ic)
    nav = []
    rebal_dates = []
    last_ry = None

    for i in range(entry_idx, len(prices)-1):
        today = prices.index[i]
        dr = np.zeros(n)
        for j, nm in enumerate(names):
            if nm == 'cash':
                dr[j] = cash_r/252
            elif nm == 'bond' and bond_r is not None:
                dr[j] = bond_r/252
            else:
                pt = prices.iloc[i][nm]
                pt2 = prices.iloc[i+1][nm]
                dr[j] = pt2/pt - 1 if pt>0 and pt2>0 else 0.0

        pv *= (1 + np.sum(w*dr))
        nw = w*(1+dr)
        ws = np.sum(nw)
        if ws > 0: w = nw/ws
        nav.append((today, pv))

        need = False
        if np.any(np.abs(w-0.25) > th): need = True
        if today.month==1 and today.day<=3 and last_ry!=today.year:
            need = True
        if need:
            w = np.ones(n)/n
            pv *= (1-tc)
            rebal_dates.append(today)
            last_ry = today.year

    fv = pv
    hy = (nav[-1][0]-nav[0][0]).days/365.0
    tr = (fv/ic-1)*100
    ar = ((fv/ic)**(1/hy)-1)*100 if hy>0 else 0

    nvs = [v for _,v in nav]
    peak = nvs[0]; mdd = 0
    for v in nvs:
        if v>peak: peak=v
        dd=(peak-v)/peak*100
        if dd>mdd: mdd=dd

    drs = [nav[i+1][1]/nav[i][1]-1 for i in range(len(nav)-1)]
    if len(drs)>1:
        av = np.std(drs)*np.sqrt(252)*100
        sr = float(np.mean(np.array(drs)-0.025/252)/np.std(drs)*np.sqrt(252)) if np.std(drs)>0 else 0
    else:
        av,sr=0,0

    sc = 'stock' if 'stock' in names else names[0]
    ss = prices.iloc[entry_idx][sc]
    se = prices.iloc[-1][sc]
    br = (se/ss-1)*100 if ss>0 else 0

    return {'entry_date':prices.index[entry_idx],'final_value':round(fv,2),
            'total_return_pct':round(tr,4),'annual_return_pct':round(ar,4),
            'max_drawdown_pct':round(mdd,4),'sharpe_ratio':round(sr,4),
            'annual_volatility_pct':round(av,4),'benchmark_return_pct':round(br,4),
            'outperform_benchmark':'Yes' if tr>br else 'No',
            'holding_years':round(hy,2),'rebalance_count':len(rebal_dates)}

def run():
    if group == 'nasdaq':
        fn = 'us_nasdaq_daily.csv'
        ic = 100000
        cash_r = 0.02
        bond_r = None
        out_fn = 'result_nasdaq.csv'
    else:
        fn = 'cn_daily.csv'
        ic = 1000000
        cash_r = 0.02
        bond_r = 0.03
        out_fn = 'result_china.csv'

    prices = pd.read_csv(os.path.join(DATA_PROC_DIR, fn), index_col=0, parse_dates=True)
    prices['cash'] = 1.0

    max_e = len(prices)-252
    if max_e <= 0: max_e = len(prices)-1

    logger.info(f"回测: {group} | 交易日: {len(prices)} | 入场点: {max_e}")
    logger.info(f"  数据: {prices.index[0]} ~ {prices.index[-1]}")
    logger.info(f"  初始资金: {ic}")

    results = []
    st = time.time()
    interval = max(1, max_e//20)

    for idx in range(max_e):
        r = backtest_single_entry(idx, prices, ic=ic, cash_r=cash_r, bond_r=bond_r)
        results.append(r)

        if (idx+1)%interval==0 or idx==max_e-1:
            el = time.time()-st
            pct = (idx+1)/max_e*100
            rate = (idx+1)/el if el>0 else 0
            rem = (max_e-idx-1)/rate if rate>0 else 0
            logger.info(f"  {group}: {idx+1}/{max_e} ({pct:.1f}%) | {el:.0f}s | {rate:.0f} 点/秒 | ~{rem:.0f}s")

    df = pd.DataFrame(results)
    out_path = os.path.join(RESULTS_DIR, out_fn)
    df.to_csv(out_path, index=False)

    el = time.time()-st
    avg_tr = df['total_return_pct'].mean()
    med_tr = df['total_return_pct'].median()
    avg_ar = df['annual_return_pct'].mean()
    avg_mdd = df['max_drawdown_pct'].mean()
    avg_sr = df['sharpe_ratio'].mean()
    out_pct = (df['outperform_benchmark']=='Yes').mean()*100

    logger.info(f"\n✅ {group} 完成! {el:.0f}s ({el/60:.1f}min)")
    logger.info(f"  平均累计收益: {avg_tr:.2f}% | 中位数: {med_tr:.2f}%")
    logger.info(f"  平均年化: {avg_ar:.2f}% | 平均回撤: {avg_mdd:.2f}%")
    logger.info(f"  平均夏普: {avg_sr:.4f} | 跑赢基准: {out_pct:.1f}%")
    logger.info(f"  输出: {out_path}")

if __name__ == '__main__':
    run()
