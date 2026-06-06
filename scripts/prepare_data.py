#!/usr/bin/env python3
"""
永久投资组合研究 — 数据清洗与对齐脚本
从MySQL读取各资产数据，对齐交易日，生成用于回测的日频数据文件
"""

import pandas as pd
import mysql.connector

DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'finance_user',
    'password': 'Finance2026!',
    'database': 'china_finance_db'
}

DATA_DIR = '/home/cpy/文档/金融数据库建立/永久投资组合研究/data'

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def load_us_index(conn, code):
    query = """
        SELECT trade_date, adj_close AS `close`
        FROM us_index_daily
        WHERE index_code = %s
        ORDER BY trade_date
    """
    return pd.read_sql(query, conn, params=(code,))

def load_us_etf(conn, code):
    query = """
        SELECT trade_date, adj_close AS `close`
        FROM us_etf_daily
        WHERE etf_code = %s
        ORDER BY trade_date
    """
    return pd.read_sql(query, conn, params=(code,))

def load_commodity(conn, code):
    """从 commodity_daily 加载商品数据（统一用已有表）"""
    query = """
        SELECT 交易日期 as trade_date, 收盘价 as `close`
        FROM commodity_daily
        WHERE 商品代码 = %s
        ORDER BY 交易日期
    """
    return pd.read_sql(query, conn, params=(code,))

def load_cn_hs300(conn):
    query = """
        SELECT 交易日期 as trade_date, 收盘价 as `close`
        FROM daily_quote
        WHERE 证券代码 = '000300.SH'
        ORDER BY 交易日期
    """
    return pd.read_sql(query, conn)

def load_cn_gold(conn):
    query = """
        SELECT 交易日期 as trade_date, 收盘价 as `close`
        FROM commodity_daily
        WHERE 商品代码 = 'AU.SHF'
        ORDER BY 交易日期
    """
    return pd.read_sql(query, conn)

def align_dates(df_list, labels):
    """对齐多个DataFrame的日期（取交易日交集）"""
    result = pd.DataFrame()
    for df, label in zip(df_list, labels):
        df = df.copy()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.set_index('trade_date')
        df = df[['close']].rename(columns={'close': label})
        if result.empty:
            result = df
        else:
            result = result.join(df, how='inner')
    result = result.sort_index()
    return result

def main():
    conn = get_connection()

    print("=" * 50)
    print("数据清洗与对齐")
    print("=" * 50)

    # 美股版（标普组）
    print("\n[1/3] 加载美股数据...")
    sp500 = load_us_index(conn, '^SP500TR')
    ndxt = load_us_index(conn, '^NDXT')
    tlt = load_us_etf(conn, 'TLT')
    gold_us = load_commodity(conn, 'GOLD_USD')

    us_sp500 = align_dates([sp500, tlt, gold_us], ['SP500TR', 'TLT', 'GOLD_USD'])
    print(f"  美股版(标普组): {len(us_sp500)} 条, {us_sp500.index[0].date()} ~ {us_sp500.index[-1].date()}")
    us_sp500.to_csv(f'{DATA_DIR}/processed/us_assets_sp500_daily.csv')
    print(f"  已保存")

    us_ndxt = align_dates([ndxt, tlt, gold_us], ['NDXT', 'TLT', 'GOLD_USD'])
    print(f"  美股版(纳指组): {len(us_ndxt)} 条, {us_ndxt.index[0].date()} ~ {us_ndxt.index[-1].date()}")
    us_ndxt.to_csv(f'{DATA_DIR}/processed/us_assets_nasdaq_daily.csv')
    print(f"  已保存")

    # 中国版
    print("\n[2/3] 加载中国数据...")
    hs300 = load_cn_hs300(conn)
    cn_gold = load_cn_gold(conn)

    cn = align_dates([hs300, cn_gold], ['HS300', 'AU_SHF'])
    print(f"  中国版: {len(cn)} 条, {cn.index[0].date()} ~ {cn.index[-1].date()}")
    cn.to_csv(f'{DATA_DIR}/processed/cn_assets_daily.csv')
    print(f"  已保存")

    # 汇总
    print("\n" + "=" * 50)
    print("数据汇总")
    print("=" * 50)
    print(f"""
┌─────────────────────┬──────────┬──────────────────────────┐
│ 数据集               │ 记录数    │ 时间范围                  │
├─────────────────────┼──────────┼──────────────────────────┤
│ 美股版(标普组)        │ {len(us_sp500):>7} │ {str(us_sp500.index[0].date())} ~ {str(us_sp500.index[-1].date())} │
│ 美股版(纳指组)        │ {len(us_ndxt):>7} │ {str(us_ndxt.index[0].date())} ~ {str(us_ndxt.index[-1].date())} │
│ 中国版               │ {len(cn):>7} │ {str(cn.index[0].date())} ~ {str(cn.index[-1].date())} │
└─────────────────────┴──────────┴──────────────────────────┘
    """)
    conn.close()
    print("数据准备完成！")

if __name__ == '__main__':
    main()
