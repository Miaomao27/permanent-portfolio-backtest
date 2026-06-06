#!/usr/bin/env python3
"""
使用东方财富API获取中证红利指数数据
"""
import requests
import json
import csv
import os

# 东方财富API
# 中证红利指数代码: 000922 (上证)
# 东方财富指数代码: 1.000922

def fetch_eastmoney_data(symbol="1.000922", name="中证红利"):
    """从东方财富获取指数日线数据"""
    print(f"\n获取 {name} ({symbol}) 数据...")
    
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": symbol,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",  # 日线
        "fqt": "1",    # 前复权
        "end": "20500101",
        "lmt": "10000"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        data = response.json()
        
        if data.get("data") and data["data"].get("klines"):
            klines = data["data"]["klines"]
            print(f"  获取到 {len(klines)} 条数据")
            
            # 解析数据
            records = []
            for line in klines:
                parts = line.split(",")
                if len(parts) >= 7:
                    records.append({
                        "date": parts[0],
                        "open": float(parts[1]),
                        "close": float(parts[2]),
                        "high": float(parts[3]),
                        "low": float(parts[4]),
                        "volume": float(parts[5]),
                        "amount": float(parts[6])
                    })
            
            print(f"  时间范围: {records[0]['date']} ~ {records[-1]['date']}")
            return records
        else:
            print(f"  没有获取到数据")
            return None
            
    except Exception as e:
        print(f"  获取失败: {e}")
        return None

def save_to_mysql(records, db_code):
    """保存数据到MySQL"""
    import pymysql
    import pandas as pd
    
    DB_CONFIG = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'finance_user',
        'password': 'Finance2026!',
        'database': 'china_finance_db',
        'charset': 'utf8mb4',
    }
    
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    columns = ['证券代码', '交易日期', '开盘价', '最高价', '最低价', '收盘价',
               '前收盘', '涨跌额', '涨跌幅', '成交量', '成交额', '是否收盘', '交易状态']
    placeholders = ', '.join(['%s'] * len(columns))
    cols_str = ', '.join(columns)
    
    insert_sql = f"INSERT IGNORE INTO daily_quote ({cols_str}) VALUES ({placeholders})"
    
    batch_size = 1000
    total = len(records)
    inserted = 0
    
    for start in range(0, total, batch_size):
        batch = records[start:start + batch_size]
        rows = []
        for rec in batch:
            rows.append((
                db_code,
                rec['date'],
                rec['open'],
                rec['high'],
                rec['low'],
                rec['close'],
                None,  # 前收盘
                None,  # 涨跌额
                None,  # 涨跌幅
                rec['volume'],
                rec['amount'],
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

def save_to_csv(records, db_code):
    """保存到CSV"""
    csv_dir = '/home/cpy/文档/金融数据库建立/永久投资组合研究/data/raw/'
    os.makedirs(csv_dir, exist_ok=True)
    
    csv_file = os.path.join(csv_dir, f"{db_code.replace('.', '_')}.csv")
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'open', 'high', 'low', 'close', 'volume', 'amount'])
        writer.writeheader()
        writer.writerows(records)
    
    print(f"  CSV保存: {csv_file}")
    return csv_file

if __name__ == '__main__':
    # 获取中证红利指数数据
    records = fetch_eastmoney_data("1.000922", "中证红利")
    
    if records:
        # 保存到CSV
        save_to_csv(records, "000922.SH")
        
        # 保存到MySQL
        save_to_mysql(records, "000922.SH")
        
        print("\n中证红利指数数据获取完成！")
    else:
        print("\n获取数据失败！")
