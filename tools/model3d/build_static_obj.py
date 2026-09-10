# -*- coding: utf-8 -*-
"""
HDRS-1 迅鸢 v0.3.1c 静态构型 OBJ 生成器（v2，干净版）
坐标：X = STA(mm) 机头尖 X=0 → 机尾 X=1580；Y 竖直向上；Z 侧向（主翼沿 ±Z）。
单位：mm。flat 面 + DoubleSide（绕序不敏感）。
4 桨绕尾杆 X 型 90°：只在 +Y 局部构建一次，输出时绕 X 轴转 0/90/180/270 复制。
"""
import math, os

TRI = []  # (mat, (ax,ay,az), (bx,by,bz), (cx,cy,cz))

def tri(m, a, b, c): TRI.append((m, tuple(a), tuple(b), tuple(c)))
def quad(m, a, b, c, d): tri(m, a, b, c); tri(m, a, c, d)

def rotX(p, k):
    x, y, z = p
    if k == 0: return (x, y, z)
    if k == 1: return (x, -z, y)     # +90°
    if k == 2: return (x, -y, -z)    # 180°
    return (x, z, -y)                # 270°

def quad4(m, a, b, c, d, k=0):
    """四点面；k 指示绕 X 复制方向（0..3），k=0 时仅本体。"""
    if k == 0:
        quad(m, a, b, c, d)
    else:
        quad(m, rotX(a, k), rotX(b, k), rotX(c, k), rotX(d, k))

# ---------- 基础网格 ----------

def ring(x, r, n, ph=0.0):
    return [(x, r * math.sin(2 * math.pi * i / n + ph),
             r * math.cos(2 * math.pi * i / n + ph)) for i in range(n)]

def tube(m, x0, r0, x1, r1, n=28):
    c0, c1 = ring(x0, r0, n), ring(x1, r1, n)
    for i in range(n):
        j = (i + 1) % n
        quad(m, c0[i], c0[j], c1[j], c1[i])

def lathe(m, prof, n=28, cap_start=False, cap_end=False):
    """prof=[(x,r)...] 沿 X 的旋转体。"""
    for k in range(len(prof) - 1):
        tube(m, prof[k][0], prof[k][1], prof[k + 1][0], prof[k + 1][1], n)
    if cap_start and prof[0][1] > 0.5:
        x, r = prof[0]
        pts = ring(x, r, n)
        c = (x, 0, 0)
        for i in range(n):
            j = (i + 1) % n
            tri(m, pts[i], pts[j], c)
    if cap_end and prof[-1][1] > 0.5:
        x, r = prof[-1]
        pts = ring(x, r, n)
        c = (x, 0, 0)
        for i in range(n):
            j = (i + 1) % n
            tri(m, pts[i], pts[j], c)

def boxY(m, xc, zc, y0, y1, hx, hz):
    """轴向 Y 的方柱（用于径向臂），横截面在 X-Z。"""
    xa, xb = xc - hx / 2, xc + hx / 2
    za, zb = zc - hz / 2, zc + hz / 2
    A = (xa, y0, za); B = (xb, y0, za); C = (xb, y0, zb); D = (xa, y0, zb)
    E = (xa, y1, za); F = (xb, y1, za); G = (xb, y1, zb); H = (xa, y1, zb)
    quad(m, A, B, C, D)   # -Y 端
    quad(m, E, H, G, F)   # +Y 端
    quad(m, A, E, F, B)   # -Z 面
    quad(m, D, C, G, H)   # +Z 面
    quad(m, A, D, H, E)   # -X 面
    quad(m, B, F, G, C)   # +X 面

# ---------- 桨（局部 +Y 方向，输出时绕 X 复制 4 份） ----------

