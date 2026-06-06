#!/usr/bin/env python3
"""
China永久组合回测 — 指定指数版本
Usage: python3 china_backtest.py <index_code>
例: python3 china_backtest.py 000016.SH  # 上证50
输出: result_china_<index_code>.csv
"""
import sys, os, time, logging
from datetime import datetime
import numpy as np
import pandas as pd
import pymysql

DB = {'host':'127.0.0.1','user':'finance_user','password':'Finance2026!','database':'china_finance_db','charset':'utf8mb4'}
BASE = os.path.dirname(os.path.abspath(__file__))
DP = os.path.join(BASE, 'data', 'processed')
DR = os.path.join(BASE, 'data', 'raw')
RES = os.path.join(BASE, 'results')
LG = os.path.join(BASE, 'logs')
os.makedirs(LG, exist_ok=True)

code = sys.argv[1]
log_f = os.path.join(LG, f'china_{code.replace(".","_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                    handlers=[logging.FileHandler(log_f, encoding='utf-8'), logging.StreamHandler()])
log = logging.getLogger(__name__)

def fetch(q):
    with pymysql.connect(**DB) as c:
        return pd.read_sql(q, c)

log.info(f"开始回测: {code}")

# 加载AU.SHF金价
au = fetch("SELECT 交易日期, 收盘价 FROM commodity_daily WHERE 商品代码='AU.SHF' ORDER BY 交易日期")
au.columns = ['date','au_price']
au['date'] = pd.to_datetime(au['date']).dt.date

# 加载指数
idx = fetch(f"SELECT 交易日期, 收盘价 FROM daily_quote WHERE 证券代码='{code}' ORDER BY 交易日期")
idx.columns = ['date','stock_price']
idx['date'] = pd.to_datetime(idx['date']).dt.date

# 合并对齐
m = pd.merge(idx, au, on='date', how='inner').sort_values('date')
m = m.ffill(limit=3).dropna()

# 添加固定值
m['bond'] = 1.0  # 基准为1，在回测中用年化3%计算
m['cash'] = 1.0

log.info(f"  数据: {len(m)} 行, {m['date'].iloc[0]} ~ {m['date'].iloc[-1]}")
log.info(f"  股票起始价格: {m['stock_price'].iloc[0]:.2f}, 黄金起始价: {m['au_price'].iloc[0]:.2f}")

prices = m[['stock_price','au_price','bond','cash']].copy()
prices.index = pd.to_datetime(m['date'])

def be(entry_idx, px, ic=1000000, cr=0.02, br=0.03, tc=0.001, th=0.08):
    n = px.shape[1]
    names = px.columns.tolist()
    w = np.ones(n)/n
    pv = float(ic)
    nav = []
    last_ry = None
    for i in range(entry_idx, len(px)-1):
        today = px.index[i]
        dr = np.zeros(n)
        for j, nm in enumerate(names):
            if nm=='cash': dr[j]=cr/252
            elif nm=='bond' and br is not None: dr[j]=br/252
            else:
                pt=px.iloc[i][nm]; pt2=px.iloc[i+1][nm]
                dr[j]=pt2/pt-1 if pt>0 and pt2>0 else 0
        pv*=(1+np.sum(w*dr))
        nw=w*(1+dr); ws=np.sum(nw)
        if ws>0: w=nw/ws
        nav.append((today,pv))
        need=False
        if np.any(np.abs(w-0.25)>th): need=True
        if today.month==1 and today.day<=3 and last_ry!=today.year: need=True
        if need:
            w=np.ones(n)/n; pv*=(1-tc); last_ry=today.year
    fv=pv; hy=(nav[-1][0]-nav[0][0]).days/365.0
    tr=(fv/ic-1)*100; ar=((fv/ic)**(1/hy)-1)*100 if hy>0 else 0
    nvs=[v for _,v in nav]; peak=nvs[0]; mdd=0
    for v in nvs:
        if v>peak: peak=v
        dd=(peak-v)/peak*100
        if dd>mdd: mdd=dd
    drs=[nav[i+1][1]/nav[i][1]-1 for i in range(len(nav)-1)]
    if len(drs)>1:
        av=np.std(drs)*np.sqrt(252)*100
        sr=float(np.mean(np.array(drs)-0.025/252)/np.std(drs)*np.sqrt(252)) if np.std(drs)>0 else 0
    else: av,sr=0,0
    ss=px.iloc[entry_idx]['stock_price']; se=px.iloc[-1]['stock_price']
    bmr=(se/ss-1)*100 if ss>0 else 0
    return {'entry_date':px.index[entry_idx],'final_value':round(fv,2),
            'total_return_pct':round(tr,4),'annual_return_pct':round(ar,4),
            'max_drawdown_pct':round(mdd,4),'sharpe_ratio':round(sr,4),
            'annual_volatility_pct':round(av,4),'benchmark_return_pct':round(bmr,4),
            'outperform_benchmark':'Yes' if tr>bmr else 'No',
            'holding_years':round(hy,2)}

max_e = len(prices)-252
if max_e<=0: max_e=len(prices)-1
log.info(f"  入场点: {max_e}")

results = []; st=time.time()
intv=max(1,max_e//20)
for idx in range(max_e):
    r = be(idx, prices, ic=1000000, cr=0.02, br=0.03)
    results.append(r)
    if (idx+1)%intv==0 or idx==max_e-1:
        el=time.time()-st; pct=(idx+1)/max_e*100
        rate=(idx+1)/el if el>0 else 0; rem=(max_e-idx-1)/rate if rate>0 else 0
        log.info(f"  {code}: {idx+1}/{max_e} ({pct:.1f}%) | {el:.0f}s | {rate:.0f}p/s | ~{rem:.0f}s")

df=pd.DataFrame(results)
out=os.path.join(RES, f'result_china_{code.replace(".","_")}.csv')
df.to_csv(out, index=False)
el=time.time()-st
log.info(f"\n✅ {code} 完成! {el:.0f}s ({el/60:.1f}min)")
log.info(f"  均值: {(df['total_return_pct'].mean()):.2f}% | 中位数: {(df['total_return_pct'].median()):.2f}%")
log.info(f"  年化: {(df['annual_return_pct'].mean()):.2f}% | 回撤: {(df['max_drawdown_pct'].mean()):.2f}%")
log.info(f"  夏普: {(df['sharpe_ratio'].mean()):.4f} | 跑赢: {(df['outperform_benchmark']=='Yes').mean()*100:.1f}%")
log.info(f"  输出: {out}")
