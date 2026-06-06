#!/usr/bin/env python3
"""更新汇总统计 - 包含11组"""
import os, pandas as pd, numpy as np

BASE = '/home/cpy/文档/金融数据库建立/永久投资组合研究'
RES = os.path.join(BASE, 'results')

label_map = {
    'sp500': '标普500', 'nasdaq': '纳指100',
    'china': '沪深300', 'china_000016_SH': '上证50',
    'china_000688_SH': '科创50', 'china_000852_SH': '中证1000',
    'china_000905_SH': '中证500', 'china_000932_SH': '中证2000',
    'china_399006_SZ': '创业板指',
    'china_000922_SH': '中证红利', 'china_H30269_CSI': '红利低波',
}

files = [
    ('sp500', 'result_sp500.csv'), ('nasdaq', 'result_nasdaq.csv'),
    ('china', 'result_china.csv'),
    ('china_000016_SH', 'result_china_000016_SH.csv'),
    ('china_000688_SH', 'result_china_000688_SH.csv'),
    ('china_000852_SH', 'result_china_000852_SH.csv'),
    ('china_000905_SH', 'result_china_000905_SH.csv'),
    ('china_000932_SH', 'result_china_000932_SH.csv'),
    ('china_399006_SZ', 'result_china_399006_SZ.csv'),
    ('china_000922_SH', 'result_china_000922_SH.csv'),
    ('china_H30269_CSI', 'result_china_H30269_CSI.csv'),
]

all_data = {}
for key, fn in files:
    path = os.path.join(RES, fn)
    if os.path.exists(path):
        df = pd.read_csv(path)
        for c in ['total_return_pct','annual_return_pct','max_drawdown_pct','sharpe_ratio','annual_volatility_pct','benchmark_return_pct']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        all_data[key] = df

rows = []
for key, df in all_data.items():
    best = df.loc[df['total_return_pct'].idxmax()]
    worst = df.loc[df['total_return_pct'].idxmin()]
    rows.append({
        '组别': label_map.get(key, key),
        '入场点数': len(df),
        '平均累计收益%': round(df['total_return_pct'].mean(), 2),
        '中位数累计收益%': round(df['total_return_pct'].median(), 2),
        '最好收益%': round(df['total_return_pct'].max(), 2),
        '最差收益%': round(df['total_return_pct'].min(), 2),
        '标准差%': round(df['total_return_pct'].std(), 2),
        '收益区间%': round(df['total_return_pct'].max() - df['total_return_pct'].min(), 2),
        '平均年化%': round(df['annual_return_pct'].mean(), 2),
        '中位数年化%': round(df['annual_return_pct'].median(), 2),
        '最好年化%': round(df['annual_return_pct'].max(), 2),
        '最差年化%': round(df['annual_return_pct'].min(), 2),
        '平均最大回撤%': round(df['max_drawdown_pct'].mean(), 2),
        '中位数回撤%': round(df['max_drawdown_pct'].median(), 2),
        '平均夏普': round(df['sharpe_ratio'].mean(), 4),
        '中位数夏普': round(df['sharpe_ratio'].median(), 4),
        '平均年化波动%': round(df['annual_volatility_pct'].mean(), 2),
        '跑赢基准%': round((df['outperform_benchmark']=='Yes').mean() * 100, 1),
        '平均基准收益%': round(df['benchmark_return_pct'].mean(), 2),
        '最佳入场日': str(best['entry_date']),
        '最差入场日': str(worst['entry_date']),
    })

summary = pd.DataFrame(rows)
summary = summary.sort_values('平均累计收益%', ascending=False)
summary.to_csv(os.path.join(RES, 'summary_statistics.csv'), index=False, encoding='utf-8-sig')

print("=== 累计收益排名 ===")
for i, (_, r) in enumerate(summary.iterrows(), 1):
    print(f"{i}. {r['组别']:8s} +{r['平均累计收益%']:6.2f}%  年化{r['平均年化%']:5.2f}%  回撤{r['平均最大回撤%']:5.2f}%  夏普{r['平均夏普']:.4f}")

print("\n=== 回撤控制排名(低=好) ===")
by_dd = summary.sort_values('平均最大回撤%')
for i, (_, r) in enumerate(by_dd.iterrows(), 1):
    print(f"{i}. {r['组别']:8s} {r['平均最大回撤%']:5.2f}%")

print("\n=== 夏普比率排名 ===")
by_sr = summary.sort_values('平均夏普', ascending=False)
for i, (_, r) in enumerate(by_sr.iterrows(), 1):
    print(f"{i}. {r['组别']:8s} {r['平均夏普']:.4f}")

print(f"\n已保存: {os.path.join(RES, 'summary_statistics.csv')}")
