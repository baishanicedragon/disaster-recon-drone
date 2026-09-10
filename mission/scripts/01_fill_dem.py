#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01_fill_dem.py —— DEM 填洼（priority-flood）

流水线位置：[mission/README.md](../README.md) 第 2 步
  下载 DEM → **填洼** → 谷网 → 航路 → 净空 → 导出

为什么要填洼：
  DEM 里的伪洼地（sink）会让 D8 流向算不出连续水流，**谷底线直接断掉**。
  真实洼地（冰湖、堰塞塘）在本任务里也是要**绕开**的，填了更保守。

依赖（选一条路线即可）：
  路线 A（推荐）：richdem      pip install richdem
  路线 B：        whitebox     pip install whitebox-workflows   （或 WhiteboxTools 独立二进制）
  路线 C：        scipy 兜底    pip install scipy numpy          （纯形态学，效果差一些）

用法：
  python 01_fill_dem.py dem_utm.tif dem_filled.tif
  python 01_fill_dem.py dem_utm.tif dem_filled.tif --engine richdem

⚠ 参考实现，**未实跑**。参数需按 DEM 分辨率与地形起伏实测调整。
"""

import argparse
import sys

import numpy as np


def fill_richdem(dem: np.ndarray, nodata: float) -> np.ndarray:
    """路线 A：richdem 的 priority-flood（Barnes 2014）"""
    import richdem as rd  # pip install richdem

    rda = rd.rdarray(dem, no_data=nodata)
    rd.FillDepressions(rda, epsilon=False, in_place=True)  # epsilon=True 加极小梯度，避免平湖
    return np.asarray(rda)


def fill_whitebox(dem: np.ndarray, nodata: float) -> np.ndarray:
    """路线 B：WhiteboxTools 的 FillDepressions（Wang & Liu）"""
    import whitebox_workflows as wbw  # pip install whitebox-workflows

    wbe = wbw.WbEnvironment()
    arr = wbe.new_raster(dem, no_data=nodata)
    filled = wbe.fill_depressions(arr, fix_flats=True, flat_increment=None)
    return np.asarray(filled)


def fill_scipy(dem: np.ndarray, nodata: float) -> np.ndarray:
    """
    路线 C：scipy 兜底（形态学重建）
    原理：用「原始 DEM + 极小量」作为种子，对「原始 DEM」做灰度形态学重建，
          等价于把洼地填到溢出口高度。效果不如 priority-flood，但零重依赖。
    """
    from scipy.ndimage import grey_reconstruction

    valid = dem != nodata
    if not valid.all():
        # NoData 先填成极大值，避免影响重建，最后再还原
        dem_work = np.where(valid, dem, np.nanmax(dem[valid]))
    else:
        dem_work = dem.copy()

    seed = dem_work - 1e-3
    filled = grey_reconstruction(seed, dem_work, method="dilation")
    filled = np.where(valid, filled, nodata)
    return filled


ENGINES = {"richdem": fill_richdem, "whitebox": fill_whitebox, "scipy": fill_scipy}


def read_geotiff(path: str):
    """读 GeoTIFF，返回 (数组, profile)。优先 rasterio，退化到 GDAL。"""
    try:
        import rasterio  # pip install rasterio
    except ImportError:
        from osgeo import gdal  # pip install gdal

        ds = gdal.Open(path)
        if ds is None:
            raise SystemExit(f"[err] 无法打开 {path}")
        arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
        nodata = ds.GetRasterBand(1).GetNoDataValue()
        return arr, (nodata if nodata is not None else -9999.0), ds.GetGeoTransform(), ds.GetProjection()

    with rasterio.open(path) as src:
        arr = src.read(1).astype(np.float32)
        return arr, (src.nodata if src.nodata is not None else -9999.0), src.transform, src.crs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="输入 DEM（GeoTIFF，建议已转 UTM）")
    ap.add_argument("dst", help="输出填洼后 DEM")
    ap.add_argument("--engine", default="richdem", choices=list(ENGINES))
    args = ap.parse_args()

    dem, nodata, transform, crs = read_geotiff(args.src)
    print(f"[in ] {args.src}  shape={dem.shape}  nodata={nodata}")

    filled = ENGINES[args.engine](dem, nodata)

    # 自检：填洼后应「无内流洼地」（每个非边缘格网至少有一个更低或等高的邻居可出流）
    diff = filled - dem
    print(f"[chk] 填洼量 max={np.nanmax(diff):.2f} m  平均={np.nanmean(diff):.3f} m")
    if np.nanmax(diff) > 200:
        print("[warn] 存在 >200 m 的填洼区：多半是 DEM 空洞/异常值，请回 dem/ 检查 M-07")

    # 写出（保持原地理参考）
    try:
        import rasterio

        prof = {
            "driver": "GTiff", "height": filled.shape[0], "width": filled.shape[1],
            "count": 1, "dtype": "float32", "crs": crs, "transform": transform,
            "nodata": nodata, "compress": "lzw",
        }
        with rasterio.open(args.dst, "w", **prof) as dst:
            dst.write(filled.astype(np.float32), 1)
    except ImportError:
        from osgeo import gdal

        drv = gdal.GetDriverByName("GTiff")
        ds = drv.Create(args.dst, filled.shape[1], filled.shape[0], 1, gdal.GDT_Float32)
        ds.SetGeoTransform(transform)
        ds.SetProjection(crs)
        ds.GetRasterBand(1).WriteArray(filled)
        ds.GetRasterBand(1).SetNoDataValue(nodata)
        ds.FlushCache()

    print(f"[ok ] 写出 {args.dst} → 下一步：02_extract_valley.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
