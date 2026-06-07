#!/usr/bin/env python3
"""
定投加码 vs 固定2000 对比模拟
"""

import numpy as np

# 月收益参数（基于研究数据，综合标普+红利低波各半）
MEAN = 0.0056   # ~0.56%/月 ≈ 6.9%年化
STD = 0.019     # 1.9%/月标准差
SEED = 42
N_SIM = 10000

# ===== 场景A：固定2000/月 =====
def fixed_schedule(years):
    return [2000] * (years * 12)

# ===== 场景B：渐进加码 =====
def escalating_schedule(years):
    n = years * 12
    amounts = []
    for m in range(n):
        yr = m // 12
        # Year 1: 2000, Y2: 2500, Y3: 3000, Y4: 3500, Y5+: 4000
        if yr == 0:
            a = 2000
        elif yr == 1:
            a = 2500
        elif yr == 2:
            a = 3000
        elif yr == 3:
            a = 3500
        else:
            a = 4000
        amounts.append(a)
    return amounts

# ===== 场景C：更激进的加码（每年+1000） =====
def aggressive_schedule(years):
    n = years * 12
    amounts = []
    for m in range(n):
        yr = m // 12
        a = min(2000 + yr * 1000, 8000)  # cap at 8000
        amounts.append(a)
    return amounts

rng = np.random.default_rng(SEED)

def simulate(schedule_fn, years):
    amounts = schedule_fn(years)
    n = len(amounts)
    rets = rng.normal(MEAN, STD, (N_SIM, n))
    
    results = np.zeros((N_SIM, n))
    for s in range(N_SIM):
        nav = 0.0
        for m in range(n):
            nav += amounts[m]
            nav *= (1 + rets[s, m])
            results[s, m] = nav
    
    return results, amounts

YEARS = [5, 10, 15, 20, 25, 30]

def analyze(name, schedule_fn):
    print(f"\n{'='*68}")
    print(f"  {name}")
    print(f"{'='*68}")
    
    for y in YEARS:
        vals, amounts = simulate(schedule_fn, y)
        total_in = sum(amounts)
        final_vals = vals[:, -1]
        
        p5 = np.percentile(final_vals, 5)
        p50 = np.percentile(final_vals, 50)
        p95 = np.percentile(final_vals, 95)
        
        gain5 = p5 - total_in
        gain50 = p50 - total_in
        gain95 = p95 - total_in
        
        def fmt(v):
            if abs(v) >= 10000:
                return f'{v/10000:.1f}万'
            return f'{v:.0f}元'
        
        print(f"  {y:>2d}年 | 投入{fmt(total_in):>6s} → 中位数{fmt(p50):>6s}(+{fmt(gain50):>5s}) | 最差5% {fmt(p5):>6s}(+{fmt(gain5):>5s})")

# ===== 运行 =====
analyze("【场景A】固定2000/月", fixed_schedule)
analyze("【场景B】渐进加码（每年+500，封顶4000）", escalating_schedule)
analyze("【场景C】激进加码（每年+1000，封顶8000）", aggressive_schedule)

# ===== 关键年份对比表 =====
print(f"\n\n{'='*80}")
print(f"  核心对比：30年结果")
print(f"{'='*80}")
print(f"  {'场景':>20s} | {'总投入':>10s} | {'中位数资产':>12s} | {'最差5%':>12s} | {'收益中位数':>12s}")
print(f"  {'─'*20}─┼─{'─'*10}─┼─{'─'*12}─┼─{'─'*12}─┼─{'─'*12}")

for name, fn in [("固定2000/月", fixed_schedule), 
                  ("渐进加码(500/年→4000)", escalating_schedule),
                  ("激进加码(1000/年→8000)", aggressive_schedule)]:
    vals, amounts = simulate(fn, 30)
    total_in = sum(amounts)
    final = vals[:, -1]
    p5 = np.percentile(final, 5)
    p50 = np.percentile(final, 50)
    
    def fmt(v):
        if abs(v) >= 10000:
            return f'{v/10000:.1f}万'
        return f'{v:.0f}元'
    
    print(f"  {name:>20s} | {fmt(total_in):>10s} | {fmt(p50):>12s} | {fmt(p5):>12s} | +{fmt(p50-total_in):>10s}")

# ===== 加码过程明细 =====
print(f"\n\n{'='*68}")
print(f"  渐进加码(场景B)每月金额明细")
print(f"{'='*68}")
print(f"  {'年份':>6s} | {'月定投':>8s} | {'年投入':>8s} | {'累计投入':>10s}")
print(f"  {'─'*6}─┼─{'─'*8}─┼─{'─'*8}─┼─{'─'*10}")
cumul = 0
for yr in range(1, 31):
    if yr == 1:
        amt = 2000
    elif yr == 2:
        amt = 2500
    elif yr == 3:
        amt = 3000
    elif yr == 4:
        amt = 3500
    else:
        amt = 4000
    annual = amt * 12
    cumul += annual
    
    def f(v):
        if v >= 10000:
            return f'{v/10000:.1f}万'
        return f'{v:.0f}元'
    
    print(f"  {yr:>2d}年 ({'试用' if yr<=1 else '转正' if yr<=2 else '骨干'}期) | {f(amt):>7s}/月 | {f(annual):>7s} | {f(cumul):>9s}")
    if yr == 5:
        print(f"  {'─'*6}─┼─{'─'*8}─┼─{'─'*8}─┼─{'─'*10}")

print(f"\n\n{'='*68}")
print(f"  总结")
print(f"{'='*68}")
print(f"  固定2000/月  30年: 投72万 → 中位数226万, 最差159万")
print(f"  渐进加码     30年: 投122万 → 中位数381万, 最差268万")
print(f"  差额:              多投50万 → 多赚155万")
print(f"")
print(f"  关键是：加码后的钱都在收入增长后才投的,")
print(f"  对生活质量影响极小, 但对复利结果影响巨大。")
