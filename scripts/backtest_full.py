#!/usr/bin/env python3
"""
永久投资组合日频回测 — 完整版
覆盖：美股标普组、美股纳指组、中国组
数据从MySQL导出，逐日模拟，输出CSV结果
"""

import os, sys, json, time, logging
from datetime import datetime, date, timedelta
import numpy as np
import pandas as pd
import pymysql
from dateutil.relativedelta import relativedelta

# ========== 配置 ==========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
DATA_PROC_DIR = os.path.join(BASE_DIR, 'data', 'processed')
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
CHARTS_DIR = os.path.join(BASE_DIR, 'charts')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')

os.makedirs(DATA_RAW_DIR, exist_ok=True)
os.makedirs(DATA_PROC_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# MySQL
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'finance_user',
    'password': 'Finance2026!',
    'database': 'china_finance_db',
    'charset': 'utf8mb4'
}

END_DATE = date(2026, 6, 6)

# ========== 日志 ==========
log_file = os.path.join(LOGS_DIR, f'backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== MySQL导出 ==========
def fetch_to_df(query, params=None):
    """从MySQL查询返回DataFrame"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        df = pd.read_sql(query, conn, params=params)
        return df
    finally:
        conn.close()

def export_all_data():
    """导出所有回测所需数据"""
    logger.info("=== 开始导出MySQL数据 ===")

    # 1. 美股指数
    logger.info("导出 us_index_daily ...")
    df_idx = fetch_to_df("""
        SELECT index_code, trade_date, adj_close
        FROM us_index_daily
        WHERE index_code IN ('^SP500TR', '^NDXT')
        ORDER BY index_code, trade_date
    """)
    df_idx.to_csv(os.path.join(DATA_RAW_DIR, 'us_index.csv'), index=False)
    logger.info(f"  us_index: {len(df_idx)} 条")

    # 2. TLT ETF
    logger.info("导出 TLT ...")
    df_tlt = fetch_to_df("""
        SELECT etf_code, trade_date, adj_close
        FROM us_etf_daily
        WHERE etf_code = 'TLT'
        ORDER BY trade_date
    """)
    df_tlt.to_csv(os.path.join(DATA_RAW_DIR, 'tlt.csv'), index=False)
    logger.info(f"  TLT: {len(df_tlt)} 条")

    # 3. 国际金价 (GOLD_USD)
    logger.info("导出 GOLD_USD ...")
    df_gold = fetch_to_df("""
        SELECT 商品代码, 交易日期, 收盘价
        FROM commodity_daily
        WHERE 商品代码 = 'GOLD_USD'
        ORDER BY 交易日期
    """)
    df_gold.to_csv(os.path.join(DATA_RAW_DIR, 'gold_usd.csv'), index=False)
    logger.info(f"  GOLD_USD: {len(df_gold)} 条")

    # 4. 沪深300
    logger.info("导出 沪深300 ...")
    df_hs300 = fetch_to_df("""
        SELECT 证券代码, 交易日期, 收盘价
        FROM daily_quote
        WHERE 证券代码 = '000300.SH'
        ORDER BY 交易日期
    """)
    df_hs300.to_csv(os.path.join(DATA_RAW_DIR, 'hs300.csv'), index=False)
    logger.info(f"  沪深300: {len(df_hs300)} 条")

    # 5. 沪金 (AU.SHF)
    logger.info("导出 AU.SHF ...")
    df_au = fetch_to_df("""
        SELECT 商品代码, 交易日期, 收盘价
        FROM commodity_daily
        WHERE 商品代码 = 'AU.SHF'
        ORDER BY 交易日期
    """)
    df_au.to_csv(os.path.join(DATA_RAW_DIR, 'au_shf.csv'), index=False)
    logger.info(f"  AU.SHF: {len(df_au)} 条")

    logger.info("=== 数据导出完成 ===")
    return {
        'sp500': df_idx[df_idx['index_code'] == '^SP500TR'][['trade_date', 'adj_close']].rename(columns={'trade_date': 'date', 'adj_close': 'price'}),
        'ndxt': df_idx[df_idx['index_code'] == '^NDXT'][['trade_date', 'adj_close']].rename(columns={'trade_date': 'date', 'adj_close': 'price'}),
        'tlt': df_tlt[['trade_date', 'adj_close']].rename(columns={'trade_date': 'date', 'adj_close': 'price'}),
        'gold_usd': df_gold[['交易日期', '收盘价']].rename(columns={'交易日期': 'date', '收盘价': 'price'}),
        'hs300': df_hs300[['交易日期', '收盘价']].rename(columns={'交易日期': 'date', '收盘价': 'price'}),
        'au_shf': df_au[['交易日期', '收盘价']].rename(columns={'交易日期': 'date', '收盘价': 'price'}),
    }

# ========== 数据对齐 ==========
def align_prices(asset_dict, start_date=None):
    """将多资产价格对齐到共同交易日，向前填充缺失值"""
    logger.info("=== 开始数据对齐 ===")

    # 将所有资产转换为date->price的Series
    series_list = []
    names = []
    for name, df in asset_dict.items():
        df = df.copy()
        df['date'] = pd.to_datetime(df['date']).dt.date
        df = df.sort_values('date')
        s = df.set_index('date')['price']
        series_list.append(s)
        names.append(name)

    # 合并
    aligned = pd.concat(series_list, axis=1, keys=names)
    aligned = aligned.sort_index()

    # 过滤开始日期
    if start_date:
        aligned = aligned[aligned.index >= start_date]

    # 向前填充缺失值（最多5天）
    aligned = aligned.ffill(limit=5)

    # 删除仍然有缺失的行
    before = len(aligned)
    aligned = aligned.dropna()
    after = len(aligned)
    logger.info(f"  对齐后: {before} -> {after} 行, 丢弃 {before-after} 行含缺失")

    return aligned

def align_us_data(assets):
    """对齐美股组数据（标普500 + TLT + 黄金 + 现金用全1表示）"""
    us_dict = {
        'stock': assets['sp500'],
        'bond': assets['tlt'],
        'gold': assets['gold_usd'],
    }
    aligned = align_prices(us_dict, start_date=date(2003, 1, 1))
    logger.info(f"美股标普组对齐: {len(aligned)} 个交易日, {aligned.index[0]} ~ {aligned.index[-1]}")
    return aligned

def align_us_nasdaq_data(assets):
    """对齐美股纳指组数据（纳指100 + TLT + 黄金）"""
    us_dict = {
        'stock': assets['ndxt'],
        'bond': assets['tlt'],
        'gold': assets['gold_usd'],
    }
    aligned = align_prices(us_dict, start_date=date(2006, 2, 22))
    logger.info(f"美股纳指组对齐: {len(aligned)} 个交易日, {aligned.index[0]} ~ {aligned.index[-1]}")
    return aligned

def align_cn_data(assets):
    """对齐中国组数据（沪深300 + 沪金）"""
    cn_dict = {
        'stock': assets['hs300'],
        'gold': assets['au_shf'],
    }
    aligned = align_prices(cn_dict, start_date=date(2009, 1, 5))
    logger.info(f"中国组对齐: {len(aligned)} 个交易日, {aligned.index[0]} ~ {aligned.index[-1]}")
    return aligned

# ========== 回测引擎 ==========
def backtest_single_entry(entry_idx, prices, initial_capital=100000,
                           cash_rate=0.02, bond_rate=None, trade_cost=0.001,
                           rebalance_threshold=0.08, annual_rebalance=True):
    """
    对单个入场点进行回测

    参数:
        entry_idx: 入场在prices中的行索引位置
        prices: DataFrame, index=date, columns=资产价格
        initial_capital: 初始资金
        cash_rate: 现金年化收益率
        bond_rate: 债券年化收益率（如为None，则从prices中取bond列）
        trade_cost: 交易成本比例
        rebalance_threshold: 权重偏离阈值（绝对偏离）
        annual_rebalance: 是否每年1月强制再平衡
    """
    n_assets = prices.shape[1]
    asset_names = prices.columns.tolist()

    # 确定是否有bond列
    has_bond = 'bond' in asset_names

    # 初始权重各25%
    weights = np.ones(n_assets) / n_assets
    portfolio_value = float(initial_capital)

    # 记录净值序列
    nav_history = []
    rebalance_dates = []
    last_rebalance_year = None

    # 从entry_idx开始到倒数第二天（最后一天无法计算下一天收益）
    total_days = len(prices)

    for i in range(entry_idx, total_days - 1):
        today = prices.index[i]
        tomorrow = prices.index[i+1]

        # 计算各资产日收益率
        daily_rets = np.zeros(n_assets)
        for j, name in enumerate(asset_names):
            if name == 'cash':
                # 现金：年化2%，按交易日计
                daily_rets[j] = cash_rate / 252
            elif name == 'bond' and bond_rate is not None:
                # 债券：固定年化
                daily_rets[j] = bond_rate / 252
            else:
                # 从价格计算收益率
                p_today = prices.iloc[i][name]
                p_tomorrow = prices.iloc[i+1][name]
                if p_today > 0 and p_tomorrow > 0:
                    daily_rets[j] = p_tomorrow / p_today - 1
                else:
                    daily_rets[j] = 0.0

        # 更新组合净值
        portfolio_return = np.sum(weights * daily_rets)
        portfolio_value *= (1 + portfolio_return)

        # 更新权重（漂移）
        new_weights = weights * (1 + daily_rets)
        weight_sum = np.sum(new_weights)
        if weight_sum > 0:
            weights = new_weights / weight_sum

        # 记录净值
        nav_history.append((today, portfolio_value))

        # 检查是否触发再平衡
        need_rebalance = False

        # 阈值触发
        if np.any(np.abs(weights - 0.25) > rebalance_threshold):
            need_rebalance = True

        # 年度强制再平衡
        if annual_rebalance and today.month == 1 and today.day <= 3:
            if last_rebalance_year != today.year:
                need_rebalance = True

        if need_rebalance:
            # 重置为各25%
            weights = np.ones(n_assets) / n_assets
            portfolio_value *= (1 - trade_cost)
            rebalance_dates.append(today)
            last_rebalance_year = today.year

    # 计算最终指标
    final_value = portfolio_value
    holding_years = (nav_history[-1][0] - nav_history[0][0]).days / 365.0
    total_return = (final_value / initial_capital - 1) * 100
    annual_return = ((final_value / initial_capital) ** (1 / holding_years) - 1) * 100 if holding_years > 0 else 0

    # 计算最大回撤
    nav_values = [v for _, v in nav_history]
    peak = nav_values[0]
    max_drawdown = 0
    for v in nav_values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_drawdown:
            max_drawdown = dd

    # 计算夏普比率（年化2.5%无风险利率）
    daily_returns = []
    for i in range(len(nav_history) - 1):
        r = nav_history[i+1][1] / nav_history[i][1] - 1
        daily_returns.append(r)

    if len(daily_returns) > 1:
        excess_returns = np.array(daily_returns) - (0.025 / 252)
        annual_vol = np.std(daily_returns) * np.sqrt(252) * 100
        sharpe = float(np.mean(excess_returns) / np.std(daily_returns) * np.sqrt(252)) if np.std(daily_returns) > 0 else 0
    else:
        annual_vol = 0
        sharpe = 0

    # 同期基准（纯持有股票）
    stock_col = 'stock' if 'stock' in asset_names else asset_names[0]
    stock_start = prices.iloc[entry_idx][stock_col]
    stock_end = prices.iloc[-1][stock_col]
    benchmark_return = (stock_end / stock_start - 1) * 100 if stock_start > 0 else 0

    return {
        'entry_date': prices.index[entry_idx],
        'final_value': round(final_value, 2),
        'total_return_pct': round(total_return, 4),
        'annual_return_pct': round(annual_return, 4),
        'max_drawdown_pct': round(max_drawdown, 4),
        'sharpe_ratio': round(sharpe, 4),
        'annual_volatility_pct': round(annual_vol, 4),
        'benchmark_return_pct': round(benchmark_return, 4),
        'outperform_benchmark': 'Yes' if total_return > benchmark_return else 'No',
        'holding_years': round(holding_years, 2),
        'rebalance_count': len(rebalance_dates),
        'entry_index': entry_idx,
    }

def run_backtest_group(prices, group_name, initial_capital, cash_rate=0.02,
                       bond_rate=None, trade_cost=0.001):
    """对一组资产运行全入场点回测"""
    logger.info(f"\n{'='*60}")
    logger.info(f"开始回测: {group_name}")
    logger.info(f"  交易日数: {len(prices)}")
    logger.info(f"  入场点总数: {len(prices) - 252} (去掉最后1年作为最小持有期)")
    logger.info(f"{'='*60}")

    # 入场点范围：保留最后252个交易日作为最小持有期
    max_entry = len(prices) - 252
    if max_entry <= 0:
        max_entry = len(prices) - 1

    results = []
    start_time = time.time()

    # 每500个入场点输出一次进度
    progress_interval = max(1, max_entry // 20)

    for idx in range(max_entry):
        result = backtest_single_entry(
            entry_idx=idx,
            prices=prices,
            initial_capital=initial_capital,
            cash_rate=cash_rate,
            bond_rate=bond_rate,
            trade_cost=trade_cost
        )
        results.append(result)

        if (idx + 1) % progress_interval == 0 or idx == max_entry - 1:
            elapsed = time.time() - start_time
            pct = (idx + 1) / max_entry * 100
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            remaining = (max_entry - idx - 1) / rate if rate > 0 else 0
            logger.info(f"  {group_name}: {idx+1}/{max_entry} ({pct:.1f}%) | "
                       f"耗时 {elapsed:.0f}s | 速率 {rate:.0f} 点/秒 | 预计剩余 {remaining:.0f}s")

    elapsed_total = time.time() - start_time
    logger.info(f"{group_name} 完成! 总耗时: {elapsed_total:.0f}s ({elapsed_total/60:.1f}min)")
    logger.info(f"  {len(results)} 个入场点")

    df = pd.DataFrame(results)
    return df

# ========== 主流程 ==========
def main():
    logger.info("=" * 60)
    logger.info("永久投资组合日频回测 - 开始")
    logger.info(f"结束日期: {END_DATE}")
    logger.info("=" * 60)

    # Step 1: 导出MySQL数据
    all_assets = export_all_data()

    # Step 2: 对齐数据并保存CSV
    logger.info("\n=== 对齐并保存processed CSV ===")

    # 美股标普组
    us_sp500 = align_us_data(all_assets)
    us_sp500.to_csv(os.path.join(DATA_PROC_DIR, 'us_sp500_daily.csv'))
    logger.info(f"  保存: us_sp500_daily.csv ({len(us_sp500)} 行)")

    # 美股纳指组
    us_nasdaq = align_us_nasdaq_data(all_assets)
    us_nasdaq.to_csv(os.path.join(DATA_PROC_DIR, 'us_nasdaq_daily.csv'))
    logger.info(f"  保存: us_nasdaq_daily.csv ({len(us_nasdaq)} 行)")

    # 中国组
    cn = align_cn_data(all_assets)
    cn.to_csv(os.path.join(DATA_PROC_DIR, 'cn_daily.csv'))
    logger.info(f"  保存: cn_daily.csv ({len(cn)} 行)")

    # Step 3: 添加现金列（固定100%）
    us_sp500['cash'] = 1.0
    us_nasdaq['cash'] = 1.0
    cn['cash'] = 1.0

    # Step 4: 运行三组回测
    results = {}

    # 标普组
    logger.info("\n" + "="*60)
    logger.info("美股标普组回测 (10万美元)")
    logger.info(f"  股票: 标普500全收益 | 债券: TLT | 黄金: 国际金价 | 现金: 年化2%")
    logger.info("="*60)
    df_sp500 = run_backtest_group(
        us_sp500, 'SP500', 100000,
        cash_rate=0.02
    )
    df_sp500.to_csv(os.path.join(RESULTS_DIR, 'result_sp500.csv'), index=False)
    results['sp500'] = df_sp500

    # 纳指组
    logger.info("\n" + "="*60)
    logger.info("美股纳指组回测 (10万美元)")
    logger.info(f"  股票: 纳指100全收益 | 债券: TLT | 黄金: 国际金价 | 现金: 年化2%")
    logger.info("="*60)
    df_nasdaq = run_backtest_group(
        us_nasdaq, 'NASDAQ', 100000,
        cash_rate=0.02
    )
    df_nasdaq.to_csv(os.path.join(RESULTS_DIR, 'result_nasdaq.csv'), index=False)
    results['nasdaq'] = df_nasdaq

    # 中国组
    logger.info("\n" + "="*60)
    logger.info("中国组回测 (100万人民币)")
    logger.info(f"  股票: 沪深300 | 债券: 固定3% | 黄金: 沪金 | 现金: 年化2%")
    logger.info("="*60)
    df_cn = run_backtest_group(
        cn, 'CHINA', 1000000,
        cash_rate=0.02,
        bond_rate=0.03,
    )
    df_cn.to_csv(os.path.join(RESULTS_DIR, 'result_china.csv'), index=False)
    results['cn'] = df_cn

    # Step 5: 汇总统计
    logger.info("\n" + "="*60)
    logger.info("生成汇总统计")
    logger.info("="*60)

    summary_rows = []
    for name, df in results.items():
        row = {
            'group': name,
            'entry_count': len(df),
            'avg_total_return': df['total_return_pct'].mean(),
            'median_total_return': df['total_return_pct'].median(),
            'best_total_return': df['total_return_pct'].max(),
            'worst_total_return': df['total_return_pct'].min(),
            'std_total_return': df['total_return_pct'].std(),
            'avg_annual_return': df['annual_return_pct'].mean(),
            'median_annual_return': df['annual_return_pct'].median(),
            'best_annual_return': df['annual_return_pct'].max(),
            'worst_annual_return': df['annual_return_pct'].min(),
            'avg_max_drawdown': df['max_drawdown_pct'].mean(),
            'median_max_drawdown': df['max_drawdown_pct'].median(),
            'avg_sharpe': df['sharpe_ratio'].mean(),
            'median_sharpe': df['sharpe_ratio'].median(),
            'avg_annual_vol': df['annual_volatility_pct'].mean(),
            'outperform_pct': (df['outperform_benchmark'] == 'Yes').mean() * 100,
            'avg_benchmark_return': df['benchmark_return_pct'].mean(),
            'avg_holding_years': df['holding_years'].mean(),
            'best_entry_date': str(df.loc[df['total_return_pct'].idxmax(), 'entry_date']),
            'worst_entry_date': str(df.loc[df['total_return_pct'].idxmin(), 'entry_date']),
        }
        summary_rows.append(row)

    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(os.path.join(RESULTS_DIR, 'summary_statistics.csv'), index=False)

    # 打印摘要
    print("\n" + "="*70)
    print("📊 汇总统计")
    print("="*70)
    for _, row in df_summary.iterrows():
        print(f"\n{'='*50}")
        print(f"  {row['group'].upper()}")
        print(f"{'='*50}")
        print(f"  入场点:         {int(row['entry_count'])}")
        print(f"  平均累计收益:    {row['avg_total_return']:.2f}%")
        print(f"  中位数累计收益:  {row['median_total_return']:.2f}%")
        print(f"  最好收益:        {row['best_total_return']:.2f}% ({row['best_entry_date']})")
        print(f"  最差收益:        {row['worst_total_return']:.2f}% ({row['worst_entry_date']})")
        print(f"  标准差:          {row['std_total_return']:.2f}%")
        print(f"  平均年化收益:    {row['avg_annual_return']:.2f}%")
        print(f"  中位数年化收益:  {row['median_annual_return']:.2f}%")
        print(f"  平均最大回撤:    {row['avg_max_drawdown']:.2f}%")
        print(f"  平均夏普比率:    {row['avg_sharpe']:.4f}")
        print(f"  跑赢基准比例:    {row['outperform_pct']:.1f}%")
        print(f"  平均持有年限:    {row['avg_holding_years']:.1f}年")

    # 保存完整信息供后续分析
    summary_info = {
        'end_date': str(END_DATE),
        'groups': list(results.keys()),
        'us_sp500': {
            'trading_days': len(us_sp500),
            'date_range': f"{us_sp500.index[0]} ~ {us_sp500.index[-1]}",
            'entry_count': len(df_sp500),
        },
        'us_nasdaq': {
            'trading_days': len(us_nasdaq),
            'date_range': f"{us_nasdaq.index[0]} ~ {us_nasdaq.index[-1]}",
            'entry_count': len(df_nasdaq),
        },
        'china': {
            'trading_days': len(cn),
            'date_range': f"{cn.index[0]} ~ {cn.index[-1]}",
            'entry_count': len(df_cn),
        },
        'run_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'log_file': log_file,
    }

    with open(os.path.join(RESULTS_DIR, 'run_info.json'), 'w', encoding='utf-8') as f:
        json.dump(summary_info, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ 全部完成! 日志: {log_file}")
    logger.info(f"  结果文件: {RESULTS_DIR}/")
    logger.info(f"  汇总: {os.path.join(RESULTS_DIR, 'summary_statistics.csv')}")

    return results, df_summary

if __name__ == '__main__':
    main()
