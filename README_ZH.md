# 永久投资组合日频回测研究

> 验证 Harry Browne 永久投资组合（25%股票+25%长期国债+25%黄金+25%现金）在不同市场、不同入场时点的表现
>
> **📄 研究论文：** [reports/研究论文.md](reports/研究论文.md)（含10篇学术参考文献）
> **🌐 English version:** [README.md](README.md)

---

## 📊 研究概况

| 项目 | 说明 |
|------|------|
| 回测日期 | 2003-01 ~ 2026-06 |
| 覆盖组数 | **11组**（美股2组 + A股9个指数） |
| 总入场点 | ~40,000+ |
| 再平衡规则 | ±8%阈值 + 每年1月强制，单次成本0.1% |
| 数据来源 | yfinance (美股) / akshare (A股) / MySQL (已有) |

### 美股组

| 组别 | 股票(25%) | 债券(25%) | 黄金(25%) | 现金(25%) | 本金 |
|------|----------|----------|----------|----------|------|
| 标普500 | ^SP500TR | TLT ETF | COMEX金 | 2% | $100K |
| 纳指100 | ^NDXT | TLT ETF | COMEX金 | 2% | $100K |

### A股组

| 组别 | 股票(25%) | 债券(25%) | 黄金(25%) | 现金(25%) | 本金 |
|------|----------|----------|----------|----------|------|
| 沪深300 | 000300.SH | 固定3% | 沪金AU.SHF | 2% | ¥100万 |
| 上证50 | 000016.SH | 固定3% | 沪金AU.SHF | 2% | ¥100万 |
| 中证500 | 000905.SH | 固定3% | 沪金AU.SHF | 2% | ¥100万 |
| 中证1000 | 000852.SH | 固定3% | 沪金AU.SHF | 2% | ¥100万 |
| 中证2000 | 000932.SH | 固定3% | 沪金AU.SHF | 2% | ¥100万 |
| 创业板指 | 399006.SZ | 固定3% | 沪金AU.SHF | 2% | ¥100万 |
| 科创50 | 000688.SH | 固定3% | 沪金AU.SHF | 2% | ¥100万 |
| 中证红利 | 000922.SH | 固定3% | 沪金AU.SHF | 2% | ¥100万 |
| 红利低波 | H30269.CSI | 固定3% | 沪金AU.SHF | 2% | ¥100万 |

---

## 📈 核心结果

```
排名  组别       累计收益    年化     回撤     夏普
─────────────────────────────────────────────────────
 1    纳指100    +174.9%   10.2%   20.5%   0.80
 2    标普500    +168.8%    8.4%   15.4%   0.76
 3    创业板指   +112.0%   11.0%   12.0%   0.91
 4    中证500    + 86.7%    8.4%   12.3%   0.75
 5    红利低波   + 80.9%    7.2%    9.2%   0.72   ←回撤最低
 6    中证2000   + 77.1%    6.2%   11.3%   0.53
 7    沪深300    + 76.7%    7.4%   10.7%   0.70
 8    中证红利   + 75.7%    7.0%   10.2%   0.68
 9    上证50     + 70.6%    6.8%   11.2%   0.63
10    中证1000   + 58.4%    9.3%   11.2%   0.80
11    科创50     + 54.1%   15.2%   10.8%   1.17   ←夏普最高
```

### 关键发现

1. **所有11组在任何入场点至今均为正收益** — 验证了永久组合"什么时候入场都行"的特性
2. **A股永久组合全部有效** — 9个A股指数平均累计+76%，64%入场点跑赢纯股票
3. **红利低波回撤控制第一** — 仅9.23%，受益于低波动股票天然的防御属性
4. **科创50夏普最高**（1.17）— 但样本期短（2020年起），需谨慎解读
5. **中国组回撤显著优于美股** — A股均值11.2% vs 美股17.9%，固定利率债券提供稳定锚

---

## 📁 目录结构

