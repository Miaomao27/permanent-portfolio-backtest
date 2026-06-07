#!/usr/bin/env python3
"""
加码定投 × 超长期模拟：35年、40年、45年、50年
"""

import numpy as np

MEAN = 0.0056
STD = 0.019
N_SIM = 10000
SEED = 42

rng = np.random.default_rng(SEED)

def escalating_amount(month):
    """渐进加码：2000→4000，第5年起封顶"""
    yr = month // 12
    if yr == 0:   return 2000
    elif yr == 1: return 2500
    elif yr == 2: return 3000
    elif yr == 3: return 3500
    else:         return 4000

YEARS = [30, 35, 40, 45, 50]
N_MONTHS = max(YEARS) * 12

# 预生成所有随机收益（所有模拟、所有月份）
rets = rng.normal(MEAN, STD, (N_SIM, N_MONTHS))

def simulate(years):
    n = years * 12
    amounts = [escalating_amount(m) for m in range(n)]
    total_in = sum(amounts)
    
    navs = np.zeros(N_SIM)
    for s in range(N_SIM):
        nav = 0.0
        for m in range(n):
            nav += amounts[m]
            nav *= (1 + rets[s, m])
        navs[s] = nav
    
    return total_in, navs

def fmt(v):
    if abs(v) >= 10000:
        return f'{v/10000:.1f}万'
    return f'{v:.0f}元'

print(f"{'='*76}")
print(f"  渐进加码定投模拟（2000→4000/月，第5年起封顶）")
print(f"  {N_SIM:,}次蒙特卡洛模拟")
print(f"{'='*76}")

print(f"\n{'='*76}")
print(f"  {'年限':>4s} │ {'总投入':>10s} │ {'中位数资产':>12s} │ {'最好5%':>12s} │ {'最差5%':>12s} │ {'中位数收益':>12s}")
print(f"  {'────':>4s}─┼─{'──────────':>10s}─┼─{'────────────':>12s}─┼─{'────────────':>12s}─┼─{'────────────':>12s}─┼─{'────────────':>12s}")

for y in YEARS:
    total_in, navs = simulate(y)
    p5 = np.percentile(navs, 5)
    p50 = np.percentile(navs, 50)
    p95 = np.percentile(navs, 95)
    
    print(f"  {y:>4d}年 │ {fmt(total_in):>10s} │ {fmt(p50):>12s} │ {fmt(p95):>12s} │ {fmt(p5):>12s} │ +{fmt(p50-total_in):>10s}")

# 再加一个明细表
print(f"\n\n{'='*76}")
print(f"  超长期趋势解析")
print(f"{'='*76}")
print(f"")

for y in YEARS:
    total_in, navs = simulate(y)
    p5 = np.percentile(navs, 5)
    p50 = np.percentile(navs, 50)
    p95 = np.percentile(navs, 95)
    
    ratio50 = p50 / total_in
    ratio5 = p5 / total_in
    gain50 = p50 - total_in
    gain5 = p5 - total_in
    
    # 简单年化
    ann50 = (p50 / total_in) ** (1/y) - 1
    ann5 = (p5 / total_in) ** (1/y) - 1
    
    age_at_end = 26 + y
    
    print(f"  ╔═══ {y}年后（你{age_at_end}岁）═══╗")
    print(f"  ║")
    print(f"  ║  累计投入:        {fmt(total_in):>10s}")
    print(f"  ║  中位数资产:      {fmt(p50):>10s}  (投入的{ratio50:.1f}倍)")
    print(f"  ║  最差5%资产:      {fmt(p5):>10s}  (投入的{ratio5:.1f}倍)")
    print(f"  ║  最好5%资产:      {fmt(p95):>10s}")
    print(f"  ║  中位数收益:      +{fmt(gain50):>10s}")
    print(f"  ║  最差5%收益:      {fmt(gain5):>10s}  (仍有{'+' if gain5>=0 else ''})")
    print(f"  ║")

# ===== 完整生命周期一览 =====
print(f"\n\n{'='*76}")
print(f"  一生投资台账（渐进加码 2000→4000/月）")
print(f"{'='*76}")
print(f"  {'年龄':>4s} │ {'年份':>6s} │ {'阶段':>10s} │ {'月定投':>8s} │ {'累计投入':>10s} │ {'中位数资产':>12s}")
print(f"  {'────':>4s}─┼─{'──────':>6s}─┼─{'──────────':>10s}─┼─{'────────':>8s}─┼─{'──────────':>10s}─┼─{'────────────':>12s}")

# 每年明细
monthly_by_year = {}
for yr in range(1, 51):
    if yr == 1:       amt = 2000
    elif yr == 2:     amt = 2500
    elif yr == 3:     amt = 3000
    elif yr == 4:     amt = 3500
    else:             amt = 4000
    monthly_by_year[yr] = amt

# 对几个关键年度做模拟
for y in [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]:
    total_in, navs = simulate(y)
    p50 = np.percentile(navs, 50)
    age = 26 + y
    phase = ('职场新人' if y<=3 else '骨干期' if y<=10 else '资深期' if y<=20 else '中年期' if y<=35 else '成熟期')
    amt = monthly_by_year.get(y, 4000)
    
    print(f"  {age:>4d}岁 │ {2026+y:>6d}年 │ {phase:>10s} │ {fmt(amt):>7s}/月 │ {fmt(total_in):>10s} │ {fmt(p50):>12s}")

# 最关键的几个里程碑
print(f"\n\n{'='*76}")
print(f"  里程碑数字")
print(f"{'='*76}")

milestones = [
    (10, "30岁", "第一个百万？"),
    (20, "40岁", "真正的中年底气"),
    (30, "50岁", "提前退休门槛"),
    (40, "60岁", "养老无忧"),
    (50, "70岁", "传给下一代"),
]

for y, label, desc in milestones:
    total_in, navs = simulate(y)
    p50 = np.percentile(navs, 50)
    p5 = np.percentile(navs, 5)
    p95 = np.percentile(navs, 95)
    peak = total_in * 3  # 粗算
    
    print(f"\n  ▸ {label}（{y}年后） — {desc}")
    print(f"    投入: {fmt(total_in):>8s}  →  中位数: {fmt(p50):>8s}  (范围: {fmt(p5)}~{fmt(p95)})")
