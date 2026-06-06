#!/usr/bin/env python3
"""分析所有回测结果，生成汇总统计"""
import os, json
import numpy as np
import pandas as pd

BASE = '/home/cpy/文档/金融数据库建立/永久投资组合研究'
RES = os.path.join(BASE, 'results')
CHARTS = os.path.join(BASE, 'charts')
os.makedirs(CHARTS, exist_ok=True)

label_map = {
    'sp500': '美股标普500组',
    'nasdaq': '美股纳斯达克100组',
    'china': '中国-沪深300',
    'china_000016_SH': '中国-上证50',
    'china_000688_SH': '中国-科创50',
    'china_000852_SH': '中国-中证1000',
    'china_000905_SH': '中国-中证500',
    'china_000932_SH': '中国-中证2000',
    'china_399006_SZ': '中国-创业板指',
}

short_label = {
    'sp500': '标普500',
    'nasdaq': '纳指100',
    'china': '沪深300',
    'china_000016_SH': '上证50',
    'china_000688_SH': '科创50',
    'china_000852_SH': '中证1000',
    'china_000905_SH': '中证500',
    'china_000932_SH': '中证2000',
    'china_399006_SZ': '创业板指',
}

files = [
    ('sp500', 'result_sp500.csv'),
    ('nasdaq', 'result_nasdaq.csv'),
    ('china', 'result_china.csv'),
    ('china_000016_SH', 'result_china_000016_SH.csv'),
    ('china_000688_SH', 'result_china_000688_SH.csv'),
    ('china_000852_SH', 'result_china_000852_SH.csv'),
    ('china_000905_SH', 'result_china_000905_SH.csv'),
    ('china_000932_SH', 'result_china_000932_SH.csv'),
    ('china_399006_SZ', 'result_china_399006_SZ.csv'),
]

all_data = {}
for key, fn in files:
    path = os.path.join(RES, fn)
    if os.path.exists(path):
        all_data[key] = pd.read_csv(path)
        print(f"  ✓ {key}: {len(all_data[key])} 条入场点")

# 汇总统计
rows = []
for key, df in all_data.items():
    df['total_return_pct'] = pd.to_numeric(df['total_return_pct'], errors='coerce')
    df['annual_return_pct'] = pd.to_numeric(df['annual_return_pct'], errors='coerce')
    df['max_drawdown_pct'] = pd.to_numeric(df['max_drawdown_pct'], errors='coerce')
    df['sharpe_ratio'] = pd.to_numeric(df['sharpe_ratio'], errors='coerce')
    df['annual_volatility_pct'] = pd.to_numeric(df['annual_volatility_pct'], errors='coerce')
    df['benchmark_return_pct'] = pd.to_numeric(df['benchmark_return_pct'], errors='coerce')

    best_idx = df['total_return_pct'].idxmax()
    worst_idx = df['total_return_pct'].idxmin()

    rows.append({
        '组别': short_label[key],
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
        '跑赢基准%': round((df['outperform_benchmark'] == 'Yes').mean() * 100, 1),
        '平均基准收益%': round(df['benchmark_return_pct'].mean(), 2),
        '平均持有年限': round(df['holding_years'].mean(), 1),
        '最佳入场日': str(df.loc[best_idx, 'entry_date']),
        '最差入场日': str(df.loc[worst_idx, 'entry_date']),
    })

summary = pd.DataFrame(rows)
summary.to_csv(os.path.join(RES, 'summary_statistics.csv'), index=False, encoding='utf-8-sig')

print("\n" + "="*100)
print("📊 永久投资组合日频回测 — 跨组汇总对比")
print("="*100)

# 格式化打印
for _, r in summary.iterrows():
    print(f"\n{'─'*60}")
    print(f"  {r['组别']}")
    print(f"{'─'*60}")
    print(f"  入场点数:      {int(r['入场点数'])}")
    print(f"  平均累计收益:   {r['平均累计收益%']}%")
    print(f"  中位数累计收益: {r['中位数累计收益%']}%")
    print(f"  收益区间:      {r['最差收益%']}% ~ {r['最好收益%']}% (跨度{r['收益区间%']}%)")
    print(f"  平均年化:      {r['平均年化%']}%")
    print(f"  中位数年化:    {r['中位数年化%']}%")
    print(f"  平均最大回撤:   {r['平均最大回撤%']}%")
    print(f"  平均夏普比率:   {r['平均夏普']}")
    print(f"  跑赢基准比例:   {r['跑赢基准%']}%")
    print(f"  最佳入场:      {r['最佳入场日']} → {r['最好收益%']}%")
    print(f"  最差入场:      {r['最差入场日']} → {r['最差收益%']}%")

print("\n" + "="*100)
print("💡 核心发现")
print("="*100)

# 按平均累计收益排序
by_return = summary.sort_values('平均累计收益%', ascending=False)
print(f"\n📈 累计收益排名:")
for i, (_, r) in enumerate(by_return.iterrows(), 1):
    print(f"  {i}. {r['组别']}: {r['平均累计收益%']}% (年化{r['平均年化%']}%, 回撤{r['平均最大回撤%']}%)")

# 按夏普排序
by_sharpe = summary.sort_values('平均夏普', ascending=False)
print(f"\n📊 夏普比率排名:")
for i, (_, r) in enumerate(by_sharpe.iterrows(), 1):
    print(f"  {i}. {r['组别']}: {r['平均夏普']} (收益{r['平均累计收益%']}%, 回撤{r['平均最大回撤%']}%)")

# 按回撤排序
by_dd = summary.sort_values('平均最大回撤%')
print(f"\n🛡️ 最大回撤排名(越低越好):")
for i, (_, r) in enumerate(by_dd.iterrows(), 1):
    print(f"  {i}. {r['组别']}: {r['平均最大回撤%']}%")

# 按跑赢基准比例
by_out = summary.sort_values('跑赢基准%', ascending=False)
print(f"\n🏆 跑赢基准比例排名:")
for i, (_, r) in enumerate(by_out.iterrows(), 1):
    print(f"  {i}. {r['组别']}: {r['跑赢基准%']}%")

print(f"\n汇总已保存: {os.path.join(RES, 'summary_statistics.csv')}")
