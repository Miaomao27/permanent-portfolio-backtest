#!/usr/bin/env python3
# 精确到各年龄的数据

import numpy as np

MEAN = 0.0056
STD = 0.019
N_SIM = 10000
SEED = 42

rng = np.random.default_rng(SEED)

def amounts_for_year(yr):
    if yr == 1: return 2000
    elif yr == 2: return 2500
    elif yr == 3: return 3000
    elif yr == 4: return 3500
    else: return 4000

# 每个年龄（从26到76）对应的年限
ages_to_years = {age: age - 26 for age in range(26, 77, 1)}
# 用户特别关心的年龄
key_ages = [30, 35, 40, 45, 50, 55, 60, 65, 70, 76]

max_years = 50
rets = rng.normal(MEAN, STD, (N_SIM, max_years * 12))

def simulate_months(n_months):
    amounts = [amounts_for_year(m//12 + 1) for m in range(n_months)]
    total_in = sum(amounts)
    
    navs = np.zeros(N_SIM)
    for s in range(N_SIM):
        nav = 0.0
        for m in range(n_months):
            nav += amounts[m]
            nav *= (1 + rets[s, m])
        navs[s] = nav
    
    return total_in, navs

def fmt(v):
    if abs(v) >= 10000:
        if v >= 10000000: return f'{v/1000000:.2f}千万'
        return f'{v/10000:.0f}万'
    return f'{v:.0f}元'

print(f"{'='*70}")
print(f"  渐进加码定投：按实际年龄")
print(f"  26岁开始，2000→4000/月，第5年起封顶")
print(f"{'='*70}")
print(f"")
print(f"  {'年龄':>4s} │ {'年限':>4s} │ {'累计投入':>10s} │ {'中位数资产':>12s} │ {'最差5%':>12s} │ {'最好5%':>12s}")
print(f"  {'────':>4s}─┼─{'────':>4s}─┼─{'──────────':>10s}─┼─{'────────────':>12s}─┼─{'────────────':>12s}─┼─{'────────────':>12s}")

for age in key_ages:
    years = age - 26
    if years <= 0: continue
    n = years * 12
    total_in, navs = simulate_months(n)
    p5 = np.percentile(navs, 5)
    p50 = np.percentile(navs, 50)
    p95 = np.percentile(navs, 95)
    
    print(f"  {age:>4d}岁 │ {years:>4d}年 │ {fmt(total_in):>10s} │ {fmt(p50):>12s} │ {fmt(p5):>12s} │ {fmt(p95):>12s}")

print(f"\n{'='*70}")
print(f"  你问的50岁：")
print(f"{'='*70}")

total_in, navs = simulate_months(24 * 12)
p5 = np.percentile(navs, 5)
p50 = np.percentile(navs, 50)
p95 = np.percentile(navs, 95)
print(f"")
print(f"  50岁时（定投24年）：")
print(f"    累计投入：  {fmt(total_in):>10s}")
print(f"    中位数资产：{fmt(p50):>10s}  (投入的{p50/total_in:.1f}倍)")
print(f"    最差也有：  {fmt(p5):>10s}  (投入的{p5/total_in:.1f}倍)")
print(f"    好则：      {fmt(p95):>10s}")
print(f"")
print(f"  其实50岁时资产已经相当可观了，")
print(f"  因为最后10年（40→50岁）是复利加速最快的阶段。")
