# -*- coding: utf-8 -*-
"""从打包 HTML 中提取 KF/PHASES，验证任务剖面时间轴数值。"""
import re, json, math, os

BASE = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(BASE, "HDRS-1-迅鸢-v0.4-任务剖面参考动画.html"),
            encoding="utf-8").read()


def grab(name):
    m = re.search(r"const %s = \[(.*?)\n\];" % name, html, re.S)
    body = m.group(1)
    body = re.sub(r"(\w+):", r'"\1":', body)          # key 加引号
    body = body.replace("'", '"')                     # 单引号 → 双引号
    body = re.sub(r",(\s*[\]}])", r"\1", body)        # 去尾逗号
    return json.loads("[" + body + "]")


KF = grab("KF")
PHASES = grab("PHASES")
EASE = {'lin': lambda u: u, 'smooth': lambda u: u*u*(3-2*u), 'acc': lambda u: u*u}

T_END = float(re.search(r"const T_END = ([\d.]+)", html).group(1))


def sample(t):
    t = max(0.0, min(T_END, t))
    i = 0
    while i < len(KF)-2 and t > KF[i+1]['t']:
        i += 1
    a, b = KF[i], KF[i+1]
    u = (t - a['t']) / (b['t'] - a['t']) if b['t'] != a['t'] else 0
    e = EASE[a.get('e', 'lin')](u)
    return {k: a[k] + (b[k]-a[k])*e for k in ('y', 'x', 'rz', 'fold', 'spin', 'thr', 'el')}


def phase(t):
    for p in PHASES:
        if p['t0'] <= t < p['t1']:
            return p
    return PHASES[-1]


print("T_END = %.1f s  |  阶段 %d 个  |  关键帧 %d 个" % (T_END, len(PHASES), len(KF)))
print("=" * 84)
print("%-5s %-6s %-22s %7s %8s %7s %6s %5s %5s"
      % ("t(s)", "ID", "阶段", "H(m)", "X(m)", "俯仰", "翼", "桨", "舵"))
checks = []
for t in [0, 3, 5, 6, 16, 27, 28, 32, 35, 36, 38, 39.5, 41, 42, 44, 50, 56, 63, 66, 70, 72]:
    s = sample(t)
    p = phase(t)
    print("%-5.1f %-6s %-22s %7.1f %8.0f %7.0f° %6s %5s %5.0f°"
          % (t, p['id'], p['n'][:20], s['y'], s['x'], s['rz'],
             "收拢" if s['fold'] > .5 else ("展开" if s['fold'] < .05 else "%.0f%%" % (100*(1-s['fold']))),
             "转" if s['spin'] > .5 else "停", s['el']))
print("=" * 84)

# ---- 硬性判据 ----
def ck(name, cond, detail=""):
    checks.append((name, cond, detail))


s150 = max((sample(t)['y'] for t in [i*0.1 for i in range(int(T_END*10)+1)]), default=0)
ck("倒拖顶点达到 150 m", abs(s150 - 150) < 1.5, "峰值 %.1f m" % s150)
ck("关机时翼仍收拢", sample(28)['fold'] > .99, "fold=%.2f" % sample(28)['fold'])
ck("关机后 0.5 s 内桨停转", sample(28)['spin'] < .01, "spin=%.2f" % sample(28)['spin'])
ck("撑开发生在 150 m 以下", sample(36.5)['y'] < 130, "H=%.1f m" % sample(36.5)['y'])
ck("撑开后fold=0（完全展开）", sample(37)['fold'] < .01, "fold=%.3f" % sample(37)['fold'])
ck("拉平结束俯仰=0（水平）", abs(sample(42)['rz']) < .5, "rz=%.1f°" % sample(42)['rz'])
ck("拉平掉高 50~60 m", 45 < (sample(37)['y'] - sample(42)['y']) < 62,
   "掉高 %.1f m" % (sample(37)['y'] - sample(42)['y']))
ck("改平后净高 ≥ 55 m", sample(42)['y'] > 55, "净高 %.1f m" % sample(42)['y'])
ck("巡航段高度稳定 70 m", abs(sample(56)['y'] - 70) < 1, "H=%.1f" % sample(56)['y'])
ck("巡航段桨运转", sample(56)['spin'] > .99, "spin=%.2f" % sample(56)['spin'])
ck("末端触地 y=0", abs(sample(72)['y']) < .5, "y=%.2f" % sample(72)['y'])
ck("末端机头略上仰", sample(72)['rz'] < -5, "rz=%.1f°" % sample(72)['rz'])
ck("航迹单向前进（X 单调递减，无倒退）",
   all(sample(i*0.2)['x'] >= sample((i+1)*0.2)['x'] - 1e-6 for i in range(int(T_END/0.2))),
   "")
ck("阶段覆盖 0→T_END 无空隙",
   PHASES[0]['t0'] == 0 and abs(PHASES[-1]['t1'] - T_END) < .01 and
   all(abs(PHASES[i]['t1'] - PHASES[i+1]['t0']) < .01 for i in range(len(PHASES)-1)), "")

ok = True
for n, c, d in checks:
    print(("  [OK]   " if c else "  [FAIL] ") + n + ("  · " + d if d else ""))
    ok = ok and c
print("=" * 84)
print("结论：%s" % ("全部通过" if ok else "存在 FAIL，需修正"))