def blade(m, C, ru, bw=16.0, off0=20.0, off1=163.0, th=4.0):
    """
    单叶片薄板。C=桨心(x,0,0 局部 Y=0 平面? 不——C 已在 +Y 位置, 作为平面旋转中心，
    桨盘面 = 过桨心、垂直于 X 的 YZ 面。ru=(0,uy,uz) 盘内单位向。
    blade 从 C+ru*off0 到 C+ru*off1；宽 2*bw 沿盘内切向 w=(0,-uz,uy)；厚 th 沿 X。
    """
    cx, cy, cz = C
    p0 = (cx, cy + ru[1] * off0, cz + ru[2] * off0)
    p1 = (cx, cy + ru[1] * off1, cz + ru[2] * off1)
    w = (-ru[2], ru[1])           # 盘内切向 (y,z)
    w0 = (p0[1] + w[0] * bw, p0[2] + w[1] * bw)
    w1 = (p1[1] + w[0] * bw, p1[2] + w[1] * bw)
    w2 = (p1[1] - w[0] * bw, p1[2] - w[1] * bw)
    w3 = (p0[1] - w[0] * bw, p0[2] - w[1] * bw)
    th2 = th / 2
    A = (cx - th2, w0[0], w0[1]); B = (cx - th2, w1[0], w1[1])
    C_ = (cx - th2, w2[0], w2[1]); D = (cx - th2, w3[0], w3[1])
    E = (cx + th2, w0[0], w0[1]); F = (cx + th2, w1[0], w1[1])
    G = (cx + th2, w2[0], w2[1]); H = (cx + th2, w3[0], w3[1])
    quad(m, A, B, C_, D)          # -X 面
    quad(m, E, H, G, F)           # +X 面
    quad(m, A, E, F, B)           # 一侧边（沿长度）
    quad(m, D, C_, G, H)          # 另一侧边
    quad(m, A, D, H, E)           # 叶根短边
    quad(m, B, F, G, C_)          # 叶尖短边

def ring_off(x, yc, zc, r, n):
    """圆心 (yc,zc) 的 YZ 圆（环），用于平行 X 轴但偏心(位于桨心)的圆柱。"""
    return [(x, yc + r * math.sin(2 * math.pi * i / n),
             zc + r * math.cos(2 * math.pi * i / n)) for i in range(n)]

def tri_rot(k, m, a, b, c):
    if k == 0: tri(m, a, b, c)
    else:      tri(m, rotX(a, k), rotX(b, k), rotX(c, k))

def tube_off_rot(k, m, x0, x1, yc, zc, r, n=14):
    """轴向 X、中心线在 (yc,zc)、半径 r 的正圆柱，绕 X 复制 k 份。"""
    c0, c1 = ring_off(x0, yc, zc, r, n), ring_off(x1, yc, zc, r, n)
    for i in range(n):
        j = (i + 1) % n
        quad_rot(k, m, c0[i], c0[j], c1[j], c1[i])
    # 两端盖（中心点法）
    for x, ringp in ((x0, c0), (x1, c1)):
        cx = (x, yc, zc)
        for i in range(n):
            j = (i + 1) % n
            tri_rot(k, m, ringp[i], ringp[j], cx)

def build_rotor_group():
    """4 桨 + 4 臂，X 型 90° 等角绕尾杆。臂沿径向(局部+Y)，电机轴=X，桨盘面 x=1460。"""
    arm_m, motor_m, prop_m = "arm", "motor", "prop"
    R, xa0, xa1 = 245.0, 1425.0, 1465.0
    for k in range(4):
        # 臂方柱（局部 +Y）：杆面 y40 → 电机后沿 R-24
        boxY_rot(k, arm_m, xc=(xa0 + xa1) / 2, zc=0.0, y0=40.0, y1=R - 24.0, hx=16.0, hz=16.0)
        # 电机：轴向 X 正圆柱，中心 (yc,zc)=(R-10,0)，x 1446→1466，r 20
        tube_off_rot(k, motor_m, 1446.0, 1466.0, R - 10.0, 0.0, 20.0)
        # 桨毂：x 1466→1478，r 15（桨心 R）
        tube_off_rot(k, motor_m, 1466.0, 1478.0, R, 0.0, 15.0)
        # 叶片：中心 C=(1478, R, 0)，两叶对径 45° 错开臂（盘内 ru）
        C = (1478.0, R, 0.0)
        for ru in ((0, 0.7071, 0.7071), (0, -0.7071, -0.7071)):
            blade_rot(k, prop_m, C, ru)

def quad_rot(k, m, a, b, c, d):
    if k == 0: quad(m, a, b, c, d)
    else:      quad(m, rotX(a, k), rotX(b, k), rotX(c, k), rotX(d, k))

