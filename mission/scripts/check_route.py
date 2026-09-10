#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_route.py —— 航线自动检查（M-01 ~ M-07）

流水线位置：[mission/README.md](../README.md) 第 5 步 / 导出前
  自动检查 → 不通过就**不许导出**，人工复核后放行。

检查项（[mission/README.md](../README.md)）：
  M-01 最小净空            ≥ 150 m
  M-02 段间坡度            ≤ 8°
  M-03 3 g 转弯半径 vs 谷宽 ≤ 谷宽 / 3
  M-04 备降点密度          每 8~10 km 一个
  M-05 与已知通行走廊一致性  尽量贴合（便于地面取回）
  M-06 飞越建筑/人口        最小化
  M-07 DEM 空洞            无；有空洞处净空加倍

依赖：
  numpy pip install numpy

用法：
  python check_route.py route.geojson clearance.json --valley-width-m 150 --report report.md
  echo $?     # 0=通过  1=有 FAIL

⚠ 参考实现，**未实跑**。
⚠ M-05 / M-06 需要外部数据（通行走廊、建筑/人口栅格），本脚本只给**接口占位**并标记 SKIP。
"""

import argparse
import json
import math
import sys

import numpy as np

MIN_CLEARANCE_M = 150.0    # M-01
MAX_SEG_SLOPE_DEG = 8.0    # M-02
TURN_G = 3.0               # M-03
CRUISE_V = 23.0            # m/s（[docs/03](../../docs/03-总体方案与气动布局.md) 盘旋速度）
LANDING_SPACING_KM = (8.0, 10.0)   # M-04


def turn_radius_m(v: float, g_load: float) -> float:
    """协调转弯半径：R = V² / (g·sqrt(n²−1))"""
    return v ** 2 / (9.81 * math.sqrt(max(g_load ** 2 - 1.0, 1e-6)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("route", help="航线 GeoJSON（03 步输出）")
    ap.add_argument("clearance", help="净空报告 JSON（04 步输出）")
    ap.add_argument("--valley-width-m", type=float, default=150.0, help="典型谷宽（m），M-03")
    ap.add_argument("--report", default=None, help="输出 Markdown 报告")
    args = ap.parse_args()

    with open(args.route, encoding="utf-8") as fh:
        route = json.load(fh)
    with open(args.clearance, encoding="utf-8") as fh:
        clear = json.load(fh)

    wps = clear.get("waypoints", [])
    results = []

    # ---- M-01 最小净空 ----
    bad = [w for w in wps if w.get("clearance_m") is not None and w["clearance_m"] < MIN_CLEARANCE_M]
    results.append(("M-01", "最小净空 ≥ 150 m",
                    "PASS" if not bad else "FAIL",
                    f"最差 {clear.get('worst_clearance_m')} m；不足 {len(bad)} 点"))

    # ---- M-02 段间坡度 ----
    worst_slope = 0.0
    for i in range(len(wps) - 1):
        a, b = wps[i], wps[i + 1]
        if a.get("wp_alt_m") is None or b.get("wp_alt_m") is None:
            continue
        dz = abs(b["wp_alt_m"] - a["wp_alt_m"])
        dx = math.hypot(b.get("col", 0) - a.get("col", 0), b.get("row", 0) - a.get("row", 0))
        if dx > 0:
            worst_slope = max(worst_slope, math.degrees(math.atan2(dz, dx)))
    results.append(("M-02", "段间坡度 ≤ 8°",
                    "PASS" if worst_slope <= MAX_SEG_SLOPE_DEG else "FAIL",
                    f"最陡 {worst_slope:.1f}°"))

    # ---- M-03 3 g 转弯半径 ----
    r_turn = turn_radius_m(CRUISE_V, TURN_G)
    limit = args.valley_width_m / 3.0
    results.append(("M-03", f"3 g 转弯半径 ≤ 谷宽/3（{limit:.0f} m）",
                    "PASS" if r_turn <= limit else "FAIL",
                    f"R = {r_turn:.1f} m @ {CRUISE_V} m/s"))

    # ---- M-04 备降点密度 ----
    total_km = route.get("properties", {}).get("total_len_km", 0.0)
    need = math.ceil(total_km / LANDING_SPACING_KM[1]) if total_km else 1
    results.append(("M-04", "备降点每 8~10 km 一个",
                    "TODO", f"全长 {total_km:.1f} km → 至少 {need} 个备降点（**需人工标定点位**）"))

    # ---- M-05 通行走廊一致性 ----
    results.append(("M-05", "与已知通行走廊一致性", "SKIP",
                    "需外部路网/走廊数据，接口占位（便于地面取回）"))

    # ---- M-06 飞越建筑/人口最小化 ----
    results.append(("M-06", "飞越建筑/人口最小化", "SKIP",
                    "需建筑/人口栅格，接口占位"))

    # ---- M-07 DEM 空洞 ----
    holes = [w for w in wps if w.get("error") == "out_of_raster"]
    results.append(("M-07", "DEM 空洞：无；有空洞处净空加倍",
                    "PASS" if not holes else "FAIL",
                    f"越界/空洞航点 {len(holes)} 个"))

    # ---- 输出 ----
    n_fail = sum(1 for r in results if r[2] == "FAIL")
    lines = ["# 航线自动检查报告", "",
             f"- 航线：`{args.route}` / 净空：`{args.clearance}`",
             f"- 全长：{total_km:.2f} km", "",
             "| # | 检查项 | 结果 | 说明 |", "|:--|:---|:---:|:---|"]
    for code, name, verdict, note in results:
        lines.append(f"| {code} | {name} | **{verdict}** | {note} |")
    lines += ["", f"**结论：{'❌ 存在 FAIL，禁止导出' if n_fail else '✅ 自动检查通过（仍需人工复核）'}**",
              "", "> 自动检查通过 ≠ 可以飞。必须再做 QGIS 目视 + 卫星影像叠加复核（流程第 6 步）。"]

    text = "\n".join(lines)
    print(text)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"\n[ok ] 报告 → {args.report}")

    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
