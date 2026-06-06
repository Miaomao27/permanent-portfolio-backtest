# Permanent Portfolio Daily Backtest — China A-Share & US Markets

> A comprehensive validation of Harry Browne's Permanent Portfolio (25% stocks + 25% long-term bonds + 25% gold + 25% cash) across different markets and entry timings.
>
> **📄 Research paper:** [reports/research_paper.md](reports/research_paper.md) (Chinese, with academic references)
> **📖 中文版:** [README_ZH.md](README_ZH.md)

---

## 📊 Overview

| Item | Details |
|------|---------|
| Backtest period | 2003-01 ~ 2026-06 (23 years) |
| Portfolio groups | **11 total** (2 US + 9 China A-share indices) |
| Entry points tested | ~40,000+ independent entry dates |
| Rebalance rule | ±8% threshold trigger + annual forced reset |
| Trading cost | 0.1% per rebalance |
| Data sources | Yahoo Finance (US) / akshare + Tushare (China) / MySQL (existing) |

### US Portfolio Groups

| Group | Stocks (25%) | Bonds (25%) | Gold (25%) | Cash (25%) | Principal |
|-------|-------------|-------------|------------|------------|-----------|
| S&P 500 | ^SP500TR (Total Return) | TLT ETF | COMEX Gold | 2% p.a. | $100K |
| Nasdaq 100 | ^NDXT (Total Return) | TLT ETF | COMEX Gold | 2% p.a. | $100K |

### China A-Share Portfolio Groups

| Group | Stocks (25%) | Bonds (25%) | Gold (25%) | Cash (25%) | Principal |
|-------|-------------|-------------|------------|------------|-----------|
| CSI 300 | 000300.SH | Fixed 3% | AU.SHF | 2% p.a. | ¥1M |
| SSE 50 | 000016.SH | Fixed 3% | AU.SHF | 2% p.a. | ¥1M |
| CSI 500 | 000905.SH | Fixed 3% | AU.SHF | 2% p.a. | ¥1M |
| CSI 1000 | 000852.SH | Fixed 3% | AU.SHF | 2% p.a. | ¥1M |
| CSI 2000 | 000932.SH | Fixed 3% | AU.SHF | 2% p.a. | ¥1M |
| ChiNext | 399006.SZ | Fixed 3% | AU.SHF | 2% p.a. | ¥1M |
| STAR 50 | 000688.SH | Fixed 3% | AU.SHF | 2% p.a. | ¥1M |
| CSI Dividend | 000922.SH | Fixed 3% | AU.SHF | 2% p.a. | ¥1M |
| Low Vol Dividend | H30269.CSI | Fixed 3% | AU.SHF | 2% p.a. | ¥1M |

---

## 📈 Core Results

```
Rank  Group            Return     CAGR    MaxDD   Sharpe
───────────────────────────────────────────────────────────
 1    Nasdaq 100      +174.9%   10.2%   20.5%    0.80
 2    S&P 500         +168.8%    8.4%   15.4%    0.76
 3    ChiNext         +112.0%   11.0%   12.0%    0.91
 4    CSI 500          +86.7%    8.4%   12.3%    0.75
 5    Low Vol Div      +80.9%    7.2%    9.2%    0.72  ← lowest drawdown
 6    CSI 2000         +77.1%    6.2%   11.3%    0.53
 7    CSI 300          +76.7%    7.4%   10.7%    0.70
 8    CSI Dividend     +75.7%    7.0%   10.2%    0.68
 9    SSE 50           +70.6%    6.8%   11.2%    0.63
10    CSI 1000         +58.4%    9.3%   11.2%    0.80
11    STAR 50          +54.1%   15.2%   10.8%    1.17  ← best Sharpe
```

### Key Findings

1. **All 11 portfolios delivered positive returns from ANY entry date** — confirming the permanent portfolio's "entry timing doesn't matter" property
2. **The strategy works in China A-shares** — 9 China portfolios averaged +76% cumulative, with 64% of entries beating pure stock holding
3. **Low Vol Dividend has the best drawdown control** (9.23%) — naturally defensive stocks make excellent permanent portfolio components
4. **STAR 50 has the highest Sharpe ratio** (1.17) — but short sample period (since 2020) warrants caution
5. **China groups significantly outperform US in drawdown control** — China avg 11.2% vs US avg 17.9%, thanks to the anchoring effect of fixed-rate bonds

---

## 📊 Visual Summary

### Return Comparison

![Return Bar Chart](charts/return_bar_compare.png)

The bar chart above shows average cumulative returns across all 11 groups. Nasdaq 100 leads at +174.9%, followed by S&P 500 (+168.8%). Among China A-share groups, ChiNext (创业板指) stands out at +112.0% with a drawdown of only 12.0% — roughly half of the US groups' drawdown.

### Risk-Adjusted Performance (Sharpe Ratio)

![Sharpe Ratio Comparison](charts/sharpe_compare.png)

