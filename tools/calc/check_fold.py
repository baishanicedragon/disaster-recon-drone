# -*- coding: utf-8 -*-
"""校验 v0.4 折叠变换：收拢态各翼段 bbox 与相互干涉（不依赖视觉）。"""
import math, re, os

BASE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(BASE, "_anim_data_v04.js"), encoding="utf-8").read()

# 解析 PART_DATA
parts = {}
for m in re.finditer(r"(\w+):\s*\{\s*mat:\s*\"(\w+)\",\s*pivot:\s*\[([^\]]*)\],\s*obj:\s*`([^`]*)`\s*\}",
                     src, re.S):
    name, mat, piv, obj = m.group(1), m.group(2), m.group(3), m.group(4)
    pivot = tuple(float(x) for x in piv.split(","))
    verts = []
    for line in obj.split("\n"):
        s = line.strip()
        if s.startswith("v "):
            p = s.split()
            verts.append((float(p[1]), float(p[2]), float(p[3])))
    parts[name] = dict(mat=mat, pivot=pivot, verts=verts)


def rotY(v, deg):
    a = math.radians(deg)
    x, y, z = v
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))


def xform(verts, pivot, rot_deg, parent_pivot=None, parent_rot=0.0, parent_off=(0, 0, 0)):
    """顶点(全机坐标) → craft 局部（先 mesh 平移 -pivot，再本段旋转，再挂到父段）。"""
    out = []
    for p in verts:
        q = (p[0] - pivot[0], p[1] - pivot[1], p[2] - pivot[2])
        q = rotY(q, rot_deg)
        out.append(q)
    if parent_pivot is None:
        return [(q[0] + pivot[0], q[1] + pivot[1], q[2] + pivot[2]) for q in out]
    # 父段：本段 grp 相对父段有 offset(=pivot_self - pivot_parent)，再经父段旋转+平移
    res = []
    for q in out:
        r = (q[0] + parent_off[0], q[1] + parent_off[1], q[2] + parent_off[2])
        r = rotY(r, parent_rot)
        res.append((r[0] + parent_pivot[0], r[1] + parent_pivot[1], r[2] + parent_pivot[2]))
    return res


def bbox(vs):
    return tuple((min(v[i] for v in vs), max(v[i] for v in vs)) for i in range(3))


def show(tag, vs):
    b = bbox(vs)
    print("  %-12s X[%7.0f,%7.0f]  Y[%6.0f,%6.0f]  Z[%7.0f,%7.0f]"
          % (tag, b[0][0], b[0][1], b[1][0], b[1][1], b[2][0], b[2][1]))
    return b


# 外段折回后的 Y 向分层量（mm），与 JS 端一致
LIFT = {"wing_U_R_o": 18.0, "wing_U_L_o": 36.0,
        "wing_L_R_o": -18.0, "wing_L_L_o": -36.0}

WINGS = [("wing_U_R_i", "wing_U_R_o", +1), ("wing_U_L_i", "wing_U_L_o", -1),
         ("wing_L_R_i", "wing_L_R_o", +1), ("wing_L_L_i", "wing_L_L_o", -1)]

for fold in (0.0, 1.0):
    print("=" * 78)
    print("fold = %.0f  (%s)" % (fold, "展开" if fold == 0 else "收拢"))
    print("=" * 78)
    boxes = {}
    for ni, no, sgn in WINGS:
        ri = fold * 90.0 * sgn
        ro = fold * 168.0 * sgn
        pi, po = parts[ni]["pivot"], parts[no]["pivot"]
        # 外段折回后 Y 向分层（右外 +18 / 左外 +36；下翼对称向下）
        lift = LIFT[no] * fold
        off = (po[0] - pi[0], po[1] - pi[1] + lift, po[2] - pi[2])
        vi = xform(parts[ni]["verts"], pi, ri)
        vo = xform(parts[no]["verts"], po, ro, pi, ri, off)
        boxes[ni] = show(ni, vi)
        boxes[no] = show(no, vo)

    # 3D 干涉检查（Z 与 Y 同时重叠才算穿透）
    print("  -- 3D 干涉检查（Z∩Y 同时重叠=穿透）--")
    names = [n for pair in WINGS for n in pair[:2]]
    bad = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            za, zb = boxes[a][2], boxes[b][2]
            ya, yb = boxes[a][1], boxes[b][1]
            ovz = min(za[1], zb[1]) - max(za[0], zb[0])
            ovy = min(ya[1], yb[1]) - max(ya[0], yb[0])
            if ovz > 1.0 and ovy > 1.0:
                bad += 1
                print("     !! %-11s × %-11s  Z重叠%.0f  Y重叠%.0f"
                      % (a, b, ovz, ovy))
    print("     结果：%s" % ("无穿透 OK" if bad == 0 else "%d 对穿透" % bad))

    # 与桨臂区（X 1425-1465，径向 r34-245）轴向间隙
    allx = [b[0] for b in boxes.values()]
    xmax = max(b[1] for b in allx)
    print("     收拢后最大 X = %.0f mm，距桨臂起点 1425 间隙 = %.0f mm  %s"
          % (xmax, 1425 - xmax, "OK" if 1425 - xmax > 0 else "<<< 撞桨"))
    zmax = max(abs(b[2][0]) for b in boxes.values())
    zmax = max(zmax, max(abs(b[2][1]) for b in boxes.values()))
    print("     收拢后最大半宽 |Z| = %.0f mm（横向包络 ⌀%.0f mm）" % (zmax, zmax * 2))
    print()
