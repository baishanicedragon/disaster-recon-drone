#!/usr/bin/env python3
# v0.3.1 CG / SM / 摆频 重算
import math

# 桨盘从 v0.3 的 STA1450 移到 v0.3.1 的 STA1550（尾杆最末端）
# 4 桨质量心 ~1550，电机/电调/棘轮也后移
# 电池初始位 STA600，重心位于电池段中心 → STA600（电池 3.7 kg）
parts = [
    # (name, mass_kg, sta_mm)
    ("主承力杆+承力隔框",      0.88, 775),    # 结构
    ("机身碳纤管",             0.48, 700),
    ("二级吸能筒+机头吸能×3",  0.63, 250),
    ("主翼+折叠机构+翼尖滑块",  1.06, 900),   # 主翼 AC ~900
    ("单片水平尾翼",            0.32, 1500),  # 单片水平尾翼
    ("舱盖/打印件+紧固件+腹滑橇", 0.89, 700),  # 含腹滑橇 0.18
    ("4×电机+电调",            1.60, 1500),  # 电机座 STA1500
    ("4×桨+棘轮毂（折叠桨）",  0.50, 1550),  # 桨盘 STA1550
    ("12S4P电池",              3.70, 820),   # 电池段中心 D 段中点（滑轨 600-820 可调）
    ("BMS+内衬",               0.32, 820),
    ("航电（飞控/IMU/GNSS等）", 1.10, 800),
    ("载荷（视觉/相机/毫米波）", 0.72, 750),
    ("线束",                   0.38, 850),
]

tot_m = sum(p[1] for p in parts)
Mx    = sum(p[1]*p[2] for p in parts)
cg    = Mx / tot_m

AC = 900
MAC = 315  # mm
SM  = (cg - AC) / MAC * 100

print(f"总质量 {tot_m:.3f} kg")
print(f"CG = {Mx:.1f} / {tot_m:.3f} = {cg:.1f} mm")
print(f"主翼 AC = {AC} mm, MAC = {MAC} mm")
print(f"SM = (CG-AC)/MAC = {SM:+.2f}%  (目标 +5%~+12%)")

# 倒拖摆：摆长 = 桨盘距 CG 的轴向距离
l_drag = abs(1550 - cg) / 1000  # m
f_hz   = (1/(2*math.pi)) * math.sqrt(9.81 / l_drag)
print(f"\n倒拖摆摆长 (CG→桨盘): {l_drag*1000:.1f} mm = {l_drag:.3f} m")
print(f"摆固有频率 f ≈ {f_hz:.3f} Hz")

# 桨盘载荷
A_total = 4 * math.pi * (0.165**2)   # 4 × 13" 桨盘
DL_hover = (tot_m * 9.81) / A_total
print(f"\n桨盘总面积 (4×13″): {A_total:.4f} m²")
print(f"桨盘载荷 DL 悬停 = {DL_hover:.0f} N/m²")

# 4 桨 X 型 90° 桨心半径校验
R = 0.245
print(f"\n桨心半径 R = {R} m, 外廓 2R = {2*R} m")
print(f"相邻桨心距 = sqrt(2)*R = {math.sqrt(2)*R:.3f} m (需 ≥ 0.347 m)")

# 电机座外伸尺寸校验
# 4 桨桨心位置（绕机身轴线 90° 等角分布）
import math
positions = []
for i, ang_deg in enumerate([0, 90, 180, 270]):
    a = math.radians(ang_deg)
    x = R * math.cos(a)
    y = R * math.sin(a)
    positions.append((i+1, ang_deg, x, y))
print("\n4 桨桨心位置（XY 平面投影，单位 m）：")
for i, ang, x, y in positions:
    print(f"  桨{i} ({ang:3d}°) = ({x:+.3f}, {y:+.3f})  r={math.hypot(x,y):.3f}")