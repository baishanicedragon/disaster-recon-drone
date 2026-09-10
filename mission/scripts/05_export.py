#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05_export.py —— 导出航线（QGC WPL 110）与 ArduPilot 地形文件

流水线位置：[mission/README.md](../README.md) 第 7~8 步
  净空 → **导出** → 生成 .terrain 放 SD 卡

产物：
  1) `*.waypoints` —— QGroundControl **WPL 110** 文本格式，Mission Planner / QGC 都能读；
  2) `.terrain` —— ArduPilot 地形跟随文件（**不由本脚本直接生成**，见下）。

依赖：
  numpy pip install numpy
  （.terrain 生成依赖 MAVProxy 或 Mission Planner，见脚本末尾说明）

用法：
  python 05_export.py route.geojson clearance.json out.waypoints

⚠ 参考实现，**未实跑**。
⚠ 导出后**必须**在 Mission Planner / QGC 里再目视一遍，确认高度基准与坐标。
"""

import argparse
import json
import sys

# --- QGC WPL 110 -----------------------------------------------------------
# 每行字段（Tab 分隔）：
#   index  current  frame  command  p1  p2  p3  p4  x(lat)  y(lon)  z(alt_m)  autocontinue
# frame:  0=Absolute(AMSL)  3=Relative(AGL)  10=Terrain(地形跟随)
# command:16=NAV_WAYPOINT  22=NAV_TAKEOFF  21=NAV_LAND  19=NAV_LOITER_TIME  20=NAV_LOITER_TURNS
HEADER = "QGC WPL 110"


def wpl_line(idx: int, current: int, frame: int, cmd: int,
             p1: float, p2: float, p3: float, p4: float,
             lat: float, lon: float, alt: float, autocontinue: int = 1) -> str:
    return "\t".join([
        str(idx), str(current), str(frame), str(cmd),
        f"{p1:.6f}", f"{p2:.6f}", f"{p3:.6f}", f"{p4:.6f}",
        f"{lat:.8f}", f"{lon:.8f}", f"{alt:.2f}", str(autocontinue),
    ])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("route", help="航线 GeoJSON（03 步输出）")
    ap.add_argument("clearance", help="净空报告 JSON（04 步输出）")
    ap.add_argument("dst", help="输出 .waypoints（WPL 110）")
    ap.add_argument("--frame", type=int, default=10,
                    help="高度基准：10=Terrain(地形跟随，推荐) 0=AMSL 3=AGL")
    ap.add_argument("--loiter-sec", type=int, default=300,
                    help="目标区盘旋时长（s），LOITER=300（[docs/02](../../docs/02-需求规格与性能指标.md) 5 min）")
    args = ap.parse_args()

    with open(args.route, encoding="utf-8") as fh:
        route = json.load(fh)
    with open(args.clearance, encoding="utf-8") as fh:
        clear = json.load(fh)

    clr_by_seq = {w["seq"]: w for w in clear.get("waypoints", []) if "seq" in w}

    # ⚠ 行列 → 经纬度的换算**必须**用 DEM 的 GeoTransform。
    #    这里为示例占位：请按实际 transform 替换（同 03 步的警告）。
    print("[warn] 行列→经纬度为示例占位，请按实际 GeoTransform 实现（同 03 步）")

    lines = [HEADER]
    feats = route.get("features", [])
    for i, feat in enumerate(feats):
        col, row = feat["geometry"]["coordinates"]
        lat = row * 1e-4 + 28.0     # 占位映射
        lon = col * 1e-4 + 85.0     # 占位映射
        seq = feat["properties"].get("seq", i)
        cw = clr_by_seq.get(seq, {})
        alt = cw.get("wp_alt_m", 250.0)
        if i == 0:
            lines.append(wpl_line(0, 1, args.frame, 16, 0, 0, 0, 0, lat, lon, alt))
        else:
            lines.append(wpl_line(i, 0, args.frame, 16, 0, 0, 0, 0, lat, lon, alt))

    # 目标区盘旋（最后一个航点前插入 LOITER_TIME）
    if feats:
        col, row = feats[-1]["geometry"]["coordinates"]
        lat, lon = row * 1e-4 + 28.0, col * 1e-4 + 85.0
        lines.append(wpl_line(len(lines) - 1, 0, args.frame, 19,
                              args.loiter_sec, 0, 0, 1, lat, lon, 250.0))

    with open(args.dst, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"[ok ] 航线 → {args.dst}（{len(lines)-1} 个航点，frame={args.frame}）")

    # --- .terrain 生成说明 -------------------------------------------------
    print("""
[next] 生成 ArduPilot 地形文件（**不由本脚本生成**）：

  方式 A（MAVProxy）：
      module load terrain
      terrain generate <lat> <lon>            # 联网从 terrain.ardupilot.org 拉取
      # 离线：把 DEM 放到本地后按 MAVProxy terrain 模块文档走

  方式 B（Mission Planner）：
      飞行计划 → 右键 → "Create terrain file" / 或使用其地形工具生成 .terrain

  然后把生成的 .terrain 放进**飞控 SD 卡根目录**，并确认：
      TERRAIN_ENABLE = 1
      TERRAIN_FOLLOW = 1
      TERRAIN_MARGIN = 150        （见 firmware/ardupilot/params/20-terrain.param）

  ⚠ DEM 高程基准必须与飞控一致（AMSL），否则地形跟随会系统性偏高/偏低。
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
