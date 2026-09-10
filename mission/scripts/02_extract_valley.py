#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_extract_valley.py —— 流向 + 汇流累积 + 谷网提取

流水线位置：[mission/README.md](../README.md) 第 3 步
  填洼 → **谷网** → 航路 → 净空 → 导出

原理：
  1) D8 流向：每个格网指向最陡下降邻居；
  2) 汇流累积：统计每格网上游汇入的格网数 → 数值大即为谷底/河道；
  3) 按阈值二值化 → 谷底栅格 → 建成图（供 03 求最短路）。

依赖：
  richdem  pip install richdem        （FlowDirection / FlowAccumulation）
  networkx pip install networkx       （建图，供下一步最短路）
  numpy    pip install numpy
  rasterio pip install rasterio       （读写与地理参考）

用法：
  python 02_extract_valley.py dem_filled.tif valley.gpickle --threshold 500
  python 02_extract_valley.py dem_filled.tif valley.gpickle --threshold 500 --geojson valley.geojson

阈值怎么定：
  threshold ≈ 汇水面积 / 格网面积。30 m DEM 下，
  threshold=500 ≈ 上游汇水 0.45 km²，适合**主谷**；
  要保留支谷就调小（100~300），只要主谷就调大（1000+）。
  ⚠ 必须目视检查：太大会漏掉可用的窄谷，太小会生成大量走不通的支线。

⚠ 参考实现，**未实跑**。
"""

import argparse
import sys

import numpy as np
import networkx as nx


def accumulate(dem: np.ndarray, nodata: float, method: str = "D8") -> np.ndarray:
    """D8 流向 + 汇流累积。"""
    import richdem as rd  # pip install richdem

    rda = rd.rdarray(dem, no_data=nodata)
    # 未填洼会在这里暴露：流向会指向洼地形成内流
    flow_dir = rd.FlowDirection(rda, method=method)
    acc = rd.FlowAccumulation(flow_dir, method=method)
    return np.asarray(acc)


def build_graph(acc: np.ndarray, dem: np.ndarray, threshold: float,
                transform, nodata: float) -> nx.Graph:
    """
    把「汇流累积 ≥ threshold」的格网建成无向图。
    节点 = 谷底格网；边 = 8 邻域相邻；边属性 = 长度(m)、坡度、高程。
    """
    rows, cols = acc.shape
    pix_w = abs(transform[0]) if hasattr(transform, "__len__") else abs(transform.a)
    pix_h = abs(transform[4]) if hasattr(transform, "__len__") else abs(transform.e)

    mask = (acc >= threshold) & (dem != nodata)
    idx = -np.ones((rows, cols), dtype=int)
    coords = np.argwhere(mask)
    for n, (r, c) in enumerate(coords):
        idx[r, c] = n

    G = nx.Graph()
    for n, (r, c) in enumerate(coords):
        G.add_node(n, row=int(r), col=int(c), elev=float(dem[r, c]), acc=float(acc[r, c]))

    for r, c in coords:
        for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
            rr, cc = int(r + dr), int(c + dc)
            if 0 <= rr < rows and 0 <= cc < cols and idx[rr, cc] >= 0:
                u, v = idx[r, c], idx[rr, cc]
                length = float(np.hypot(dr * pix_h, dc * pix_w))
                slope = abs(float(dem[rr, cc]) - float(dem[r, c])) / max(length, 1e-6)
                G.add_edge(int(u), int(v), length=length, slope=slope)

    print(f"[info] 谷底格网 {G.number_of_nodes()} 个，边 {G.number_of_edges()} 条")
    if G.number_of_nodes() == 0:
        print("[warn] 没有格网超过阈值 —— 请把 --threshold 调小，或检查填洼结果")
    return G


def to_geojson(G: nx.Graph, transform, path: str) -> None:
    """谷网导出 GeoJSON（便于 QGIS 目视复核）。"""
    import json

    a, b, c0, d, e, f = (transform[:6] if hasattr(transform, "__len__")
                         else (transform.a, transform.b, transform.c,
                               transform.d, transform.e, transform.f))
    feats = []
    for u, v, data in G.edges(data=True):
        ru, cu = G.nodes[u]["row"], G.nodes[u]["col"]
        rv, cv = G.nodes[v]["row"], G.nodes[v]["col"]
        x1, y1 = a * cu + b * ru + c0, d * cu + e * ru + f
        x2, y2 = a * cv + b * rv + c0, d * cv + e * rv + f
        feats.append({
            "type": "Feature",
            "properties": {"length_m": round(data["length"], 1), "slope": round(data["slope"], 3)},
            "geometry": {"type": "LineString", "coordinates": [[x1, y1], [x2, y2]]},
        })
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"type": "FeatureCollection", "features": feats}, fh, ensure_ascii=False)
    print(f"[ok ] 谷网 GeoJSON → {path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="填洼后的 DEM（01 步输出）")
    ap.add_argument("dst", help="输出谷网图（.gpickle）")
    ap.add_argument("--threshold", type=float, default=500.0, help="汇流累积阈值（格网数）")
    ap.add_argument("--geojson", default=None, help="同时导出 GeoJSON 供 QGIS 目视")
    args = ap.parse_args()

    # 读 DEM（与 01 一致的读法）
    try:
        import rasterio

        with rasterio.open(args.src) as src:
            dem = src.read(1).astype(np.float32)
            nodata = src.nodata if src.nodata is not None else -9999.0
            transform = src.transform
    except ImportError:
        from osgeo import gdal

        ds = gdal.Open(args.src)
        dem = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
        nodata = ds.GetRasterBand(1).GetNoDataValue() or -9999.0
        transform = ds.GetGeoTransform()

    acc = accumulate(dem, nodata)
    G = build_graph(acc, dem, args.threshold, transform, nodata)

    # 只保留最大连通分量：避免最短路掉进孤立支谷
    if G.number_of_nodes():
        largest = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest).copy()
        print(f"[info] 取最大连通分量：{G.number_of_nodes()} 节点")

    import pickle

    with open(args.dst, "wb") as fh:
        pickle.dump(G, fh)
    print(f"[ok ] 谷网图 → {args.dst}")

    if args.geojson:
        to_geojson(G, transform, args.geojson)

    print("[next] 03_route.py：在谷网上求起飞点→目标点的最短路")
    return 0


if __name__ == "__main__":
    sys.exit(main())
