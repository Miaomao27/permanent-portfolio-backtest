#!/usr/bin/env python3
"""
永久投资组合研究 — 数据入库脚本
将CSV原始数据导入MySQL对应表
"""

import pandas as pd
import mysql.connector
from datetime import datetime

DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'finance_user',
    'password': 'Finance2026!',
    'database': 'china_finance_db'
}

DATA_DIR = '/home/cpy/文档/金融数据库建立/永久投资组合研究/data/raw'

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def import_us_index(conn, csv_file, code, name):
    """导入美股指数数据到 us_index_daily"""
    df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
    cursor = conn.cursor()
    inserted = 0
    for date, row in df.iterrows():
        try:
            sql = """INSERT IGNORE INTO us_index_daily 
                     (index_code, index_name, trade_date, open, high, low, close, adj_close, volume)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (
                code, name, date.date(),
                float(row.get('Open', 0)), float(row.get('High', 0)),
                float(row.get('Low', 0)), float(row.get('Close', 0)),
                float(row.get('Adj Close', row.get('Close', 0))),
                int(row.get('Volume', 0)) if pd.notna(row.get('Volume')) else 0
            ))
            inserted += cursor.rowcount
        except Exception as e:
            print(f"  {date.date()}: {e}")
    conn.commit()
    cursor.close()
    return inserted

def import_us_etf(conn, csv_file, code, name):
    """导入美股ETF数据到 us_etf_daily"""
    df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
    cursor = conn.cursor()
    inserted = 0
    for date, row in df.iterrows():
        try:
            sql = """INSERT IGNORE INTO us_etf_daily 
                     (etf_code, etf_name, trade_date, open, high, low, close, adj_close, volume)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (
                code, name, date.date(),
                float(row.get('Open', 0)), float(row.get('High', 0)),
                float(row.get('Low', 0)), float(row.get('Close', 0)),
                float(row.get('Adj Close', row.get('Close', 0))),
                int(row.get('Volume', 0)) if pd.notna(row.get('Volume')) else 0
            ))
            inserted += cursor.rowcount
        except Exception as e:
            print(f"  {date.date()}: {e}")
    conn.commit()
    cursor.close()
    return inserted

def import_us_commodity(conn, csv_file, code, name):
    """导入国际商品数据到 us_commodity_daily"""
    df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
    cursor = conn.cursor()
    inserted = 0
    for date, row in df.iterrows():
        try:
            sql = """INSERT IGNORE INTO us_commodity_daily 
                     (commodity_code, commodity_name, trade_date, open, high, low, close, volume)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (
                code, name, date.date(),
                float(row.get('Open', 0)), float(row.get('High', 0)),
                float(row.get('Low', 0)), float(row.get('Close', 0)),
                int(row.get('Volume', 0)) if pd.notna(row.get('Volume')) else 0
            ))
            inserted += cursor.rowcount
        except Exception as e:
            print(f"  {date.date()}: {e}")
    conn.commit()
    cursor.close()
    return inserted

def import_cn_hs300(conn, csv_file):
    """导入沪深300数据到 daily_quote（复用已有表）"""
    df = pd.read_csv(csv_file, parse_dates=['date'])
    cursor = conn.cursor()
    inserted = 0
    for _, row in df.iterrows():
        try:
            sql = """INSERT IGNORE INTO daily_quote 
                     (ts_code, trade_date, open, high, low, close, vol, amount)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (
                '000300.SH', row['date'].date(),
                float(row['open']), float(row['high']),
                float(row['low']), float(row['close']),
                int(row['volume']) if pd.notna(row['volume']) else 0,
                0  # amount not available from akshare index daily
            ))
            inserted += cursor.rowcount
        except Exception as e:
            print(f"  {row['date']}: {e}")
    conn.commit()
    cursor.close()
    return inserted

def main():
    conn = get_connection()
    print("=" * 50)
    print("开始数据入库...")
    print("=" * 50)

    # 1. 标普500全收益 -> us_index_daily
    print("\n[1/5] 标普500全收益指数 ^SP500TR -> us_index_daily")
    n = import_us_index(conn, f'{DATA_DIR}/sp500_tr.csv', '^SP500TR', 'S&P 500 Total Return')
    print(f"  入库 {n} 条")

    # 2. 纳斯达克100全收益 -> us_index_daily
    print("\n[2/5] 纳斯达克100全收益 ^NDXT -> us_index_daily")
    n = import_us_index(conn, f'{DATA_DIR}/nasdaq100_tr.csv', '^NDXT', 'NASDAQ 100 Total Return')
    print(f"  入库 {n} 条")

    # 3. TLT ETF -> us_etf_daily
    print("\n[3/5] TLT ETF -> us_etf_daily")
    n = import_us_etf(conn, f'{DATA_DIR}/tlt.csv', 'TLT', 'iShares 20+ Year Treasury Bond ETF')
    print(f"  入库 {n} 条")

    # 4. 国际金价 -> us_commodity_daily
    print("\n[4/5] 国际金价 GC=F -> us_commodity_daily")
    n = import_us_commodity(conn, f'{DATA_DIR}/gold_usd.csv', 'GOLD_USD', 'International Gold Price (COMEX)')
    print(f"  入库 {n} 条")

    # 5. 沪深300 -> daily_quote
    print("\n[5/5] 沪深300指数 sh000300 -> daily_quote")
    n = import_cn_hs300(conn, f'{DATA_DIR}/hs300.csv')
    print(f"  入库 {n} 条")

    conn.close()
    print("\n" + "=" * 50)
    print("数据入库完成！")

if __name__ == '__main__':
    main()
