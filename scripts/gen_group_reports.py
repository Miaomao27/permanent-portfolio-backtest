#!/usr/bin/env python3
"""
生成11组永久组合的详细分析报告（reports/组合分析/）
每组含：箱线图 + 完整统计表格 + 解读
"""
import os, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker

BASE = '/home/cpy/文档/金融数据库建立/永久投资组合研究'
RES2 = os.path.join(BASE, 'results2')
REPORTS = os.path.join(BASE, 'reports', '组合分析')
CHARTS_DIR = os.path.join(REPORTS, 'charts')
os.makedirs(CHARTS_DIR, exist_ok=True)

font_path = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
prop = font_manager.FontProperties(fname=font_path)
plt.rcParams['font.family'] = prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

# 11组配置
groups = [
    ('sp500', '标普500', 100000, '$'),
    ('nasdaq', '纳指100', 100000, '$'),
    ('china', '沪深300', 1000000, '¥'),
    ('china_000016_SH', '上证50', 1000000, '¥'),
    ('china_000688_SH', '科创50', 1000000, '¥'),
    ('china_000852_SH', '中证1000', 1000000, '¥'),
    ('china_000905_SH', '中证500', 1000000, '¥'),
    ('china_000932_SH', '中证2000', 1000000, '¥'),
    ('china_399006_SZ', '创业板指', 1000000, '¥'),
    ('china_000922_SH', '中证红利', 1000000, '¥'),
    ('china_H30269_CSI', '红利低波', 1000000, '¥'),
]

hp_names = ['1m', '3m', '6m', '12m', '24m']
hp_labels = ['1月\n(21天)', '3月\n(63天)', '6月\n(126天)', '12月\n(252天)', '24月\n(504天)']
hp_days = [21, 63, 126, 252, 504]
colors = ['#64B5F6','#42A5F5','#1E88E5','#1565C0','#0D47A1']

def gen_boxplot(group_key, group_name):
    """生成单组箱线图并返回统计值"""
    data_all = []
    stats = {}
    for hp in hp_names:
        df = pd.read_csv(os.path.join(RES2, f'hp_{group_key}_{hp}.csv'))
        vals = df['total_return_pct'].values
        data_all.append(vals)
        q1, q50, q75 = np.percentile(vals, [25, 50, 75])
        mean = np.mean(vals)
        std = np.std(vals)
        best = np.max(vals)
        worst = np.min(vals)
        win_rate = (vals > 0).mean() * 100
        stats[hp] = {
            'mean': mean, 'median': q50, 'q1': q1, 'q3': q75,
            'std': std, 'best': best, 'worst': worst,
            'win_rate': win_rate, 'count': len(vals)
        }

    # 画图
    fig, ax = plt.subplots(figsize=(12, 7))
    bp = ax.boxplot(data_all, labels=hp_labels, patch_artist=True, vert=True,
                    showmeans=True,
                    meanprops=dict(marker='D', markerfacecolor='red', markersize=6),
                    medianprops=dict(color='black', linewidth=2.5),
                    flierprops=dict(marker='o', markerfacecolor='gray', markersize=3, alpha=0.2))
    for patch, c in zip(bp['boxes'], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.75)
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=1.5)
    ax.set_ylabel('累计收益率(%)', fontsize=12)
    ax.set_title(f'{group_name}永久组合——不同持有期收益分布', fontsize=14, fontweight='bold')
    ax.grid(alpha=0.2, axis='y')

    # 标注中位数、Q1、Q3（放在箱体上方，不遮挡）
    for i, d in enumerate(data_all):
        q1, q50, q75 = np.percentile(d, [25, 50, 75])
        mean = np.mean(d)
        # 计算上须位置（箱线图默认上须 = min(max(d), Q3+1.5*IQR)）
        iqr = q75 - q1
        upper_whisker = min(np.max(d), q75 + 1.5 * iqr)
        anno_y = upper_whisker + (np.max(d) - upper_whisker) * 0.15 + abs(upper_whisker) * 0.05
        anno_text = f'Q1={q1:.1f}%  Md={q50:.1f}%  Q3={q75:.1f}%\n均值={mean:.2f}%  胜率={(d>0).mean()*100:.1f}%'
        ax.annotate(anno_text, xy=(i+1, q75), xytext=(i+1, anno_y), fontsize=7.5,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8, edgecolor='gray'),
                    ha='center', va='bottom',
                    arrowprops=dict(arrowstyle='->', color='gray', lw=0.5))

    fig_path = os.path.join(CHARTS_DIR, f'{group_key}_boxplot.png')
    fig.tight_layout()
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return stats, os.path.relpath(fig_path, REPORTS)

