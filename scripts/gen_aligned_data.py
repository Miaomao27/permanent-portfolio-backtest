#!/usr/bin/env python3
"""生成所有中国指数对齐数据文件"""
import os, pandas as pd, pymysql

BASE = '/home/cpy/文档/金融数据库建立/永久投资组合研究'
DP = os.path.join(BASE, 'data', 'processed')
os.makedirs(DP, exist_ok=True)

DB = {'host':'127.0.0.1','user':'finance_user','password':'Finance2026!',
      'database':'china_finance_db','charset':'utf8mb4'}

def fetch(q):
    with pymysql.connect(**DB) as c:
        return pd.read_sql(q, c)

# 黄金数据
au = fetch("SELECT 交易日期 as date, 收盘价 as gold FROM commodity_daily WHERE 商品代码='AU.SHF' ORDER BY 交易日期")
au['date'] = pd.to_datetime(au['date']).dt.date

# 所有指数
indices = {
    '000016_SH': '上证50', '000688_SH': '科创50', '000852_SH': '中证1000',
    '000905_SH': '中证500', '000932_SH': '中证2000', '399006_SZ': '创业板指',
    '000922_SH': '中证红利', 'H30269_CSI': '红利低波',
}

# 已有的cn_daily.csv = 沪深300，直接复制
print("沪深300: 已存在 cn_daily.csv")

for code, name in indices.items():
    if code == 'H30269_CSI':
        idx = fetch(f"SELECT 交易日期 as date, 收盘价 as stock FROM commodity_daily WHERE 商品代码='H30269.CSI' ORDER BY 交易日期")
    else:
        idx = fetch(f"SELECT 交易日期 as date, 收盘价 as stock FROM daily_quote WHERE 证券代码='{code.replace('_','.')}' ORDER BY 交易日期")
    
    idx['date'] = pd.to_datetime(idx['date']).dt.date
    m = pd.merge(idx, au, on='date', how='inner').sort_values('date')
    m = m.ffill(limit=3).dropna()
    
    out = os.path.join(DP, f'cn_{code}.csv')
    m.to_csv(out, index=False)
    print(f"{name} ({code}): {len(m)}行, {m['date'].iloc[0]} ~ {m['date'].iloc[-1]}")

print("\n完成!")