def boxY_rot(k, m, xc, zc, y0, y1, hx, hz):
    xa, xb = xc - hx / 2, xc + hx / 2
    za, zb = zc - hz / 2, zc + hz / 2
    A = (xa, y0, za); B = (xb, y0, za); C = (xb, y0, zb); D = (xa, y0, zb)
    E = (xa, y1, za); F = (xb, y1, za); G = (xb, y1, zb); H = (xa, y1, zb)
    quad_rot(k, m, A, B, C, D)
    quad_rot(k, m, E, H, G, F)
    quad_rot(k, m, A, E, F, B)
    quad_rot(k, m, D, C, G, H)
    quad_rot(k, m, A, D, H, E)
    quad_rot(k, m, B, F, G, C)

def lathe_rot(k, m, prof, n=14):
    for s in range(len(prof) - 1):
        (x0, r0), (x1, r1) = prof[s], prof[s + 1]
        if r0 < 0.5 and r1 < 0.5: continue
        c0, c1 = ring(x0, max(r0, 0.01), n), ring(x1, max(r1, 0.01), n)
        for i in range(n):
            j = (i + 1) % n
            quad_rot(k, m, c0[i], c0[j], c1[j], c1[i])
    # 尖端盖
    for (x, r) in (prof[0], prof[-1]):
        if r < 0.5: continue
        pts = ring(x, r, n); c = (x, 0, 0)
        for i in range(n):
            j = (i + 1) % n
            quad_rot(k, m, pts[i], pts[j], c)

def blade_rot(k, m, C, ru):
    """叶片，绕 X 复制 k。"""
    bw, off0, off1, th = 16.0, 18.0, 162.0, 4.0
    cx, cy, cz = C
    w = (-ru[2], ru[1])
    def P(off, sgn):  # 叶片线上点
        return (cx, cy + ru[1] * off, cz + ru[2] * off)
    p0 = P(off0, 1); p1 = P(off1, 1)
    c0y, c0z = p0[1], p0[2]; c1y, c1z = p1[1], p1[2]
    th2 = th / 2
    A = (cx - th2, c0y + w[0] * bw, c0z + w[1] * bw)
    B = (cx - th2, c1y + w[0] * bw, c1z + w[1] * bw)
    C_ = (cx - th2, c1y - w[0] * bw, c1z - w[1] * bw)
    D = (cx - th2, c0y - w[0] * bw, c0z - w[1] * bw)
    E = (cx + th2, c0y + w[0] * bw, c0z + w[1] * bw)
    F = (cx + th2, c1y + w[0] * bw, c1z + w[1] * bw)
    G = (cx + th2, c1y - w[0] * bw, c1z - w[1] * bw)
    H = (cx + th2, c0y - w[0] * bw, c0z - w[1] * bw)
    quad_rot(k, m, A, B, C_, D)
    quad_rot(k, m, E, H, G, F)
    quad_rot(k, m, A, E, F, B)
    quad_rot(k, m, D, C_, G, H)
    quad_rot(k, m, A, D, H, E)
    quad_rot(k, m, B, F, G, C_)

# ---------- 主翼（±Z 对称梯形平板，上单翼） ----------

def wing_side(sign):
    m = "wing"
    x_le, c_root, c_tip, span, y_lev, thk = 821.0, 390.0, 230.0, 1000.0, 108.0, 18.0
    z = sign * span
    y0, y1 = y_lev - thk / 2, y_lev + thk / 2
    xt0 = x_le + 0.25 * (c_root - c_tip)
    xr0, xr1 = x_le, x_le + c_root
    xt1 = xt0 + c_tip
    # 上表面
    quad(m, (xr0, y1, 0), (xt0, y1, z), (xt1, y1, z), (xr1, y1, 0))
    # 下表面
    quad(m, (xr0, y0, 0), (xr1, y0, 0), (xt1, y0, z), (xt0, y0, z))
    # 前缘带
    quad(m, (xr0, y0, 0), (xr0, y1, 0), (xt0, y1, z), (xt0, y0, z))
    # 后缘带
    quad(m, (xr1, y0, 0), (xt1, y0, z), (xt1, y1, z), (xr1, y1, 0))
    # 翼尖带
    quad(m, (xt0, y0, z), (xt0, y1, z), (xt1, y1, z), (xt1, y0, z))
    # 翼根带（背脊）
    quad(m, (xr0, y0, 0), (xr1, y0, 0), (xr1, y1, 0), (xr0, y1, 0))

