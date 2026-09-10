# -*- coding: utf-8 -*-
"""
HDRS-1 迅鸢 v0.4 双翼快拆构型 —— 动画部件生成器
输出：_anim_data_v04.js（各部件 OBJ 片段 + 铰接点 + 材质）

坐标（全机局部，mm）：X=STA 机头尖 0 → 机尾 1580；Y 上；Z 侧向（翼沿 ±Z）。
部件拆分原则：可独立运动的件单独成段，并给出 pivot（铰接点，全机局部 mm）。

部件：
  固定   nose / hull / arm / motor / tailv
  可动   wing_U{R,L}_{i,o}（上翼内外段，绕翼根 Y 轴折）
         wing_L{R,L}_{i,o}（下翼内外段）
         prop_0..3（桨叶，绕各自轴 X 自转）
         elevator（全动平尾，绕前缘 Z 轴偏转）
"""
import math, os, json

# ---------------- 收集器 ----------------
PARTS = {}          # name -> list[(a,b,c)]
PIVOT = {}          # name -> (x,y,z)
MATOF = {}          # name -> material key


def _p(name):
    return PARTS.setdefault(name, [])


def tri(part, a, b, c):
    _p(part).append((tuple(a), tuple(b), tuple(c)))


def quad(part, a, b, c, d):
    tri(part, a, b, c)
    tri(part, a, c, d)


def rotX(p, k):
    x, y, z = p
    if k == 0:
        return (x, y, z)
    if k == 1:
        return (x, -z, y)
    if k == 2:
        return (x, -y, -z)
    return (x, z, -y)


def quad_rot(k, part, a, b, c, d):
    if k == 0:
        quad(part, a, b, c, d)
    else:
        quad(part, rotX(a, k), rotX(b, k), rotX(c, k), rotX(d, k))


def tri_rot(k, part, a, b, c):
    if k == 0:
        tri(part, a, b, c)
    else:
        tri(part, rotX(a, k), rotX(b, k), rotX(c, k))


# ---------------- 基础网格 ----------------
def ring(x, r, n, ph=0.0):
    return [(x, r * math.sin(2 * math.pi * i / n + ph),
             r * math.cos(2 * math.pi * i / n + ph)) for i in range(n)]


def tube(part, x0, r0, x1, r1, n=28):
    c0, c1 = ring(x0, r0, n), ring(x1, r1, n)
    for i in range(n):
        j = (i + 1) % n
        quad(part, c0[i], c0[j], c1[j], c1[i])


def lathe(part, prof, n=28, cap_end=False):
    for k in range(len(prof) - 1):
        tube(part, prof[k][0], prof[k][1], prof[k + 1][0], prof[k + 1][1], n)
    if cap_end and prof[-1][1] > 0.5:
        x, r = prof[-1]
        pts = ring(x, r, n)
        c = (x, 0, 0)
        for i in range(n):
            j = (i + 1) % n
            tri(part, pts[i], pts[j], c)


def boxX(part, x0, x1, y0, y1, z0, z1):
    A = (x0, y0, z0); B = (x1, y0, z0); C = (x1, y0, z1); D = (x0, y0, z1)
    E = (x0, y1, z0); F = (x1, y1, z0); G = (x1, y1, z1); H = (x0, y1, z1)
    quad(part, A, B, C, D); quad(part, E, H, G, F)
    quad(part, A, E, F, B); quad(part, D, C, G, H)
    quad(part, A, D, H, E); quad(part, B, F, G, C)


def ring_off(x, yc, zc, r, n):
    return [(x, yc + r * math.sin(2 * math.pi * i / n),
             zc + r * math.cos(2 * math.pi * i / n)) for i in range(n)]


def tube_off_rot(k, part, x0, x1, yc, zc, r, n=14):
    c0, c1 = ring_off(x0, yc, zc, r, n), ring_off(x1, yc, zc, r, n)
    for i in range(n):
        j = (i + 1) % n
        quad_rot(k, part, c0[i], c0[j], c1[j], c1[i])
    for x, rp in ((x0, c0), (x1, c1)):
        cx = (x, yc, zc)
        for i in range(n):
            j = (i + 1) % n
            tri_rot(k, part, rp[i], rp[j], cx)


