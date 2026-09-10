# dem · DEM 数据源与获取

> **DEM 本身不入库**——体积大、许可各异、且需按任务区裁剪。
> 本目录只放**数据源清单与获取脚本**；使用时把 GeoTIFF 落到本目录（已由 `.gitignore` 排除 `*.tif`）。

---

## 1. 源清单（与 [docs/16 源注册表](../../docs/16-安卓APP架构与素材库.md) 一致）

| 源 ID | 分辨率 | 覆盖 | 获取方式 | 许可 / 备注 |
|:---|---:|:---|:---|:---|
| `COP_DEM30` | 30 m | 全球 | Copernicus Open Access（API / AWS Open Data） | 开放，**需署名**；垂直精度 ~4 m |
| `ALOS_AW3D` | 30 m | 全球 | JAXA 注册下载 | 开放，需注册 |
| `SRTM30` | 30 m | 全球（±60°） | USGS EarthExplorer / LP DAAC | 开放 |
| `GS_CLOUD` | 30 m / 高分 | 中国 | 地理空间数据云 gscloud.cn | 国内；资源三号 / 高分系列 |
| `OPEN_TOPO` | 1 ~ 30 m | 全球（部分区 1 m） | OpenTopography API | 开放，需 API key |
| `GF_DISASTER` | 0.5 ~ 2 m | 中国 | 高分专项应急通道 | **需申请**；窄谷最实用 |

> **选型建议**：预规划用 `COP_DEM30` + `GS_CLOUD` 互补；窄谷/关键段争取 `GF_DISASTER` 或 `OPEN_TOPO` 高分。
> **灾时影像优先** `SENTINEL2`（5 天重访，时效）+ `GF_DISASTER`（精度）。

---

## 2. 分辨率够不够？

| 用途 | 需求 | 说明 |
|:---|:---|:---|
| 走廊净空计算 | 30 m 够 | [docs/08](../../docs/08-自主导航与山区穿越.md)：走廊 500 m、净空 150 m |
| 谷底线提取 | 30 m 勉强，高分更好 | 窄谷（谷底宽 < 200 m）建议 ≤ 12 m |
| 地形跟随 .terrain | 30 m 够 | ArduPilot 地形文件有自身抽稀 |

> ⚠ **DEM 空洞**：空洞区在净空计算里**加倍处理**（检查项 M-07）。
> 宁可把整段判为"净空不足"绕飞，也不要在空洞上赌。

---

## 3. 坐标与格式

| 项 | 值 |
|:---|:---|
| 水平基准 | **WGS84（EPSG:4326）** |
| 投影 | 计算时转 **UTM**（按任务区带号），输出航线再转回经纬度 |
| 垂直基准 | **EGM96 大地水准面高**；注意 ArduPilot 地形文件用 **AMSL**，与 DEM 高程基准必须一致 |
| 格式 | GeoTIFF（浮点/整型均可，需带 `.tfw` 或内嵌地理参考） |

> ⚠ **基准不一致是最常见的坑**：DEM 高程是相对大地水准面还是椭球面，
> 直接决定"气压高 − DEM 高程"算出的 AGL 对不对（[docs/18 18.4](../../docs/18-软件实现示例代码-机载固件.md)）。

---

## 4. 使用流程

```bash
# 1) 下载（见 download.sh）
./download.sh --source COP_DEM30 --bbox 85.0,28.0,85.6,28.4 --out ./dem_raw.tif

# 2) 裁剪到任务区（±2 km 缓冲）并转 UTM
gdalwarp -t_srs EPSG:32645 -te ... -tr 30 30 dem_raw.tif dem_utm.tif

# 3) 交给 scripts/01_fill_dem.py 做填洼
python ../scripts/01_fill_dem.py dem_utm.tif dem_filled.tif
```

---

## 5. 合规

| 项 | 说明 |
|:---|:---|
| 署名 | Copernicus / ALOS / SRTM 均需**署名**；商用前核对各自最新条款 |
| 国产高分 | 需申请，按批准用途使用 |
| 坐标 | 本仓库**只放样例/虚构坐标**，不放真实敏感坐标（[mission README](../README.md)） |
| 边境 | 航线可能涉及边境地区，**必须取得全部飞行许可** |

---

## 相关

- [../README.md](../README.md) · 完整流程与依赖
- [../scripts/](../scripts/) · 填洼 / 谷网 / 航路 / 净空 / 导出
- [../../docs/08-自主导航与山区穿越.md](../../docs/08-自主导航与山区穿越.md)
