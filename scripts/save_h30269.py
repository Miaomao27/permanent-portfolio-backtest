#!/usr/bin/env python3
"""
处理红利低波指数数据，存入MySQL
"""
import json
import pymysql
import pandas as pd
import os

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'finance_user',
    'password': 'Finance2026!',
    'database': 'china_finance_db',
    'charset': 'utf8mb4',
}

CSV_DIR = '/home/cpy/文档/金融数据库建立/永久投资组合研究/data/raw/'
os.makedirs(CSV_DIR, exist_ok=True)

def connect_db():
    return pymysql.connect(**DB_CONFIG)

def save_to_mysql(df, db_code):
    """保存数据到MySQL"""
    conn = connect_db()
    cursor = conn.cursor()
    
    columns = ['证券代码', '交易日期', '开盘价', '最高价', '最低价', '收盘价',
               '前收盘', '涨跌额', '涨跌幅', '成交量', '成交额', '是否收盘', '交易状态']
    placeholders = ', '.join(['%s'] * len(columns))
    cols_str = ', '.join(columns)
    
    insert_sql = f"INSERT IGNORE INTO daily_quote ({cols_str}) VALUES ({placeholders})"
    
    batch_size = 1000
    total = len(df)
    inserted = 0
    
    for start in range(0, total, batch_size):
        batch = df.iloc[start:start + batch_size]
        rows = []
        for _, row in batch.iterrows():
            rows.append((
                db_code,
                row['trade_date'],
                float(row['open']) if pd.notna(row['open']) else None,
                float(row['high']) if pd.notna(row['high']) else None,
                float(row['low']) if pd.notna(row['low']) else None,
                float(row['close']) if pd.notna(row['close']) else None,
                float(row['pre_close']) if pd.notna(row['pre_close']) else None,
                float(row['change']) if pd.notna(row['change']) else None,
                float(row['pct_chg']) if pd.notna(row['pct_chg']) else None,
                float(row['vol']) if pd.notna(row['vol']) else 0,
                float(row['amount']) if pd.notna(row['amount']) else 0,
                1,
                '正常',
            ))
        
        try:
            cursor.executemany(insert_sql, rows)
            conn.commit()
            inserted += cursor.rowcount
        except Exception as e:
            conn.rollback()
            print(f"  ERROR: {e}")
    
    cursor.close()
    conn.close()
    print(f"  数据库写入: 插入{inserted}条, 共{total}条")
    return inserted

if __name__ == '__main__':
    file_path = '/tmp/hermes-results/call_7a9a6dd562924bf496da141f.txt'
    db_code = 'H30269.CSI'
    
    print(f"处理 {db_code} 数据...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = json.loads(content)
    result = data.get('result', '[]')
    
    if isinstance(result, str):
        records = json.loads(result)
    else:
        records = result
    
    print(f"  原始记录数: {len(records)}")
    
    if not records:
        print(f"  没有数据，跳过")
    else:
        df = pd.DataFrame(records)
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        csv_file = os.path.join(CSV_DIR, f"{db_code.replace('.', '_')}.csv")
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"  CSV保存: {csv_file}")
        
        save_to_mysql(df, db_code)
    
    print("完成！")