def boxY_rot(k, part, xc, zc, y0, y1, hx, hz):
    xa, xb = xc - hx / 2, xc + hx / 2
    za, zb = zc - hz / 2, zc + hz / 2
    A = (xa, y0, za); B = (xb, y0, za); C = (xb, y0, zb); D = (xa, y0, zb)
    E = (xa, y1, za); F = (xb, y1, za); G = (xb, y1, zb); H = (xa, y1, zb)
    quad_rot(k, part, A, B, C, D); quad_rot(k, part, E, H, G, F)
    quad_rot(k, part, A, E, F, B); quad_rot(k, part, D, C, G, H)
    quad_rot(k, part, A, D, H, E); quad_rot(k, part, B, F, G, C)


# ---------------- 主翼（分段，钻石背两段折） ----------------
def wing_seg(part, sign, x_le, c_root, c_tip, span, y_lev, thk, za, zb):
    """沿展向 za→zb 的一段梯形翼（za/zb 为正值，sign 决定左右）。"""
    y0, y1 = y_lev - thk / 2, y_lev + thk / 2

    def cz(z):
        return c_root + (c_tip - c_root) * (z / span)

    def lex(z):
        return x_le + 0.25 * (c_root - cz(z))

    ca, cb = cz(za), cz(zb)
    la, lb = lex(za), lex(zb)
    A = (la, y1, sign * za); B = (lb, y1, sign * zb)
    C = (lb + cb, y1, sign * zb); D = (la + ca, y1, sign * za)
    quad(part, A, B, C, D)                                    # 上表面
    quad(part, (la, y0, sign * za), (la + ca, y0, sign * za),
         (lb + cb, y0, sign * zb), (lb, y0, sign * zb))       # 下表面
    quad(part, (la, y0, sign * za), (la, y1, sign * za),
         (lb, y1, sign * zb), (lb, y0, sign * zb))            # 前缘
    quad(part, (la + ca, y0, sign * za), (lb + cb, y0, sign * zb),
         (lb + cb, y1, sign * zb), (la + ca, y1, sign * za))  # 后缘
    quad(part, (lb, y0, sign * zb), (lb, y1, sign * zb),
         (lb + cb, y1, sign * zb), (lb + cb, y0, sign * zb))  # 外端
    quad(part, (la, y0, sign * za), (lb, y0, sign * zb),
         (lb, y1, sign * zb), (la, y1, sign * za))            # 内侧端(z=0 时即翼根)


# ---------------- 桨叶 ----------------
def blade_rot(k, part, C, ru):
    bw, off0, off1, th = 16.0, 18.0, 162.0, 4.0
    cx, cy, cz = C
    w = (-ru[2], ru[1])

    def Pn(off):
        return (cx, cy + ru[1] * off, cz + ru[2] * off)

    p0, p1 = Pn(off0), Pn(off1)
    t2 = th / 2
    A = (cx - t2, p0[1] + w[0] * bw, p0[2] + w[1] * bw)
    B = (cx - t2, p1[1] + w[0] * bw, p1[2] + w[1] * bw)
    C_ = (cx - t2, p1[1] - w[0] * bw, p1[2] - w[1] * bw)
    D = (cx - t2, p0[1] - w[0] * bw, p0[2] - w[1] * bw)
    E = (cx + t2, p0[1] + w[0] * bw, p0[2] + w[1] * bw)
    F = (cx + t2, p1[1] + w[0] * bw, p1[2] + w[1] * bw)
    G = (cx + t2, p1[1] - w[0] * bw, p1[2] - w[1] * bw)
    H = (cx + t2, p0[1] - w[0] * bw, p0[2] - w[1] * bw)
    quad_rot(k, part, A, B, C_, D); quad_rot(k, part, E, H, G, F)
    quad_rot(k, part, A, E, F, B); quad_rot(k, part, D, C_, G, H)
    quad_rot(k, part, A, D, H, E); quad_rot(k, part, B, F, G, C_)


