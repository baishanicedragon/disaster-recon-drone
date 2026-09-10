# -*- coding: utf-8 -*-
"""
HDRS-1 迅鸢 v0.4 双翼快拆构型 —— 静态 OBJ 生成器
坐标：X=STA(mm) 机头尖 0 → 机尾 1580；Y 上；Z 侧向（翼沿 ±Z）。单位 mm。
模块：机头泡沫(可拆)0–300 | 主体300–1100(电池/航电/翼盒) | 尾组1100–1580(插接)
升力面：上翼2片 y+175 b1.5 / 下翼2片 y−175 b1.4，gap≈350
"""
import math, os

TRI = []
def tri(m, a, b, c): TRI.append((m, tuple(a), tuple(b), tuple(c)))
def quad(m, a, b, c, d): tri(m, a, b, c); tri(m, a, c, d)

def rotX(p, k):
    x, y, z = p
    if k == 0: return (x, y, z)
    if k == 1: return (x, -z, y)
    if k == 2: return (x, -y, -z)
    return (x, z, -y)

def quad_rot(k, m, a, b, c, d):
    if k == 0: quad(m, a, b, c, d)
    else:      quad(m, rotX(a, k), rotX(b, k), rotX(c, k), rotX(d, k))

def tri_rot(k, m, a, b, c):
    if k == 0: tri(m, a, b, c)
    else:      tri(m, rotX(a, k), rotX(b, k), rotX(c, k))

# ---------- 基础网格 ----------
def ring(x, r, n, ph=0.0):
    return [(x, r * math.sin(2 * math.pi * i / n + ph),
             r * math.cos(2 * math.pi * i / n + ph)) for i in range(n)]

def tube(m, x0, r0, x1, r1, n=28):
    c0, c1 = ring(x0, r0, n), ring(x1, r1, n)
    for i in range(n):
        j = (i + 1) % n
        quad(m, c0[i], c0[j], c1[j], c1[i])

def lathe(m, prof, n=28, cap_end=False):
    for k in range(len(prof) - 1):
        tube(m, prof[k][0], prof[k][1], prof[k + 1][0], prof[k + 1][1], n)
    if cap_end and prof[-1][1] > 0.5:
        x, r = prof[-1]
        pts = ring(x, r, n); c = (x, 0, 0)
        for i in range(n):
            j = (i + 1) % n
            tri(m, pts[i], pts[j], c)

def boxX(m, x0, x1, y0, y1, z0, z1):
    """轴向 X 的轴对齐盒体（翼盒塔/整流座）。"""
    A=(x0,y0,z0); B=(x1,y0,z0); C=(x1,y0,z1); D=(x0,y0,z1)
    E=(x0,y1,z0); F=(x1,y1,z0); G=(x1,y1,z1); H=(x0,y1,z1)
    quad(m, A,B,C,D)   # -Y
    quad(m, E,H,G,F)   # +Y
    quad(m, A,E,F,B)   # -Z
    quad(m, D,C,G,H)   # +Z
    quad(m, A,D,H,E)   # -X
    quad(m, B,F,G,C)   # +X

# ---------- 主翼（左右梯形半翼，参数化；翼根在 z=0 穿过中央翼盒塔） ----------
def wing_side(m, sign, x_le, c_root, c_tip, span, y_lev, thk):
    z = sign * span
    y0, y1 = y_lev - thk/2, y_lev + thk/2
    xt0 = x_le + 0.25 * (c_root - c_tip)          # 翼尖前缘（梯形后掠）
    xr0, xr1 = x_le, x_le + c_root
    xt1 = xt0 + c_tip
    quad(m, (xr0,y1,0), (xt0,y1,z), (xt1,y1,z), (xr1,y1,0))   # 上表面
    quad(m, (xr0,y0,0), (xr1,y0,0), (xt1,y0,z), (xt0,y0,z))   # 下表面
    quad(m, (xr0,y0,0), (xr0,y1,0), (xt0,y1,z), (xt0,y0,z))   # 前缘
    quad(m, (xr1,y0,0), (xt1,y0,z), (xt1,y1,z), (xr1,y1,0))   # 后缘
    quad(m, (xt0,y0,z), (xt0,y1,z), (xt1,y1,z), (xt1,y0,z))   # 翼尖
    quad(m, (xr0,y0,0), (xr1,y0,0), (xr1,y1,0), (xr0,y1,0))   # 翼根(穿塔)

