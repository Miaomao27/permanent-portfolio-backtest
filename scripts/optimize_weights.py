#!/usr/bin/env python3
"""
Phase 3: 最优权重探索引擎
===========================
对每个版本的4资产永久组合，网格搜索最优权重配置。
核心算法：numpy向量化——每个权重组合的所有入场点同时模拟。
多线程：ThreadPoolExecutor 并行处理多个权重组合。

用法:
  python optimize_weights.py <version> [--workers N] [--batch-start B] [--batch-end E]

版本:
  hongli_lowvol  红利低波版（A）
  sp500          标普500版（B）
  nasdaq         纳指100版（C）
  nikkei225      日经225版（D）

示例:
  python optimize_weights.py hongli_lowvol --workers 8
  python optimize_weights.py sp500 --batch-start 0 --batch-end 35 --workers 4
"""

import os
import sys
import time
import csv
import logging
import itertools
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd

# ─── 路径配置 ───────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"
RESULTS3_DIR = PROJECT_DIR / "results3"
RESULTS3_DIR.mkdir(parents=True, exist_ok=True)

END_DATE = "2026-06-06"
TRADING_DAYS_PER_YEAR = 252
REBAL_THRESHOLD = 0.08
TRANSACTION_COST = 0.001  # 0.1%


# ─── 日志配置 ───────────────────────────────────────────────────
def setup_logging(version: str) -> logging.Logger:
    logger = logging.getLogger(f"optimize_{version}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    log_dir = PROJECT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(log_dir / f"optim3_{version}_{ts}.log")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ─── 数据加载 ───────────────────────────────────────────────────
def load_data(version: str, logger: logging.Logger) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    加载指定版本的数据，返回 (prices_matrix, daily_returns, meta)
    prices_matrix: shape (T, 4) — 价格矩阵（stock, bond, gold, cash）
    daily_returns: shape (T-1, 4) — 日收益率
    meta: {'dates': [...], 'bond_rate': float, 'cash_rate': float, 'label': str}
    """
    logger.info(f"加载版本: {version}")

    if version == "hongli_lowvol":
        # 红利低波版：cn_H30269_CSI.csv (有 date,stock,gold) + 固定债券3% + 固定现金2%
        df = pd.read_csv(PROCESSED_DIR / "cn_H30269_CSI.csv", parse_dates=["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df = df[df["date"] <= END_DATE]
        bond_rate = 0.03
        cash_rate = 0.02
        label = "红利低波版 (H30269.CSI, 债券3%, 沪金AU.SHF, 现金2%)"

        # 构造固定收益列的日收益率
        n = len(df)
        bond_daily = (1 + bond_rate) ** (1 / TRADING_DAYS_PER_YEAR) - 1
        cash_daily = (1 + cash_rate) ** (1 / TRADING_DAYS_PER_YEAR) - 1

        prices = np.column_stack([
            df["stock"].values,          # 红利低波指数
            np.full(n, 1.0),              # 债券：从1开始复利
            df["gold"].values,            # 沪金 AU.SHF
            np.full(n, 1.0),              # 现金：从1开始复利
        ])
        # 为债券和现金生成假价格序列
        for i in range(1, n):
            prices[i, 1] = prices[i-1, 1] * (1 + bond_daily)
            prices[i, 3] = prices[i-1, 3] * (1 + cash_daily)

    elif version in ("sp500", "nasdaq"):
        # 美股版：有 date,stock,bond,gold 三列 + 固定现金2%
        fname = "us_sp500_daily.csv" if version == "sp500" else "us_nasdaq_daily.csv"
        df = pd.read_csv(PROCESSED_DIR / fname, parse_dates=["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df = df[df["date"] <= END_DATE]
        bond_rate = None  # 实际TLT价格
        cash_rate = 0.02
        label = ("标普500版 (^SP500TR, TLT, COMEX金, 现金2%)" if version == "sp500"
                 else "纳指100版 (^NDXT, TLT, COMEX金, 现金2%)")

        n = len(df)
        cash_daily = (1 + cash_rate) ** (1 / TRADING_DAYS_PER_YEAR) - 1
        prices = np.column_stack([
            df["stock"].values,
            df["bond"].values,
            df["gold"].values,
            np.full(n, 1.0),  # 现金从1开始
        ])
        for i in range(1, n):
            prices[i, 3] = prices[i-1, 3] * (1 + cash_daily)

    elif version == "nikkei225":
        # 日经225版：需要处理 nikkei225.csv（奇怪格式）+ gold_usd.csv + 固定债券1.5% + 固定现金0.5%
        bond_rate = 0.015
        cash_rate = 0.005
        label = "日经225版 (^N225, 债券1.5%, GOLD_USD, 现金0.5%)"

        # 解析nikkei225.csv
        raw = pd.read_csv(RAW_DIR / "nikkei225.csv", skiprows=3, header=None,
                          names=["Date", "Price", "Close", "High", "Low", "Open", "Volume"])
        raw["Date"] = pd.to_datetime(raw["Date"])
        raw = raw.sort_values("Date").reset_index(drop=True)
        # 过滤2003年后的数据
        raw = raw[raw["Date"] >= "2003-01-01"]
        raw = raw[raw["Date"] <= END_DATE]
        raw["Close"] = raw["Close"].astype(float)

        # 加载黄金数据
        gold = pd.read_csv(RAW_DIR / "gold_usd.csv", parse_dates=["交易日期"])
        gold = gold.rename(columns={"交易日期": "date", "收盘价": "gold"})
        gold = gold.sort_values("date")

        # 合并日期
        df = raw[["Date", "Close"]].rename(columns={"Date": "date", "Close": "stock"})
        df = df.merge(gold[["date", "gold"]], on="date", how="left")
        df = df.dropna(subset=["gold"])
        df = df.sort_values("date").reset_index(drop=True)

        n = len(df)
        bond_daily = (1 + bond_rate) ** (1 / TRADING_DAYS_PER_YEAR) - 1
        cash_daily = (1 + cash_rate) ** (1 / TRADING_DAYS_PER_YEAR) - 1

        prices = np.column_stack([
            df["stock"].values,
            np.full(n, 1.0),
            df["gold"].values,
            np.full(n, 1.0),
        ])
        for i in range(1, n):
            prices[i, 1] = prices[i-1, 1] * (1 + bond_daily)
            prices[i, 3] = prices[i-1, 3] * (1 + cash_daily)

    else:
        raise ValueError(f"未知版本: {version}")

    # 剔除全零行（如果有）
    valid = ~np.all(prices <= 0, axis=1)
    prices = prices[valid]
    dates = df["date"].values[valid] if "df" in dir() else np.arange(len(prices))

    # 计算日收益率
    daily_returns = prices[1:] / prices[:-1] - 1.0
    # 处理异常值
    daily_returns = np.clip(daily_returns, -0.95, 10.0)

    n_days = len(prices)
    logger.info(f"  数据: {n_days} 行, {dates[0]} ~ {dates[-1]}")
    logger.info(f"  日收益率矩阵: ({len(daily_returns)}, 4)")

    # 年线再平衡标记
    annual_rebal = {}
    for i, d in enumerate(dates[:-1]):  # 索引对应 daily_returns[i]
        dt = pd.Timestamp(d)
        if dt.month == 1 and dt.day <= 5:
            annual_rebal[i] = dt.year

    logger.info(f"  年线再平衡日: {len(annual_rebal)} 天 (索引)")

    meta = {
        "dates": dates,
        "bond_rate": bond_rate,
        "cash_rate": cash_rate,
        "label": label,
        "annual_rebal": annual_rebal,
        "version": version,
    }
    return prices, daily_returns, meta


# ─── 权重组合生成 ───────────────────────────────────────────────
def generate_weight_combinations():
    """
    按照计划约束生成所有权重组合：
    股票: 10-50% step 5%
    债券: 5-50% step 5%
    黄金: 5-40% step 5%
    现金: 5-30% step 5%
    四者之和 = 100%
    """
    stocks = np.arange(0.10, 0.55, 0.05)
    bonds = np.arange(0.05, 0.55, 0.05)
    golds = np.arange(0.05, 0.45, 0.05)
    cashes = np.arange(0.05, 0.35, 0.05)

    valid = []
    for ws, wb, wg, wc in itertools.product(stocks, bonds, golds, cashes):
        total = round(ws + wb + wg + wc, 10)
        if abs(total - 1.0) < 1e-9:
            valid.append((float(ws), float(wb), float(wg), float(wc)))

    # 按股票权重排序
    valid.sort(key=lambda x: (x[0], x[1], x[2]))
    return valid


# ─── 核心回测引擎（向量化）─────────────────────────────────────
def backtest_weight_combination(
    daily_returns: np.ndarray,
    w_target: np.ndarray,
    annual_rebal: dict,
    logger: logging.Logger = None,
) -> dict:
    """
    对单个权重组合，回测所有可能的入场点。

    核心算法：
    - T 个交易日，初始化 n=T 个入场点
    - 逐日推进，用 mask 控制活跃入场点
    - 所有运算都是 numpy 向量化矩阵运算

    返回: 统计字典
    """
    T = len(daily_returns) + 1  # 价格天数
    n = T - 1  # 入场点数量（每天可入场，最后一天除外）

    pv = np.ones(n, dtype=np.float64)          # 每个入场点的当前净值
    w = np.tile(w_target, (n, 1)).astype(np.float64)  # 每个入场点的当前权重 (n, 4)
    last_rebal_year = np.full(n, -1, dtype=np.int32)  # 每个入场点上次再平衡年份

    for d in range(T - 1):
        # 活跃入场点：entry_idx <= d
        active_count = d + 1
        if active_count > n:
            active_count = n
        if active_count <= 0:
            continue

        r_d = daily_returns[d]  # (4,) 当日收益率

        # 切片活跃部分
        w_active = w[:active_count]
        pv_active = pv[:active_count]

        # 组合日收益率：w_active @ r_d
        port_ret = np.dot(w_active, r_d)  # (active_count,)

        # 更新净值
        pv_active *= (1.0 + port_ret)

        # 权重漂移
        new_w = w_active * (1.0 + r_d)
        row_sums = new_w.sum(axis=1)
        row_sums = np.maximum(row_sums, 1e-300)
        w_active[:] = new_w / row_sums[:, np.newaxis]

        # ── 再平衡检查 ──
        need_rebal = np.zeros(active_count, dtype=bool)

        # 1. 阈值触发：任何资产偏离目标 > ±8%
        deviation = np.abs(w_active - w_target).max(axis=1)
        need_rebal |= (deviation > REBAL_THRESHOLD)

        # 2. 年线触发（1月前几天）
        if d in annual_rebal:
            yr = annual_rebal[d]
            yr_changed = (last_rebal_year[:active_count] != yr)
            need_rebal |= yr_changed
            last_rebal_year[:active_count][yr_changed] = yr

        # 执行再平衡
        if need_rebal.any():
            w_active[need_rebal] = w_target
            pv_active[need_rebal] *= (1.0 - TRANSACTION_COST)

    # ── 统计计算 ──
    final_returns = pv - 1.0  # 终值 - 1 = 累计收益率

    # 年化收益率 (CAGR)
    holding_years = np.arange(n - 1, -1, -1) / TRADING_DAYS_PER_YEAR
    holding_years = np.maximum(holding_years, 1/TRADING_DAYS_PER_YEAR)  # 最少1天
    cagrs = (pv ** (1.0 / holding_years)) - 1.0

    # 最大回撤（简化计算：用最终PV估算，精确回撤需要持仓路径）
    # 这里用终期回撤近似：从峰值的最大跌幅
    # 由于我们只有终值PV，没有中间路径，用简化版：
    # maxdd = max(0, 1 - pv / peak_pv)
    # 需要峰值路径，在循环中追踪...
    # 目前用简化：假设均匀下跌，回撤≈终值偏离峰值
    # 实际应该在循环中追踪peak-to-trough

    # 胜率计算（不同持有期）
    win_rates = {}
    for months in [1, 3, 6, 12, 24]:
        min_days = months * 21  # 约21个交易日/月
        mask = (np.arange(n) <= (n - 1 - min_days))
        if mask.sum() > 0:
            win_rates[f"win_rate_{months}m"] = float((final_returns[mask] > 0).mean())

    stats = {
        "entry_count": n,
        "mean_return": float(np.mean(final_returns)),
        "median_return": float(np.median(final_returns)),
        "mean_cagr": float(np.mean(cagrs)),
        "median_cagr": float(np.median(cagrs)),
        "cagr_p10": float(np.percentile(cagrs, 10)),
        "cagr_p90": float(np.percentile(cagrs, 90)),
        "std_return": float(np.std(final_returns)),
        "best_return": float(np.max(final_returns)),
        "worst_return": float(np.min(final_returns)),
        "all_positive": int(np.all(final_returns > 0)),
        "positive_rate": float((final_returns > 0).mean()),
    }
    stats.update(win_rates)

    return stats


# ─── 最大回撤精确计算（需要修改backtest循环） ──────────────────
def backtest_weight_combination_with_drawdown(
    daily_returns: np.ndarray,
    w_target: np.ndarray,
    annual_rebal: dict,
    logger: logging.Logger = None,
) -> dict:
    """
    带精确最大回撤计算的版本。
    在循环中追踪每个入场点的峰值PV和最大回撤。
    """
    T = len(daily_returns) + 1
    n = T - 1

    pv = np.ones(n, dtype=np.float64)
    peak_pv = np.ones(n, dtype=np.float64)  # 追踪每个入场点历史峰值
    max_dd = np.zeros(n, dtype=np.float64)   # 追踪每个入场点最大回撤
    w = np.tile(w_target, (n, 1)).astype(np.float64)
    last_rebal_year = np.full(n, -1, dtype=np.int32)

    # 年化无风险利率近似（用于夏普比率）
    rf_daily = 0.02 / TRADING_DAYS_PER_YEAR
    daily_port_returns_list = []  # 收集每个活跃入场点的日收益用于夏普

    for d in range(T - 1):
        active_count = d + 1
        if active_count > n:
            active_count = n
        if active_count <= 0:
            continue

        r_d = daily_returns[d]
        w_active = w[:active_count]
        pv_active = pv[:active_count]

        port_ret = np.dot(w_active, r_d)
        pv_active *= (1.0 + port_ret)

        # 更新峰值和回撤
        peak_active = peak_pv[:active_count]
        mask_new_peak = pv_active > peak_active
        peak_active[mask_new_peak] = pv_active[mask_new_peak]
        peak_pv[:active_count] = peak_active

        dd = (peak_active - pv_active) / peak_active
        max_dd[:active_count] = np.maximum(max_dd[:active_count], dd)

        # 权重漂移
        new_w = w_active * (1.0 + r_d)
        row_sums = new_w.sum(axis=1)
        row_sums = np.maximum(row_sums, 1e-300)
        w_active[:] = new_w / row_sums[:, np.newaxis]

        # 再平衡检查
        need_rebal = np.zeros(active_count, dtype=bool)
        deviation = np.abs(w_active - w_target).max(axis=1)
        need_rebal |= (deviation > REBAL_THRESHOLD)

        if d in annual_rebal:
            yr = annual_rebal[d]
            yr_changed = (last_rebal_year[:active_count] != yr)
            need_rebal |= yr_changed
            last_rebal_year[:active_count][yr_changed] = yr

        if need_rebal.any():
            w_active[need_rebal] = w_target
            pv_active[need_rebal] *= (1.0 - TRANSACTION_COST)

    # ── 统计 ──
    final_returns = pv - 1.0
    holding_years = np.arange(n - 1, -1, -1) / TRADING_DAYS_PER_YEAR
    holding_years = np.maximum(holding_years, 1/TRADING_DAYS_PER_YEAR)
    cagrs = (pv ** (1.0 / holding_years)) - 1.0

    # 夏普比率（简化：用cagr - rf 除以年化波动率）
    # 需要每个入场点的日收益序列来算波动率——用终值反推
    # 简化：用cagrs的截面波动
    annual_vol = np.std(cagrs)
    sharpe = (np.mean(cagrs) - 0.02) / max(annual_vol, 1e-6)

    # 卡尔玛比率
    mean_maxdd = np.mean(max_dd)
    calmar = np.mean(cagrs) / max(mean_maxdd, 1e-6)

    stats = {
        "entry_count": n,
        "mean_return": float(np.mean(final_returns)),
        "median_return": float(np.median(final_returns)),
        "mean_cagr": float(np.mean(cagrs)),
        "median_cagr": float(np.median(cagrs)),
        "cagr_p10": float(np.percentile(cagrs, 10)),
        "cagr_p90": float(np.percentile(cagrs, 90)),
        "std_return": float(np.std(final_returns)),
        "mean_maxdd": float(np.mean(max_dd)),
        "worst_maxdd": float(np.max(max_dd)),
        "mean_sharpe": float(sharpe),
        "mean_calmar": float(calmar),
        "best_return": float(np.max(final_returns)),
        "worst_return": float(np.min(final_returns)),
        "all_positive": int(np.all(final_returns > 0)),
        "positive_rate": float((final_returns > 0).mean()),
    }

    # 持有期胜率
    for months in [1, 3, 6, 12, 24]:
        min_days = months * 21
        mask = (np.arange(n) <= (n - 1 - min_days))
        if mask.sum() > 0:
            stats[f"win_rate_{months}m"] = float((final_returns[mask] > 0).mean())

    return stats


# ─── 批量处理 ───────────────────────────────────────────────────
def process_batch(
    weight_combos: list,
    daily_returns: np.ndarray,
    annual_rebal: dict,
    version: str,
    batch_id: int,
    logger: logging.Logger,
) -> list[dict]:
    """处理一批权重组合"""
    results = []
    n_batch = len(weight_combos)
    logger.info(f"  批次 {batch_id}: 共 {n_batch} 个权重组合")

    t0 = time.time()
    for i, (ws, wb, wg, wc) in enumerate(weight_combos):
        w_target = np.array([ws, wb, wg, wc], dtype=np.float64)
        stats = backtest_weight_combination_with_drawdown(
            daily_returns, w_target, annual_rebal, logger
        )
        stats["w_stock"] = ws
        stats["w_bond"] = wb
        stats["w_gold"] = wg
        stats["w_cash"] = wc
        stats["version"] = version
        results.append(stats)

        if (i + 1) % 50 == 0 or i == n_batch - 1:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (n_batch - i - 1) / rate if rate > 0 else 0
            logger.info(f"    进度 {i+1}/{n_batch} | 速度 {rate:.1f}/s | "
                        f"已耗时 {elapsed:.0f}s | 预计剩余 {eta:.0f}s")

    elapsed = time.time() - t0
    logger.info(f"  批次 {batch_id} 完成: {n_batch} 组, 耗时 {elapsed:.1f}s")
    return results


def process_batch_parallel(
    weight_combos: list,
    daily_returns: np.ndarray,
    annual_rebal: dict,
    version: str,
    batch_id: int,
    logger: logging.Logger,
    workers: int = 4,
) -> list[dict]:
    """多线程处理一批权重组合"""
    n_batch = len(weight_combos)
    if workers <= 1:
        return process_batch(weight_combos, daily_returns, annual_rebal, version, batch_id, logger)

    logger.info(f"  批次 {batch_id}: {n_batch} 组, {workers} 线程并行")

    # 按线程数拆分
    chunk_size = max(1, n_batch // workers)
    chunks = []
    for w in range(workers):
        start = w * chunk_size
        end = start + chunk_size if w < workers - 1 else n_batch
        if start < n_batch:
            chunks.append(weight_combos[start:end])

    t0 = time.time()
    all_results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for cid, chunk in enumerate(chunks):
            fut = executor.submit(
                process_single_chunk_serial,
                chunk, daily_returns, annual_rebal, version, logger
            )
            futures[fut] = cid

        completed = 0
        for fut in as_completed(futures):
            cid = futures[fut]
            chunk_results = fut.result()
            all_results.extend(chunk_results)
            completed += 1
            logger.info(f"    分块 {cid+1}/{len(chunks)} 完成 ({completed}/{len(chunks)})")

    elapsed = time.time() - t0
    logger.info(f"  批次 {batch_id} 完成: {n_batch} 组, {workers} 线程, 耗时 {elapsed:.1f}s")
    return all_results


def process_single_chunk_serial(
    chunk: list,
    daily_returns: np.ndarray,
    annual_rebal: dict,
    version: str,
    logger: logging.Logger,
) -> list[dict]:
    """单线程处理一个分块"""
    results = []
    for ws, wb, wg, wc in chunk:
        w_target = np.array([ws, wb, wg, wc], dtype=np.float64)
        stats = backtest_weight_combination_with_drawdown(
            daily_returns, w_target, annual_rebal
        )
        stats["w_stock"] = ws
        stats["w_bond"] = wb
        stats["w_gold"] = wg
        stats["w_cash"] = wc
        stats["version"] = version
        results.append(stats)
    return results


# ─── 保存结果 ───────────────────────────────────────────────────
def save_results(results: list[dict], version: str, logger: logging.Logger):
    """保存网格结果CSV"""
    out_dir = RESULTS3_DIR / version
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "grid_results.csv"
    fieldnames = [
        "w_stock", "w_bond", "w_gold", "w_cash",
        "entry_count", "mean_return", "median_return",
        "mean_cagr", "median_cagr", "cagr_p10", "cagr_p90",
        "std_return", "mean_maxdd", "worst_maxdd",
        "mean_sharpe", "mean_calmar",
        "best_return", "worst_return",
        "all_positive", "positive_rate",
        "win_rate_1m", "win_rate_3m", "win_rate_6m",
        "win_rate_12m", "win_rate_24m",
        "version",
    ]

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"  结果已保存: {csv_path} ({len(results)} 行)")


# ─── 帕累托前沿提取 ────────────────────────────────────────────
def extract_pareto_frontier(results: list[dict]) -> list[dict]:
    """提取帕累托前沿：收益-回撤二维前沿"""
    df = pd.DataFrame(results)
    if df.empty:
        return []

    # 按 mean_cagr(最大化) 和 worst_maxdd(最小化) 找前沿
    df = df.sort_values("worst_maxdd").reset_index(drop=True)
    pareto = []
    max_cagr_so_far = -np.inf

    for _, row in df.iterrows():
        if row["mean_cagr"] > max_cagr_so_far:
            pareto.append(row.to_dict())
            max_cagr_so_far = row["mean_cagr"]

    return pareto


def extract_recommendations(results: list[dict], logger: logging.Logger) -> list[dict]:
    """提取三档推荐配置"""
    df = pd.DataFrame(results)
    if df.empty:
        return []

    recs = []

    # 稳健型：所有入场正收益 + 最差回撤最小
    positive = df[df["all_positive"] == 1].copy()
    if not positive.empty:
        stable = positive.sort_values("worst_maxdd").iloc[0]
        stable_dict = stable.to_dict()
        stable_dict["tier"] = "稳健型"
        stable_dict["sort_criterion"] = "worst_maxdd最小(全正收益)"
        recs.append(stable_dict)
        logger.info(f"  稳健型: w=({stable['w_stock']:.0%},{stable['w_bond']:.0%},"
                    f"{stable['w_gold']:.0%},{stable['w_cash']:.0%}) "
                    f"回撤={stable['worst_maxdd']:.2%} CAGR={stable['mean_cagr']:.2%}")

    # 均衡型：卡尔玛比率最高
    balanced = df.sort_values("mean_calmar", ascending=False).iloc[0]
    balanced_dict = balanced.to_dict()
    balanced_dict["tier"] = "均衡型"
    balanced_dict["sort_criterion"] = "mean_calmar最高"
    recs.append(balanced_dict)
    logger.info(f"  均衡型: w=({balanced['w_stock']:.0%},{balanced['w_bond']:.0%},"
                f"{balanced['w_gold']:.0%},{balanced['w_cash']:.0%}) "
                f"Calmar={balanced['mean_calmar']:.2f} CAGR={balanced['mean_cagr']:.2%}")

    # 进取型：CAGR最高，回撤≤25%
    aggressive = df[df["worst_maxdd"] <= 0.25].copy()
    if aggressive.empty:
        aggressive = df.copy()  # fallback
    agg = aggressive.sort_values("mean_cagr", ascending=False).iloc[0]
    agg_dict = agg.to_dict()
    agg_dict["tier"] = "进取型"
    agg_dict["sort_criterion"] = "mean_cagr最高(worst_maxdd≤25%)"
    recs.append(agg_dict)
    logger.info(f"  进取型: w=({agg['w_stock']:.0%},{agg['w_bond']:.0%},"
                f"{agg['w_gold']:.0%},{agg['w_cash']:.0%}) "
                f"CAGR={agg['mean_cagr']:.2%} 回撤={agg['worst_maxdd']:.2%}")

    # 保存推荐
    out_dir = RESULTS3_DIR / results[0].get("version", "unknown")
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "top_recommendations.csv"
    rec_df = pd.DataFrame(recs)
    rec_df.to_csv(csv_path, index=False)
    logger.info(f"  推荐已保存: {csv_path}")

    return recs


# ─── 主函数 ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Phase 3: 最优权重探索引擎")
    parser.add_argument("version", choices=["hongli_lowvol", "sp500", "nasdaq", "nikkei225"],
                        help="版本标识")
    parser.add_argument("--workers", type=int, default=4,
                        help="并行线程数 (default: 4)")
    parser.add_argument("--batch-start", type=int, default=None,
                        help="批次起始索引")
    parser.add_argument("--batch-end", type=int, default=None,
                        help="批次结束索引（不包含）")
    parser.add_argument("--no-parallel", action="store_true",
                        help="禁用多线程（调试用）")
    args = parser.parse_args()

    logger = setup_logging(args.version)
    logger.info(f"=" * 60)
    logger.info(f"Phase 3 最优权重探索引擎")
    logger.info(f"版本: {args.version}")
    logger.info(f"线程数: {args.workers}")
    logger.info(f"=" * 60)

    # 1. 加载数据
    prices, daily_returns, meta = load_data(args.version, logger)

    # 2. 生成权重组合
    all_combos = generate_weight_combinations()
    logger.info(f"总权重组合: {len(all_combos)}")

    # 批次过滤
    if args.batch_start is not None or args.batch_end is not None:
        start = args.batch_start or 0
        end = args.batch_end or len(all_combos)
        combos = all_combos[start:end]
        batch_label = f"[{start}:{end}]"
        logger.info(f"本批次: {batch_label} = {len(combos)} 组")
    else:
        combos = all_combos
        batch_label = "full"

    # 3. 运行回测
    workers = 1 if args.no_parallel else args.workers
    t_start = time.time()

    if workers > 1:
        results = process_batch_parallel(
            combos, daily_returns, meta["annual_rebal"],
            args.version, batch_label, logger, workers
        )
    else:
        results = process_batch(
            combos, daily_returns, meta["annual_rebal"],
            args.version, batch_label, logger
        )

    total_time = time.time() - t_start
    logger.info(f"总耗时: {total_time:.1f}s ({total_time/60:.1f}min)")

    # 4. 保存结果
    save_results(results, args.version, logger)

    # 5. 帕累托前沿 + 推荐
    pareto = extract_pareto_frontier(results)
    logger.info(f"帕累托前沿点数: {len(pareto)}")
    if pareto:
        out_dir = RESULTS3_DIR / args.version
        pd.DataFrame(pareto).to_csv(out_dir / "pareto_frontier.csv", index=False)

    recs = extract_recommendations(results, logger)

    logger.info("完成 ✓")


if __name__ == "__main__":
    main()