# ---------- 十字尾翼 ----------

def cruciform_tail():
    # 平尾：弦 80 (X1500-1580)、半展 350、y=+46、厚 10
    m = "tailh"
    x0, x1, y, thk = 1500.0, 1580.0, 34.0, 10.0
    yb, yt = y - thk / 2, y + thk / 2
    for sign in (+1, -1):
        z = sign * 350.0
        quad(m, (x0, yb, 0), (x0, yt, 0), (x1, yt, 0), (x1, yb, 0))          # 翼根带? 中缝
        quad(m, (x0, yb, 0), (x1, yb, 0), (x1, yb, z), (x0, yb, z))          # 下表面
        quad(m, (x0, yt, 0), (x0, yt, z), (x1, yt, z), (x1, yt, 0))          # 上表面
        quad(m, (x0, yb, 0), (x0, yb, z), (x0, yt, z), (x0, yt, 0))          # 前缘
        quad(m, (x1, yb, 0), (x1, yt, 0), (x1, yt, z), (x1, yb, z))          # 后缘
        quad(m, (x0, yb, z), (x0, yt, z), (x1, yt, z), (x1, yb, z))          # 翼尖
    # 垂尾：高 250（y 30→250，杆表面起）、弦 80、厚 8 于 z=0
    m = "tailv"
    zt, zb = 4.0, -4.0
    ya, yb2 = 30.0, 250.0
    quad(m, (x0, ya, zb), (x0, ya, zt), (x1, ya, zt), (x1, ya, zb))          # 底
    quad(m, (x0, yb2, zb), (x1, yb2, zb), (x1, yb2, zt), (x0, yb2, zt))      # 顶
    quad(m, (x0, ya, zb), (x1, ya, zb), (x1, yb2, zb), (x0, yb2, zb))        # -Z 面
    quad(m, (x0, ya, zt), (x0, yb2, zt), (x1, yb2, zt), (x1, ya, zt))        # +Z 面
    quad(m, (x0, ya, zb), (x0, yb2, zb), (x0, yb2, zt), (x0, ya, zt))        # 前缘
    quad(m, (x1, ya, zb), (x1, ya, zt), (x1, yb2, zt), (x1, yb2, zb))        # 后缘

# ---------- 组装 ----------

def build():
    # 机头吸能罩 A：0→200，半径 0→70（tangent-ogive 轮廓）
    lathe("nose", [(0, 0.0), (40, 40.0), (90, 58.0), (140, 67.0), (200, 70.0)], n=28)
    # 机身筒 C/D/E/F：200→1250 r70
    lathe("hull", [(200, 70.0), (1250, 70.0)], n=28)
    # 尾杆过渡 + 细尾杆：1250→1300 r70→30；1300→1580 r30
    lathe("hull", [(1250, 70.0), (1300, 30.0)], n=28)
    lathe("hull", [(1300, 30.0), (1580, 30.0)], n=28, cap_end=True)
    # 主翼左右
    wing_side(+1); wing_side(-1)
    # 4 桨 + 臂
    build_rotor_group()
    # 十字尾翼
    cruciform_tail()

# ---------- OBJ 输出 ----------

MAT_ORDER = ["nose", "hull", "wing", "arm", "motor", "prop", "tailh", "tailv"]

def write_obj(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("# HDRS-1 迅鸢 v0.3.1c 静态构型（mm；X=STA 机头0→机尾1580；Y上；Z侧向）\n")
        f.write("# 材质: nose红/hull灰/wing蓝/arm深灰/motor中灰/prop橙/tailh绿/tailv青\n")
        v = 1
        cur = None
        for m, a, b, c in TRI:
            if m != cur:
                f.write("usemtl %s\n" % m)
                cur = m
            for p in (a, b, c):
                f.write("v %.3f %.3f %.3f\n" % p)
                v += 1
            f.write("f %d %d %d\n" % (v - 3, v - 2, v - 1))
    print("OBJ written:", path, "| tris:", len(TRI))

if __name__ == "__main__":
    build()
    base = os.path.dirname(os.path.abspath(__file__))
    write_obj(os.path.join(base, "HDRS-1-迅鸢-v0.3.1c-静态模型.obj"))