STAR 50 (科创50) achieves the highest Sharpe ratio at 1.17, despite having the lowest absolute return (+54.1%). ChiNext and Nasdaq 100 follow closely. Notably, A-share portfolios deliver competitive risk-adjusted returns versus their US counterparts.

### Risk-Return Profile

![Risk-Return Scatter](charts/risk_return_scatter.png)

The scatter plot maps all 11 portfolios on a risk-return plane (annual return vs. max drawdown, colored by Sharpe ratio). The ideal location is the upper-left corner (high return, low drawdown, high Sharpe). Key observations:
- **ChiNext** and **Low Vol Dividend** occupy the premium zone (high Sharpe + low drawdown)
- **US groups** deliver higher absolute returns but with significantly larger drawdowns (right side)
- **CSI 300** and **CSI Dividend** sit in the balanced middle ground

### Distribution of Returns Across Entry Points

![Return Distribution](charts/distribution_compare.png)

All portfolios show right-skewed return distributions — most entry points cluster around the median with a long tail of high returns from early entries (post-crisis bottoms of 2003/2009).

---

## 📁 Directory Structure

```
permanent-portfolio-backtest/
├── README.md                          # This file
├── README_ZH.md                       # Chinese version
├── research_plan.md                   # Original research plan
├── data/
│   ├── raw/                           # Raw collected data (CSV)
│   │   ├── sp500_tr.csv              # S&P 500 Total Return
│   │   ├── nasdaq100_tr.csv          # Nasdaq 100 Total Return
│   │   ├── tlt.csv                   # TLT ETF
│   │   ├── gold_usd.csv              # COMEX Gold
│   │   ├── hs300.csv                 # CSI 300
│   │   ├── 000016_SH.csv             # SSE 50
│   │   ├── 000905_SH.csv             # CSI 500
│   │   ├── 000852_SH.csv             # CSI 1000
│   │   ├── 000932_SH.csv             # CSI 2000
│   │   ├── 000922_SH.csv             # CSI Dividend
│   │   └── H30269_CSI.csv            # Low Vol Dividend
│   └── processed/                    # Aligned price data
│       ├── us_sp500_daily.csv        # US S&P-aligned
│       ├── us_nasdaq_daily.csv       # US Nasdaq-aligned
│       └── cn_daily.csv              # China-aligned
├── results/                          # Backtest results
│   ├── result_sp500.csv             # S&P 500 (5,646 entries)
│   ├── result_nasdaq.csv            # Nasdaq 100 (4,856 entries)
│   ├── result_china.csv             # CSI 300 (3,952 entries)
│   ├── result_china_000016_SH.csv   # SSE 50
│   ├── result_china_000905_SH.csv   # CSI 500
│   ├── result_china_000852_SH.csv   # CSI 1000
│   ├── result_china_000932_SH.csv   # CSI 2000
│   ├── result_china_399006_SZ.csv   # ChiNext
│   ├── result_china_000688_SH.csv   # STAR 50
│   ├── result_china_000922_SH.csv   # CSI Dividend
│   ├── result_china_H30269_CSI.csv  # Low Vol Dividend
│   └── summary_statistics.csv       # Cross-group comparison
├── charts/                           # Visualizations
│   ├── distribution_compare.png     # Return distribution comparison
│   ├── return_bar_compare.png       # Return bar chart
│   ├── sharpe_compare.png           # Sharpe ratio comparison
│   └── risk_return_scatter.png      # Risk-return scatter
├── reports/
│   ├── research_paper.md            # Full research paper (Chinese, 10 references)
│   └── analysis_report.md           # Chinese analysis report
└── scripts/                          # Backtest & analysis scripts
    ├── backtest_full.py             # Original full engine
    ├── run_single.py                # Single-group runner
    ├── china_backtest.py            # Parameterized China backtest
    ├── gen_summary_11.py            # 11-group summary
    ├── gen_charts_11.py             # 11-group charts
    └── ...                          # Data collection scripts
```

---

## 🛠 Quick Reproduce

```bash
# Run a single China index backtest
python3 scripts/china_backtest.py 000300.SH

# Or parallel
python3 scripts/china_backtest.py 000016.SH &
python3 scripts/china_backtest.py 000905.SH &

# Generate summary and charts
python3 scripts/gen_summary_11.py
python3 scripts/gen_charts_11.py
```

---

## 📄 Research Paper

A comprehensive research paper is available at **[reports/research_paper.md](reports/research_paper.md)** (Chinese), covering:
- Introduction and literature review (Browne 1987, Brinson 1986, Fama-French 2015, Liu-Stambaugh-Yuan 2019)
- Data sources and methodology
- Full 11-group backtest results with discussion
- Practical implications for A-share investors
- 10 academic references

---

## 📜 License

This project is for research and educational purposes only. The backtest results do not constitute investment advice. Past performance does not guarantee future returns.
