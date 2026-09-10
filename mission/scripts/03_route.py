#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03_route.py —— 谷网最短路（Dijkstra + 坡度惩罚）

流水线位置：[mission/README.md](../README.md) 第 4 步
  谷网 → **航路** → 净空 → 导出

代价函数（[mission/README.md](../README.md) 关键算法要点）：
    cost(edge) = length(edge) × (1 + k_slope × |slope| + k_exposure × exposure)

  k_slope    ：惩罚陡坡（爬升耗能）
  k_exposure ：惩罚暴露段（净空低、侧风大）

依赖：
  networkx  pip install networkx
  numpy     pip install numpy

用法：
  python 03_route.py valley.gpickle route.geojson \
      --start "28.1234,85.1234" --goal "28.2345,85.3456" \
      --k-slope 3.0 --k-exposure 2.0

⚠ 参考实现，**未实跑**。
⚠ 最短路**必须**人工复核（QGIS + 卫星影像叠加）——见 [mission/README.md](../README.md) 第 6 步。
"""

import argparse
import json
import pickle
import sys

import numpy as np
import networkx as nx


def nearest_node(G: nx.Graph, row: int, col: int) -> int:
    """把起飞点/目标点吸附到最近的谷网节点。"""
    best, best_d = None, float("inf")
    for n, d in G.nodes(data=True):
        dist = (d["row"] - row) ** 2 + (d["col"] - col) ** 2
        if dist < best_d:
            best, best_d = n, dist
    return best


def add_cost(G: nx.Graph, k_slope: float, k_exposure: float) -> None:
    """给每条边算 cost。exposure 用「节点高程相对谷网最低点的落差」粗估。"""
    elevations = [d["elev"] for _, d in G.nodes(data=True)]
    base = float(np.min(elevations)) if elevations else 0.0
    rng = float(np.max(elevations) - base) if elevations else 1.0

    for u, v, data in G.edges(data=True):
        exposure = ((G.nodes[u]["elev"] - base) + (G.nodes[v]["elev"] - base)) / 2.0 / max(rng, 1.0)
        data["exposure"] = float(exposure)
        data["cost"] = data["length"] * (1.0 + k_slope * data["slope"] + k_exposure * exposure)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("graph", help="谷网图（02 步输出的 .gpickle）")
    ap.add_argument("dst", help="输出航线 GeoJSON")
    ap.add_argument("--start", required=True, help='起飞点 "lat,lon"')
    ap.add_argument("--goal", required=True, help='目标点 "lat,lon"')
    ap.add_argument("--k-slope", type=float, default=3.0)
    ap.add_argument("--k-exposure", type=float, default=2.0)
    args = ap.parse_args()

    with open(args.graph, "rb") as fh:
        G: nx.Graph = pickle.load(fh)
    if G.number_of_nodes() == 0:
        raise SystemExit("[err] 谷网为空，请回 02 步调小 --threshold")

    add_cost(G, args.k_slope, args.k_exposure)

    # ⚠ 起点/终点是**经纬度**，需先转回谷网的行列号。
    #    这里依赖 02 步图里存的行列；工程上应保存 GeoTransform 一并序列化。
    #    示例：按图内行列范围做线性映射（**必须按实际 transform 替换**）。
    rows = [d["row"] for _, d in G.nodes(data=True)]
    cols = [d["col"] for _, d in G.nodes(data=True)]
    print(f"[warn] 经纬度→行列映射为示例占位，请按实际 GeoTransform 实现")
    s_lat, s_lon = (float(x) for x in args.start.split(","))
    g_lat, g_lon = (float(x) for x in args.goal.split(","))
    src = nearest_node(G, int(np.mean(rows)), int(np.mean(cols)))
    dst = nearest_node(G, int(np.mean(rows)), int(np.mean(cols)) + 1)
    print(f"[info] 吸附节点 src={src} dst={dst}（示例映射，需替换）")

    path = nx.dijkstra_path(G, src, dst, weight="cost")
    total_m = sum(G[path[i]][path[i + 1]]["length"] for i in range(len(path) - 1))
    print(f"[ok ] 最短路 {len(path)} 节点，地面长度 {total_m/1000:.2f} km")

    feats = [{
        "type": "Feature",
        "properties": {"seq": i, "elev": round(G.nodes[n]["elev"], 1)},
        "geometry": {"type": "Point", "coordinates": [G.nodes[n]["col"], G.nodes[n]["row"]]},
    } for i, n in enumerate(path)]

    with open(args.dst, "w", encoding="utf-8") as fh:
        json.dump({
            "type": "FeatureCollection",
            "properties": {
                "total_len_km": round(total_m / 1000, 2),
                "k_slope": args.k_slope, "k_exposure": args.k_exposure,
                "start": [s_lat, s_lon], "goal": [g_lat, g_lon],
            },
            "features": feats,
        }, fh, ensure_ascii=False, indent=2)

    print(f"[ok ] 航线 → {args.dst}")
    print("[next] 04_clearance.py：走廊内最高地形 + 净空检查（**最容易搞错的一步**）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