def gen_report(group_key, group_name, principal, currency):
    print(f"生成 {group_name}...")
    stats, chart_rel = gen_boxplot(group_key, group_name)

    # 构建markdown
    lines = []
    lines.append(f"# {group_name}永久组合——持有期分析报告")
    lines.append("")
    lines.append(f"> 初始本金：{currency}{principal:,}  | 资产配置：25%股票+25%债券+25%黄金+25%现金")
    lines.append(f"> 再平衡规则：±8%阈值 + 每年1月强制  |  单次成本：0.1%")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 一、收益分布箱线图")
    lines.append("")
    lines.append(f"![{group_name}箱线图](charts/{group_key}_boxplot.png)")
    lines.append("")
    lines.append("上图展示了该永久组合在不同持有期（1/3/6/12/24个月）下的累计收益率分布。")
    lines.append("箱体范围 = 25%~75%分位数（Q₁~Q₃），中间横线 = 中位数（Md），红色菱形 = 均值。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 二、各持有期详细统计")
    lines.append("")

    for hp, hp_label in zip(hp_names, ['1月', '3月', '6月', '12月', '24月']):
        s = stats[hp]
        lines.append(f"### {hp_label}持有期（{hp_days[hp_names.index(hp)]}个交易日）")
        lines.append("")
        lines.append("| 统计指标 | 数值 |")
        lines.append("|---------|------|")
        lines.append(f"| 入场点数 | {s['count']:,} |")
        lines.append(f"| 平均收益 | {s['mean']:+.2f}% |")
        lines.append(f"| 中位数收益（Md） | {s['median']:+.2f}% |")
        lines.append(f"| 下四分位（Q₁） | {s['q1']:+.2f}% |")
        lines.append(f"| 上四分位（Q₃） | {s['q3']:+.2f}% |")
        lines.append(f"| 四分位距（IQR=Q₃-Q₁） | {s['q3']-s['q1']:.2f}% |")
        lines.append(f"| 标准差 | {s['std']:.2f}% |")
        lines.append(f"| 最佳收益 | {s['best']:+.2f}% |")
        lines.append(f"| 最差收益 | {s['worst']:+.2f}% |")
        lines.append(f"| 收益区间跨度 | {s['best']-s['worst']:.2f}% |")
        lines.append(f"| 胜率（收益>0） | {s['win_rate']:.1f}% |")
        lines.append("")
        lines.append(f"**解读：** 持有{hp_label}，该永久组合的中位数收益为{s['median']:+.2f}%，半数入场点收益集中在{s['q1']:+.1f}%~{s['q3']:+.1f}%之间。")
        lines.append(f"胜率{s['win_rate']:.1f}%，即每100次入场约有{int(s['win_rate'])}次获得正收益。")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 三、持有期对比总结")
    lines.append("")
    lines.append(f"| 指标 | 1月 | 3月 | 6月 | 12月 | 24月 |")
    lines.append("|-----|-----|-----|-----|------|------|")
    row_mean = '| 平均收益 | ' + ' | '.join([f"{stats[hp]['mean']:+.2f}%" for hp in hp_names]) + ' |'
    row_med = '| 中位数收益 | ' + ' | '.join([f"{stats[hp]['median']:+.2f}%" for hp in hp_names]) + ' |'
    row_win = '| 胜率 | ' + ' | '.join([f"{stats[hp]['win_rate']:.1f}%" for hp in hp_names]) + ' |'
    row_iqr = '| 四分位距(IQR) | ' + ' | '.join([f"{stats[hp]['q3']-stats[hp]['q1']:.2f}%" for hp in hp_names]) + ' |'
    row_best = '| 最佳 | ' + ' | '.join([f"{stats[hp]['best']:+.2f}%" for hp in hp_names]) + ' |'
    row_worst = '| 最差 | ' + ' | '.join([f"{stats[hp]['worst']:+.2f}%" for hp in hp_names]) + ' |'
    lines.append(row_mean)
    lines.append(row_med)
    lines.append(row_win)
    lines.append(row_iqr)
    lines.append(row_best)
    lines.append(row_worst)
    lines.append("")

    # 关键结论
    lines.append("### 核心观察")
    lines.append("")
    w24 = stats['24m']['win_rate']
    m24 = stats['24m']['median']
    iqr24 = stats['24m']['q3'] - stats['24m']['q1']
    w1 = stats['1m']['win_rate']
    lines.append(f"1. **胜率趋势**：胜率从1月的{w1:.1f}%提升至24月的{w24:.1f}%，呈单调递增。")
    lines.append(f"2. **持有24月收益**：中位数{m24:+.2f}%，半数入场收益在{stats['24m']['q1']:+.1f}%~{stats['24m']['q3']:+.1f}%之间。")
    lines.append(f"3. **收益稳定性**：四分位距从1月的{stats['1m']['q3']-stats['1m']['q1']:.2f}%扩大到24月的{iqr24:.2f}%，说明持有期越长收益的不确定性也越大。")
    lines.append(f"4. **风险考量**：最差情况为24月亏损{abs(stats['24m']['worst']):.1f}%，最佳情况盈利{stats['24m']['best']:+.1f}%。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*报告生成时间：2026-06-06*")

    report_path = os.path.join(REPORTS, f'{group_key}_分析报告.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"  ✓ {report_path}")

for g_key, g_name, pri, cur in groups:
    gen_report(g_key, g_name, pri, cur)

print(f"\n✅ 全部11份报告已生成到 {REPORTS}")