# ---------- 桨（局部 +Y，绕 X 复制 4 份） ----------
def blade_rot(k, m, C, ru):
    bw, off0, off1, th = 16.0, 18.0, 162.0, 4.0
    cx, cy, cz = C
    w = (-ru[2], ru[1])
    def P(off): return (cx, cy + ru[1]*off, cz + ru[2]*off)
    p0, p1 = P(off0), P(off1)
    th2 = th/2
    A=(cx-th2, p0[1]+w[0]*bw, p0[2]+w[1]*bw); B=(cx-th2, p1[1]+w[0]*bw, p1[2]+w[1]*bw)
    C_=(cx-th2, p1[1]-w[0]*bw, p1[2]-w[1]*bw); D=(cx-th2, p0[1]-w[0]*bw, p0[2]-w[1]*bw)
    E=(cx+th2, p0[1]+w[0]*bw, p0[2]+w[1]*bw); F=(cx+th2, p1[1]+w[0]*bw, p1[2]+w[1]*bw)
    G=(cx+th2, p1[1]-w[0]*bw, p1[2]-w[1]*bw); H=(cx+th2, p0[1]-w[0]*bw, p0[2]-w[1]*bw)
    quad_rot(k,m,A,B,C_,D); quad_rot(k,m,E,H,G,F)
    quad_rot(k,m,A,E,F,B); quad_rot(k,m,D,C_,G,H)
    quad_rot(k,m,A,D,H,E); quad_rot(k,m,B,F,G,C_)

def ring_off(x, yc, zc, r, n):
    return [(x, yc + r*math.sin(2*math.pi*i/n), zc + r*math.cos(2*math.pi*i/n)) for i in range(n)]

def tube_off_rot(k, m, x0, x1, yc, zc, r, n=14):
    c0, c1 = ring_off(x0, yc, zc, r, n), ring_off(x1, yc, zc, r, n)
    for i in range(n):
        j = (i+1) % n
        quad_rot(k, m, c0[i], c0[j], c1[j], c1[i])
    for x, ringp in ((x0, c0), (x1, c1)):
        cx = (x, yc, zc)
        for i in range(n):
            j = (i+1) % n
            tri_rot(k, m, ringp[i], ringp[j], cx)

def boxY_rot(k, m, xc, zc, y0, y1, hx, hz):
    xa, xb = xc-hx/2, xc+hx/2
    za, zb = zc-hz/2, zc+hz/2
    A=(xa,y0,za); B=(xb,y0,za); C=(xb,y0,zb); D=(xa,y0,zb)
    E=(xa,y1,za); F=(xb,y1,za); G=(xb,y1,zb); H=(xa,y1,zb)
    quad_rot(k,m,A,B,C,D); quad_rot(k,m,E,H,G,F)
    quad_rot(k,m,A,E,F,B); quad_rot(k,m,D,C,G,H)
    quad_rot(k,m,A,D,H,E); quad_rot(k,m,B,F,G,C)

def build_rotor_group():
    """4 桨绕尾杆 X 型 90°：臂 x1425-1465，桨盘面 1460，毂/叶到 1478。臂根贴杆面(y0=34,杆 r30)。"""
    R, xa0, xa1 = 245.0, 1425.0, 1465.0
    for k in range(4):
        boxY_rot(k, "arm", xc=(xa0+xa1)/2, zc=0.0, y0=34.0, y1=R-24.0, hx=16.0, hz=16.0)
        tube_off_rot(k, "motor", 1446.0, 1466.0, R-10.0, 0.0, 20.0)   # 电机
        tube_off_rot(k, "motor", 1466.0, 1478.0, R, 0.0, 15.0)        # 桨毂
        C = (1478.0, R, 0.0)
        for ru in ((0, 0.7071, 0.7071), (0, -0.7071, -0.7071)):
            blade_rot(k, "prop", C, ru)