# ================= 装配 =================
# ---- 几何常量（与 v0.4 评审稿一致）----
UP = dict(x_le=818.0, c_root=230.0, c_tip=190.0, span=750.0, y=175.0, thk=16.0)
LO = dict(x_le=860.0, c_root=240.0, c_tip=200.0, span=700.0, y=-175.0, thk=16.0)


def build():
    # ---------- 固定件 ----------
    # 机头泡沫（可拆模块）0–318
    lathe("nose", [(0, 0.0), (55, 38.0), (120, 55.0), (190, 64.0),
                   (260, 68.5), (300, 70.0)], n=28)
    lathe("nose", [(294, 70.0), (302, 75.5), (310, 75.5), (318, 70.0)], n=28)
    MATOF["nose"] = "nose"

    # 主体 318–1118 + 尾杆 1118–1580 + 上下翼盒塔
    lathe("hull", [(318, 70.0), (1092, 70.0)], n=28)
    lathe("hull", [(1092, 70.0), (1100, 75.5), (1110, 75.5), (1118, 70.0)], n=28)
    lathe("hull", [(1118, 70.0), (1250, 30.0)], n=28)
    lathe("hull", [(1250, 30.0), (1580, 30.0)], n=28, cap_end=True)
    boxX("hull", 818.0, 1030.0, 71.0, 176.0, -40.0, 40.0)
    boxX("hull", 860.0, 1100.0, -176.0, -71.0, -40.0, 40.0)
    MATOF["hull"] = "hull"

    # 4 桨臂 + 电机座（固定）
    R, xa0, xa1 = 245.0, 1425.0, 1465.0
    for k in range(4):
        boxY_rot(k, "arm", xc=(xa0 + xa1) / 2, zc=0.0, y0=34.0, y1=R - 24.0,
                 hx=16.0, hz=16.0)
        tube_off_rot(k, "motor", 1446.0, 1466.0, R - 10.0, 0.0, 20.0)
        tube_off_rot(k, "motor", 1466.0, 1478.0, R, 0.0, 15.0)
    MATOF["arm"] = "arm"
    MATOF["motor"] = "motor"

    # 4 个桨叶组（可自转）
    for k in range(4):
        nm = "prop_%d" % k
        C = (1478.0, R, 0.0)
        for ru in ((0, 0.7071, 0.7071), (0, -0.7071, -0.7071)):
            blade_rot(k, nm, C, ru)
        PIVOT[nm] = rotX((1478.0, R, 0.0), k)
        MATOF[nm] = "prop"

    # 垂尾（固定）1500–1580 高 250
    x0, x1 = 1500.0, 1580.0
    zt, zb, ya, yb2 = 4.0, -4.0, 30.0, 250.0
    tv = "tailv"
    quad(tv, (x0, ya, zb), (x0, ya, zt), (x1, ya, zt), (x1, ya, zb))
    quad(tv, (x0, yb2, zb), (x1, yb2, zb), (x1, yb2, zt), (x0, yb2, zt))
    quad(tv, (x0, ya, zb), (x1, ya, zb), (x1, yb2, zb), (x0, yb2, zb))
    quad(tv, (x0, ya, zt), (x0, yb2, zt), (x1, yb2, zt), (x1, ya, zt))
    quad(tv, (x0, ya, zb), (x0, yb2, zb), (x0, yb2, zt), (x0, ya, zt))
    quad(tv, (x1, ya, zb), (x1, ya, zt), (x1, yb2, zt), (x1, yb2, zb))
    MATOF["tailv"] = "tailv"

    # 全动平尾（可偏转）绕前缘 (1500,34,0) 绕 Z 轴
    th, hh = 10.0, 350.0
    y = 34.0
    yb, yt = y - th / 2, y + th / 2
    ev = "elevator"
    for sign in (+1, -1):
        z = sign * hh
        quad(ev, (x0, yb, 0), (x0, yt, 0), (x1, yt, 0), (x1, yb, 0))
        quad(ev, (x0, yb, 0), (x1, yb, 0), (x1, yb, z), (x0, yb, z))
        quad(ev, (x0, yt, 0), (x0, yt, z), (x1, yt, z), (x1, yt, 0))
        quad(ev, (x0, yb, 0), (x0, yb, z), (x0, yt, z), (x0, yt, 0))
        quad(ev, (x1, yb, 0), (x1, yt, 0), (x1, yt, z), (x1, yb, z))
        quad(ev, (x0, yb, z), (x0, yt, z), (x1, yt, z), (x1, yb, z))
    PIVOT["elevator"] = (1500.0, 34.0, 0.0)
    MATOF["elevator"] = "tailh"

    # ---------- 双翼 8 段（钻石背两段折）----------
    def side(tag, cfg, sign, mat):
        half = cfg["span"] / 2.0

        def cz(z):
            return cfg["c_root"] + (cfg["c_tip"] - cfg["c_root"]) * (z / cfg["span"])

        def lex(z):
            return cfg["x_le"] + 0.25 * (cfg["c_root"] - cz(z))

        nm_i = "%s_%s_i" % (tag, "R" if sign > 0 else "L")
        nm_o = "%s_%s_o" % (tag, "R" if sign > 0 else "L")
        wing_seg(nm_i, sign, cfg["x_le"], cfg["c_root"], cfg["c_tip"],
                 cfg["span"], cfg["y"], cfg["thk"], 0.0, half)
        wing_seg(nm_o, sign, cfg["x_le"], cfg["c_root"], cfg["c_tip"],
                 cfg["span"], cfg["y"], cfg["thk"], half, cfg["span"])
        # 内段铰：翼根【前缘】角点（弦向整段甩到一侧，左右收拢后不穿透）
        # 外段铰：内段外端【后缘】角点（外段折回后弦向甩向外侧，不与对侧相撞）
        PIVOT[nm_i] = (cfg["x_le"], cfg["y"], 0.0)
        PIVOT[nm_o] = (lex(half), cfg["y"], sign * half)
        MATOF[nm_i] = mat
        MATOF[nm_o] = mat

    for s in (+1, -1):
        side("wing_U", UP, s, "wing_u")
        side("wing_L", LO, s, "wing_l")


