# -*- coding: utf-8 -*-
"""v0.4 双翼快拆 —— 文档口径统一核算（02/03/05/10/14 章全部取数来源）"""
import math

g = 9.81
m_dp = 12.93          # 设计点 MTOW
m_bom = 12.54         # BOM 随飞件累加
W_dp = m_dp * g
W_bom = m_bom * g
rho_h = 0.933         # 2750 m
rho_c = 0.98          # 巡航平均 2200 m
rho_t = 1.024         # 目标区 2050 m

print("=== ① 质量 ===")
print(f"设计点 {m_dp} kg -> W = {W_dp:.1f} N")
print(f"BOM 随飞件 {m_bom} kg（+F9P {m_bom+0.08:.2f}）   余量 {m_dp-m_bom:.2f} kg")
print(f"静推力 160 N: BOM T/W = {160/W_bom:.3f} | 设计点 T/W = {160/W_dp:.3f}")
print(f"2750m 可用推力 ~134 N: 设计点 T/W = {134/W_dp:.3f}")
print()

print("=== ② 倒拖悬停（4x13\" 桨） ===")
R = 0.1651
A4 = 4 * math.pi * R * R
for m, tag in [(12.55, 'v0.3'), (m_dp, 'v0.4')]:
    W = m * g
    vi = math.sqrt(W / (2 * rho_h * A4))
    P_id = W * vi
    P_sh = P_id / 0.70
    P_el = P_sh / 0.845
    print(f"{tag} m={m} vi={vi:.2f} m/s  P_ideal={P_id:.0f} W  P_shaft={P_sh:.0f}  P_elec={P_el:.0f} W")
print(f"A4 = {A4:.4f} m^2")
print()

print("=== ③ 双翼等效与失速 ===")
S = 0.63
b_up, b_lo, gap = 1.5, 1.4, 0.35
b_avg = (b_up + b_lo) / 2
k_munk = 1.10                       # h/b_avg = 0.241 -> Munk 展因子
b_eq = b_avg * k_munk
AR_eq = b_eq ** 2 / S
print(f"b_avg={b_avg:.3f}  k={k_munk}  b_eq={b_eq:.3f} m  AR_eq={AR_eq:.2f} (单翼 AR 6.35)")
for cl in (1.20, 1.15):
    vs = math.sqrt(2 * W_dp / (rho_h * S * cl))
    print(f"  Cl_max={cl:.2f} -> Vs = {vs:.2f} m/s ({vs*3.6:.0f} km/h) | 1.1Vs={1.1*vs:.1f} | 1.25Vs={1.25*vs:.1f}")
print()

print("=== ④ 巡航 / 盘旋 功率 ===")
e_o = 0.85
k_ind = 1 / (math.pi * AR_eq * e_o)
print(f"k_ind = {k_ind:.4f} (单翼 0.0589 -> x{k_ind/0.0589:.2f})")
CD0 = 0.032
# 巡航 28 m/s
V = 28.0
Cl = 2 * W_dp / (rho_c * V * V * S)
CD = CD0 + k_ind * Cl ** 2
LD = Cl / CD
D = W_dp / LD
P_th = D * V
P_el = P_th / 0.66 / 0.85 + 60
print(f"巡航 28 m/s: Cl={Cl:.3f} CD={CD:.4f} L/D={LD:.2f} D={D:.2f} N  P_th={P_th:.0f} W  P_el={P_el:.0f} W")
# 盘旋 23 m/s n=1.064
Vt = 23.0
n = 1.064
Clt = n * 2 * W_dp / (rho_t * Vt * Vt * S)
CDt = CD0 + k_ind * Clt ** 2
LDt = Clt / CDt
Dt = n * W_dp / LDt
P_tht = Dt * Vt
P_elt = P_tht / 0.65 / 0.85 + 60
print(f"盘旋 23 m/s: Cl={Clt:.3f} CD={CDt:.4f} L/D={LDt:.2f} D={Dt:.2f} N  P_th={P_tht:.0f} W  P_el={P_elt:.0f} W")
print()

print("=== ⑤ 无动力改平（关机 150 m） ===")
Vf = 1.25 * 19.0
h_acc = Vf ** 2 / (2 * g)
R_fl = Vf ** 2 / (g * (2.0 - 1))
h_fl = R_fl
print(f"改平触发 V={Vf:.1f} m/s | 增速掉高 {h_acc:.1f} m | 2.0g 半径 {R_fl:.1f} m -> 掉高 {h_fl:.1f} m")
print(f"双翼阻力多耗 ~4 m -> 总掉高 {h_acc + h_fl + 4:.0f} m | 150 m 关机净高 {150 - h_acc - h_fl - 4:.0f} m")
print()

print("=== ⑥ 任务能量预算（12S4P 778 Wh x 80% = 622 Wh） ===")
P_hov_climb = 3050
P_cruise = 750
P_loiter = 640
seg = [
    ("P1 倒拖爬升 0->150 m", 45, P_hov_climb),
    ("P2 关机/俯冲/撑开/拉平", 25, 200),
    ("P3 爬升至巡航高度", 70, 1030),
    ("P4 去程巡航 25 km", 893, P_cruise),
    ("P6 返航 25 km + 爬升 950 m", 893, P_cruise + 113),  # 28 Wh/893s = 113 W
]
for loit_min in (10, 5):
    segs = seg[:4] + [("P5 目标区盘旋", loit_min * 60, P_loiter)] + seg[4:] + [("P7 迫降", 60, 200)]
    tot = sum(t * p for _, t, p in segs) / 3600
    print(f"盘旋 {loit_min} min -> 合计 {tot:.0f} Wh | 622 Wh 可用 | 余量 {622-tot:.0f} Wh ({(622-tot)/622*100:.0f}%)")
    for nm, t, p in segs:
        print(f"   {nm:28s} {t:5d} s {p:5d} W {t*p/3600:6.1f} Wh")
print()
wh_per_km = 893 * P_cruise / 3600 / 25
print(f"巡航能耗 {wh_per_km:.2f} Wh/km (v0.3 {893*600/3600/25:.2f}) -> 航程比 {600/P_cruise:.2f}")
print(f"最大航程 78 km x {600/P_cruise:.2f} = {78*600/P_cruise:.0f} km")