```
永久投资组合研究/
├── README.md                          # 本文件
├── 研究计划.md                        # 原始研究计划
├── data/
│   ├── raw/                           # 原始采集数据（CSV）
│   │   ├── sp500_tr.csv              # 标普500全收益（yfinance）
│   │   ├── nasdaq100_tr.csv          # 纳指100全收益（yfinance）
│   │   ├── tlt.csv                   # TLT ETF（yfinance）
│   │   ├── gold_usd.csv              # COMEX金（yfinance）
│   │   ├── hs300.csv                 # 沪深300（akshare）
│   │   ├── 000016_SH.csv             # 上证50（akshare）
│   │   ├── 000905_SH.csv             # 中证500（akshare）
│   │   ├── 000852_SH.csv             # 中证1000（akshare）
│   │   ├── 000932_SH.csv             # 中证2000（akshare）
│   │   ├── 000922_SH.csv             # 中证红利（akshare）
│   │   ├── H30269_CSI.csv            # 红利低波（Tushare）
│   │   ├── au_shf.csv                # 沪金（MySQL已有）
│   │   └── us_index.csv              # 美股指数合并
│   └── processed/                    # 对齐后数据
│       ├── us_sp500_daily.csv        # 美股标普组对齐
│       ├── us_nasdaq_daily.csv       # 美股纳指组对齐
│       └── cn_daily.csv              # 中国组对齐
├── results/                          # 回测结果
│   ├── result_sp500.csv             # 标普500组（5,646入场点）
│   ├── result_nasdaq.csv            # 纳指100组（4,856入场点）
│   ├── result_china.csv             # 沪深300组（3,952入场点）
│   ├── result_china_000016_SH.csv   # 上证50组（3,952入场点）
│   ├── result_china_000905_SH.csv   # 中证500组
│   ├── result_china_000852_SH.csv   # 中证1000组
│   ├── result_china_000932_SH.csv   # 中证2000组
│   ├── result_china_399006_SZ.csv   # 创业板指组
│   ├── result_china_000688_SH.csv   # 科创50组（1,282入场点）
│   ├── result_china_000922_SH.csv   # 中证红利组
│   ├── result_china_H30269_CSI.csv  # 红利低波组
│   └── summary_statistics.csv       # 11组汇总对比
├── charts/                           # 可视化图表
│   ├── distribution_compare.png     # 收益分布对比
│   ├── return_bar_compare.png       # 累计收益柱状图
│   ├── sharpe_compare.png           # 夏普比率对比
│   └── risk_return_scatter.png      # 风险-收益散点图
├── reports/
│   └── 统计分析报告.md               # 完整分析报告
├── scripts/                          # 回测与处理脚本
│   ├── backtest_full.py             # 完整回测引擎（原始版）
│   ├── backtest_continue.py         # 延续脚本
│   ├── run_single.py                # 单组回测脚本
│   ├── china_backtest.py            # 中国组通用回测（指数参数化）
│   ├── analyze_results.py           # 结果分析（旧版）
│   ├── gen_summary_11.py            # 11组汇总生成
│   ├── generate_charts.py           # 图表生成（旧版）
│   ├── gen_charts_11.py             # 11组图表生成
│   ├── fetch_000922.py              # 中证红利采集
│   ├── save_h30269.py               # 红利低波采集
│   ├── fetch_dividend_indices.py    # 综合采集脚本
│   ├── import_to_mysql.py           # MySQL入库
│   └── prepare_data.py              # 数据清洗对齐
└── logs/                             # 运行日志
```

---

## 🛠 快速复现

```bash
# 1. 数据准备（已入库MySQL）
# 2. 运行单组回测
python3 scripts/china_backtest.py 000300.SH

# 3. 同时跑多个（并行）
python3 scripts/china_backtest.py 000016.SH &
python3 scripts/china_backtest.py 000905.SH &

# 4. 生成汇总
python3 scripts/gen_summary_11.py

# 5. 生成图表
python3 scripts/gen_charts_11.py
```
