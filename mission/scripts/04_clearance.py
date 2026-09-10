#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04_clearance.py —— 走廊净空计算与检查（**全流程最容易搞错的一步**）

流水线位置：[mission/README.md](../README.md) 第 5 步
  航路 → **净空** → 导出

❌ 错误做法（只算正下方）：
    clearance = wp_alt - dem[wp_row, wp_col]
    飞机不会精确走在谷底线上：侧风、航位误差、转弯外扩都会让它偏离。

✅ 正确做法（算走廊内最高地形）：
    clearance = wp_alt - dem_buffer_max(wp, radius_m=500)
    走廊 = 航路点左右各 500 m 的缓冲带（[docs/08](../../docs/08-自主导航与山区穿越.md)）

> **按走廊最大值算是唯一保守的做法。**

实现：用 `scipy.ndimage.maximum_filter` 对 DEM 做半径 R 的滑动最大值，
      再逐航点查表 —— 比逐点画缓冲区快两个数量级。

依赖：
  numpy  pip install numpy
  scipy  pip install scipy
  rasterio pip install rasterio

用法：
  python 04_clearance.py dem_filled.tif route.geojson clearance.json --radius-m 500 --min-clear-m 150

⚠ 参考实现，**未实跑**。
"""

import argparse
import json
import sys

import numpy as np
from scipy.ndimage import maximum_filter


def buffer_max_dem(dem: np.ndarray, nodata: float, pix_m: float, radius_m: float) -> np.ndarray:
    """对 DEM 做半径 radius_m 的滑动最大值（= 每个格网邻域内的最高地形）。"""
    r_cells = max(1, int(round(radius_m / pix_m)))
    size = 2 * r_cells + 1
    print(f"[info] 走廊半径 {radius_m} m ≈ {r_cells} 格网 → 滤波窗口 {size}×{size}")

    valid = dem != nodata
    work = np.where(valid, dem, -np.inf)
    buf = maximum_filter(work, size=size, mode="nearest")
    buf = np.where(valid, buf, nodata)
    return buf


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dem", help="填洼后 DEM（01 步输出，UTM）")
    ap.add_argument("route", help="航线 GeoJSON（03 步输出）")
    ap.add_argument("dst", help="输出净空报告 JSON")
    ap.add_argument("--radius-m", type=float, default=500.0, help="走廊缓冲半径（m）")
    ap.add_argument("--min-clear-m", type=float, default=150.0, help="最小净空（m），M-01")
    ap.add_argument("--cruise-alt-m", type=float, default=250.0, help="巡航相对高度基准（m AGL）")
    args = ap.parse_args()

    # 读 DEM
    try:
        import rasterio

        with rasterio.open(args.dem) as src:
            dem = src.read(1).astype(np.float32)
            nodata = src.nodata if src.nodata is not None else -9999.0
            pix_m = abs(src.transform.a)
            transform = src.transform
    except ImportError:
        from osgeo import gdal

        ds = gdal.Open(args.dem)
        dem = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
        nodata = ds.GetRasterBand(1).GetNoDataValue() or -9999.0
        pix_m = abs(ds.GetGeoTransform()[1])
        transform = ds.GetGeoTransform()

    buf = buffer_max_dem(dem, nodata, pix_m, args.radius_m)

    with open(args.route, encoding="utf-8") as fh:
        route = json.load(fh)

    results, worst = [], float("inf")
    for feat in route.get("features", []):
        col, row = feat["geometry"]["coordinates"]
        r, c = int(round(row)), int(round(col))
        if not (0 <= r < dem.shape[0] and 0 <= c < dem.shape[1]):
            results.append({"seq": feat["properties"].get("seq"), "error": "out_of_raster"})
            continue

        top_corridor = float(buf[r, c])          # ✅ 走廊内最高地形
        below = float(dem[r, c])                 # 正下方（仅作对照）
        wp_alt = below + args.cruise_alt_m       # 按谷底 + 巡航高度设定航路点高度
        clearance = wp_alt - top_corridor

        worst = min(worst, clearance)
        results.append({
            "seq": feat["properties"].get("seq"),
            "row": r, "col": c,
            "dem_below_m": round(below, 1),
            "top_in_corridor_m": round(top_corridor, 1),
            "wp_alt_m": round(wp_alt, 1),
            "clearance_m": round(clearance, 1),
            "ok": clearance >= args.min_clear_m,
        })

    report = {
        "radius_m": args.radius_m,
        "min_clear_m": args.min_clear_m,
        "cruise_alt_m": args.cruise_alt_m,
        "worst_clearance_m": None if worst == float("inf") else round(worst, 1),
        "waypoints": results,
    }
    with open(args.dst, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    n_bad = sum(1 for x in results if x.get("ok") is False)
    print(f"[ok ] 净空报告 → {args.dst}")
    print(f"[chk] 最差净空 {report['worst_clearance_m']} m；不合格航点 {n_bad} 个（阈值 {args.min_clear_m} m）")
    if n_bad:
        print("[warn] 存在净空不足航点：抬升该段高度或改走更宽的谷（不要强行飞）")

    print("[next] 05_export.py：导出 .waypoints / QGC WPL 110 + ArduPilot .terrain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