# ---------------- 输出 JS ----------------
def part_obj(name):
    """把部件三角面写成 OBJ 文本（顶点去重，1-based 索引）。"""
    idx = {}
    vs = []
    fs = []
    for a, b, c in PARTS[name]:
        face = []
        for p in (a, b, c):
            key = (round(p[0], 3), round(p[1], 3), round(p[2], 3))
            if key not in idx:
                idx[key] = len(vs) + 1
                vs.append(key)
            face.append(idx[key])
        fs.append(face)
    out = []
    for v in vs:
        out.append("v %.3f %.3f %.3f" % v)
    for f in fs:
        out.append("f %d %d %d" % tuple(f))
    return "\n".join(out)


if __name__ == "__main__":
    build()
    base = os.path.dirname(os.path.abspath(__file__))
    order = ["nose", "hull", "arm", "motor", "tailv", "elevator",
             "prop_0", "prop_1", "prop_2", "prop_3",
             "wing_U_R_i", "wing_U_R_o", "wing_U_L_i", "wing_U_L_o",
             "wing_L_R_i", "wing_L_R_o", "wing_L_L_i", "wing_L_L_o"]
    chunks = []
    for nm in order:
        obj = part_obj(nm)
        piv = PIVOT.get(nm, (0.0, 0.0, 0.0))
        chunks.append(
            '  %s: {\n    mat: "%s",\n    pivot: [%s],\n    obj: `%s`\n  }'
            % (nm, MATOF[nm], ", ".join("%.1f" % v for v in piv), obj))
    js = ("// HDRS-1 迅鸢 v0.4 动画部件数据（自动生成，勿手改）\n"
          "// 坐标：全机局部 mm；X=STA 0(机头)→1580(机尾)；Y 上；Z 侧向\n"
          "const PART_DATA = {\n" + ",\n".join(chunks) + "\n};\n")
    dst = os.path.join(base, "_anim_data_v04.js")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(js)
    tot = sum(len(PARTS[n]) for n in order)
    print("parts:", len(order), "| tris:", tot)
    print("written:", dst, "%.1f KB" % (os.path.getsize(dst) / 1024))
    for nm in order:
        if nm.startswith("wing") or nm == "elevator":
            print("   %-12s pivot=%s" % (nm, PIVOT[nm]))
