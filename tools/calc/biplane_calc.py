# -*- coding: utf-8 -*-
"""v0.4 双翼 + 钻石背/剪刀收拢 基线核算"""
import math
g = 9.81
m = 12.58          # MTOW 起点（不含展开机构）
W = m * g
rho = 0.933        # 2750m 高原
Vc = 28            # 巡航 m/s
S_tot = 0.63       # 总面积锚点（高原失速 19 m/s）

def cruise_P(S, b_eff, cd0=0.028, eta=0.72):
    """粗巡航功率：D_p + D_i(双翼用 b_eff 与干扰因子近似)"""
    Dp = 0.5 * rho * Vc * Vc * S * cd0
    Di = 2 * W * W / (rho * Vc * Vc * math.pi * b_eff * b_eff * 0.82)
    return (Dp + Di) * Vc / eta, Dp, Di

print("=== ① 双翼尺寸档位（面积上0.315+下0.315，半翼≤78cm 入85桶） ===")
rows = []
for b_up, b_lo in [(1.5, 1.4), (1.5, 1.5), (1.6, 1.5), (1.55, 1.45)]:
    # 双翼等效：b_eff = 0.95*min(b_up,b_lo)?? 按两翼平均 展 b~b_up~b_lo，gap≥2c 干扰因子k~1.12
    b_eff = math.sqrt(2) / 2 * (b_up + b_lo) / math.sqrt(2)  # 简化取均
    b_eff = (b_up + b_lo) / 2 * 0.98
    P, Dp, Di = cruise_P(S_tot, b_eff)
    c_up, c_lo = S_tot/2 / b_up, S_tot/2 / b_lo
    hu, hl = b_up/2*1000, b_lo/2*1000
    # 收拢（剪刀单铰：绕翼根竖轴后折 或 钻石背两段折）
    fold_back = max(hu, hl)          # 剪刀后折轴向占用(贴尾方向)
    fold_dia = max(hu, hl) / 2 + 60  # 钻石背两段折占用
    ok_back = '✗' if fold_back > 750 else ('△' if fold_back > 650 else '✓')
    ok_dia = '✓' if fold_dia <= 420 else '△'
    rows.append((b_up, b_lo, c_up*1000, c_lo*1000, hu, hl, P, fold_back, ok_back, fold_dia, ok_dia))
    print(f"上翼b={b_up} 下翼b={b_lo} | 弦 {c_up*1000:.0f}/{c_lo*1000:.0f}mm | 半展 {hu:.0f}/{hl:.0f}mm | "
          f"巡航≈{P:.0f}W | 剪刀后折占用{fold_back:.0f}mm {ok_back} | 钻石背两段折{fold_dia:.0f}mm {ok_dia}")
# 基线对比
P0,_,_ = cruise_P(S_tot, 2.0)
print(f"--- 参照：单翼 b=2.0 巡航≈{P0:.0f}W ---")
print()
print("=== ② 倒拖段（双翼收拢贴体）功率 ===")
A4 = 4*math.pi*0.1651**2
P_hover = W*math.sqrt(W/(2*rho*A4))
print(f"收拢态倒拖悬停≈{P_hover:.0f}W（vs 展开态 4.3kW+）—— 下洗流问题消除 ✓")
print()
print("=== ③ 雨伞撑开质量账 ===")
print("双翼×2 副展开机构(钻石背两段折: 每侧2铰+连杆+弹簧+锁) ≈ +0.35kg")
print("或剪刀单铰(每侧1铰+弹簧+锁, 轴向占用大) ≈ +0.22kg")
print(f"MTOW: 12.58 → 钻石背 {12.58+0.35:.2f}kg / 剪刀 {12.58+0.22:.2f}kg (红线15kg)")
print()
print("=== ④ 无动力改平能量（双翼 L/D≈9 vs 单翼 11.8） ===")
vs = 19.0
v_flare = 1.25*vs
dKE = 0.5*m*(v_flare*v_flare-vs*vs)          # 增速动能
h_acc = dKE/(m*g)
# 拉平 2.0g 掉高（弧段）≈ (v^2/2g)(1-1/n) 修正 取原账 56m
# 双翼阻力耗散增加：增速段平均 D 更大 → 等效多掉高
h_total = 32 + 56 + 8   # 增速28→32(双翼阻力+4) + 拉平56 + 裕量8
print(f"增速+拉平需掉高 ≈ {h_total:.0f}m → 关机高度建议 150~170m")
print()
print("=== ⑤ 装机/收拢态装箱 ===")
print("桶1(主体桶, H≤85cm): 主体800mm + 双翼收拢挂体(钻石背两段折后各~0.4m, 贴机腹/背)")
print("桶2(附件桶): 机头泡沫300 + 尾杆450 + 4电机架(六角螺丝装) + 桨叶×4 + 十字尾翼")
