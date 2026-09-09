# assets/ · 图纸、渲染与试飞素材

> ⚠ **本目录默认只包含占位说明，不存放二进制素材。**

---

## 为什么不放素材

| 原因 | 说明 |
|:---|:---|
| **体积** | 图纸、STEP、渲染图、视频会让仓库迅速膨胀，拖慢 clone |
| **许可** | 3D 模型/字体/素材常带各自许可，混入仓库有合规风险 |
| **隐私** | 试飞照片可能拍到人脸、车牌、敏感地形 |
| **伦理** | **绝不放任何灾区影像** |

**推荐做法**：用 Git LFS，或放外部存储（网盘/对象存储）后在文档里链接。

---

## 目录结构（规划）

```
assets/
├── README.md            ← 本文件
├── 3d/                  ← **v0.4 双翼 3D 参考产物**（离线单文件 HTML + OBJ，见下）
├── drawings/            ← 图纸导出（PDF / DXF / SVG）
│   ├── 01-general-arrangement.pdf
│   ├── 02-nose-energy-absorber.pdf
│   ├── 03-wing-fold-mechanism.pdf
│   └── 04-wiring-diagram.pdf
├── renders/             ← 渲染图（PNG，≤ 500 KB/张）
├── plots/               ← 计算图表（能量预算、阻力极曲线等）
└── flight/              ← 试飞素材（**绝不放入脸/车牌/灾区影像**）
```

---

## 命名约定

| 类型 | 格式 | 示例 |
|:---|:---|:---|
| 图纸 | `NN-名称.pdf` | `03-wing-fold-mechanism.pdf` |
| 渲染 | `view-<视角>-<版本>.png` | `view-side-v02.png` |
| 图表 | `fig-<编号>-<主题>.svg` | `fig-05-energy-budget.svg` |
| 试飞 | `YYYYMMDD-<地点>-<序号>.jpg` | `20260908-testfield-01.jpg` |

**所有素材都要有对应的来源说明**：
在 `assets/METADATA.md` 中登记：文件名、生成方式（CAD 导出 / 实拍 / 脚本生成）、
许可、是否含敏感信息。

---

## 生成图表的脚本

`docs/` 中的计算建议**同步提供生成脚本**（Python + matplotlib），
放在各自章节对应的 `assets/plots/` 下，便于参数改动时一键重算。

示例：

| 图 | 说明 |
|:---|:---|
| `fig-01-density-vs-altitude` | 空气密度随海拔（ISA） |
| `fig-02-drag-polar` | 阻力极曲线与升阻比 |
| `fig-03-energy-budget` | 任务能量预算堆叠图 |
| `fig-04-crush-force-stroke` | 泡沫压溃力-行程曲线 |
| `fig-05-nose-deceleration` | 迫降过载-行程曲线 |

---

## 素材许可

- CAD 导出的图纸：随硬件设计，**CERN-OHL-S v2**
- 自绘图表：**MIT**
- 实拍照片：**不放脸、不放车牌**；若必须放，先模糊处理

---

## 相关文档

- [assets/3d/README.md](./3d/README.md) ← **v0.4 双翼静态模型与 72 s 任务剖面动画**
- [docs/03-总体方案与气动布局.md](../docs/03-总体方案与气动布局.md)
- [docs/04-结构设计与材料.md](../docs/04-结构设计与材料.md)
- [docs/06-末端迫降与泡沫机头吸能.md](../docs/06-末端迫降与泡沫机头吸能.md)
- [hardware/README.md](../hardware/README.md)
