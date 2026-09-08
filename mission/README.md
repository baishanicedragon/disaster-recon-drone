# mission/ · 航路规划与任务准备

> **核心原则：在飞之前就把 90 % 的决策做完。**
> 峡谷里没有"绕一圈看看"的余地，实时避障反应时间不足（见 [docs/08](../docs/08-自主导航与山区穿越.md)）。

---

## 流程

```
1. 下载 DEM（GeoTIFF）
      ↓
2. 填洼 + 流向 + 汇流提取 → 谷网
      ↓
3. 起飞点 → 目标点，在谷网上求最短路
      ↓
4. 重采样为航路点，每点计算「走廊内最高地形 + 净空 150 m」
      ↓
5. 自动检查（净空 / 坡度 / 转弯半径 / 备降点）
      ↓
6. 人工复核（QGIS 目视 + 卫星影像叠加）
      ↓
7. 导出 .waypoints / QGC WPL 110
      ↓
8. 生成 ArduPilot 地形文件（.terrain）放进飞控 SD 卡
```

---

## 目录结构（规划）

```
mission/
├── README.md              ← 本文件
├── dem/
│   ├── README.md          ← DEM 数据源与获取方式（**DEM 本身不入库**）
│   └── download.sh        ← 下载脚本（Copernicus / ALOS / SRTM）
├── scripts/
│   ├── 01_fill_dem.py     ← 填洼（priority-flood）
│   ├── 02_extract_valley.py  ← 流向 + 汇流 + 谷网
│   ├── 03_route.py        ← 谷网最短路（Dijkstra + 坡度惩罚）
│   ├── 04_clearance.py    ← 走廊内最高地形 + 净空检查
│   ├── 05_export.py       ← 导出 waypoints / terrain 文件
│   └── check_route.py     ← 自动检查（M-01 ~ M-07）
├── examples/
│   ├── demo_waypoints.wpl ← 样例航线（非真实坐标）
│   └── demo_report.md     ← 样例检查报告
└── field/
    ├── preflight_checklist.md   ← 飞行前检查表
    └── site_survey.md           ← 回收场勘察表（**承载力/坡度/障碍**）
```

---

## 依赖

| 工具 | 用途 |
|:---|:---|
| **GDAL** | GeoTIFF 读写、投影转换、裁剪 |
| **RichDEM** / WhiteboxTools | 填洼、D8 流向、汇流累积 |
| numpy / scipy | 栅格计算 |
| networkx | 谷网最短路 |
| matplotlib / QGIS | 可视化与人工复核 |
| MAVProxy / Mission Planner | 导出地形文件与航线 |

```bash
# 示例（使用你自己的虚拟环境）
python -m venv .venv
source .venv/bin/activate
pip install gdal numpy scipy networkx matplotlib richdem
```

---

## 关键算法要点

### 净空计算（**最容易搞错的地方**）

```python
# ❌ 错误：只算正下方
clearance = wp_alt - dem[wp_row, wp_col]

# ✅ 正确：算走廊内最高地形
#  走廊 = 航路点左右各 500 m 的缓冲带
clearance = wp_alt - dem_buffer_max(wp, radius_m=500)
```

> 飞机不会精确走在谷底线上（侧风、航位误差、转弯外扩）。
> **按走廊最大值算是唯一保守的做法。**

### 谷网最短路的代价函数

```
cost(edge) = length(edge) × (1 + k_slope × |slope| + k_exposure × exposure)

  k_slope    ：惩罚陡坡（爬升耗能）
  k_exposure ：惩罚暴露段（净空低、侧风大）
```

### 自动检查（M-01 ~ M-07）

| # | 检查 | 判据 |
|:--|:---|:---|
| M-01 | 最小净空 | ≥ 150 m |
| M-02 | 段间坡度 | ≤ 8° |
| M-03 | 3 g 转弯半径 vs 谷宽 | ≤ 谷宽 / 3 |
| M-04 | 备降点密度 | 每 8~10 km 一个 |
| M-05 | 与已知通行走廊一致性 | 尽量贴合（便于地面取回） |
| M-06 | 飞越建筑/人口 | 最小化 |
| M-07 | DEM 空洞 | 无；有空洞处净空加倍 |

---

## 回收场勘察表（**必须人工填写，不能只靠算法**）

见 `field/site_survey.md`。核心六项：

| # | 判据 | 现场简易判据 |
|:--|:---|:---|
| L-01 | 承载力 30~60 kPa | **鞋跟能踩进 3~5 cm，拔出不粘鞋** |
| L-02 | 坡度 ≤ 8° | 目视基本水平 |
| L-03 | 无 > 10 cm 石块 | 目视 |
| L-04 | 长 ≥ 120 m × 宽 ≥ 30 m | 步测 / 测距 |
| L-05 | 进近 300 m 无障碍 | 目视 |
| L-06 | 无积水/流沙 | 目视 |

> **绝对禁止**：泥石流淤积区（承载力 < 15 kPa，会陷）、水泥/沥青、冻土、
> 碎石滩、水面、坡度 > 15°、密林。

---

## 数据许可与合规

| 项 | 说明 |
|:---|:---|
| DEM | Copernicus / ALOS / SRTM 均需**署名**；商用前核对各自条款 |
| 高分辨率国产 DEM | 需申请，按批准用途使用 |
| 航线 | 可能涉及边境地区，**必须取得全部飞行许可** |
| 坐标 | 本仓库**只放样例/虚构坐标**，不放真实敏感坐标 |

---

## 相关文档

- [docs/01-任务场景-吉隆灾情与设计输入.md](../docs/01-任务场景-吉隆灾情与设计输入.md)
- [docs/08-自主导航与山区穿越.md](../docs/08-自主导航与山区穿越.md)
- [docs/12-测试与验证流程.md](../docs/12-测试与验证流程.md)