# ---------- 十字尾翼（全机最后 1500-1580） ----------
def cruciform_tail():
    mh, mv = "tailh", "tailv"
    x0, x1, thk = 1500.0, 1580.0, 10.0
    # 平尾：半展 350，杆 r30 上表面 y=34
    y, hh = 34.0, 350.0
    yb, yt = y-thk/2, y+thk/2
    for sign in (+1,-1):
        z = sign*hh
        quad(mh,(x0,yb,0),(x0,yt,0),(x1,yt,0),(x1,yb,0))
        quad(mh,(x0,yb,0),(x1,yb,0),(x1,yb,z),(x0,yb,z))
        quad(mh,(x0,yt,0),(x0,yt,z),(x1,yt,z),(x1,yt,0))
        quad(mh,(x0,yb,0),(x0,yb,z),(x0,yt,z),(x0,yt,0))
        quad(mh,(x1,yb,0),(x1,yt,0),(x1,yt,z),(x1,yb,z))
        quad(mh,(x0,yb,z),(x0,yt,z),(x1,yt,z),(x1,yb,z))
    # 垂尾：高 250 弦 80 厚 8
    zt, zb = 4.0, -4.0
    ya, yb2 = 30.0, 250.0
    quad(mv,(x0,ya,zb),(x0,ya,zt),(x1,ya,zt),(x1,ya,zb))
    quad(mv,(x0,yb2,zb),(x1,yb2,zb),(x1,yb2,zt),(x0,yb2,zt))
    quad(mv,(x0,ya,zb),(x1,ya,zb),(x1,yb2,zb),(x0,yb2,zb))
    quad(mv,(x0,ya,zt),(x0,yb2,zt),(x1,yb2,zt),(x1,ya,zt))
    quad(mv,(x0,ya,zb),(x0,yb2,zb),(x0,yb2,zt),(x0,ya,zt))
    quad(mv,(x1,ya,zb),(x1,ya,zt),(x1,yb2,zt),(x1,yb2,zb))

# ---------- 组装 ----------
def build():
    # 机头泡沫模块（可拆，ogive 0→300）—— 拧接缝在 300
    lathe("nose", [(0,0.0),(55,38.0),(120,55.0),(190,64.0),(260,68.5),(300,70.0)], n=28)
    # 接口凸环 @300（螺纹口）
    lathe("nose", [(294,70.0),(302,75.5),(310,75.5),(318,70.0)], n=28)
    # 主体 300→1100（电池/航电/翼盒），r70
    lathe("hull", [(318,70.0),(1092,70.0)], n=28)
    # 尾组插接口凸环 @1100
    lathe("hull", [(1092,70.0),(1100,75.5),(1110,75.5),(1118,70.0)], n=28)
    # 尾杆模块（插接）1100→1580：粗锥 1118-1250 → 细杆 1250-1580
    lathe("hull", [(1118,70.0),(1250,30.0)], n=28)
    lathe("hull", [(1250,30.0),(1580,30.0)], n=28, cap_end=True)
    # 中央翼盒塔：上塔（背脊 y72→175, 翼盒区 560-770）、下塔（机腹 y-175→-72, 区 650-871）
    boxX("hull", 818.0, 1030.0, 71.0, 176.0, -40.0, 40.0)
    boxX("hull", 860.0, 1100.0, -176.0, -71.0, -40.0, 40.0)
    # 双翼 4 片（展开态）
    # 上翼：LE818 根230 梢190 半展750 y+175（AC≈870, S≈0.315）
    wing_side("wing_u", +1, 818.0, 230.0, 190.0, 750.0, 175.0, 16.0)
    wing_side("wing_u", -1, 818.0, 230.0, 190.0, 750.0, 175.0, 16.0)
    # 下翼：LE860 根240 梢200 半展700 y−175（AC≈920, S≈0.315）
    wing_side("wing_l", +1, 860.0, 240.0, 200.0, 700.0, -175.0, 16.0)
    wing_side("wing_l", -1, 860.0, 240.0, 200.0, 700.0, -175.0, 16.0)
    # 尾组：4 桨 + 十字尾翼
    build_rotor_group()
    cruciform_tail()

# ---------- OBJ 输出 ----------
MAT_ORDER = ["nose","hull","wing_u","wing_l","arm","motor","prop","tailh","tailv"]

def write_obj(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("# HDRS-1 迅鸢 v0.4 双翼快拆构型 静态模型（mm; X=STA 0→1580; Y上; Z侧向）\n")
        f.write("# 模块: 机头泡沫0-300(拆) 主体300-1100 尾组1100-1580(插接)\n")
        f.write("# 材质: nose红 hull灰 wing_u蓝(上翼y+175) wing_l紫(下翼y-175) arm深灰 motor中灰 prop橙 tailh绿 tailv青\n")
        v = 1; cur = None
        for m, a, b, c in TRI:
            if m != cur:
                f.write("usemtl %s\n" % m); cur = m
            for p in (a, b, c):
                f.write("v %.3f %.3f %.3f\n" % p); v += 1
            f.write("f %d %d %d\n" % (v-3, v-2, v-1))
    print("OBJ written:", path, "| tris:", len(TRI))

if __name__ == "__main__":
    build()
    base = os.path.dirname(os.path.abspath(__file__))
    write_obj(os.path.join(base, "HDRS-1-迅鸢-v0.4-双翼快拆-静态模型.obj"))
